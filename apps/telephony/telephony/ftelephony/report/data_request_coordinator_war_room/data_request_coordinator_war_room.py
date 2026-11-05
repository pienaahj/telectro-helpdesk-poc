"""Coordinator oversight of active, incomplete Data Requests."""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime


ALLOWED_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
}

ACTIVE_STATUSES = ("Open", "Replied")
OVERDUE_SECONDS = int(timedelta(minutes=10).total_seconds())


def _require_access():
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw(
            _("Data Request oversight access is required."),
            frappe.PermissionError,
        )

    if user == "Administrator":
        return user

    roles = set(frappe.get_roles(user) or [])

    if not roles.intersection(ALLOWED_ROLES):
        frappe.throw(
            _("Data Request oversight access is required."),
            frappe.PermissionError,
        )

    account = frappe.db.get_value(
        "User",
        user,
        ["enabled", "user_type"],
        as_dict=True,
    )

    if (
        not account
        or not account.enabled
        or account.user_type != "System User"
    ):
        frappe.throw(
            _("An enabled internal user is required."),
            frappe.PermissionError,
        )

    return user


def _format_age(seconds):
    seconds = max(0, int(seconds))

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)

    if days:
        return (
            f"{days}d {hours:02d}h "
            f"{minutes:02d}m {remaining_seconds:02d}s"
        )

    if hours:
        return (
            f"{hours}h {minutes:02d}m "
            f"{remaining_seconds:02d}s"
        )

    return f"{minutes}m {remaining_seconds:02d}s"


def _columns():
    return [
        {
            "label": _("Ticket"),
            "fieldname": "ticket",
            "fieldtype": "Link",
            "options": "HD Ticket",
            "width": 110,
        },
        {
            "label": _("Subject"),
            "fieldname": "subject",
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Team"),
            "fieldname": "agent_group",
            "fieldtype": "Link",
            "options": "HD Team",
            "width": 160,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Age"),
            "fieldname": "age",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("10-Minute Threshold"),
            "fieldname": "age_state",
            "fieldtype": "Data",
            "width": 170,
        },
        {
            "label": _("Created"),
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 170,
        },
        {
            "label": _("Age Seconds"),
            "fieldname": "age_seconds",
            "fieldtype": "Int",
            "hidden": 1,
        },
    ]


def execute(filters=None):
    """Return only Data Requests readable by the current user."""
    user = _require_access()
    now = now_datetime()

    # Frappe applies list-level HD Ticket permissions.
    candidates = frappe.get_list(
        "HD Ticket",
        filters={
            "custom_service_area": "Data Request",
            "status": ["in", list(ACTIVE_STATUSES)],
            "custom_data_request_first_completed_on": [
                "is",
                "not set",
            ],
        },
        fields=["name"],
        order_by="creation asc",
        limit_page_length=0,
    )

    rows = []

    for candidate in candidates:
        ticket = frappe.get_doc("HD Ticket", candidate.name)

        # Also enforce document-level permission per ticket.
        if not frappe.has_permission(
            "HD Ticket",
            ptype="read",
            doc=ticket,
            user=user,
        ):
            continue

        created = get_datetime(ticket.creation)
        age_seconds = max(
            0,
            int((now - created).total_seconds()),
        )

        rows.append({
            "ticket": ticket.name,
            "subject": ticket.subject,
            "customer": (
                getattr(ticket, "custom_customer", None)
                or getattr(ticket, "customer", None)
                or ""
            ),
            "agent_group": ticket.agent_group,
            "status": ticket.status,
            "age": _format_age(age_seconds),
            "age_seconds": age_seconds,
            "age_state": (
                "OVERDUE"
                if age_seconds >= OVERDUE_SECONDS
                else "WITHIN 10 MIN"
            ),
            "creation": ticket.creation,
        })

    return _columns(), rows
