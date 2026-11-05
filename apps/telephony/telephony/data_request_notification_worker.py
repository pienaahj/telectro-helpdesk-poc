"""Single-intent transactional Data Request notification worker.

For dedicated background-worker transactions only.

No batch scheduler is registered here. Deployment does not activate
delivery. The worker owns commit and rollback for one intent.
"""

from datetime import timedelta

import frappe

from telephony.data_request_notification_delivery import DOCTYPE
from telephony.data_request_notification_dispatcher import (
    dispatch_notification_intent,
)
from telephony.data_request_notification_selection import (
    ACTIVATION_KEY,
    RECOVERY_MINUTES,
)
from telephony.data_request_notification_worker_policy import (
    plan_worker_failure,
    plan_worker_result,
)


SNAPSHOT_FIELDS = (
    "creation",
    "delivery_state",
    "attempt_count",
    "last_attempt_on",
    "next_attempt_on",
    "in_app_state",
    "notification_log",
    "email_state",
    "email_queue",
)


def _lock_intent(name):
    rows = frappe.db.sql(
        """
        SELECT
            name,
            creation,
            delivery_state,
            attempt_count,
            last_attempt_on,
            next_attempt_on,
            in_app_state,
            notification_log,
            email_state,
            email_queue
        FROM `tabTELECTRO Data Request Notification Intent`
        WHERE name = %s
        FOR UPDATE
        """,
        (name,),
        as_dict=True,
    )

    return rows[0] if rows else None


def _snapshot(row):
    return tuple(row.get(field) for field in SNAPSHOT_FIELDS)


def _due(row, activation, now):
    creation = frappe.utils.get_datetime(row["creation"])

    if creation < activation or creation > now:
        return False

    state = str(row.get("delivery_state") or "")
    deadline = row.get("next_attempt_on")

    if deadline is not None:
        deadline = frappe.utils.get_datetime(deadline)

    if state == "Pending":
        return deadline is None or deadline <= now

    if state == "Retry":
        return deadline is not None and deadline <= now

    if state == "Processing":
        if deadline is not None:
            return deadline <= now

        last = row.get("last_attempt_on") or creation
        last = frappe.utils.get_datetime(last)

        return last <= now - timedelta(
            minutes=RECOVERY_MINUTES
        )

    return False


def _failure_code(error):
    if isinstance(error, frappe.PermissionError):
        return "AUTHORIZATION_REVOKED"

    # Other failures remain retryable until classified more
    # specifically. Never persist raw exception details.
    return "DISPATCH_ERROR"


def process_due_notification_intent(intent_name, *, now=None):
    """Process one due intent using isolated database transactions."""

    name = str(intent_name or "").strip()

    if not name:
        raise ValueError("Notification intent identity required")

    configured = frappe.conf.get(ACTIVATION_KEY)

    if not configured:
        return {
            "intent": name,
            "state": "disabled",
        }

    activation = frappe.utils.get_datetime(configured)

    current = (
        frappe.utils.get_datetime(now)
        if now is not None
        else frappe.utils.now_datetime()
    )

    if activation.tzinfo is not None or current.tzinfo is not None:
        raise ValueError(
            "Worker timestamps must be site-local naive datetimes"
        )

    before = None
    claimed = False

    try:
        row = _lock_intent(name)

        if row is None:
            frappe.db.rollback()
            return {
                "intent": name,
                "state": "missing",
            }

        if not _due(row, activation, current):
            frappe.db.rollback()
            return {
                "intent": name,
                "state": "not_due",
            }

        before = _snapshot(row)
        claimed = True

        dispatch = dispatch_notification_intent(name)

        planned = plan_worker_result(
            now=current,
            attempt_count=int(row.get("attempt_count") or 0),
            delivery_state=dispatch["delivery_state"],
        )

        frappe.db.set_value(DOCTYPE, name, planned)

        frappe.db.commit()

        return {
            "intent": name,
            "state": planned["delivery_state"],
            "attempt_count": planned["attempt_count"],
            "next_attempt_on": planned["next_attempt_on"],
            "email_queue": dispatch["email_queue"],
            "notification_log": dispatch["notification_log"],
        }

    except Exception as error:
        # Nothing created by a failed dispatch may be committed.
        frappe.db.rollback()

        if not claimed:
            raise

        code = _failure_code(error)

        try:
            # Another worker may have processed this intent after
            # our rollback. Never overwrite that worker's progress.
            current_row = _lock_intent(name)

            if (
                current_row is None
                or _snapshot(current_row) != before
                or not _due(current_row, activation, current)
            ):
                frappe.db.rollback()

                return {
                    "intent": name,
                    "state": "superseded",
                }

            planned = plan_worker_failure(
                now=current,
                attempt_count=int(
                    current_row.get("attempt_count") or 0
                ),
                failure_code=code,
            )

            frappe.db.set_value(DOCTYPE, name, planned)

            frappe.db.commit()

            return {
                "intent": name,
                "state": planned["delivery_state"],
                "attempt_count": planned["attempt_count"],
                "next_attempt_on": planned["next_attempt_on"],
                "failure_code": code,
            }

        except Exception:
            frappe.db.rollback()
            raise
