import frappe


def execute(filters=None):
    columns = [
        {
            "label": "Ticket",
            "fieldname": "ticket",
            "fieldtype": "Link",
            "options": "HD Ticket",
            "width": 120,
        },
        {
            "label": "Subject",
            "fieldname": "subject",
            "fieldtype": "Data",
            "width": 360,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Priority",
            "fieldname": "priority",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Team",
            "fieldname": "team",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Modified",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 170,
        },
    ]

    user = (frappe.session.user or "").strip()

    if not user or user == "Guest":
        return columns, []

    rows = frappe.db.sql(
        """
        SELECT
            ticket.name AS ticket,
            ticket.subject,
            ticket.status,
            ticket.priority,
            ticket.agent_group AS team,
            ticket.modified
        FROM `tabHD Ticket` ticket
        WHERE EXISTS (
            SELECT 1
            FROM `tabToDo` assignment
            WHERE assignment.reference_type = 'HD Ticket'
              AND assignment.reference_name = ticket.name
              AND assignment.allocated_to = %(user)s
              AND assignment.status = 'Open'
        )
        ORDER BY ticket.modified DESC
        LIMIT 200
        """,
        {
            "user": user,
        },
        as_dict=True,
    )

    return columns, rows