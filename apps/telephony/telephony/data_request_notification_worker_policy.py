"""Pure retry and recovery policy for Data Request notifications.

No Frappe imports, database operations, email or job scheduling.

attempt_count counts unsuccessful attempts, not routine
Email Queue reconciliation polls.
"""

from datetime import datetime, timedelta


MAX_FAILED_ATTEMPTS = 5
PROCESSING_POLL_MINUTES = 5

RETRY_DELAYS_MINUTES = (1, 2, 4, 8)

RETRYABLE_FAILURE_CODES = frozenset({
    "DISPATCH_ERROR",
    "NATIVE_EMAIL_FAILURE",
})

TERMINAL_FAILURE_CODES = frozenset({
    "AUTHORIZATION_REVOKED",
    "INVALID_INTENT",
})


def _validate_inputs(now, attempt_count):
    if not isinstance(now, datetime):
        raise ValueError("Worker timestamp must be a datetime")

    if now.tzinfo is not None:
        raise ValueError(
            "Worker timestamp must be site-local and naive"
        )

    if (
        isinstance(attempt_count, bool)
        or not isinstance(attempt_count, int)
        or attempt_count < 0
    ):
        raise ValueError(
            "Failed attempt count must be a nonnegative integer"
        )


def plan_worker_failure(
    *,
    now,
    attempt_count,
    failure_code,
):
    """Plan a durable failure without exposing exception details."""

    _validate_inputs(now, attempt_count)

    if failure_code not in (
        RETRYABLE_FAILURE_CODES | TERMINAL_FAILURE_CODES
    ):
        raise ValueError(
            f"Unsupported failure classification: {failure_code!r}"
        )

    failures = attempt_count + 1

    terminal = (
        failure_code in TERMINAL_FAILURE_CODES
        or failures >= MAX_FAILED_ATTEMPTS
    )

    if terminal:
        return {
            "delivery_state": "Failed",
            "attempt_count": failures,
            "last_attempt_on": now,
            "next_attempt_on": None,
            "last_error": failure_code,
        }

    delay_index = min(
        failures - 1,
        len(RETRY_DELAYS_MINUTES) - 1,
    )

    delay = RETRY_DELAYS_MINUTES[delay_index]

    return {
        "delivery_state": "Retry",
        "attempt_count": failures,
        "last_attempt_on": now,
        "next_attempt_on": now + timedelta(minutes=delay),
        "last_error": failure_code,
    }


def plan_worker_result(
    *,
    now,
    attempt_count,
    delivery_state,
):
    """Plan the next state after successful dispatcher execution."""

    _validate_inputs(now, attempt_count)

    if delivery_state == "Retry":
        return plan_worker_failure(
            now=now,
            attempt_count=attempt_count,
            failure_code="NATIVE_EMAIL_FAILURE",
        )

    if delivery_state == "Processing":
        return {
            "delivery_state": "Processing",
            "attempt_count": attempt_count,
            "last_attempt_on": now,
            "next_attempt_on": (
                now + timedelta(
                    minutes=PROCESSING_POLL_MINUTES
                )
            ),
            "last_error": None,
        }

    if delivery_state == "Complete":
        return {
            "delivery_state": "Complete",
            "attempt_count": attempt_count,
            "last_attempt_on": now,
            "next_attempt_on": None,
            "last_error": None,
        }

    raise ValueError(
        f"Unsupported dispatcher result: {delivery_state!r}"
    )
