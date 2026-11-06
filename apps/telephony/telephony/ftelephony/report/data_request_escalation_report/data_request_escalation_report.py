"""Operational oversight of Data Request escalations.

Distinguishes current overdue eligibility from persisted escalation
intents and their notification states.

No notification delivery or database mutation occurs in this report.
"""

from collections import Counter
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from telephony.ftelephony.report.data_request_coordinator_war_room.data_request_coordinator_war_room import (
    _require_access,
)


SERVICE_AREA = "Data Request"
INTENT_DOCTYPE = "TELECTRO Data Request Notification Intent"
ACTIVE_STATUSES = ("Open", "Replied")
OVERDUE_MINUTES = 10
BATCH_SIZE = 200


def _columns():
    def col(label, fieldname, fieldtype="Data", width=140, **kwargs):
        return {
            "label": _(label),
            "fieldname": fieldname,
            "fieldtype": fieldtype,
            "width": width,
            **kwargs,
        }

    return [
        col("Ticket", "ticket", "Link", 110, options="HD Ticket"),
        col("Subject", "subject", width=260),
        col("Team", "agent_group", "Link", 150, options="HD Team"),
        col("Status", "status", width=100),
        col("Currently Overdue", "currently_overdue", width=145),
        col("Current Age (min)", "current_age_minutes", "Int", 135),
        col("Minutes Past Threshold", "minutes_past_threshold", "Int", 165),
        col("Escalation Captured", "escalation_captured", width=155),
        col("Escalation Intents", "escalation_intents", "Int", 140),
        col("Delivery States", "delivery_states", width=210),
        col("In-App States", "in_app_states", width=200),
        col("Email States", "email_states", width=200),
        col("First Escalation Captured", "first_escalation_on", "Datetime", 175),
        col("Last Escalation Captured", "last_escalation_on", "Datetime", 175),
        col("Created", "creation", "Datetime", 175),
        col("First Completed", "first_completed_on", "Datetime", 175),
    ]


def _candidate_names(now):
    """Union current overdue names with historically escalated names.

    These are untrusted candidates, NOT authorized report rows.
    """

    cutoff = now - timedelta(minutes=OVERDUE_MINUTES)

    current = frappe.get_list(
        "HD Ticket",
        filters={
            "custom_service_area": SERVICE_AREA,
            "status": ["in", list(ACTIVE_STATUSES)],
            "creation": ["<=", cutoff],
            "custom_data_request_first_completed_on": [
                "is",
                "not set",
            ],
        },
        fields=["name"],
        limit_page_length=0,
    )

    names = {str(row.name) for row in current}

    # Read escalation identifiers only. These are subsequently subjected
    # to Frappe list permissions and per-document read authorization.
    historical = frappe.db.sql(
        """
        SELECT DISTINCT ticket
        FROM `tabTELECTRO Data Request Notification Intent`
        WHERE event = %s
          AND ticket IS NOT NULL
          AND ticket != ''
        """,
        ("escalation",),
        as_dict=True,
    )

    names.update(str(row.ticket) for row in historical)

    return sorted(names)


def _visible_names(candidate_names):
    """Apply Frappe's HD Ticket list-level permission boundary."""

    visible = set()

    for offset in range(0, len(candidate_names), BATCH_SIZE):
        batch = candidate_names[offset:offset + BATCH_SIZE]

        matches = frappe.get_list(
            "HD Ticket",
            filters={
                "name": ["in", batch],
                "custom_service_area": SERVICE_AREA,
            },
            fields=["name"],
            limit_page_length=0,
        )

        visible.update(str(row.name) for row in matches)

    return visible


def _state_summary(intents, fieldname):
    if not intents:
        return "Not captured"

    counts = Counter(
        str(row.get(fieldname) or "Unset")
        for row in intents
    )

    return ", ".join(
        f"{state}: {counts[state]}"
        for state in sorted(counts)
    )


def _escalation_intents(ticket_name):
    """Read states for one authorized ticket, not recipient identities."""

    return frappe.get_all(
        INTENT_DOCTYPE,
        filters={
            "ticket": ticket_name,
            "event": "escalation",
        },
        fields=[
            "creation",
            "delivery_state",
            "in_app_state",
            "email_state",
        ],
        order_by="creation asc",
        limit_page_length=0,
    )


def _report_row(ticket, intents, now):
    created = get_datetime(ticket.creation)
    completed = ticket.get(
        "custom_data_request_first_completed_on"
    )

    is_active_incomplete = (
        ticket.status in ACTIVE_STATUSES
        and not completed
    )

    elapsed_seconds = max(
        0,
        int((now - created).total_seconds()),
    )

    overdue = (
        is_active_incomplete
        and elapsed_seconds >= OVERDUE_MINUTES * 60
    )

    age_minutes = (
        elapsed_seconds // 60
        if is_active_incomplete
        else None
    )

    captured_times = [
        get_datetime(row.creation)
        for row in intents
        if row.creation
    ]

    return {
        "ticket": ticket.name,
        "subject": ticket.subject,
        "agent_group": ticket.agent_group,
        "status": ticket.status,
        "currently_overdue": "YES" if overdue else "NO",
        "current_age_minutes": age_minutes,
        "minutes_past_threshold": (
            max(0, age_minutes - OVERDUE_MINUTES)
            if overdue
            else None
        ),
        "escalation_captured": "YES" if intents else "NO",
        "escalation_intents": len(intents),
        "delivery_states": _state_summary(
            intents, "delivery_state"
        ),
        "in_app_states": _state_summary(
            intents, "in_app_state"
        ),
        "email_states": _state_summary(
            intents, "email_state"
        ),
        "first_escalation_on": (
            min(captured_times) if captured_times else None
        ),
        "last_escalation_on": (
            max(captured_times) if captured_times else None
        ),
        "creation": ticket.creation,
        "first_completed_on": completed,
    }


def execute(filters=None):
    """Return permitted current overdue and historical escalated tickets."""

    user = _require_access()
    now = now_datetime()

    candidates = _candidate_names(now)
    visible = _visible_names(candidates)

    rows = []

    for ticket_name in sorted(visible):
        ticket = frappe.get_doc("HD Ticket", ticket_name)

        if not frappe.has_permission(
            "HD Ticket",
            ptype="read",
            doc=ticket,
            user=user,
        ):
            continue

        if ticket.get("custom_service_area") != SERVICE_AREA:
            continue

        intents = _escalation_intents(ticket_name)
        row = _report_row(ticket, intents, now)

        # Retain only current overdue requests or tickets with
        # actual persisted escalation evidence.
        if (
            row["currently_overdue"] != "YES"
            and not intents
        ):
            continue

        rows.append(row)

    # Prioritize overdue requests with no captured escalation.
    # Follow with other currently overdue requests, then history.
    rows.sort(
        key=lambda row: (
            0 if (
                row["currently_overdue"] == "YES"
                and row["escalation_captured"] == "NO"
            ) else (
                1 if row["currently_overdue"] == "YES" else 2
            ),
            -(row["current_age_minutes"] or 0),
            str(row["ticket"]),
        )
    )

    return _columns(), rows
