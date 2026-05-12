import frappe

from telephony.partner_create import get_partner_note_summary
from datetime import datetime


ACTIVE_EXCLUDED_STATUSES = ("Closed", "Archived", "Resolved")


def modified_sort_value(row):
    return row.get("modified") or datetime.min

def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {
            "label": "Action Bucket",
            "fieldname": "action_bucket",
            "fieldtype": "Data",
            "width": 260,
        },
        {
            "label": "Waiting On",
            "fieldname": "waiting_on",
            "fieldtype": "Data",
            "width": 130,
        },
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
            "label": "Acceptance State",
            "fieldname": "custom_partner_acceptance_state",
            "fieldtype": "Data",
            "width": 190,
        },
        {
            "label": "Work State",
            "fieldname": "custom_partner_work_state",
            "fieldtype": "Data",
            "width": 190,
        },
        {
            "label": "Latest Partner Note",
            "fieldname": "latest_partner_note",
            "fieldtype": "Small Text",
            "width": 520,
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
            coalesce(t.custom_request_source, '') as custom_request_source,
            coalesce(t.custom_fulfilment_party, '') as custom_fulfilment_party,
            coalesce(t.custom_partner_acceptance_state, '') as custom_partner_acceptance_state,
            t.custom_partner_accepted_on,
            coalesce(t.custom_partner_work_state, '') as custom_partner_work_state,
            t.custom_partner_work_completed,
            coalesce(t.owner, '') as owner,
            coalesce(t._assign, '') as _assign,
            t.modified,
            'HD Ticket' as reference_doctype
        from `tabHD Ticket` t
        where coalesce(t.status, '') not in %s
          and (
                coalesce(t.custom_request_source, '') = 'Partner'
                or coalesce(t.custom_fulfilment_party, '') = 'Partner'
              )
        order by t.modified desc
        """,
        (ACTIVE_EXCLUDED_STATUSES,),
        as_dict=True,
    )

    data = []

    for row in rows:
        action = classify_partner_action(row)

        if not action:
            continue

        notes = get_partner_note_summary(row.name)

        row["action_bucket"] = action["bucket"]
        row["waiting_on"] = action["waiting_on"]
        row["customer_display"] = get_customer_display_name(
            row.get("custom_customer") or row.get("customer")
        )
        row["campus_display"] = get_location_display_name(row.get("custom_site_group"))
        row["fault_point_display"] = get_location_display_name(row.get("custom_site"))
        row["assigned_to"] = clean_assign(row.get("_assign"))
        row["latest_partner_note"] = get_latest_note_for_action(action["note_key"], notes)

        data.append(row)

    return sorted(
        data,
        key=lambda row: (
            action_sort_key(row.get("action_bucket")),
            -modified_sort_value(row).timestamp(),
        ),
    )


def classify_partner_action(row):
    request_source = row.get("custom_request_source")
    fulfilment_party = row.get("custom_fulfilment_party")
    acceptance_state = row.get("custom_partner_acceptance_state")
    work_state = row.get("custom_partner_work_state")

    if request_source == "Partner" and fulfilment_party == "Telectro":
        if acceptance_state == "Rework Required":
            return {
                "bucket": "Partner Acceptance Rework Required",
                "waiting_on": "Telectro",
                "note_key": "latest_partner_review_note",
            }

        if acceptance_state == "Accepted by Partner":
            return {
                "bucket": "Partner Accepted / Telectro Review Needed",
                "waiting_on": "Telectro",
                "note_key": "latest_partner_acceptance_note",
            }

        if acceptance_state == "Pending Partner Acceptance":
            return {
                "bucket": "Pending Partner Acceptance",
                "waiting_on": "Partner",
                "note_key": "latest_partner_review_note",
            }

    if fulfilment_party == "Partner":
        if work_state == "Work Completed by Partner":
            return {
                "bucket": "Partner Work Completed / Telectro Review Needed",
                "waiting_on": "Telectro",
                "note_key": "latest_partner_work_done_note",
            }

        if work_state == "Rework Required":
            return {
                "bucket": "Partner Work Rework Required",
                "waiting_on": "Partner",
                "note_key": "latest_partner_review_note",
            }

        if work_state == "Assigned to Partner":
            return {
                "bucket": "Assigned to Partner",
                "waiting_on": "Partner",
                "note_key": "latest_partner_review_note",
            }

    return None


def get_latest_note_for_action(note_key, notes):
    preferred_note = (notes or {}).get(note_key)

    if preferred_note:
        return preferred_note

    for fallback_key in (
        "latest_partner_review_note",
        "latest_partner_acceptance_note",
        "latest_partner_work_done_note",
    ):
        fallback_note = (notes or {}).get(fallback_key)

        if fallback_note:
            return fallback_note

    return ""


def action_sort_key(action_bucket):
    order = {
        "Partner Acceptance Rework Required": 10,
        "Partner Work Completed / Telectro Review Needed": 20,
        "Partner Accepted / Telectro Review Needed": 30,
        "Pending Partner Acceptance": 40,
        "Partner Work Rework Required": 50,
        "Assigned to Partner": 60,
    }

    return order.get(action_bucket or "", 999)


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