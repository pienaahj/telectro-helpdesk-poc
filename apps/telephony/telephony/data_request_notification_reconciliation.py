"""Reconcile Data Request email intents with native Frappe Email Queue.

An existing queue is never recreated here.
The caller owns the database transaction.
"""

import frappe

from telephony.data_request_notification_delivery import DOCTYPE


QUEUE_STATES = {
    "Not Sent": "Queued",
    "Sending": "Queued",
    "Sent": "Sent",
    "Partially Sent": "Failed",
    "Error": "Failed",
}


def classify_email_queue_status(status):
    """Map native queue status to conservative intent state."""

    value = str(status or "").strip()

    if value not in QUEUE_STATES:
        raise ValueError(
            f"Unsupported Email Queue status: {value!r}"
        )

    return QUEUE_STATES[value]


def reconcile_intent_email_state(intent_name):
    """Update intent email state without enqueueing or committing."""

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
        raise ValueError(
            f"Notification intent not found: {name}"
        )

    intent = frappe.get_doc(DOCTYPE, name)

    current = str(intent.get("email_state") or "").strip()
    queue_name = str(intent.get("email_queue") or "").strip()

    if current not in {"Queued", "Sent", "Failed"}:
        raise ValueError(
            f"Intent cannot be reconciled in state: {current}"
        )

    if not queue_name:
        raise ValueError(
            "Email reconciliation requires an existing queue"
        )

    queue = frappe.get_doc("Email Queue", queue_name)

    if (
        queue.reference_doctype != DOCTYPE
        or str(queue.reference_name) != name
        or queue.get("communication")
    ):
        raise ValueError(
            "Email Queue identity or privacy mismatch"
        )

    native_status = str(queue.status or "").strip()
    updated = classify_email_queue_status(native_status)

    # Never silently downgrade a previously recorded Sent state.
    if current == "Sent" and updated != "Sent":
        raise ValueError(
            "Previously sent email has inconsistent queue status"
        )

    if updated != current:
        frappe.db.set_value(
            DOCTYPE,
            name,
            "email_state",
            updated,
        )

    return {
        "intent": name,
        "email_queue": queue_name,
        "queue_status": native_status,
        "email_state": updated,
        "changed": updated != current,
    }
