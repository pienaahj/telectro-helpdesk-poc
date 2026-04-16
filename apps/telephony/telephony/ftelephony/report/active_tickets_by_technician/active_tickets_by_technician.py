import frappe


def execute(filters=None):
    columns = [
        {
            "label": "Technician",
            "fieldname": "technician",
            "fieldtype": "Data",
            "width": 300,
        },
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
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Stale Hours",
            "fieldname": "stale_hours",
            "fieldtype": "Int",
            "width": 105,
        },
        {
            "label": "Attention Band",
            "fieldname": "attention_band",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Modified",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 180,
        },
    ]

    data = frappe.db.sql(
        """
        SELECT
            td.allocated_to AS technician,
            h.name AS ticket,
            h.subject,
            h.status,
            TIMESTAMPDIFF(HOUR, h.modified, NOW()) AS stale_hours,
            CASE
                WHEN TIMESTAMPDIFF(HOUR, h.modified, NOW()) >= 72 THEN 'Critical'
                WHEN TIMESTAMPDIFF(HOUR, h.modified, NOW()) >= 24 THEN 'At Risk'
                WHEN TIMESTAMPDIFF(HOUR, h.modified, NOW()) >= 4 THEN 'Watch'
                ELSE 'Fresh'
            END AS attention_band,
            h.modified
        FROM `tabHD Ticket` h
        INNER JOIN `tabToDo` td
            ON td.reference_type = 'HD Ticket'
           AND td.reference_name = h.name
           AND td.status = 'Open'
        WHERE h.status NOT IN ('Resolved', 'Archived')
        ORDER BY
            td.allocated_to ASC,
            stale_hours DESC,
            h.modified ASC,
            h.name ASC
        """,
        as_dict=True,
    )

    return columns, data