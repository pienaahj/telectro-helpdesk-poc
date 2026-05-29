import frappe
from frappe import _
from frappe.utils.data import escape_html


def notify_ticket_action_required(
    *,
    ticket_name: str,
    for_user: str,
    actor_user: str | None = None,
    action_text: str,
    email_intro: str,
    note: str | None = None,
    note_label: str = "Note",
):
    """
    Create an in-app Notification Log and send a mobile-friendly email alert.

    Email failures must never break the workflow action that triggered the
    notification.
    """

    ticket_name = str(ticket_name or "").strip()
    for_user = str(for_user or "").strip()
    actor_user = str(actor_user or "").strip() or frappe.session.user
    action_text = str(action_text or "").strip()
    email_intro = str(email_intro or "").strip()
    note = str(note or "").strip()
    note_label = str(note_label or "Note").strip() or "Note"

    result = {
        "notification": None,
        "email_attempted": 0,
        "email_sent": 0,
        "email_error": "",
    }

    if not ticket_name or not for_user or not action_text:
        return result

    if for_user in {"Administrator", "Guest"}:
        return result

    user_email = (
        frappe.db.get_value("User", for_user, "email")
        or for_user
        or ""
    ).strip()

    if not user_email or "@" not in user_email:
        result["email_error"] = "No valid recipient email"
        return result

    doc = frappe.get_doc("HD Ticket", ticket_name)

    notification_name = _create_notification_log(
        doc=doc,
        for_user=for_user,
        actor_user=actor_user,
        action_text=action_text,
        email_intro=email_intro,
        note=note,
        note_label=note_label,
    )

    result["notification"] = notification_name

    email_result = _send_ticket_action_email(
        doc=doc,
        recipient=user_email,
        action_text=action_text,
        email_intro=email_intro,
        note=note,
        note_label=note_label,
    )

    result.update(email_result)
    return result


def _create_notification_log(
    *,
    doc,
    for_user: str,
    actor_user: str,
    action_text: str,
    email_intro: str,
    note: str | None = None,
    note_label: str = "Note",
):
    subject = escape_html(doc.get("subject") or doc.name)
    ticket_label = escape_html(doc.name)
    actor_label = escape_html(
        frappe.db.get_value("User", actor_user, "full_name") or actor_user
    )

    notification_subject = (
        f"<strong>{actor_label}</strong> {escape_html(action_text)} "
        f"<strong>HD Ticket</strong> "
        f'<b class="subject-title">{subject}</b>'
    )

    email_content = (
        f"<p>{escape_html(email_intro)} "
        f"<strong>HD Ticket {ticket_label}</strong>.</p>"
    )

    if note:
        email_content += (
            f"<p><strong>{escape_html(note_label)}:</strong> "
            f"{escape_html(note)}</p>"
        )

    notification = frappe.get_doc(
        {
            "doctype": "Notification Log",
            "subject": notification_subject,
            "for_user": for_user,
            "type": "Alert",
            "document_type": "HD Ticket",
            "document_name": doc.name,
            "email_content": email_content,
        }
    )
    notification.insert(ignore_permissions=True)

    return notification.name


def _send_ticket_action_email(
    *,
    doc,
    recipient: str,
    action_text: str,
    email_intro: str,
    note: str | None = None,
    note_label: str = "Note",
):
    result = {
        "email_attempted": 1,
        "email_sent": 0,
        "email_error": "",
    }

    try:
        base_url = (frappe.utils.get_url() or "").rstrip("/")
        ticket_url = f"{base_url}/app/hd-ticket/{doc.name}"

        subject = f"Action required: HD Ticket {doc.name} - {doc.get('subject') or doc.name}"

        lines = [
            "<p>A ticket requires your attention.</p>",
            "<table>",
            _email_row("Ticket", doc.name),
            _email_row("Subject", doc.get("subject")),
            _email_row("Customer", doc.get("customer") or doc.get("custom_customer")),
            _email_row("Campus", doc.get("custom_site_group")),
            _email_row("Service Area", doc.get("custom_service_area")),
            _email_row("Status", doc.get("status")),
            _email_row("Priority", doc.get("priority")),
            "</table>",
            f"<p>{escape_html(email_intro)}</p>",
        ]

        if note:
            lines.append(
                f"<p><strong>{escape_html(note_label)}:</strong> {escape_html(note)}</p>"
            )

        lines.append(
            f'<p><a href="{escape_html(ticket_url)}">Open HD Ticket {escape_html(doc.name)}</a></p>'
        )

        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message="\n".join(lines),
            reference_doctype="HD Ticket",
            reference_name=doc.name,
            delayed=True,
        )

        result["email_sent"] = 1

    except Exception:
        result["email_error"] = frappe.get_traceback()
        frappe.log_error(
            title="TELECTRO action notification email failed",
            message=result["email_error"],
        )

    return result


def _email_row(label: str, value) -> str:
    value = str(value or "").strip()
    if not value:
        return ""

    return (
        "<tr>"
        f"<td><strong>{escape_html(label)}:</strong></td>"
        f"<td>{escape_html(value)}</td>"
        "</tr>"
    )