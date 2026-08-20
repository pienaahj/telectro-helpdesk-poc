import frappe

from telephony.permissions import get_partner_ticket_report_condition


ARCHIVED_STATUSES = ("Archived", "Resolved", "Closed")


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {
            "label": "ID",
            "fieldname": "name",
            "fieldtype": "Data",
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
            "label": "Priority",
            "fieldname": "priority",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": "Request Source",
            "fieldname": "custom_request_source",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Fulfilment Party",
            "fieldname": "custom_fulfilment_party",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Raised By",
            "fieldname": "raised_by",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Modified",
            "fieldname": "modified",
            "fieldtype": "Datetime",
            "width": 170,
        },
        {
            "label": "Reference DocType",
            "fieldname": "reference_doctype",
            "fieldtype": "Data",
            "hidden": 1,
            "width": 1,
        },
    ]


def get_data():
    partner_condition = get_partner_ticket_report_condition(
        frappe.session.user,
        side="either",
    )

    partner_scope_clause = (
        f"and ({partner_condition})"
        if partner_condition
        else ""
    )

    return frappe.db.sql(
        f"""
        select
            t.name,
            t.subject,
            t.status,
            t.priority,
            coalesce(t.custom_request_source, '') as custom_request_source,
            coalesce(t.custom_fulfilment_party, '') as custom_fulfilment_party,
            coalesce(t.raised_by, '') as raised_by,
            t.modified,
            'HD Ticket' as reference_doctype
        from `tabHD Ticket` t
        where (
                coalesce(t.custom_request_source, '') = 'Partner'
                or coalesce(t.custom_fulfilment_party, '') = 'Partner'
              )
          and coalesce(t.status, '') in %s
          {partner_scope_clause}
        order by t.modified desc
        """,
        (ARCHIVED_STATUSES,),
        as_dict=True,
    )