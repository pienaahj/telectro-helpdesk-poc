import frappe


def execute(filters=None):
    filters = filters or {}

    include_partner = cint_safe(filters.get("include_partner", 1))
    stale_hours = cint_safe(filters.get("stale_hours", 24))

    columns = get_columns()
    data = get_data(include_partner=include_partner, stale_hours=stale_hours)

    return columns, data


def get_columns():
    return [
        {
            "label": "Technician",
            "fieldname": "technician",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Active Open Tickets",
            "fieldname": "active_open_tickets",
            "fieldtype": "Int",
            "width": 150,
        },
        {
            "label": "Oldest Active Modified",
            "fieldname": "oldest_active_modified",
            "fieldtype": "Datetime",
            "width": 180,
        },
        {
            "label": "Stale > 24h",
            "fieldname": "stale_over_threshold",
            "fieldtype": "Int",
            "width": 120,
        },
    ]


def get_data(include_partner: int, stale_hours: int):
    conditions = []
    params = {
        "stale_hours": stale_hours,
    }

    if not include_partner:
        conditions.append("td.allocated_to != 'partner@local.test'")

    extra_where = ""
    if conditions:
        extra_where = " AND " + " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            td.allocated_to AS technician,
            COUNT(DISTINCT h.name) AS active_open_tickets,
            MIN(h.modified) AS oldest_active_modified,
            CAST(SUM(
                CASE
                    WHEN h.modified < (NOW() - INTERVAL %(stale_hours)s HOUR) THEN 1
                    ELSE 0
                END
            ) AS UNSIGNED) AS stale_over_threshold
        FROM `tabHD Ticket` h
        INNER JOIN `tabToDo` td
            ON td.reference_type = 'HD Ticket'
           AND td.reference_name = h.name
           AND td.status = 'Open'
        WHERE h.status NOT IN ('Resolved', 'Archived')
        {extra_where}
        GROUP BY td.allocated_to
        ORDER BY active_open_tickets DESC, technician ASC
        """,
        params,
        as_dict=True,
    )

    return rows


def cint_safe(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default