"""Durably capture Coordinator escalation notification intents.

The caller owns commit/rollback.

No email, Notification Log, enqueue, commit, SLA change,
ticket update, or assignment modification occurs here.
"""

import frappe

from telephony.data_request_arrival_outbox import _insert_if_missing
from telephony.data_request_escalation_intent import (
    plan_escalation_intents,
)
from telephony.data_request_escalation_policy import (
    evaluate_escalation,
)
from telephony.data_request_escalation_recipients import (
    resolve_coordinator_recipients,
)

SERVICE_AREA = "Data Request"


def capture_escalation_intents(ticket_name, *, now=None):
    """Persist due Coordinator intents within the caller's transaction.

    A locking read serializes this decision with ticket updates.
    The caller must end its transaction promptly.
    """

    name = str(ticket_name or "").strip()

    if not name:
        raise ValueError("Persisted HD Ticket name required")

    # Lock the authoritative ticket row before reading its
    # completion state or deciding to create notification intents.
    locked = frappe.db.sql(
        """
        SELECT name
        FROM `tabHD Ticket`
        WHERE name = %s
        FOR UPDATE
        """,
        (name,),
        as_dict=True,
    )

    if not locked:
        raise ValueError(f"HD Ticket not found: {name}")

    ticket = frappe.get_doc("HD Ticket", name)

    area = str(
        ticket.get("custom_service_area") or ""
    ).strip()

    if area != SERVICE_AREA:
        return []

    arrival = ticket.get("creation")

    if not arrival:
        raise ValueError("Ticket creation timestamp required")

    first_completed = ticket.get(
        "custom_data_request_first_completed_on"
    )

    current_time = (
        now if now is not None else frappe.utils.now_datetime()
    )

    decision = evaluate_escalation(
        service_area=area,
        arrival_at=frappe.utils.get_datetime(arrival),
        first_completed_at=(
            frappe.utils.get_datetime(first_completed)
            if first_completed
            else None
        ),
        now=frappe.utils.get_datetime(current_time),
    )

    if not decision["notification_due"]:
        return []

    recipients = resolve_coordinator_recipients(ticket)

    planned = plan_escalation_intents(
        ticket_name=name,
        recipients=recipients,
        # The resolver has already checked each user against
        # role membership, account status, email and ticket access.
        eligible_user=lambda user: True,
    )

    inserted = []

    for item in planned:
        if _insert_if_missing(item):
            inserted.append(item["name"])

    return inserted
