"""Transactional in-app delivery of Data Request notification intents.

The caller owns commit/rollback. No email is queued here.
"""

from html import escape

import frappe

from telephony.data_request_arrival_outbox import (
    AREA,
    TEAM,
    _eligible_user,
)
from telephony.data_request_escalation_recipients import (
    resolve_coordinator_recipients,
)

DOCTYPE = "TELECTRO Data Request Notification Intent"


def _require_authorized_recipient(intent, ticket):
    """Recheck event-specific authority at delivery time."""

    user = str(intent.get("recipient") or "").strip()

    if user in {"", "Administrator", "Guest"}:
        raise frappe.PermissionError("Invalid notification recipient")

    if str(ticket.get("custom_service_area") or "").strip() != AREA:
        raise ValueError("Ticket is not a Data Request")

    event = str(intent.get("event") or "").strip()

    if event == "arrival":
        if not _eligible_user(user):
            raise frappe.PermissionError(
                "Arrival recipient account is ineligible"
            )

        if str(ticket.get("agent_group") or "").strip() != TEAM:
            raise frappe.PermissionError(
                "Ticket is no longer assigned to Data Provisioning"
            )

        team = frappe.get_doc("HD Team", TEAM)

        members = {
            str(row.get("user") or "").strip()
            for row in (team.get("users") or [])
        }

        authorized = (
            user in members
            and frappe.has_permission(
                "HD Ticket",
                ptype="read",
                doc=ticket,
                user=user,
            )
        )

    elif event == "escalation":
        authorized = (
            user in resolve_coordinator_recipients(ticket)
        )

    else:
        raise ValueError(
            f"Unsupported notification event: {event}"
        )

    if not authorized:
        raise frappe.PermissionError(
            "Recipient is no longer authorized for this event"
        )

def record_in_app_alert(intent_name):
    """Record one Alert notification within the caller's transaction."""

    name = str(intent_name or "").strip()

    if not name:
        raise ValueError("Notification intent identity required")

    locked = frappe.db.sql(
        """
        SELECT name
        FROM `tabTELECTRO Data Request Notification Intent`
        WHERE name = %s
        FOR UPDATE
        """,
        (name,),
        as_dict=True,
    )

    if not locked:
        raise ValueError(f"Notification intent not found: {name}")

    intent = frappe.get_doc(DOCTYPE, name)

    state = str(intent.get("in_app_state") or "").strip()
    existing_log = str(intent.get("notification_log") or "").strip()

    if state == "Recorded":
        if not existing_log:
            raise ValueError("Recorded alert has no Notification Log")

        if not frappe.db.exists("Notification Log", existing_log):
            raise ValueError("Recorded Notification Log is missing")

        return existing_log

    if state not in {"Pending", "Failed"}:
        raise ValueError(f"Unexpected in-app state: {state}")

    if existing_log:
        raise ValueError(
            "Notification Log reference exists without Recorded state"
        )

    ticket = frappe.get_doc("HD Ticket", intent.get("ticket"))

    _require_authorized_recipient(intent, ticket)

    event = intent.get("event")

    if event == "arrival":
        action = "New Data Request"
    elif event == "escalation":
        action = "Data Request exceeded ten minutes"
    else:
        raise ValueError("Unsupported notification event")

    ticket_name = escape(str(ticket.name), quote=True)

    notification = frappe.get_doc({
        "doctype": "Notification Log",
        "type": "Alert",
        "for_user": intent.get("recipient"),
        "subject": f"{action} — HD Ticket {ticket_name}",
        "email_content": (
            f"<p>Internal operational notification for "
            f"HD Ticket {ticket_name}.</p>"
        ),
        "document_type": "HD Ticket",
        "document_name": ticket.name,
    })

    notification.insert(ignore_permissions=True)

    frappe.db.set_value(
        DOCTYPE,
        name,
        {
            "notification_log": notification.name,
            "in_app_state": "Recorded",
        },
    )

    return notification.name
