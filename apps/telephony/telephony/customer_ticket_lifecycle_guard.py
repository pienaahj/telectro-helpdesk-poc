import frappe
from frappe import _


_INTERNAL_FINALISATION_ROLES = {
    "System Manager",
    "TELECTRO-POC Role - Tech",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
    "Agent",
}


def prevent_customer_portal_ticket_closure(doc, method=None):
    """Prevent Customer portal users from closing Customer tickets in V1.

    Customer Ticket Lifecycle V1 is Telectro-finalised:
    customers can create tickets and add information, but Telectro closes
    customer tickets internally after confirming the outcome with the customer.
    """

    if doc.doctype != "HD Ticket":
        return

    if doc.is_new():
        return

    if not doc.has_value_changed("status"):
        return

    new_status = (doc.get("status") or "").strip()
    if new_status != "Closed":
        return

    if frappe.session.user in ("Administrator", "Guest"):
        return

    if _is_internal_finalisation_user():
        return

    if not _is_customer_portal_context(doc):
        return

    frappe.throw(
        _(
            "Customer portal users cannot close tickets. "
            "Telectro will close the ticket after confirming the outcome with the customer."
        )
    )


def _is_internal_finalisation_user() -> bool:
    roles = set(frappe.get_roles(frappe.session.user))
    return bool(roles.intersection(_INTERNAL_FINALISATION_ROLES))


def _is_customer_portal_context(doc) -> bool:
    if doc.get("via_customer_portal"):
        return True

    if (doc.get("custom_request_source") or "").strip() == "Customer":
        return True

    roles = set(frappe.get_roles(frappe.session.user))
    if "Customer" in roles:
        return True

    user_type = frappe.db.get_value("User", frappe.session.user, "user_type")
    return user_type == "Website User"
