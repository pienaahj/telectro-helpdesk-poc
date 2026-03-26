import frappe


POOL_LABEL = "Unclaimed (Pool)"


def execute(filters=None):
    filters = filters or {}

    columns = [
        {
            "label": "Technician",
            "fieldname": "technician",
            "fieldtype": "Data",
            "width": 240,
        },
        {
            "label": "Active Tickets",
            "fieldname": "active_ticket_count",
            "fieldtype": "Int",
            "width": 140,
        },
    ]

    raw_data = frappe.db.sql(
        """
        SELECT
            CASE
                WHEN IFNULL(`_assign`, '') IN ('', '[]') THEN %(pool_label)s
                WHEN `_assign` = '["helpdesk@local.test"]' THEN %(pool_label)s
                WHEN JSON_VALID(`_assign`) THEN JSON_UNQUOTE(JSON_EXTRACT(`_assign`, '$[0]'))
                ELSE %(pool_label)s
            END AS technician,
            COUNT(*) AS active_ticket_count
        FROM `tabHD Ticket`
        WHERE status IN ('Open', 'Replied')
        GROUP BY 1
        ORDER BY COUNT(*) DESC, technician ASC
        """,
        {"pool_label": POOL_LABEL},
        as_dict=True,
    )

    user_ids = [
        row["technician"]
        for row in raw_data
        if row["technician"] and row["technician"] != POOL_LABEL
    ]

    full_name_map = {}
    if user_ids:
        users = frappe.get_all(
            "User",
            filters={"name": ["in", user_ids]},
            fields=["name", "full_name"],
        )
        full_name_map = {
            user["name"]: (user.get("full_name") or user["name"])
            for user in users
        }

    data = []
    for row in raw_data:
        technician_id = row["technician"]
        display_name = (
            POOL_LABEL
            if technician_id == POOL_LABEL
            else full_name_map.get(technician_id, technician_id)
        )

        data.append(
            {
                "technician": display_name,
                "active_ticket_count": row["active_ticket_count"],
            }
        )

    labels = [row["technician"] for row in data]
    values = [row["active_ticket_count"] for row in data]

    total_active_tickets = sum(values)
    owner_bucket_count = len(data)
    unclaimed_count = next(
        (
            row["active_ticket_count"]
            for row in data
            if row["technician"] == POOL_LABEL
        ),
        0,
    )

    chart = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Active Tickets",
                    "values": values,
                }
            ],
        },
        "type": "bar",
        "height": 300,
    }

    report_summary = [
        {
            "label": "Total Active Tickets",
            "value": total_active_tickets,
            "indicator": "Blue",
        },
        {
            "label": "Active Owners / Buckets",
            "value": owner_bucket_count,
            "indicator": "Green",
        },
        {
            "label": "Unclaimed (Pool)",
            "value": unclaimed_count,
            "indicator": "Orange" if unclaimed_count else "Green",
        },
    ]

    return columns, data, None, chart, report_summary