"""Pure 10-minute Data Request operational escalation policy.

Independent of Helpdesk SLA, ticket assignment and notification delivery.
"""

from datetime import datetime, timedelta

SERVICE_AREA = "Data Request"
ESCALATION_WINDOW = timedelta(minutes=10)


def evaluate_escalation(
    *,
    service_area,
    arrival_at,
    first_completed_at,
    now,
):
    if str(service_area or "").strip() != SERVICE_AREA:
        return {
            "state": "not_applicable",
            "due_at": None,
            "notification_due": False,
        }

    if not isinstance(arrival_at, datetime):
        raise ValueError("Valid arrival datetime required")

    if not isinstance(now, datetime):
        raise ValueError("Valid current datetime required")

    if first_completed_at is not None and not isinstance(
        first_completed_at, datetime
    ):
        raise ValueError("Invalid completion datetime")

    due_at = arrival_at + ESCALATION_WINDOW

    if first_completed_at is not None:
        state = (
            "completed_on_time"
            if first_completed_at <= due_at
            else "completed_late"
        )
    elif now >= due_at:
        state = "escalation_due"
    else:
        state = "waiting"

    return {
        "state": state,
        "due_at": due_at,
        "notification_due": state == "escalation_due",
    }
