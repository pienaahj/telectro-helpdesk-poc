import frappe


def execute(filters=None):
    filters = filters or {}

    columns = [
        {
            "label": "Ticket",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "HD Ticket",
            "width": 120,
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
            "width": 110,
        },
        {
            "label": "Modified",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 180,
        },
        {
            "label": "Idle Hours",
            "fieldname": "idle_hours",
            "fieldtype": "Int",
            "width": 110,
        },
    ]

    data = frappe.db.sql(
        """
        SELECT
            name,
            subject,
            status,
            modified,
            TIMESTAMPDIFF(HOUR, modified, NOW()) AS idle_hours
        FROM `tabHD Ticket`
        WHERE status IN ('Open', 'Replied')
          AND IFNULL(`_assign`, '') IN ('', '[]')
          AND modified <= NOW() - INTERVAL 1 DAY
        ORDER BY modified ASC, name ASC
        """,
        as_dict=True,
    )

    report_summary = [
        {
            "label": "Unclaimed > 1 Day",
            "value": len(data),
            "indicator": "Orange" if data else "Green",
        }
    ]

    return columns, data, None, None, report_summary