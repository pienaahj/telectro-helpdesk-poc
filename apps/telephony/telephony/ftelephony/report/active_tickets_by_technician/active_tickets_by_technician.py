import frappe


def execute(filters=None):
    columns = [
        {
            "label": "Technician",
            "fieldname": "technician",
            "fieldtype": "Data",
            "width": 220,
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
            "label": "Modified",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 180,
        },
    ]

    data = frappe.db.sql("""
        SELECT
            td.allocated_to AS technician,
            h.name AS ticket,
            h.subject,
            h.status,
            h.modified
        FROM `tabHD Ticket` h
        INNER JOIN `tabToDo` td
            ON td.reference_type = 'HD Ticket'
           AND td.reference_name = h.name
           AND td.status = 'Open'
        WHERE h.status NOT IN ('Resolved', 'Archived')
        ORDER BY td.allocated_to ASC, h.modified ASC, h.name ASC
    """, as_dict=True)

    return columns, data