import json

import frappe
from frappe.utils import get_datetime, now_datetime, time_diff_in_seconds


TERMINAL_STATUSES = ("Resolved", "Closed", "Archived")

OVERSIGHT_ROLES = {
    "System Manager",
    "Pilot Admin",
    "Agent Manager",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
}


def execute(filters=None):
    return get_columns(), get_data(filters or {})


def get_columns():
    return [
        {
            "label": "Breach Type",
            "fieldname": "breach_type",
            "fieldtype": "Data",
            "width": 210,
        },
        {
            "label": "Worst Breach Age",
            "fieldname": "worst_breach_age",
            "fieldtype": "Data",
            "width": 210,
        },
        {
            "label": "First Response Breach Age",
            "fieldname": "first_response_breach_age",
            "fieldtype": "Data",
            "width": 210,
        },
        {
            "label": "Resolution Breach Age",
            "fieldname": "resolution_breach_age",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": "First Response By",
            "fieldname": "response_by",
            "fieldtype": "Datetime",
            "width": 190,
        },
        {
            "label": "Resolution By",
            "fieldname": "resolution_by",
            "fieldtype": "Datetime",
            "width": 190,
        },
        {
            "label": "Ticket",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "HD Ticket",
            "width": 100,
        },
        {
            "label": "Subject",
            "fieldname": "subject",
            "fieldtype": "Data",
            "width": 320,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Customer",
            "fieldname": "customer_display",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Campus",
            "fieldname": "custom_site_group",
            "fieldtype": "Link",
            "options": "Location",
            "width": 150,
        },
        {
            "label": "Service Area",
            "fieldname": "custom_service_area",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Agent Group",
            "fieldname": "agent_group",
            "fieldtype": "Link",
            "options": "HD Team",
            "width": 140,
        },
        {
            "label": "Assigned To",
            "fieldname": "assigned_to",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Equipment Ref",
            "fieldname": "custom_equipment_ref",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "First Responded On",
            "fieldname": "first_responded_on",
            "fieldtype": "Datetime",
            "width": 190,
        },
        {
            "label": "Age",
            "fieldname": "age",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": "Modified",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 200,
        },
    ]


def get_data(filters):
    user = frappe.session.user

    if not _is_oversight_user(user):
        return []

    now = now_datetime()

    rows = frappe.db.sql(
        """
        select
            t.name,
            t.subject,
            t.status,
            t.priority,
            t.custom_severity,
            t.customer,
            t.custom_customer,
            t.custom_site_group,
            t.custom_service_area,
            t.custom_request_source,
            t.via_customer_portal,
            t.raised_by,
            t.agent_group,
            t.custom_equipment_ref,
            t._assign,
            t.first_responded_on,
            t.response_by,
            t.resolution_by,
            t.resolution_date,
            t.creation,
            t.modified
        from `tabHD Ticket` t
        where
            t.status not in %(terminal_statuses)s
            and (
                ifnull(t.via_customer_portal, 0) = 1
                or ifnull(t.custom_request_source, '') = 'Customer'
                or (
                    ifnull(t.customer, '') != ''
                    and ifnull(t.raised_by, '') != ''
                )
            )
            and (
                (
                    t.first_responded_on is null
                    and t.response_by is not null
                    and t.response_by < %(now)s
                )
                or (
                    t.resolution_by is not null
                    and t.resolution_by < %(now)s
                )
            )
        order by
            t.modified desc
        """,
        {
            "terminal_statuses": TERMINAL_STATUSES,
            "now": now,
        },
        as_dict=True,
    )

    report_rows = []

    for row in rows:
        first_response_breach_seconds = _first_response_breach_seconds(row, now)
        resolution_breach_seconds = _resolution_breach_seconds(row, now)

        if first_response_breach_seconds <= 0 and resolution_breach_seconds <= 0:
            continue

        row["customer_display"] = row.get("customer") or row.get("custom_customer") or ""
        row["assigned_to"] = _assigned_to(row)
        row["breach_type"] = _breach_type(
            first_response_breach_seconds,
            resolution_breach_seconds,
        )
        row["first_response_breach_age"] = _duration_label(first_response_breach_seconds)
        row["resolution_breach_age"] = _duration_label(resolution_breach_seconds)
        row["worst_breach_seconds"] = max(
            first_response_breach_seconds,
            resolution_breach_seconds,
        )
        row["worst_breach_age"] = _duration_label(row["worst_breach_seconds"])
        row["age"] = _age(row, now)

        report_rows.append(row)

    return sorted(
        report_rows,
        key=lambda row: (
            -int(row.get("worst_breach_seconds") or 0),
            _breach_type_sort(row.get("breach_type")),
            -_modified_sort_value(row).timestamp(),
            str(row.get("name") or ""),
        ),
    )


def _is_oversight_user(user: str) -> bool:
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user))
    return bool(roles & OVERSIGHT_ROLES)


def _assigned_to(row) -> str:
    assigned = _parse_assign(row.get("_assign"))

    if assigned:
        return ", ".join(assigned)

    todo_users = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": row.get("name"),
            "status": "Open",
        },
        fields=["allocated_to"],
        order_by="creation asc",
    )

    assigned = [todo.allocated_to for todo in todo_users if todo.allocated_to]
    return ", ".join(assigned)


def _parse_assign(raw) -> list[str]:
    if not raw:
        return []

    if isinstance(raw, list):
        return [value for value in raw if value]

    if isinstance(raw, str):
        trimmed = raw.strip()

        if not trimmed or trimmed == "[]":
            return []

        try:
            parsed = json.loads(trimmed)
        except Exception:
            return [trimmed]

        if isinstance(parsed, list):
            return [value for value in parsed if value]

        return [trimmed]

    return []


def _first_response_breach_seconds(row, now) -> int:
    if row.get("first_responded_on"):
        return 0

    response_by = row.get("response_by")

    if not response_by:
        return 0

    seconds = int(time_diff_in_seconds(now, get_datetime(response_by)))
    return max(seconds, 0)


def _resolution_breach_seconds(row, now) -> int:
    resolution_by = row.get("resolution_by")

    if not resolution_by:
        return 0

    seconds = int(time_diff_in_seconds(now, get_datetime(resolution_by)))
    return max(seconds, 0)


def _breach_type(first_response_seconds: int, resolution_seconds: int) -> str:
    has_first_response_breach = first_response_seconds > 0
    has_resolution_breach = resolution_seconds > 0

    if has_first_response_breach and has_resolution_breach:
        return "First Response + Resolution"

    if has_first_response_breach:
        return "First Response"

    if has_resolution_breach:
        return "Resolution"

    return ""


def _breach_type_sort(breach_type: str) -> int:
    order = {
        "First Response + Resolution": 10,
        "Resolution": 20,
        "First Response": 30,
    }

    return order.get(breach_type or "", 99)


def _duration_label(seconds: int) -> str:
    seconds = int(seconds or 0)

    if seconds <= 0:
        return ""

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes or not parts:
        parts.append(f"{minutes}m")

    return "Overdue by " + " ".join(parts)


def _age(row, now) -> str:
    created = row.get("creation")

    if not created:
        return ""

    seconds = int(time_diff_in_seconds(now, get_datetime(created)))

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    if days:
        return f"{days}d {hours}h"

    if hours:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"


def _modified_sort_value(row):
    value = row.get("modified")

    if value:
        return get_datetime(value)

    return get_datetime("1900-01-01")