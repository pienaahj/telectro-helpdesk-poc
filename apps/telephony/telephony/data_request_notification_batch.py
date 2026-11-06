"""Bounded Data Request notification batch orchestration.

Selection and single-intent processing are delegated to existing,
verified components.

No scheduler registration or direct notification delivery occurs here.
Each single-intent worker owns its successful commit or failure
transaction. Unhandled per-intent errors are isolated.
"""

import frappe

from telephony.data_request_notification_reporting import (
    persist_unhandled_batch_error,
)
from telephony.data_request_notification_worker import (
    record_unhandled_notification_failure,
)
from telephony.data_request_notification_selection import (
    MAX_BATCH,
    select_due_notification_intents,
)
from telephony.data_request_notification_worker import (
    process_due_notification_intent,
)


OUTCOME_COUNTERS = {
    "Processing": "processing",
    "Complete": "complete",
    "Retry": "retry",
    "Failed": "failed",
    "missing": "skipped",
    "not_due": "skipped",
    "superseded": "skipped",
}


def run_notification_delivery_batch(
    *,
    limit=100,
    dry_run=False,
    now=None,
):
    """Process a bounded snapshot of due notification intents."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_BATCH
    ):
        raise ValueError("Invalid notification batch limit")

    if not isinstance(dry_run, bool):
        raise ValueError("dry_run must be boolean")

    current = (
        frappe.utils.get_datetime(now)
        if now is not None
        else frappe.utils.now_datetime()
    )

    selection = select_due_notification_intents(
        now=current,
        limit=limit,
    )

    summary = {
        "state": selection["state"],
        "selected": 0,
        "attempted": 0,
        "processing": 0,
        "complete": 0,
        "retry": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "error_intents": [],
        "outcomes": [],
    }

    if selection["state"] in ("disabled", "not_due"):
        return summary

    if selection["state"] != "ready":
        raise ValueError("Unknown notification selection state")

    names = selection["intents"]

    if (
        not isinstance(names, list)
        or len(names) > limit
        or len(names) != len(set(names))
        or selection["selected"] != len(names)
    ):
        raise ValueError("Invalid notification candidate batch")

    summary["selected"] = len(names)

    if dry_run:
        summary["state"] = "dry_run"
        return summary

    for name in names:
        summary["attempted"] += 1

        try:
            result = process_due_notification_intent(
                name,
                now=current,
            )

            if not isinstance(result, dict):
                raise ValueError("Invalid worker response")

            state = result.get("state")

            if (
                state not in OUTCOME_COUNTERS
                and state != "disabled"
            ):
                raise ValueError("Unknown worker outcome")

        except Exception:
            # Discard any incomplete InnoDB delivery work first.
            frappe.db.rollback()

            # The verified native Error Log uses MyISAM.
            # Its insert survives rollback without committing
            # unrelated InnoDB changes.
            #
            # If persistence fails, propagate the failure.
            error_log = persist_unhandled_batch_error(name)

            # Persist retry backoff in a new locked InnoDB
            # transaction. The helper rechecks eligibility
            # before changing the intent's durable state.
            failure = record_unhandled_notification_failure(
                name,
                now=current,
            )

            if (
                not isinstance(failure, dict)
                or failure.get("state") not in {
                    "Retry",
                    "Failed",
                    "missing",
                    "superseded",
                    "disabled",
                }
            ):
                raise RuntimeError(
                    "Unexpected durable notification failure state"
                )

            summary["errors"] += 1
            summary["error_intents"].append(name)
            summary["outcomes"].append({
                "intent": name,
                "state": "error",
                "error_log": error_log,
                "failure_state": failure["state"],
            })
            continue

        summary["outcomes"].append({
            "intent": name,
            "state": state,
        })

        if state == "disabled":
            # Activation may have been removed during the batch.
            # Do not process any subsequent candidates.
            summary["state"] = "deactivated"
            summary["skipped"] += 1
            break

        counter = OUTCOME_COUNTERS[state]
        summary[counter] += 1

    if summary["state"] != "deactivated":
        summary["state"] = (
            "partial_failure"
            if summary["errors"]
            else "processed"
        )

    return summary
