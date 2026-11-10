
"""Authorized, site-configured Data Request escalation recipients."""

import re

import frappe


RECIPIENTS_KEY = "telectro_data_request_escalation_recipients"
SERVICE_AREA = "Data Request"

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def _configured_recipients():
    """Read the explicit site allowlist. Missing means nobody."""

    configured = frappe.conf.get(RECIPIENTS_KEY)

    if configured is None:
        return []

    if (
        not isinstance(configured, list)
        or any(not isinstance(user, str) for user in configured)
    ):
        raise ValueError(
            "Escalation recipients must be a JSON list of user IDs"
        )

    return sorted({
        user.strip()
        for user in configured
        if user.strip()
    })


def resolve_coordinator_recipients(ticket):
    """Return configured recipients authorized to read this ticket."""

    if getattr(ticket, "doctype", None) != "HD Ticket":
        raise ValueError("HD Ticket document required")

    if str(ticket.get("custom_service_area") or "").strip() != SERVICE_AREA:
        return []

    recipients = []

    for user in _configured_recipients():
        if user in {"Administrator", "Guest"}:
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
