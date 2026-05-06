import json
from collections import defaultdict

import frappe
from frappe.utils import add_days, cint, getdate, nowdate


DEFAULT_PERIOD = "Last 14 days"
DEFAULT_MINIMUM_REPEAT_COUNT = 2

PERIOD_DAYS = {
    "Last 7 days": 7,
    "Last 14 days": 14,
    "Last 30 days": 30,
}


def execute(filters=None):
    filters = frappe._dict(filters or {})

    from_date, to_date = get_date_range(filters)
    minimum_repeat_count = max(cint(filters.get("minimum_repeat_count")) or DEFAULT_MINIMUM_REPEAT_COUNT, 1)

    columns = get_columns()
    tickets = get_tickets(filters, from_date, to_date)
    data = build_rows(tickets, minimum_repeat_count)

    return columns, data


def get_columns():
    return [
        {
            "label": "Customer",
            "fieldname": "customer",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Campus",
            "fieldname": "campus",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Fault Point",
            "fieldname": "site",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Fault Asset",
            "fieldname": "fault_point",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Service Area",
            "fieldname": "service_area",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Fault Category",
            "fieldname": "fault_category",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Fault Count",
            "fieldname": "fault_count",
            "fieldtype": "Int",
            "width": 105,
        },
        {
            "label": "First Ticket Date",
            "fieldname": "first_ticket_date",
            "fieldtype": "Datetime",
            "width": 170,
        },
        {
            "label": "Last Ticket Date",
            "fieldname": "last_ticket_date",
            "fieldtype": "Datetime",
            "width": 170,
        },
        {
            "label": "Open Count",
            "fieldname": "open_count",
            "fieldtype": "Int",
            "width": 105,
        },
        {
            "label": "Resolved Count",
            "fieldname": "resolved_count",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": "Archived Count",
            "fieldname": "archived_count",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": "Sev1 Count",
            "fieldname": "sev1_count",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": "Sev2 Count",
            "fieldname": "sev2_count",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": "Latest Ticket",
            "fieldname": "latest_ticket",
            "fieldtype": "Link",
            "options": "HD Ticket",
            "width": 120,
        },
        {
            "label": "Latest Subject",
            "fieldname": "latest_subject",
            "fieldtype": "Data",
            "width": 280,
        },
        {
            "label": "Latest Status",
            "fieldname": "latest_status",
            "fieldtype": "Data",
            "width": 115,
        },
        {
            "label": "Latest Owner",
            "fieldname": "latest_owner",
            "fieldtype": "Data",
            "width": 180,
        },
    ]


def get_date_range(filters):
    period = filters.get("period") or DEFAULT_PERIOD

    if period == "Custom":
        if not filters.get("from_date") or not filters.get("to_date"):
            frappe.throw("From Date and To Date are required when Period is Custom.")

        from_date = getdate(filters.get("from_date"))
        to_date = getdate(filters.get("to_date"))

        if from_date > to_date:
            frappe.throw("From Date cannot be after To Date.")

        return from_date, to_date

    days = PERIOD_DAYS.get(period, PERIOD_DAYS[DEFAULT_PERIOD])
    to_date = getdate(nowdate())
    from_date = getdate(add_days(to_date, -(days - 1)))

    return from_date, to_date


def get_tickets(filters, from_date, to_date):
    conditions = [
        "date(t.creation) between %(from_date)s and %(to_date)s",
    ]

    values = {
        "from_date": from_date,
        "to_date": to_date,
    }

    add_optional_condition(
        conditions,
        values,
        filters,
        filter_key="customer",
        column_name="custom_customer",
    )
    add_optional_condition(
        conditions,
        values,
        filters,
        filter_key="campus",
        column_name="custom_site_group",
    )
    add_optional_condition(
        conditions,
        values,
        filters,
        filter_key="site",
        column_name="custom_site",
    )
    add_optional_condition(
        conditions,
        values,
        filters,
        filter_key="service_area",
        column_name="custom_service_area",
    )
    add_optional_condition(
        conditions,
        values,
        filters,
        filter_key="fault_category",
        column_name="custom_fault_category",
    )
    add_optional_condition(
        conditions,
        values,
        filters,
        filter_key="severity",
        column_name="custom_severity",
    )

    where_clause = " and ".join(conditions)

    return frappe.db.sql(
        f"""
        select
            t.name,
            t.subject,
            t.status,
            t.creation,
            t.modified,
            t.owner,
            t.raised_by,
            t.custom_customer,
            t.customer,
            t.custom_site_group,
            t.custom_site,
            t.custom_fault_asset,
            t.custom_service_area,
            t.custom_fault_category,
            t.custom_severity,
            t.custom_fulfilment_party,
            t._assign
        from `tabHD Ticket` t
        where {where_clause}
        order by t.creation asc
        """,
        values,
        as_dict=True,
    )


def add_optional_condition(conditions, values, filters, filter_key, column_name):
    value = filters.get(filter_key)

    if value:
        conditions.append(f"coalesce({column_name}, '') = %({filter_key})s")
        values[filter_key] = value


def build_rows(tickets, minimum_repeat_count):
    grouped = defaultdict(list)

    for ticket in tickets:
        key = get_group_key(ticket)
        grouped[key].append(ticket)

    rows = []

    for key, group_tickets in grouped.items():
        if len(group_tickets) < minimum_repeat_count:
            continue

        sorted_tickets = sorted(group_tickets, key=lambda row: row.creation)
        first_ticket = sorted_tickets[0]
        latest_ticket = sorted_tickets[-1]

        customer, campus, site, fault_point, service_area, fault_category = key

        rows.append(
            {
                "customer": customer,
                "campus": campus,
                "site": site,
                "fault_point": fault_point,
                "service_area": service_area,
                "fault_category": fault_category,
                "fault_count": len(group_tickets),
                "first_ticket_date": first_ticket.creation,
                "last_ticket_date": latest_ticket.creation,
                "open_count": count_status(group_tickets, "Open"),
                "resolved_count": count_status(group_tickets, "Resolved"),
                "archived_count": count_status(group_tickets, "Archived"),
                "sev1_count": count_severity(group_tickets, "Sev1"),
                "sev2_count": count_severity(group_tickets, "Sev2"),
                "latest_ticket": latest_ticket.name,
                "latest_subject": latest_ticket.subject or "",
                "latest_status": latest_ticket.status or "",
                "latest_owner": get_latest_owner(latest_ticket),
            }
        )

    rows.sort(
        key=lambda row: (
            row["fault_count"],
            row["last_ticket_date"],
        ),
        reverse=True,
    )

    return rows


def get_group_key(ticket):
    return (
        get_customer_display_name(ticket.get("custom_customer") or ticket.get("customer")),
        get_location_display_name(ticket.get("custom_site_group")),
        get_location_display_name(ticket.get("custom_site")),
        get_location_display_name(ticket.get("custom_fault_asset")),
        clean_value(ticket.get("custom_service_area")),
        clean_value(ticket.get("custom_fault_category")),
    )


def clean_value(value):
    return value or "-"


def count_status(tickets, status):
    return sum(1 for ticket in tickets if (ticket.status or "") == status)


def count_severity(tickets, severity):
    return sum(1 for ticket in tickets if (ticket.custom_severity or "") == severity)


def get_latest_owner(ticket):
    assigned = parse_assigned_users(ticket.get("_assign"))

    if assigned:
        return ", ".join(assigned)

    return ticket.get("owner") or ""


def parse_assigned_users(raw_assign):
    if not raw_assign:
        return []

    if isinstance(raw_assign, list):
        return [user for user in raw_assign if user]

    if isinstance(raw_assign, str):
        raw_assign = raw_assign.strip()

        if not raw_assign:
            return []

        try:
            parsed = json.loads(raw_assign)
        except Exception:
            return [raw_assign]

        if isinstance(parsed, list):
            return [user for user in parsed if user]

        if parsed:
            return [str(parsed)]

    return []

def get_customer_display_name(customer):
    return get_display_value("Customer", customer, ["customer_name"])


def get_location_display_name(location):
    return get_display_value("Location", location, ["location_name"])


def get_display_value(doctype, name, display_fields):
    name = clean_value(name)

    if name == "-":
        return "-"

    if not frappe.db.exists(doctype, name):
        return name

    for fieldname in display_fields:
        value = frappe.db.get_value(doctype, name, fieldname)

        if value:
            return value

    title_field = frappe.get_meta(doctype).title_field

    if title_field:
        value = frappe.db.get_value(doctype, name, title_field)

        if value:
            return value

    return name
