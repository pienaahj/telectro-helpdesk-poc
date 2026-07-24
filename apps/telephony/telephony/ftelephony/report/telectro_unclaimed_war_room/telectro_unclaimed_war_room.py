import frappe
from frappe import _


ALLOWED_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Tech",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
}


def _require_access():
    user = frappe.session.user

    if user == "Administrator":
        return

    roles = set(frappe.get_roles(user) or [])

    if not roles.intersection(ALLOWED_ROLES):
        frappe.throw(
            _("You are not allowed to view the unclaimed ticket war room."),
            frappe.PermissionError,
        )


def execute(filters=None):
    _require_access()

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
            "width": 300,
        },
        {
            "label": "Team",
            "fieldname": "team",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Service Area",
            "fieldname": "service_area",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Idle (min)",
            "fieldname": "idle_minutes",
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "label": "Last Updated",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 170,
        },
        {
            "label": "Created",
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 170,
        },
    ]

    rows = frappe.db.sql(
        """
        SELECT
            ticket.name AS ticket,
            ticket.subject,
            ticket.agent_group AS team,
            ticket.custom_service_area AS service_area,
            TIMESTAMPDIFF(
                MINUTE,
                ticket.modified,
                NOW()
            ) AS idle_minutes,
            ticket.modified,
            ticket.creation
        FROM `tabHD Ticket` ticket
        WHERE ticket.status = 'Open'
          AND COALESCE(
              ticket.custom_fulfilment_party,
              ''
          ) = 'Telectro'
          AND COALESCE(
              ticket._assign,
              ''
          ) IN ('', '[]')
          AND NOT EXISTS (
              SELECT 1
              FROM `tabToDo` assignment
              WHERE assignment.reference_type = 'HD Ticket'
                AND assignment.reference_name = ticket.name
                AND assignment.status = 'Open'
          )
        ORDER BY TIMESTAMPDIFF(
            MINUTE,
            ticket.modified,
            NOW()
        ) DESC
        """,
        as_dict=True,
    )

    return columns, rows
