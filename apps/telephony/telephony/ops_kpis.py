import frappe

_ACTIVE_STATUSES = ("Open", "Replied")

POOL_JSON = '["helpdesk@local.test"]'

# Unclaimed = unassigned-ish OR pool-owned
_UNCLAIMED_SQL = f"(IFNULL(_assign, '') IN ('', '[]') OR _assign = '{POOL_JSON}')"


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