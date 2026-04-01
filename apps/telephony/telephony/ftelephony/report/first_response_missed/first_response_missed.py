import frappe


_ACTIVE_STATUSES = ("Open", "Replied")


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {
            "label": "Ticket",
            "fieldname": "ticket",
            "fieldtype": "Link",
            "options": "HD Ticket",
            "width": 110,
        },
        {
            "label": "Subject",
            "fieldname": "subject",
            "fieldtype": "Data",
            "width": 320,
        },
        {
            "label": "Owner Bucket",
            "fieldname": "owner_bucket",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Response By",
            "fieldname": "response_by",
            "fieldtype": "Datetime",
            "width": 170,
        },
        {
            "label": "Hours Missed",
            "fieldname": "hours_missed",
            "fieldtype": "Int",
            "width": 110,
        },
    ]


def get_data():
    return frappe.db.sql(
        """
        SELECT
            name AS ticket,
            subject,
            CASE
                WHEN COALESCE(custom_fulfilment_party, '') = 'Partner' THEN 'Partner'
                WHEN IFNULL(_assign, '') IN ('', '[]') THEN 'Pool'
                WHEN _assign = '["tech.alfa@local.test"]' THEN 'tech.alfa'
                WHEN _assign = '["tech.bravo@local.test"]' THEN 'tech.bravo'
                WHEN _assign = '["tech.charlie@local.test"]' THEN 'tech.charlie'
                WHEN _assign = '["partner@local.test"]' THEN 'Partner'
                ELSE _assign
            END AS owner_bucket,
            response_by,
            ABS(TIMESTAMPDIFF(HOUR, response_by, NOW())) AS hours_missed
        FROM `tabHD Ticket`
        WHERE status IN %(active_statuses)s
          AND response_by IS NOT NULL
          AND response_by < NOW()
        ORDER BY response_by ASC, modified ASC
        """,
        {"active_statuses": _ACTIVE_STATUSES},
        as_dict=True,
    )