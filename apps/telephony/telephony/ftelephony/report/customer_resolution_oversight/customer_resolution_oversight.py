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
            "label": "Resolution Risk",
            "fieldname": "resolution_risk",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Time Left",
            "fieldname": "time_left_to_resolution",
            "fieldtype": "Data",
            "width": 200,
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
            "label": "Account",
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
            "width": 170,
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
            "width": 160,
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
            and t.resolution_by is not null
            and t.resolution_by >= %(now)s
            and (
                ifnull(t.via_customer_portal, 0) = 1
                or ifnull(t.custom_request_source, '') = 'Customer'
                or (
                    ifnull(t.customer, '') != ''
                    and ifnull(t.raised_by, '') != ''
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

    for row in rows:
        row["customer_display"] = row.get("customer") or row.get("custom_customer") or ""
        row["assigned_to"] = _assigned_to(row)
        row["resolution_risk"] = _resolution_risk(row, now)
        row["time_left_to_resolution"] = _time_left_to_resolution(row, now)
        row["age"] = _age(row, now)

    return sorted(
        rows,
        key=lambda row: (
            _risk_sort(row.get("resolution_risk")),
            _resolution_by_sort(row.get("resolution_by")),
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


def _resolution_risk(row, now) -> str:
    resolution_by = row.get("resolution_by")

    if not resolution_by:
        return "No SLA"

    resolution_by = get_datetime(resolution_by)
    seconds_left = time_diff_in_seconds(resolution_by, now)

    if seconds_left < 0:
        return "Breached"

    if seconds_left <= 60 * 60:
        return "Due < 1h"

    if seconds_left <= 4 * 60 * 60:
        return "Due < 4h"

    if resolution_by.date() == now.date():
        return "Due today"

    return "OK"


def _time_left_to_resolution(row, now) -> str:
    resolution_by = row.get("resolution_by")

    if not resolution_by:
        return "No SLA"

    resolution_by = get_datetime(resolution_by)
    seconds_left = int(time_diff_in_seconds(resolution_by, now))

    prefix = ""

    if seconds_left < 0:
        prefix = "Overdue by "
        seconds_left = abs(seconds_left)

    days, remainder = divmod(seconds_left, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes or not parts:
        parts.append(f"{minutes}m")

    return prefix + " ".join(parts)


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


def _risk_sort(risk: str) -> int:
    order = {
        "Due < 1h": 10,
        "Due < 4h": 20,
        "Due today": 30,
        "OK": 40,
        "Breached": 50,
        "No SLA": 60,
    }

    return order.get(risk or "", 99)


def _resolution_by_sort(value):
    if value:
        return get_datetime(value)

    return get_datetime("2999-12-31")


def _modified_sort_value(row):
    value = row.get("modified")

    if value:
        return get_datetime(value)

    return get_datetime("1900-01-01")
