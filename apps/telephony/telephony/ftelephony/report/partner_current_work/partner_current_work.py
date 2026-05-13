import frappe
from datetime import datetime

from telephony.partner_create import get_partner_note_summary


ACTIVE_EXCLUDED_STATUSES = ("Closed", "Archived", "Resolved")


def execute(filters=None):
    return get_columns(), get_data()


def get_columns():
    return [
        {
            "label": "Current Work Bucket",
            "fieldname": "current_work_bucket",
            "fieldtype": "Data",
            "width": 240,
        },
        {
            "label": "Waiting On",
            "fieldname": "waiting_on",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Next Action",
            "fieldname": "next_action",
            "fieldtype": "Data",
            "width": 300,
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
            "label": "Priority",
            "fieldname": "priority",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Request Type",
            "fieldname": "custom_request_type",
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
            "width": 180,
        },
        {
            "label": "Latest Partner Note",
            "fieldname": "latest_partner_note",
            "fieldtype": "Small Text",
            "width": 520,
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
            t.priority,
            coalesce(t.custom_request_type, '') as custom_request_type,
            coalesce(t.custom_request_source, '') as custom_request_source,
            coalesce(t.custom_fulfilment_party, '') as custom_fulfilment_party,
            coalesce(t.custom_partner_acceptance_state, '') as custom_partner_acceptance_state,
            t.custom_partner_accepted_on,
            coalesce(t.custom_partner_work_state, '') as custom_partner_work_state,
            t.custom_partner_work_completed,
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
        action = classify_partner_current_work(row)

        if not action:
            continue

        notes = get_partner_note_summary(row.name)

        row["current_work_bucket"] = action["bucket"]
        row["waiting_on"] = action["waiting_on"]
        row["next_action"] = action["next_action"]
        row["latest_partner_note"] = get_latest_note_for_action(
            action["note_key"],
            notes,
        )

        data.append(row)

    return sorted(
        data,
        key=lambda row: (
            action_sort_key(row.get("current_work_bucket")),
            -modified_sort_value(row).timestamp(),
        ),
    )


def classify_partner_current_work(row):
    request_source = (row.get("custom_request_source") or "").strip()
    fulfilment_party = (row.get("custom_fulfilment_party") or "").strip()
    acceptance_state = (row.get("custom_partner_acceptance_state") or "").strip()
    work_state = (row.get("custom_partner_work_state") or "").strip()

    if request_source == "Partner" and fulfilment_party != "Partner":
        if acceptance_state == "Pending Partner Acceptance":
            return {
                "bucket": "Acceptance requested",
                "waiting_on": "Partner",
                "next_action": "Submit acceptance note or request rework",
                "note_key": "latest_partner_acceptance_request_note",
            }

        if acceptance_state == "Rework Required":
            return {
                "bucket": "Acceptance rework with Telectro",
                "waiting_on": "Telectro",
                "next_action": "Monitor Telectro rework progress",
                "note_key": "latest_partner_rework_note",
            }

        if acceptance_state == "Accepted by Partner":
            return {
                "bucket": "Waiting for Telectro acceptance review",
                "waiting_on": "Telectro",
                "next_action": "Monitor Telectro acceptance review outcome",
                "note_key": "latest_partner_acceptance_note",
            }

        if not acceptance_state:
            return {
                "bucket": "Submitted request open",
                "waiting_on": "Telectro",
                "next_action": "Monitor submitted request",
                "note_key": "latest_partner_review_note",
            }

    if fulfilment_party == "Partner":
        if work_state == "Assigned to Partner":
            return {
                "bucket": "Work assigned to Partner",
                "waiting_on": "Partner",
                "next_action": "Complete work and submit work done note",
                "note_key": "latest_partner_review_note",
            }

        if work_state == "Rework Required":
            return {
                "bucket": "Work rework required",
                "waiting_on": "Partner",
                "next_action": "Complete rework and resubmit work done note",
                "note_key": "latest_partner_work_rework_note",
            }

        if work_state == "Work Completed by Partner":
            return {
                "bucket": "Waiting for Telectro work review",
                "waiting_on": "Telectro",
                "next_action": "Monitor Telectro work review outcome",
                "note_key": "latest_partner_work_done_note",
            }

        if work_state == "Reviewed by Telectro":
            return {
                "bucket": "Work reviewed by Telectro",
                "waiting_on": "Telectro",
                "next_action": "Monitor ticket resolution or closure",
                "note_key": "latest_partner_work_review_note",
            }

    return None


def get_latest_note_for_action(note_key, notes):
    preferred_note = (notes or {}).get(note_key)

    if preferred_note:
        return preferred_note

    for fallback_key in (
        "latest_partner_acceptance_request_note",
        "latest_partner_acceptance_note",
        "latest_partner_rework_note",
        "latest_partner_work_done_note",
        "latest_partner_work_rework_note",
        "latest_partner_work_review_note",
        "latest_partner_review_note",
    ):
        fallback_note = (notes or {}).get(fallback_key)

        if fallback_note:
            return fallback_note

    return ""


def action_sort_key(bucket):
    order = {
        "Acceptance requested": 10,
        "Work rework required": 20,
        "Work assigned to Partner": 30,
        "Waiting for Telectro work review": 40,
        "Waiting for Telectro acceptance review": 50,
        "Acceptance rework with Telectro": 60,
        "Submitted request open": 70,
        "Work reviewed by Telectro": 80,
    }

    return order.get(bucket or "", 999)


def modified_sort_value(row):
    return row.get("modified") or datetime.min
