"""First-completion audit for Data Request tickets.

The first successful transition into Resolved is recorded once.
Subsequent reopening, closing, or editing must preserve that timestamp.

This module does not assign tickets, send notifications, or commit.
"""

import frappe
from frappe.utils import now_datetime


SERVICE_AREA = "Data Request"
COMPLETION_STATUS = "Resolved"
AUDIT_FIELD = "custom_data_request_first_completed_on"


def _clean(value):
    return str(value or "").strip()


def capture_first_completion(doc, method=None):
    """Validate audit immutability and record first resolution in-save."""
    if doc.doctype != "HD Ticket":
        return

    current_stamp = _clean(doc.get(AUDIT_FIELD))

    if doc.is_new():
        if current_stamp:
            frappe.throw(
                "Data Request completion audit cannot be supplied "
                "when creating a ticket.",
                frappe.PermissionError,
            )
        return

    previous = doc.get_doc_before_save()

    if previous is None:
        previous = frappe.db.get_value(
            "HD Ticket",
            doc.name,
            ["status", AUDIT_FIELD],
            as_dict=True,
        )

    if previous is None:
        frappe.throw(
            "Previous ticket state is unavailable for "
            "Data Request completion auditing.",
            frappe.ValidationError,
        )

    previous_stamp = _clean(previous.get(AUDIT_FIELD))

    if current_stamp != previous_stamp:
        frappe.throw(
            "The first Data Request completion timestamp "
            "cannot be changed manually.",
            frappe.PermissionError,
        )

    if previous_stamp:
        return

    if _clean(doc.get("custom_service_area")) != SERVICE_AREA:
        return

    if _clean(doc.get("status")) != COMPLETION_STATUS:
        return

    if _clean(previous.get("status")) == COMPLETION_STATUS:
        return

    # Set the field in memory. Frappe persists it with the ticket.
    # A failed save must not leave a standalone completion record.
    doc.set(AUDIT_FIELD, now_datetime())
