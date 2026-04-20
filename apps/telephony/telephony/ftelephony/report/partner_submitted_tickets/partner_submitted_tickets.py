import frappe


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
            "label": "Fulfilment Party",
            "fieldname": "custom_fulfilment_party",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Request Source",
            "fieldname": "custom_request_source",
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
    user = frappe.session.user

    rows = frappe.db.sql(
        """
        select
            t.name,
            t.subject,
            t.status,
            t.priority,
            coalesce(t.custom_request_type, '') as custom_request_type,
            coalesce(t.custom_fulfilment_party, '') as custom_fulfilment_party,
            coalesce(t.custom_request_source, '') as custom_request_source,
            t.modified,
            'HD Ticket' as reference_doctype
        from `tabHD Ticket` t
        where t.owner = %s
        order by t.modified desc
        """,
        (user,),
        as_dict=True,
    )
    return rows