import frappe

from telephony.service_coverage import get_user_coverage_rows


TERMINAL_STATUSES = ("Resolved", "Closed", "Archived")
POOL_LABEL = "Unclaimed (Pool)"

INTERNAL_VIEW_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Tech",
    "Agent",
    "Support Team",
}


def execute(filters=None):
    user = frappe.session.user

    if not _can_view_report(user):
        return get_columns(), []

    coverage_rows = get_user_coverage_rows(user)
    if not coverage_rows:
        return get_columns(), []

    rows = _get_matching_ticket_rows(coverage_rows)
    rows = _dedupe_rows(rows)

    rows.sort(
        key=lambda row: (
            _severity_sort_value(row.get("custom_severity") or row.get("priority")),
            _coverage_match_rank(row.get("coverage_scope")),
            int(row.get("coverage_priority") or 100),
            -_modified_sort_value(row).timestamp(),
            str(row.get("name") or ""),
        )
    )

    return get_columns(), rows


def get_columns():
    return [
        {"label": "Coverage Match", "fieldname": "coverage_match", "fieldtype": "Data", "width": 190},
        {"label": "Coverage Role", "fieldname": "coverage_role", "fieldtype": "Data", "width": 120},
        {"label": "Ticket", "fieldname": "name", "fieldtype": "Link", "options": "HD Ticket", "width": 110},
        {"label": "Subject", "fieldname": "subject", "fieldtype": "Data", "width": 280},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Priority", "fieldname": "priority", "fieldtype": "Data", "width": 90},
        {"label": "Severity", "fieldname": "custom_severity", "fieldtype": "Data", "width": 90},
        {"label": "Customer", "fieldname": "custom_customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Campus", "fieldname": "custom_site_group", "fieldtype": "Link", "options": "Location", "width": 150},
        {"label": "Service Area", "fieldname": "custom_service_area", "fieldtype": "Data", "width": 140},
        {"label": "Owner / Bucket", "fieldname": "owner_label", "fieldtype": "Data", "width": 180},
        {"label": "Request Source", "fieldname": "custom_request_source", "fieldtype": "Data", "width": 130},
        {"label": "Fulfilment Party", "fieldname": "custom_fulfilment_party", "fieldtype": "Data", "width": 130},
        {"label": "Modified", "fieldname": "modified", "fieldtype": "Datetime", "width": 160},
    ]


def _can_view_report(user: str) -> bool:
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user))
    return bool(roles & INTERNAL_VIEW_ROLES)


def _get_matching_ticket_rows(coverage_rows):
    rows = []

    for coverage in coverage_rows:
        scope = _clean(coverage.get("coverage_scope"))
        service_area = _clean(coverage.get("service_area"))

        if not service_area:
            continue

        where_parts = [
            "t.status not in %(terminal_statuses)s",
            "ifnull(t.custom_service_area, '') = %(service_area)s",
        ]

        params = {
            "terminal_statuses": TERMINAL_STATUSES,
            "service_area": service_area,
        }

        customer = _clean(coverage.get("customer"))
        campus = _clean(coverage.get("campus"))

        if scope == "Customer/Campus":
            if not customer or not campus:
                continue
            where_parts.append("ifnull(t.custom_customer, '') = %(customer)s")
            where_parts.append("ifnull(t.custom_site_group, '') = %(campus)s")
            params["customer"] = customer
            params["campus"] = campus

        elif scope == "Customer":
            if not customer:
                continue
            where_parts.append("ifnull(t.custom_customer, '') = %(customer)s")
            params["customer"] = customer

        elif scope == "Campus":
            if not campus:
                continue
            where_parts.append("ifnull(t.custom_site_group, '') = %(campus)s")
            params["campus"] = campus

        elif scope == "Default":
            pass

        else:
            continue

        ticket_rows = frappe.db.sql(
            f"""
            select
                t.name,
                t.subject,
                t.status,
                t.priority,
                t.custom_severity,
                t.custom_customer,
                t.custom_site_group,
                t.custom_service_area,
                t.custom_request_source,
                t.custom_fulfilment_party,
                t.modified,
                t._assign,
                td.allocated_to as todo_owner
            from `tabHD Ticket` t
            left join `tabToDo` td
                on td.reference_type = 'HD Ticket'
                and td.reference_name = t.name
                and td.status = 'Open'
            where {" and ".join(where_parts)}
            order by t.modified desc
            """,
            params,
            as_dict=True,
        )

        for row in ticket_rows:
            row["name"] = _clean(row.get("name"))
            row["coverage_match"] = _coverage_match_label(coverage)
            row["coverage_scope"] = scope
            row["coverage_role"] = coverage.get("coverage_role")
            row["coverage_priority"] = coverage.get("priority")
            row["coverage_row"] = coverage.get("name")
            row["owner_label"] = _owner_bucket(row)

        rows.extend(ticket_rows)

    _apply_user_labels(rows)
    return rows


def _dedupe_rows(rows):
    """
    A ticket may match more than one of the current user's coverage rows.
    Keep the strongest coverage match.
    """
    best_by_ticket = {}

    for row in rows:
        ticket = _clean(row.get("name"))
        if not ticket:
            continue

        existing = best_by_ticket.get(ticket)
        if not existing or _row_strength(row) < _row_strength(existing):
            best_by_ticket[ticket] = row

    return list(best_by_ticket.values())


def _row_strength(row):
    return (
        _coverage_match_rank(row.get("coverage_scope")),
        int(row.get("coverage_priority") or 100),
        _coverage_role_rank(row.get("coverage_role")),
    )


def _coverage_match_rank(scope: str) -> int:
    scope = _clean(scope)
    order = {
        "Customer/Campus": 1,
        "Campus": 2,
        "Customer": 3,
        "Default": 4,
    }
    return order.get(scope, 99)


def _coverage_role_rank(role: str) -> int:
    role = _clean(role)
    order = {
        "Primary": 1,
        "Eligible": 2,
        "Backup": 3,
    }
    return order.get(role, 99)


def _coverage_match_label(coverage) -> str:
    scope = _clean(coverage.get("coverage_scope"))

    if scope == "Customer/Campus":
        return f"{coverage.get('customer') or '-'} / {coverage.get('campus') or '-'}"

    if scope == "Customer":
        return f"Customer: {coverage.get('customer') or '-'}"

    if scope == "Campus":
        return f"Campus: {coverage.get('campus') or '-'}"

    if scope == "Default":
        return "Default service-area coverage"

    return scope or "-"


def _owner_bucket(row) -> str:
    todo_owner = _clean(row.get("todo_owner"))
    if todo_owner:
        return todo_owner

    assign_users = _parse_assign_users(row.get("_assign"))
    if assign_users and assign_users != ["helpdesk@local.test"]:
        return assign_users[0]

    return POOL_LABEL


def _parse_assign_users(assign_val) -> list[str]:
    if not assign_val:
        return []

    if isinstance(assign_val, list):
        return [_clean(x) for x in assign_val if _clean(x)]

    if not isinstance(assign_val, str):
        return []

    value = assign_val.strip()
    if not value:
        return []

    try:
        parsed = frappe.parse_json(value)
        if isinstance(parsed, list):
            return [_clean(x) for x in parsed if _clean(x)]
    except Exception:
        return []

    return []


def _apply_user_labels(rows):
    owners = {
        row.get("owner_label")
        for row in rows
        if row.get("owner_label") and row.get("owner_label") != POOL_LABEL
    }

    if not owners:
        return

    users = frappe.get_all(
        "User",
        filters={"name": ["in", list(owners)]},
        fields=["name", "full_name"],
    )

    full_name_map = {
        user["name"]: (user.get("full_name") or user["name"])
        for user in users
    }

    for row in rows:
        owner = row.get("owner_label")
        if owner and owner != POOL_LABEL:
            row["owner_label"] = full_name_map.get(owner, owner)


def _severity_sort_value(severity: str) -> int:
    severity = _clean(severity)

    order = {
        "Sev1": 10,
        "Sev2": 20,
        "Sev3": 30,
        "Sev4": 40,
    }

    return order.get(severity, 99)


def _modified_sort_value(row):
    value = row.get("modified")
    if value:
        return value

    return frappe.utils.get_datetime("1900-01-01")


def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()
