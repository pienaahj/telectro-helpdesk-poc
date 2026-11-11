"""Customer Portal ticket classification validation."""

import frappe


ALLOWED_TICKET_TYPES = frozenset({
    "Faults",
    "Service Request",
})

SERVICE_REQUEST = "Service Request"
DATA_REQUEST = "Data Request"
DEFAULT_REQUEST_TYPE = "Other"


def validate_customer_portal_ticket_type(doc, method=None):
    """Validate new Customer Portal ticket classification.

    Internal, email and existing-ticket workflows retain their
    established behaviour.
    """

    if not doc.is_new():
        return

    if not doc.get("via_customer_portal"):
        return

    actor = str(frappe.session.user or "").strip()

    if actor in ("", "Guest", "Administrator"):
        return

    # The native Helpdesk API can mark agent-created tickets as
    # portal-originated. Use the authenticated account type too.
    if frappe.db.get_value(
        "User",
        actor,
        "user_type",
    ) != "Website User":
        return

    ticket_type = str(doc.get("ticket_type") or "").strip()
    service_area = str(
        doc.get("custom_service_area") or ""
    ).strip()
    request_type = str(
        doc.get("custom_request_type") or ""
    ).strip()

    if ticket_type not in ALLOWED_TICKET_TYPES:
        frappe.throw(
            "Choose Report a Fault or Request a Service.",
            frappe.ValidationError,
        )

    if (
        service_area == DATA_REQUEST
        and ticket_type != SERVICE_REQUEST
    ):
        frappe.throw(
            "Data Requests must be Service Requests.",
            frappe.ValidationError,
        )

    if (
        ticket_type == SERVICE_REQUEST
        and request_type != DEFAULT_REQUEST_TYPE
    ):
        frappe.throw(
            "Customer Service Requests must use "
            "Request Type Other.",
            frappe.ValidationError,
        )
