import frappe

_ACTIVE_STATUSES = ("Open", "Replied")

_UNCLAIMED_SQL = "(IFNULL(_assign, '') IN ('', '[]'))"

def _count_sql(where_sql: str, params: tuple = ()) -> int:
    row = frappe.db.sql(
        f"""
        SELECT COUNT(*) AS c
        FROM `tabHD Ticket`
        WHERE {where_sql}
        """,
        params,
        as_dict=True,
    )[0]

    return int(row.get("c") or 0)


def _count_active(extra_where_sql: str = "", extra_params: tuple = ()) -> int:
    where_sql = "status IN %s"
    params = [_ACTIVE_STATUSES]

    if extra_where_sql:
        where_sql += f" AND {extra_where_sql}"
        params.extend(extra_params)

    return _count_sql(where_sql, tuple(params))


def _count_unclaimed(min_idle_minutes: int) -> int:
    mins = int(min_idle_minutes)
    return _count_active(
        f"{_UNCLAIMED_SQL} AND TIMESTAMPDIFF(MINUTE, modified, NOW()) >= %s",
        (mins,),
    )


def _card(value: int, report_name: str) -> dict:
    return {
        "value": value,
    }


# Keep method names for compatibility (optional), but route to the new report names
@frappe.whitelist()
def unassigned_now() -> dict:
    return _card(_count_unclaimed(0), "TELECTRO Ops Unclaimed Now")


@frappe.whitelist()
def unassigned_over_60m() -> dict:
    return _card(_count_unclaimed(60), "TELECTRO Ops Unclaimed Over 60m")


@frappe.whitelist()
def unassigned_over_4h() -> dict:
    return _card(_count_unclaimed(240), "TELECTRO Ops Unclaimed Over 4h")


@frappe.whitelist()
def total_active_now() -> dict:
    return _card(_count_active(), "TELECTRO Ops Total Active")


@frappe.whitelist()
def partner_queue_now() -> dict:
    return _card(
        _count_active("COALESCE(custom_fulfilment_party, '') = %s", ("Partner",)),
        "TELECTRO Ops Partner Queue",
    )


# Optional: add “properly named” aliases for later cleanup
@frappe.whitelist()
def unclaimed_now() -> dict:
    return unassigned_now()


@frappe.whitelist()
def unclaimed_over_60m() -> dict:
    return unassigned_over_60m()


@frappe.whitelist()
def unclaimed_over_4h() -> dict:
    return unassigned_over_4h()


@frappe.whitelist()
def unclaimed_pool_now() -> dict:
    return unassigned_now()

_DATA_REQUEST_OVERSIGHT_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
}


@frappe.whitelist()
def data_request_overdue_now() -> dict:
    """Count overdue incomplete Data Requests visible to the caller."""
    from datetime import timedelta
    from frappe.utils import now_datetime

    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw(
            "Data Request oversight access is required.",
            frappe.PermissionError,
        )

    if user != "Administrator":
        roles = set(frappe.get_roles(user) or [])

        if not roles.intersection(_DATA_REQUEST_OVERSIGHT_ROLES):
            frappe.throw(
                "Data Request oversight access is required.",
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
                "An enabled internal user is required.",
                frappe.PermissionError,
            )

    cutoff = now_datetime() - timedelta(minutes=10)

    # List-level permissions are applied by Frappe.
    candidates = frappe.get_list(
        "HD Ticket",
        filters={
            "custom_service_area": "Data Request",
            "status": ["in", list(_ACTIVE_STATUSES)],
            "creation": ["<=", cutoff],
            "custom_data_request_first_completed_on": [
                "is", "not set"
            ],
        },
        fields=["name"],
        limit_page_length=0,
    )

    visible_count = 0

    for row in candidates:
        ticket = frappe.get_doc("HD Ticket", row.name)

        # Independently enforce document-level read permission.
        if frappe.has_permission(
            "HD Ticket",
            ptype="read",
            doc=ticket,
            user=user,
        ):
            visible_count += 1

    return _card(
        visible_count,
        "TELECTRO Ops Data Request Overdue",
    )
