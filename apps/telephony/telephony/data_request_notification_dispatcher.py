"""Transactional Data Request notification dispatcher.

Coordinates the previously verified in-app and email channels.

This module does not schedule work, commit transactions, or send
email directly. Failure recovery and batch scheduling are separate
responsibilities.
"""

import frappe

from telephony.data_request_notification_delivery import (
    DOCTYPE,
    record_in_app_alert,
)
from telephony.data_request_notification_email import (
    queue_intent_email,
)
from telephony.data_request_notification_reconciliation import (
    reconcile_intent_email_state,
)


DELIVERY_STATES = {
    "Queued": "Processing",
    "Sent": "Complete",
    "Failed": "Retry",
}


def dispatch_notification_intent(intent_name):
    """Process one intent without committing the caller's transaction."""

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

    event = str(intent.get("event") or "").strip()
    delivery_state = str(
        intent.get("delivery_state") or ""
    ).strip()
    in_app_state = str(
        intent.get("in_app_state") or ""
    ).strip()
    email_state = str(
        intent.get("email_state") or ""
    ).strip()
    email_queue = str(
        intent.get("email_queue") or ""
    ).strip()

    if event not in {"arrival", "escalation"}:
        raise ValueError(
            f"Unsupported notification event: {event}"
        )

    if delivery_state not in {
        "Pending", "Processing", "Retry", "Complete", "Failed"
    }:
        raise ValueError(
            f"Unsupported delivery state: {delivery_state}"
        )

    if in_app_state not in {"Pending", "Recorded", "Failed"}:
        raise ValueError(
            f"Unsupported in-app state: {in_app_state}"
        )

    if email_state not in {
        "Pending", "Queued", "Sent", "Failed"
    }:
        raise ValueError(
            f"Unsupported email state: {email_state}"
        )

    if email_queue and email_state == "Pending":
        raise ValueError(
            "Pending email has an existing Email Queue reference"
        )

    if not email_queue and email_state in {"Queued", "Sent"}:
        raise ValueError(
            "Queued or sent email is missing its Email Queue"
        )

    # Each channel re-locks and re-reads the intent. Reentrant
    # row locks are safe within the same MariaDB transaction.
    #
    # The in-app function also verifies an existing log on replay.
    notification_log = record_in_app_alert(name)

    if email_queue:
        # Includes Failed: reconcile the original queue.
        # Never create a second queue for an existing reference.
        email_result = reconcile_intent_email_state(name)
    else:
        # Only Pending or Failed without a queue may create one.
        queue_intent_email(name)
        email_result = reconcile_intent_email_state(name)

    updated = frappe.get_doc(DOCTYPE, name)

    if str(updated.get("in_app_state") or "") != "Recorded":
        raise ValueError(
            "In-app notification was not recorded"
        )

    if str(updated.get("notification_log") or "") != str(
        notification_log
    ):
        raise ValueError(
            "Notification Log identity mismatch"
        )

    final_email_state = str(
        updated.get("email_state") or ""
    ).strip()

    if final_email_state != email_result["email_state"]:
        raise ValueError(
            "Email reconciliation state mismatch"
        )

    final_delivery_state = DELIVERY_STATES.get(
        final_email_state
    )

    if not final_delivery_state:
        raise ValueError(
            f"Unexpected final email state: {final_email_state}"
        )

    if (
        delivery_state == "Complete"
        and final_delivery_state != "Complete"
    ):
        raise ValueError(
            "Previously complete delivery cannot be downgraded"
        )

    changed = final_delivery_state != delivery_state

    if changed:
        frappe.db.set_value(
            DOCTYPE,
            name,
            "delivery_state",
            final_delivery_state,
        )

    return {
        "intent": name,
        "event": event,
        "notification_log": notification_log,
        "email_queue": email_result["email_queue"],
        "email_state": final_email_state,
        "delivery_state": final_delivery_state,
        "changed": changed,
    }
