import frappe


ACTIVE_EXCLUDED_STATUSES = ("Closed", "Archived", "Resolved")


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
            "width": 100,
        },
        {
            "label": "Priority",
            "fieldname": "priority",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Request Source",
            "fieldname": "custom_request_source",
            "fieldtype": "Data",
            "width": 145,
        },
        {
            "label": "Fulfilment Party",
            "fieldname": "custom_fulfilment_party",
            "fieldtype": "Data",
            "width": 145,
        },
        {
            "label": "Fulfilment Status",
            "fieldname": "custom_partner_work_state",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Work Completed",
            "fieldname": "custom_partner_work_completed",
            "fieldtype": "Date",
            "width": 140,
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
    return frappe.db.sql(
        """
        select
            t.name,
            t.subject,
            t.status,
            t.priority,
            coalesce(t.custom_request_source, '') as custom_request_source,
            coalesce(t.custom_fulfilment_party, '') as custom_fulfilment_party,
            coalesce(t.custom_partner_work_state, '') as custom_partner_work_state,
            t.custom_partner_work_completed as custom_partner_work_completed,
            coalesce(t.raised_by, '') as raised_by,
            t.modified,
            'HD Ticket' as reference_doctype
        from `tabHD Ticket` t
        where coalesce(t.custom_fulfilment_party, '') = 'Partner'
          and coalesce(t.status, '') not in %s
        order by t.modified desc
        """,
        (ACTIVE_EXCLUDED_STATUSES,),
        as_dict=True,
    )