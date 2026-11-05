"""Activation-gated selection for Data Request notification delivery.

Read-only. No delivery, commit, queue creation or job scheduling.
"""

from datetime import timedelta

import frappe


ACTIVATION_KEY = (
    "telectro_data_request_notification_delivery_start_at"
)

MAX_BATCH = 100
RECOVERY_MINUTES = 5


def select_due_notification_intents(*, now=None, limit=100):
    """Return eligible intent names without processing them."""

    configured = frappe.conf.get(ACTIVATION_KEY)

    # Deployment must not automatically activate delivery.
    if not configured:
        return {
            "state": "disabled",
            "intents": [],
            "selected": 0,
        }

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_BATCH
    ):
        raise ValueError("Batch limit must be between 1 and 100")

    activation = frappe.utils.get_datetime(configured)

    current = (
        frappe.utils.get_datetime(now)
        if now is not None
        else frappe.utils.now_datetime()
    )

    if (
        activation.tzinfo is not None
        or current.tzinfo is not None
    ):
        raise ValueError(
            "Delivery timestamps must be site-local "
            "naive datetimes"
        )

    if current < activation:
        return {
            "state": "not_due",
            "intents": [],
            "selected": 0,
        }

    recovery_cutoff = current - timedelta(
        minutes=RECOVERY_MINUTES
    )

    rows = frappe.db.sql(
        """
        SELECT name, delivery_state
        FROM `tabTELECTRO Data Request Notification Intent`
        WHERE creation >= %s
          AND creation <= %s
          AND (
                (
                    delivery_state = 'Pending'
                    AND (
                        next_attempt_on IS NULL
                        OR next_attempt_on <= %s
                    )
                )
                OR (
                    delivery_state = 'Retry'
                    AND next_attempt_on IS NOT NULL
                    AND next_attempt_on <= %s
                )
                OR (
                    delivery_state = 'Processing'
                    AND (
                        (
                            next_attempt_on IS NOT NULL
                            AND next_attempt_on <= %s
                        )
                        OR (
                            next_attempt_on IS NULL
                            AND COALESCE(
                                last_attempt_on,
                                creation
                            ) <= %s
                        )
                    )
                )
          )
        ORDER BY
            COALESCE(next_attempt_on, creation),
            creation,
            name
        LIMIT %s
        """,
        (
            activation,
            current,
            current,
            current,
            current,
            recovery_cutoff,
            limit,
        ),
        as_dict=True,
    )

    names = [str(row["name"]) for row in rows]

    if len(names) != len(set(names)):
        raise ValueError(
            "Duplicate notification intents selected"
        )

    return {
        "state": "ready",
        "intents": names,
        "selected": len(names),
    }
