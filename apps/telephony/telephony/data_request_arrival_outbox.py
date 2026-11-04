"""Record Data Request arrival intents in the ticket transaction.

No email, Notification Log, job, commit, assignment change,
or post-commit callback is performed here.
"""

import frappe

from telephony.data_request_arrival import plan_arrival_intents

DOCTYPE = "TELECTRO Data Request Notification Intent"
TEAM = "Data Provisioning"
AREA = "Data Request"


def _eligible_user(user):
    profile = frappe.db.get_value(
        "User",
        user,
        ["enabled", "email", "user_type"],
        as_dict=True,
    )

    if not profile or int(profile.get("enabled") or 0) != 1:
        return False

    email = str(profile.get("email") or "").strip()

    return (
        profile.get("user_type") == "System User"
        and "@" in email
    )


def _verify_existing(existing, item):
    for field, expected in (
        ("ticket", item["ticket"]),
        ("recipient", item["recipient"]),
        ("event", item["event"]),
    ):
        if str(existing.get(field) or "") != expected:
            raise ValueError(
                "Notification intent identity collision "
                f"for {item['name']}: {field}"
            )


def _insert_if_missing(item):
    existing = frappe.db.get_value(
        DOCTYPE,
        item["name"],
        ["ticket", "recipient", "event"],
        as_dict=True,
    )

    if existing:
        _verify_existing(existing, item)
        return False

    record = {
        "doctype": DOCTYPE,
        "intent_id": item["name"],
        "ticket": item["ticket"],
        "recipient": item["recipient"],
        "event": item["event"],
        "delivery_state": "Pending",
        "in_app_state": "Pending",
        "email_state": "Pending",
    }

    try:
        frappe.get_doc(record).insert(ignore_permissions=True)

    except frappe.DuplicateEntryError:
        # A concurrent writer may have inserted the
        # same deterministic intent identifier.
        existing = frappe.db.get_value(
            DOCTYPE,
            item["name"],
            ["ticket", "recipient", "event"],
            as_dict=True,
        )

        if not existing:
            raise

        _verify_existing(existing, item)
        return False

    return True


def capture_arrival_intents(doc, method=None):
    """Intended for HD Ticket.after_insert.

    The originating ticket transaction owns commit/rollback.
    A persistence failure propagates rather than silently
    creating an untracked request.
    """

    if getattr(doc, "doctype", None) != "HD Ticket":
        return []

    if str(doc.get("custom_service_area") or "").strip() != AREA:
        return []

    if str(doc.get("agent_group") or "").strip() != TEAM:
        return []

    if str(doc.get("status") or "").strip() != "Open":
        return []

    ticket = str(getattr(doc, "name", "") or "").strip()

    if not ticket:
        raise ValueError("A persisted HD Ticket name is required")

    team = frappe.get_doc("HD Team", TEAM)

    members = [
        row.get("user")
        for row in (team.get("users") or [])
    ]

    planned = plan_arrival_intents(
        ticket_name=ticket,
        service_area=AREA,
        members=members,
        eligible_user=_eligible_user,
    )

    inserted = []

    for item in planned:
        if _insert_if_missing(item):
            inserted.append(item["name"])

    return inserted
