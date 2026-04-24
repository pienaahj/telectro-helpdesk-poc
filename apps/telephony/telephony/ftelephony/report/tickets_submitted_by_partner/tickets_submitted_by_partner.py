import frappe


ACTIVE_EXCLUDED_STATUSES = ("Archived", "Resolved", "Closed")


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
            "label": "Request Type",
            "fieldname": "custom_request_type",
            "fieldtype": "Data",
            "width": 170,
        },
        {
            "label": "Partner Acceptance State",
            "fieldname": "custom_partner_acceptance_state",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Partner Accepted On",
            "fieldname": "custom_partner_accepted_on",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": "Fulfilment Party",
            "fieldname": "custom_fulfilment_party",
            "fieldtype": "Data",
            "width": 140,
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
    return frappe.db.sql(
        """
        select
            t.name,
            t.subject,
            t.status,
            t.priority,
            coalesce(t.custom_request_type, '') as custom_request_type,
            coalesce(t.custom_partner_acceptance_state, '') as custom_partner_acceptance_state,
            t.custom_partner_accepted_on,
            coalesce(t.custom_fulfilment_party, '') as custom_fulfilment_party,
            t.modified,
            'HD Ticket' as reference_doctype
        from `tabHD Ticket` t
        where coalesce(t.custom_request_source, '') = 'Partner'
          and coalesce(t.status, '') not in %s
        order by t.modified desc
        """,
        (ACTIVE_EXCLUDED_STATUSES,),
        as_dict=True,
    )