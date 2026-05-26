import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.data import escape_html


_INTERNAL_RESOLUTION_ROLES = {
    "System Manager",
    "TELECTRO-POC Role - Tech",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
    "Agent",
}


@frappe.whitelist()
def resolve_customer_ticket(ticket_name: str, resolution_note: str):
    """Resolve a Customer ticket with a deliberate Customer-visible update."""

    ticket_name = (ticket_name or "").strip()
    resolution_note = (resolution_note or "").strip()

    if not ticket_name:
        frappe.throw(_("Ticket is required"))

    if not resolution_note:
        frappe.throw(_("Customer-visible resolution update is required"))

    _require_internal_resolution_access()

    doc = frappe.get_doc("HD Ticket", ticket_name)

    if not _is_customer_ticket(doc):
        frappe.throw(_("This action is only available for Customer tickets"))

    current_status = (doc.get("status") or "").strip()
    if current_status in {"Resolved", "Closed"}:
        frappe.throw(_("This ticket is already resolved or closed"))

    comm_count_before = _count_ticket_communications(doc.name)
    comment_count_before = _count_ticket_comments(doc.name)

    comm = _create_customer_visible_resolution_communication(doc, resolution_note)

    frappe.db.set_value(
        "HD Ticket",
        doc.name,
        "status",
        "Resolved",
        update_modified=True,
    )

    audit_comment = _add_internal_resolution_audit_comment(doc.name, resolution_note)

    frappe.db.commit()

    final_status = frappe.db.get_value("HD Ticket", doc.name, "status")

    return {
        "name": doc.name,
        "status": final_status,
        "communication": comm.name,
        "communications_before": comm_count_before,
        "communications_after": _count_ticket_communications(doc.name),
        "comment": audit_comment.name if audit_comment else None,
        "comments_before": comment_count_before,
        "comments_after": _count_ticket_comments(doc.name),
        "message": _("Customer ticket resolved"),
    }


def _require_internal_resolution_access():
    roles = set(frappe.get_roles(frappe.session.user))
    if not roles.intersection(_INTERNAL_RESOLUTION_ROLES):
        frappe.throw(_("You are not allowed to resolve Customer tickets"))


def _is_customer_ticket(doc) -> bool:
    if doc.get("via_customer_portal"):
        return True

    if (doc.get("custom_request_source") or "").strip() == "Customer":
        return True

    if doc.get("customer") and doc.get("raised_by"):
        return True

    return False


def _create_customer_visible_resolution_communication(doc, resolution_note: str):
    recipient = (doc.get("raised_by") or "").strip()
    if not recipient:
        frappe.throw(_("Customer email / raised by is missing on this ticket"))

    subject = f"Re: {doc.get('subject') or doc.name} (#{doc.name})"
    content = (
        '<div class="ql-editor read-mode">'
        f"<p>{escape_html(resolution_note)}</p>"
        "</div>"
    )

    comm = frappe.get_doc(
        {
            "doctype": "Communication",
            "communication_type": "Communication",
            "communication_medium": "Email",
            "sent_or_received": "Sent",
            "email_status": "Open",
            "sender": frappe.session.user,
            "recipients": recipient,
            "subject": subject,
            "content": content,
            "status": "Linked",
            "reference_doctype": "HD Ticket",
            "reference_name": doc.name,
            "communication_date": now_datetime(),
        }
    )
    comm.insert(ignore_permissions=True)
    return comm


def _add_internal_resolution_audit_comment(ticket_name: str, resolution_note: str):
    doc = frappe.get_doc("HD Ticket", ticket_name)
    return doc.add_comment(
        "Comment",
        _(
            "Customer Ticket Resolution | Resolved by {0} | Customer-visible update: {1}"
        ).format(frappe.session.user, resolution_note),
    )


def _count_ticket_communications(ticket_name: str) -> int:
    return frappe.db.count(
        "Communication",
        {
            "reference_doctype": "HD Ticket",
            "reference_name": ticket_name,
        },
    )


def _count_ticket_comments(ticket_name: str) -> int:
    return frappe.db.count(
        "Comment",
        {
            "reference_doctype": "HD Ticket",
            "reference_name": ticket_name,
            "comment_type": "Comment",
        },
    )