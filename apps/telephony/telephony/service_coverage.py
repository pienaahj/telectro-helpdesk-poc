import frappe


COVERAGE_DOCTYPE = "TELECTRO Service Coverage"

ROLE_ORDER = {
    "Primary": 0,
    "Eligible": 1,
    "Backup": 2,
}


def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _role_rank(role: str) -> int:
    return ROLE_ORDER.get(_clean(role), 99)


def _row_sort_key(row: dict):
    return (
        int(row.get("_match_rank") or 99),
        int(row.get("priority") or 100),
        _role_rank(row.get("coverage_role")),
        _clean(row.get("user")).casefold(),
        _clean(row.get("name")).casefold(),
    )


def _coverage_fields() -> list[str]:
    return [
        "name",
        "enabled",
        "coverage_scope",
        "customer",
        "campus",
        "service_area",
        "user",
        "coverage_role",
        "priority",
        "notes",
    ]


def get_matching_coverage_rows(
    *,
    customer: str | None = None,
    campus: str | None = None,
    service_area: str | None = None,
) -> list[dict]:
    """
    Return enabled TELECTRO Service Coverage rows matching a ticket context.

    Read-only helper:
    - does not mutate tickets
    - does not create ToDos
    - does not write _assign
    - does not make routing decisions by itself

    Matching order:
    1. Customer/Campus + Service Area
    2. Campus + Service Area
    3. Customer + Service Area
    4. Default + Service Area
    """
    service_area = _clean(service_area)
    if not service_area:
        return []

    customer = _clean(customer)
    campus = _clean(campus)

    all_rows: list[dict] = []

    match_specs = [
        (
            1,
            {
                "enabled": 1,
                "coverage_scope": "Customer/Campus",
                "customer": customer,
                "campus": campus,
                "service_area": service_area,
            },
            bool(customer and campus),
        ),
        (
            2,
            {
                "enabled": 1,
                "coverage_scope": "Campus",
                "campus": campus,
                "service_area": service_area,
            },
            bool(campus),
        ),
        (
            3,
            {
                "enabled": 1,
                "coverage_scope": "Customer",
                "customer": customer,
                "service_area": service_area,
            },
            bool(customer),
        ),
        (
            4,
            {
                "enabled": 1,
                "coverage_scope": "Default",
                "service_area": service_area,
            },
            True,
        ),
    ]

    for match_rank, filters, should_run in match_specs:
        if not should_run:
            continue

        rows = frappe.get_all(
            COVERAGE_DOCTYPE,
            filters=filters,
            fields=_coverage_fields(),
            order_by="priority asc, user asc",
        )

        for row in rows:
            row["_match_rank"] = match_rank

        if rows:
            all_rows.extend(rows)
            break

    all_rows.sort(key=_row_sort_key)
    return all_rows


def get_user_coverage_rows(user: str) -> list[dict]:
    """
    Return enabled coverage rows for a specific user.
    """
    user = _clean(user)
    if not user:
        return []

    rows = frappe.get_all(
        COVERAGE_DOCTYPE,
        filters={
            "enabled": 1,
            "user": user,
        },
        fields=_coverage_fields(),
        order_by="priority asc, service_area asc, coverage_scope asc",
    )

    return rows


def get_ticket_context(ticket_or_name) -> dict:
    """
    Extract the coverage-relevant context from an HD Ticket document or name.
    """
    if isinstance(ticket_or_name, str):
        ticket = frappe.db.get_value(
            "HD Ticket",
            ticket_or_name,
            ["name", "custom_customer", "custom_site_group", "custom_service_area"],
            as_dict=True,
        )
    else:
        ticket = ticket_or_name

    if not ticket:
        return {
            "ticket": "",
            "customer": "",
            "campus": "",
            "service_area": "",
        }

    return {
        "ticket": _clean(ticket.get("name")),
        "customer": _clean(ticket.get("custom_customer")),
        "campus": _clean(ticket.get("custom_site_group")),
        "service_area": _clean(ticket.get("custom_service_area")),
    }


def get_matching_coverage_rows_for_ticket(ticket_or_name) -> list[dict]:
    """
    Convenience wrapper for ticket-driven coverage lookup.
    """
    context = get_ticket_context(ticket_or_name)

    return get_matching_coverage_rows(
        customer=context["customer"],
        campus=context["campus"],
        service_area=context["service_area"],
    )


def user_has_ticket_coverage(user: str, ticket_or_name) -> bool:
    """
    Return True when user appears in the matched coverage rows for a ticket.
    """
    user = _clean(user)
    if not user:
        return False

    rows = get_matching_coverage_rows_for_ticket(ticket_or_name)
    return any(_clean(row.get("user")) == user for row in rows)