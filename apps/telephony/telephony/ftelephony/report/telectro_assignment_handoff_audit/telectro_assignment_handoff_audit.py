import frappe


def execute(filters=None):
    columns = [
        {"label": "Changed On", "fieldname": "changed_on", "fieldtype": "Datetime", "width": 180},
        {"label": "Ticket", "fieldname": "ticket", "fieldtype": "Link", "options": "HD Ticket", "width": 110},
        {"label": "Subject", "fieldname": "ticket_subject", "fieldtype": "Data", "width": 280},
        {"label": "Changed By", "fieldname": "changed_by", "fieldtype": "Link", "options": "User", "width": 220},
        {"label": "From User", "fieldname": "from_user", "fieldtype": "Link", "options": "User", "width": 220},
        {"label": "To User", "fieldname": "to_user", "fieldtype": "Link", "options": "User", "width": 220},
        {"label": "Reason", "fieldname": "reason", "fieldtype": "Small Text", "width": 360},
        {"label": "Source", "fieldname": "source", "fieldtype": "Data", "width": 160},
    ]

    data = frappe.db.sql(
        """
        SELECT
            changed_on,
            ticket,
            ticket_subject,
            changed_by,
            from_user,
            to_user,
            reason,
            source
        FROM `tabTELECTRO Assignment Handoff Log`
        ORDER BY
            changed_on DESC,
            name DESC
        """,
        as_dict=True,
    )

    return columns, data