import frappe
from telephony.partner_create import get_partner_note_summary

EXCLUDED_STATUSES = ("Resolved", "Closed", "Archived")


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {
            "label": "ID",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "HD Ticket",
            "width": 90,
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
            "width": 120,
        },
        {
            "label": "Customer",
            "fieldname": "custom_customer",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Campus",
            "fieldname": "custom_site_group",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Request Type",
            "fieldname": "custom_request_type",
            "fieldtype": "Data",
            "width": 170,
        },
        {
            "label": "Partner Acceptance State",
            "fieldname": "custom_partner_acceptance_state",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": "Partner Accepted On",
            "fieldname": "custom_partner_accepted_on",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": "Partner Acceptance Note",
            "fieldname": "latest_partner_acceptance_note",
            "fieldtype": "Small Text",
            "width": 650,
        },
        {
            "label": "Modified",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 170,
        },
    ]


def get_data():
    rows = frappe.db.sql(
        """
        select
            t.name,
            t.subject,
            t.status,
            coalesce(t.custom_customer, '') as custom_customer,
            coalesce(t.custom_site_group, '') as custom_site_group,
            coalesce(t.custom_request_type, '') as custom_request_type,
            coalesce(t.custom_partner_acceptance_state, '') as custom_partner_acceptance_state,
            t.custom_partner_accepted_on,
            t.modified
        from `tabHD Ticket` t
        where coalesce(t.custom_request_source, '') = 'Partner'
          and coalesce(t.custom_partner_acceptance_state, '') = 'Accepted by Partner'
          and coalesce(t.status, '') not in %s
        order by
            t.custom_partner_accepted_on desc,
            t.modified desc
        """,
        (EXCLUDED_STATUSES,),
        as_dict=True,
    )

    for row in rows:
        row.update(get_partner_note_summary(row.name))

    return rows