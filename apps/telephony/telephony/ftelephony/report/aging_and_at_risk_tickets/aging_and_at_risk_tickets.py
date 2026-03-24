import frappe


def execute(filters=None):
    columns = [
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
            "label": "Technician",
            "fieldname": "technician",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Modified",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 180,
        },
    ]

    data = frappe.db.sql("""
        SELECT
            h.name AS ticket,
            h.subject,
            td.allocated_to AS technician,
            h.status,
            h.modified
        FROM `tabHD Ticket` h
        INNER JOIN `tabToDo` td
            ON td.reference_type = 'HD Ticket'
           AND td.reference_name = h.name
           AND td.status = 'Open'
        WHERE h.status NOT IN ('Resolved', 'Archived')
          AND h.modified < (NOW() - INTERVAL 24 HOUR)
        ORDER BY h.modified ASC, td.allocated_to ASC, h.name ASC
    """, as_dict=True)

    return columns, data