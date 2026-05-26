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
def resolve_customer_ticket(
    ticket_name: str,
    resolution_note: str,
    completion_file: str | None = None,
):
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

    completion_file_doc = None
    if completion_file:
        completion_file_doc = _get_completion_file(doc.name, completion_file)

    comm = _create_customer_visible_resolution_communication(doc, resolution_note)

    completion_file_link = None
    if completion_file_doc:
        completion_file_link = _attach_completion_file_to_customer_communication(
            communication_name=comm.name,
            file_doc=completion_file_doc,
        )
    
    frappe.db.set_value(
        "HD Ticket",
        doc.name,
        "status",
        "Resolved",
        update_modified=True,
    )

    audit_comment = _add_internal_resolution_audit_comment(
        doc.name,
        resolution_note,
        completion_file_link.name if completion_file_link else None,
    )

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
        "completion_file": completion_file_link.name if completion_file_link else None,
    }


def _attach_completion_file_to_customer_communication(
    communication_name: str,
    file_doc,
):
    linked_file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_doc.file_name,
            "file_url": file_doc.file_url,
            "is_private": 1,
            "folder": file_doc.get("folder") or "Home/Attachments",
            "attached_to_doctype": "Communication",
            "attached_to_name": communication_name,
        }
    )
    linked_file.insert(ignore_permissions=True)

    return linked_file


def _get_completion_file(ticket_name: str, completion_file: str):
    completion_file = (completion_file or "").strip()
    if not completion_file:
        frappe.throw(_("Completion evidence file is required"))

    file_name = None

    if frappe.db.exists("File", completion_file):
        file_name = completion_file

    if not file_name:
        file_name = frappe.db.get_value("File", {"file_url": completion_file}, "name")

    if not file_name:
        file_name = frappe.db.get_value(
            "File",
            {
                "file_name": completion_file,
                "attached_to_doctype": "HD Ticket",
                "attached_to_name": ticket_name,
            },
            "name",
        )

    if not file_name:
        frappe.throw(_("Completion evidence file was not found"))

    file_doc = frappe.get_doc("File", file_name)

    attached_to_doctype = file_doc.get("attached_to_doctype")
    attached_to_name = file_doc.get("attached_to_name")

    if attached_to_doctype and attached_to_doctype != "HD Ticket":
        frappe.throw(_("Completion evidence must be attached to this ticket first"))

    if attached_to_doctype == "HD Ticket" and str(attached_to_name) != str(ticket_name):
        frappe.throw(_("Completion evidence must belong to the same ticket"))

    return file_doc



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


def _add_internal_resolution_audit_comment(
    ticket_name: str,
    resolution_note: str,
    completion_file_name: str | None = None,
):
    doc = frappe.get_doc("HD Ticket", ticket_name)

    message = _(
        "Customer Ticket Resolution | Resolved by {0} | Customer-visible update: {1}"
    ).format(frappe.session.user, resolution_note)

    if completion_file_name:
        message = _("{0} | Completion evidence shared: {1}").format(
            message,
            completion_file_name,
        )

    return doc.add_comment("Comment", message)


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
  
def _require_customer_ticket_access(doc):
    user = frappe.session.user

    if user == "Administrator":
        return

    roles = set(frappe.get_roles(user))
    if roles.intersection(_INTERNAL_RESOLUTION_ROLES):
        return

    if user != (doc.get("raised_by") or "").strip():
        frappe.throw(_("You are not allowed to access this ticket"))


def _get_customer_completion_evidence_file(
    ticket_name: str,
    file_url: str | None = None,
    file_id: str | None = None,
):
    filters = {
        "attached_to_doctype": "Communication",
    }

    if file_id:
        filters["name"] = file_id
    else:
        filters["file_url"] = file_url

    file_name = frappe.db.get_value("File", filters, "name")

    if not file_name:
        frappe.throw(_("Completion evidence file was not found"))

    file_doc = frappe.get_doc("File", file_name)

    communication_name = file_doc.get("attached_to_name")
    if not communication_name:
        frappe.throw(_("Completion evidence is not linked to a Customer update"))

    comm = frappe.get_doc("Communication", communication_name)

    if comm.get("reference_doctype") != "HD Ticket" or str(comm.get("reference_name")) != str(ticket_name):
        frappe.throw(_("Completion evidence does not belong to this ticket"))

    if (comm.get("sent_or_received") or "").strip() != "Sent":
        frappe.throw(_("Completion evidence is not Customer-facing"))

    return file_doc
  
@frappe.whitelist()
def download_customer_completion_evidence(
    ticket_name: str,
    file_url: str | None = None,
    file_id: str | None = None,
):
    ticket_name = (ticket_name or "").strip()
    file_url = (file_url or "").strip()
    file_id = (file_id or "").strip()

    if not ticket_name:
        frappe.throw(_("Ticket is required"))

    if not file_url and not file_id:
        frappe.throw(_("Completion evidence file is required"))

    doc = frappe.get_doc("HD Ticket", ticket_name)

    if not _is_customer_ticket(doc):
        frappe.throw(_("This action is only available for Customer tickets"))

    _require_customer_ticket_access(doc)

    file_doc = _get_customer_completion_evidence_file(
        ticket_name=ticket_name,
        file_url=file_url,
        file_id=file_id,
    )

    content = file_doc.get_content()
    frappe.local.response.filename = file_doc.file_name
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"