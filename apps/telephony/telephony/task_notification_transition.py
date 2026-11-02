"""Capture verified task-ownership transitions.

This module does not establish ownership or perform delivery.

The caller must establish a genuine transition and supply
a stable event_id derived from the authoritative workflow.

All persistence belongs to the caller's transaction.
"""

from importlib import import_module

from telephony.task_notification_policy import (
    should_notify_assignment,
)


def capture_verified_task_ownership_transition(
    *,
    ticket,
    action,
    previous_owner,
    recipient,
    event_id,
    transition_confirmed,
    actor_user="",
    note="",
):
    """Capture an intent for confirmed new task responsibility.

    A skipped event is not a capture error.

    Capture failures are returned by the safe outbox wrapper.
    A failure to restore transaction integrity propagates.
    """

    skipped = {
        "ok": True,
        "created": False,
        "event_key": None,
        "error": "",
    }

    # The integration caller must explicitly prove success.
    # An API response alone does not establish a transition.
    if transition_confirmed is not True:
        return skipped

    ticket = str(ticket or "").strip()
    action = str(action or "").strip().lower()
    previous_owner = str(
        previous_owner or ""
    ).strip().casefold()
    recipient = str(recipient or "").strip().casefold()
    event_id = str(event_id or "").strip()

    # Never invent an event identity or permit incomplete
    # ownership information to create an obligation.
    if not ticket or not event_id:
        return skipped

    if not should_notify_assignment(
        action=action,
        previous_owner=previous_owner,
        recipient=recipient,
    ):
        return skipped

    # Import at invocation time to keep this adapter
    # independent of Frappe initialization and to permit
    # isolated regression testing.
    outbox = import_module(
        "telephony.task_notification_outbox"
    )

    return outbox.capture_task_notification_intent_safely(
        ticket=ticket,
        action=action,
        event_id=event_id,
        recipient=recipient,
        actor_user=str(actor_user or "").strip(),
        note=str(note or "").strip(),
    )
