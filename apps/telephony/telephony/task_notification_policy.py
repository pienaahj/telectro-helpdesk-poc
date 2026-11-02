"""
Pure decision policy for TELECTRO task-assignment notifications.

This module does not create Notification Logs, queue emails,
change ownership, or modify database state.
"""


def should_notify_assignment(
    *,
    action,
    previous_owner,
    recipient,
):
    """Return whether a genuine new responsibility warrants an alert."""

    action = str(action or "").strip().lower()
    previous_owner = str(previous_owner or "").strip().casefold()
    recipient = str(recipient or "").strip().casefold()

    if not recipient:
        return False

    if action not in {"assignment", "claim", "handoff"}:
        return False

    if previous_owner == recipient:
        return False

    return True

def task_notification_event_key(
    *,
    ticket,
    action,
    event_id,
    recipient,
):
    """
    Return a deterministic identity for one notification obligation.

    The same event and recipient produce the same key.
    A later genuine event requires a different event_id.

    This function performs no I/O or notification delivery.
    """
    import hashlib
    import json

    ticket = str(ticket or "").strip()
    action = str(action or "").strip().lower()
    event_id = str(event_id or "").strip()
    recipient = str(recipient or "").strip().casefold()

    if not all((ticket, action, event_id, recipient)):
        raise ValueError("Incomplete notification event identity")

    allowed_actions = {
        "assignment",
        "claim",
        "handoff",
        "share_context",
    }

    if action not in allowed_actions:
        raise ValueError("Unsupported notification action")

    payload = json.dumps(
        [
            "telectro-task-notification-v1",
            ticket,
            action,
            event_id,
            recipient,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()
