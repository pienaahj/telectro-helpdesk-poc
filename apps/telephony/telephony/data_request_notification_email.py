"""Transactional email queueing for Data Request notification intents.

The caller owns commit/rollback. Queueing is not SMTP delivery.
"""

from html import escape

import frappe

from telephony.data_request_notification_delivery import (
    DOCTYPE,
    _require_authorized_recipient,
)
from telephony.data_request_escalation_recipients import (
    EMAIL_PATTERN,
)


def queue_intent_email(intent_name):
    """Queue one internal email, or reuse its existing queue record."""

    name = str(intent_name or "").strip()

    if not name:
        raise ValueError("Notification intent identity required")

    locked = frappe.db.sql(
        """
        SELECT name
        FROM `tabTELECTRO Data Request Notification Intent`
        WHERE name = %s
        FOR UPDATE
        """,
        (name,),
        as_dict=True,
    )

    if not locked:
        raise ValueError(f"Notification intent not found: {name}")

    intent = frappe.get_doc(DOCTYPE, name)

    state = str(intent.get("email_state") or "").strip()
    existing_queue = str(intent.get("email_queue") or "").strip()

    if state in {"Queued", "Sent"}:
        if not existing_queue:
            raise ValueError(
                "Queued or sent email has no Email Queue reference"
            )

        queue = frappe.get_doc("Email Queue", existing_queue)

        if (
            queue.reference_doctype != DOCTYPE
            or str(queue.reference_name) != name
            or queue.get("communication")
        ):
            raise ValueError(
                "Existing Email Queue identity or privacy mismatch"
            )

        return queue.name

    if state not in {"Pending", "Failed"}:
        raise ValueError(f"Unexpected email state: {state}")

    if existing_queue:
        raise ValueError(
            "Existing Email Queue requires reconciliation; "
            "refusing duplicate queue creation"
        )

    ticket = frappe.get_doc(
        "HD Ticket",
        intent.get("ticket"),
    )

    _require_authorized_recipient(intent, ticket)

    recipient = str(intent.get("recipient") or "").strip()

    email = str(
        frappe.db.get_value(
            "User",
            recipient,
            "email",
        ) or ""
    ).strip()

    if not EMAIL_PATTERN.fullmatch(email):
        raise frappe.PermissionError(
            "Recipient has no valid email address"
        )

    event = str(intent.get("event") or "").strip()

    if event == "arrival":
        subject = f"New Data Request — HD Ticket {ticket.name}"
        action = "A new Data Request requires attention."

    elif event == "escalation":
        subject = (
            f"Data Request escalation — HD Ticket {ticket.name}"
        )
        action = (
            "This Data Request reached the ten-minute "
            "escalation threshold."
        )

    else:
        raise ValueError(
            f"Unsupported notification event: {event}"
        )

    base_url = (frappe.utils.get_url() or "").rstrip("/")
    ticket_name = escape(str(ticket.name), quote=True)

    ticket_url = escape(
        f"{base_url}/app/hd-ticket/{ticket.name}",
        quote=True,
    )

    message = (
        f"<p>{escape(action)}</p>"
        f"<p>HD Ticket {ticket_name}</p>"
        f'<p><a href="{ticket_url}">'
        f"Open internal Helpdesk ticket"
        f"</a></p>"
    )

    queue = frappe.sendmail(
        recipients=[email],
        subject=subject,
        message=message,
        delayed=True,
        queue_separately=False,
        reference_doctype=DOCTYPE,
        reference_name=name,
        communication=None,
        is_notification=True,
        add_unsubscribe_link=0,
    )

    if not queue or not getattr(queue, "name", None):
        raise ValueError(
            "Frappe did not return a persisted Email Queue"
        )

    if (
        queue.get("communication")
        or queue.reference_doctype != DOCTYPE
        or str(queue.reference_name) != name
    ):
        raise ValueError(
            "Created Email Queue identity or privacy mismatch"
        )

    frappe.db.set_value(
        DOCTYPE,
        name,
        {
            "email_queue": queue.name,
            "email_state": "Queued",
        },
    )

    return queue.name
