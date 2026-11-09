"""Authorized Coordinator recipients for Data Request escalation."""

import re

import frappe

COORDINATOR_ROLE = "TELECTRO-POC Role - Coordinator Ops"
MANDATORY_ESCALATION_RECIPIENTS = frozenset({
    "christo@telectro.co.za",
    "pierre@telectro.co.za",
    "sean@telectro.co.za",
})
SERVICE_AREA = "Data Request"

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def resolve_coordinator_recipients(ticket):
    """Return eligible Coordinators permitted to read this ticket."""

    if getattr(ticket, "doctype", None) != "HD Ticket":
        raise ValueError("HD Ticket document required")

    if str(ticket.get("custom_service_area") or "").strip() != SERVICE_AREA:
        return []

    members = frappe.get_all(
        "Has Role",
        filters={
            "role": COORDINATOR_ROLE,
            "parenttype": "User",
        },
        pluck="parent",
    )

    recipients = []

    for user in sorted(
        set(members) | MANDATORY_ESCALATION_RECIPIENTS
    ):
        if not user or user in {"Administrator", "Guest"}:
            continue

        profile = frappe.db.get_value(
            "User",
            user,
            ["enabled", "user_type", "email"],
            as_dict=True,
        )

        if not profile or not profile.enabled:
            continue

        if profile.user_type != "System User":
            continue

        email = str(profile.email or "").strip()

        if not EMAIL_PATTERN.fullmatch(email):
            continue

        if not frappe.has_permission(
            "HD Ticket",
            ptype="read",
            doc=ticket,
            user=user,
        ):
            continue

        recipients.append(user)

    return recipients
