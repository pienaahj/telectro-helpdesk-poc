"""
Transactional capture of TELECTRO task-notification obligations.

Capture only. No email sending, worker scheduling or commits.

Requires TELECTRO Task Notification Intent DocType to be
installed before this function is connected to live workflows.
"""

import frappe

from telephony.task_notification_policy import (
    task_notification_event_key,
)


INTENT_DOCTYPE = "TELECTRO Task Notification Intent"



def _stored_event_identity_matches(
    *,
    event_key,
    ticket,
    action,
    event_id,
    recipient,
):
    """
    Verify that an existing event key belongs to the same
    complete logical notification identity.

    Missing or conflicting records are never accepted as
    successful duplicate capture.
    """
    row = frappe.db.get_value(
        INTENT_DOCTYPE,
        event_key,
        [
            "event_key",
            "ticket",
            "action",
            "event_id",
            "recipient",
        ],
        as_dict=True,
        for_update=True,
    )

    if not row:
        return False

    return (
        str(row.get("event_key") or "").strip() == event_key
        and str(row.get("ticket") or "").strip() == ticket
        and str(row.get("action") or "").strip().lower() == action
        and str(row.get("event_id") or "").strip() == event_id
        and str(row.get("recipient") or "").strip().casefold()
            == recipient
    )


def capture_task_notification_intent(
    *,
    ticket,
    action,
    event_id,
    recipient,
    actor_user="",
    note="",
):
    """
    Insert one Pending intent using a deterministic event key.

    The caller owns the transaction. A rollback must also
    roll back this insert.

    Duplicate events return created=False. Unexpected insert
    failures remain visible to the caller.
    """

    ticket = str(ticket or "").strip()
    action = str(action or "").strip().lower()
    event_id = str(event_id or "").strip()
    recipient = str(recipient or "").strip().casefold()
    actor_user = str(actor_user or "").strip()
    note = str(note or "").strip()

    # Validate the complete identity before touching the database.
    event_key = task_notification_event_key(
        ticket=ticket,
        action=action,
        event_id=event_id,
        recipient=recipient,
    )

    if frappe.db.exists(INTENT_DOCTYPE, event_key):
        if not _stored_event_identity_matches(
            event_key=event_key,
            ticket=ticket,
            action=action,
            event_id=event_id,
            recipient=recipient,
        ):
            raise ValueError(
                "Existing notification key has conflicting identity"
            )

        return {
            "created": False,
            "event_key": event_key,
        }

    payload = {
        "doctype": INTENT_DOCTYPE,
        "name": event_key,
        "event_key": event_key,
        "ticket": ticket,
        "action": action,
        "event_id": event_id,
        "recipient": recipient,
        "actor_user": actor_user,
        "note": note,
        "status": "Pending",
        "attempt_count": 0,
    }

    try:
        frappe.get_doc(payload).insert(
            ignore_permissions=True
        )
    except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
        # Handle a competing insert of the same event.
        # Do not hide unrelated integrity failures.
        # An ordinary existence read may use an old
        # REPEATABLE-READ snapshot. Verify the stored event
        # through the current locking read instead.
        if not _stored_event_identity_matches(
            event_key=event_key,
            ticket=ticket,
            action=action,
            event_id=event_id,
            recipient=recipient,
        ):
            # Preserve the original database exception.
            raise

        return {
            "created": False,
            "event_key": event_key,
        }

    return {
        "created": True,
        "event_key": event_key,
    }

def _log_task_notification_capture_failure(stage):
    """
    Best-effort diagnostic logging.

    Logging failure must not obscure successful savepoint
    restoration or the original capture failure.
    """
    try:
        frappe.logger("telephony").exception(
            "TELECTRO task notification capture failed at %s",
            stage,
        )
    except Exception:
        pass


def capture_task_notification_intent_safely(
    *,
    ticket,
    action,
    event_id,
    recipient,
    actor_user="",
    note="",
):
    """
    Capture a notification intent without owning the transaction.

    On a capture error, restore the notification work using
    a savepoint. Never commit, send email or schedule jobs.

    If rollback to the savepoint fails, propagate that
    exception: transaction integrity is not established.

    A failed capture is explicitly reported as ok=False.
    """
    from uuid import uuid4

    savepoint = "task_notification_" + uuid4().hex

    arguments = {
        "ticket": ticket,
        "action": action,
        "event_id": event_id,
        "recipient": recipient,
        "actor_user": actor_user,
        "note": note,
    }

    try:
        frappe.db.savepoint(savepoint)
    except Exception:
        _log_task_notification_capture_failure(
            "savepoint"
        )

        return {
            "ok": False,
            "created": False,
            "event_key": None,
            "error": "savepoint_failed",
        }

    try:
        result = capture_task_notification_intent(
            **arguments
        )

    except Exception:
        # This must succeed before suppressing a capture error.
        # A failed rollback deliberately propagates.
        frappe.db.rollback(save_point=savepoint)

        _log_task_notification_capture_failure(
            "capture"
        )

        return {
            "ok": False,
            "created": False,
            "event_key": None,
            "error": "capture_failed",
        }

    return {
        "ok": True,
        "created": bool(result["created"]),
        "event_key": result["event_key"],
        "error": "",
    }
