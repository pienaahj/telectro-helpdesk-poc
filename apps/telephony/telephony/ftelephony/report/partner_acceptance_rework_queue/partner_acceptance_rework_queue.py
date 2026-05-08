import frappe

from telephony.partner_create import get_partner_note_summary


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
            "width": 300,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Customer",
            "fieldname": "customer_display",
            "fieldtype": "Data",
            "width": 210,
        },
        {
            "label": "Campus",
            "fieldname": "campus_display",
            "fieldtype": "Data",
            "width": 190,
        },
        {
            "label": "Fault Point",
            "fieldname": "fault_point_display",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Fault Asset",
            "fieldname": "fault_asset_display",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Request Type",
            "fieldname": "custom_request_type",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Service Area",
            "fieldname": "custom_service_area",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Severity",
            "fieldname": "custom_severity",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Partner Acceptance State",
            "fieldname": "custom_partner_acceptance_state",
            "fieldtype": "Data",
            "width": 190,
        },
        {
            "label": "Latest Rework Reason",
            "fieldname": "latest_partner_rework_note",
            "fieldtype": "Small Text",
            "width": 650,
        },
        {
            "label": "Raised By",
            "fieldname": "owner",
            "fieldtype": "Data",
            "width": 190,
        },
        {
            "label": "Assigned",
            "fieldname": "assigned_to",
            "fieldtype": "Data",
            "width": 190,
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
    rows = frappe.db.sql(
        """
        select
            t.name,
            t.subject,
            t.status,
            coalesce(t.custom_customer, '') as custom_customer,
            coalesce(t.customer, '') as customer,
            coalesce(t.custom_site_group, '') as custom_site_group,
            coalesce(t.custom_site, '') as custom_site,
            coalesce(t.custom_fault_asset, '') as custom_fault_asset,
            coalesce(t.custom_request_type, '') as custom_request_type,
            coalesce(t.custom_service_area, '') as custom_service_area,
            coalesce(t.custom_severity, '') as custom_severity,
            coalesce(t.custom_partner_acceptance_state, '') as custom_partner_acceptance_state,
            coalesce(t.custom_fulfilment_party, '') as custom_fulfilment_party,
            coalesce(t.custom_request_source, '') as custom_request_source,
            coalesce(t.owner, '') as owner,
            coalesce(t._assign, '') as _assign,
            t.modified,
            'HD Ticket' as reference_doctype
        from `tabHD Ticket` t
        where coalesce(t.custom_request_source, '') = 'Partner'
          and coalesce(t.custom_fulfilment_party, '') = 'Telectro'
          and coalesce(t.custom_partner_acceptance_state, '') = 'Rework Required'
          and coalesce(t.status, '') not in %s
        order by t.modified desc
        """,
        (ACTIVE_EXCLUDED_STATUSES,),
        as_dict=True,
    )

    for row in rows:
        row.update(get_partner_note_summary(row.name))

        row["customer_display"] = get_customer_display_name(
            row.get("custom_customer") or row.get("customer")
        )
        row["campus_display"] = get_location_display_name(row.get("custom_site_group"))
        row["fault_point_display"] = get_location_display_name(row.get("custom_site"))
        row["fault_asset_display"] = get_location_display_name(row.get("custom_fault_asset"))
        row["assigned_to"] = clean_assign(row.get("_assign"))

    return rows


def get_customer_display_name(customer):
    return get_display_value("Customer", customer, ["customer_name"])


def get_location_display_name(location):
    return get_display_value("Location", location, ["location_name"])


def get_display_value(doctype, name, display_fields):
    name = (name or "").strip()

    if not name:
        return "-"

    if not frappe.db.exists(doctype, name):
        return name

    for fieldname in display_fields:
        value = frappe.db.get_value(doctype, name, fieldname)

        if value:
            return value

    title_field = frappe.get_meta(doctype).title_field

    if title_field:
        value = frappe.db.get_value(doctype, name, title_field)

        if value:
            return value

    return name


def clean_assign(raw_assign):
    raw_assign = (raw_assign or "").strip()

    if not raw_assign or raw_assign == "[]":
        return "-"

    try:
        parsed = frappe.parse_json(raw_assign)
    except Exception:
        return raw_assign

    if isinstance(parsed, list):
        return ", ".join([user for user in parsed if user]) or "-"

    return str(parsed or "-")