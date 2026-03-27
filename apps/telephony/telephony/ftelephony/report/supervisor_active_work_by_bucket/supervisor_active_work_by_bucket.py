import frappe

POOL_LABEL = "Unclaimed (Pool)"
PARTNER_LABEL = "Partner"


def execute(filters=None):
    filters = filters or {}

    columns = [
        {
            "label": "Owner / Bucket",
            "fieldname": "owner_bucket",
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

    raw_rows = frappe.db.sql(
        """
        SELECT
            CASE
                WHEN IFNULL(`_assign`, '') IN ('', '[]') OR `_assign` = '["helpdesk@local.test"]'
                    THEN %(pool_label)s
                WHEN COALESCE(`custom_fulfilment_party`, '') = 'Partner'
                    THEN %(partner_label)s
                WHEN JSON_VALID(`_assign`)
                    THEN JSON_UNQUOTE(JSON_EXTRACT(`_assign`, '$[0]'))
                ELSE %(pool_label)s
            END AS owner_bucket,
            COUNT(*) AS active_ticket_count
        FROM `tabHD Ticket`
        WHERE status IN ('Open', 'Replied')
        GROUP BY 1
        ORDER BY COUNT(*) DESC, owner_bucket ASC
        """,
        {
            "pool_label": POOL_LABEL,
            "partner_label": PARTNER_LABEL,
        },
        as_dict=True,
    )

    user_ids = [
        row["owner_bucket"]
        for row in raw_rows
        if row["owner_bucket"] not in (POOL_LABEL, PARTNER_LABEL)
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
    for row in raw_rows:
        bucket = row["owner_bucket"]
        display_name = full_name_map.get(bucket, bucket)

        data.append(
            {
                "owner_bucket": display_name,
                "active_ticket_count": int(row["active_ticket_count"] or 0),
            }
        )

    chart = {
        "data": {
            "labels": [row["owner_bucket"] for row in data],
            "datasets": [
                {
                    "name": "Active Tickets",
                    "values": [row["active_ticket_count"] for row in data],
                }
            ],
        },
        "type": "bar",
        "height": 280,
    }

    report_summary = [
        {
            "label": "Total Buckets",
            "value": len(data),
            "indicator": "Blue",
        }
    ]

    return columns, data, None, chart, report_summary