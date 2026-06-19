import frappe


ACTIVE_EXCLUDED_STATUSES = ("Closed", "Archived", "Resolved")


def execute(filters=None):
    return get_columns(), get_data()


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
            "width": 110,
        },
        {
            "label": "Priority",
            "fieldname": "priority",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Request Type",
            "fieldname": "custom_request_type",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Account",
            "fieldname": "custom_customer",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Campus",
            "fieldname": "custom_site_group",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Site",
            "fieldname": "custom_site",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Service Area",
            "fieldname": "custom_service_area",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Request Source",
            "fieldname": "custom_request_source",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Fulfilment Party",
            "fieldname": "custom_fulfilment_party",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Acceptance State",
            "fieldname": "custom_partner_acceptance_state",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Work State",
            "fieldname": "custom_partner_work_state",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Raised By",
            "fieldname": "raised_by",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Owner",
            "fieldname": "owner",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Created",
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 170,
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
            coalesce(t.custom_customer, '') as custom_customer,
            coalesce(t.custom_site_group, '') as custom_site_group,
            coalesce(t.custom_site, '') as custom_site,
            coalesce(t.custom_service_area, '') as custom_service_area,
            coalesce(t.custom_request_source, '') as custom_request_source,
            coalesce(t.custom_fulfilment_party, '') as custom_fulfilment_party,
            coalesce(t.custom_partner_acceptance_state, '') as custom_partner_acceptance_state,
            coalesce(t.custom_partner_work_state, '') as custom_partner_work_state,
            t.raised_by,
            t.owner,
            t.creation,
            t.modified,
            'HD Ticket' as reference_doctype
        from `tabHD Ticket` t
        where coalesce(t.status, '') not in %s
          and coalesce(t.custom_request_source, '') = 'Partner'
          and coalesce(t.custom_fulfilment_party, '') != 'Partner'
          and coalesce(t.custom_partner_acceptance_state, '') = ''
          and coalesce(t.custom_partner_work_state, '') = ''
        order by t.creation desc, t.modified desc
        """,
        (ACTIVE_EXCLUDED_STATUSES,),
        as_dict=True,
    )
