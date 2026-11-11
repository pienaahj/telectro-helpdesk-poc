import frappe

from helpdesk.utils import get_customer


DATA_REQUEST = "Data Request"


def _is_data_request(doc):
    return (
        str(doc.get("custom_service_area") or "").strip()
        == DATA_REQUEST
    )


def _require_customer_account(doc, *, require_ticket_customer=False):
    actor = str(frappe.session.user or "").strip()

    if actor in ("", "Guest", "Administrator"):
        raise frappe.PermissionError(
            "Data Requests must be created by a Customer account."
        )

    user = frappe.db.get_value(
        "User",
        actor,
        ["enabled", "user_type"],
        as_dict=True,
    )

    if (
        not user
        or not user.enabled
        or user.user_type != "Website User"
    ):
        raise frappe.PermissionError(
            "Data Requests must be created by a Customer account."
        )

    customers = set(get_customer(actor))

    if not customers:
        raise frappe.PermissionError(
            "A linked Helpdesk Customer is required."
        )

    customer = doc.get("customer")

    if require_ticket_customer and not customer:
        raise frappe.PermissionError(
            "Data Request requires a linked HD Customer."
        )

    if customer and customer not in customers:
        raise frappe.PermissionError(
            "Data Request Customer is not authorized."
        )

    raised_by = str(doc.get("raised_by") or "").strip()

    if raised_by and raised_by != actor:
        raise frappe.PermissionError(
            "Data Request requester must match the Customer account."
        )


def prepare_data_request_insert(doc, method=None):
    """Prepare Customer Data Requests before native priority/SLA selection."""

    if not _is_data_request(doc):
        return

    _require_customer_account(doc)

    # Reject contradictory selections from the native Customer Portal
    # before normalization could hide the submitted Ticket Type.
    if (
        doc.get("via_customer_portal")
        and str(doc.get("ticket_type") or "").strip()
        != "Service Request"
    ):
        raise frappe.ValidationError(
            "Data Requests must be Service Requests."
        )

    # Data Requests are Service Requests, not equipment faults.
    # Do not trust the Ticket Type supplied by the browser.
    doc.ticket_type = "Service Request"

    # Customer-supplied priority is not authoritative.
    # Authorized internal users may escalate to Urgent later.
    doc.priority = "High"

    doc.flags.data_request_intake_prepared = True


def validate_data_request_intake(doc, method=None):
    """Enforce the final classification after routing validation."""

    if not _is_data_request(doc):
        return

    if doc.is_new():
        _require_customer_account(
            doc,
            require_ticket_customer=True,
        )

        if not doc.flags.data_request_intake_prepared:
            raise frappe.PermissionError(
                "Data Request must be selected during Customer creation."
            )

        if doc.priority != "High":
            raise frappe.PermissionError(
                "New Data Request priority must be High."
            )

        return

    previous = doc.get_doc_before_save()

    if previous and not _is_data_request(previous):
        raise frappe.PermissionError(
            "Existing tickets cannot be converted to Data Requests."
        )
