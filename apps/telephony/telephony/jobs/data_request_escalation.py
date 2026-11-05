"""Activation-gated Data Request Coordinator escalation scheduler.

No notification delivery occurs here.

The Frappe scheduler owns the transaction. This module does
not explicitly commit, enqueue, email or modify HD Tickets.
"""

from datetime import timedelta

import frappe

from telephony.data_request_escalation_outbox import (
    capture_escalation_intents,
)

ACTIVATION_KEY = "telectro_data_request_escalation_start_at"
SERVICE_AREA = "Data Request"
PAGE_SIZE = 100
ESCALATION_MINUTES = 10


def run(*, dry_run=False):
    """Capture due escalation intents after explicit site activation."""

    configured = frappe.conf.get(ACTIVATION_KEY)

    # Fail closed: deployment alone does not activate escalation.
    if not configured:
        return {
            "state": "disabled",
            "scanned": 0,
            "inserted": 0,
        }

    activation = frappe.utils.get_datetime(configured)
    now = frappe.utils.now_datetime()

    if activation.tzinfo is not None or now.tzinfo is not None:
        raise ValueError(
            "Escalation timestamps must be site-local naive datetimes"
        )

    cutoff = now - timedelta(minutes=ESCALATION_MINUTES)

    if cutoff < activation:
        return {
            "state": "not_due",
            "scanned": 0,
            "inserted": 0,
        }

    scanned = 0
    inserted = 0
    offset = 0

    while True:
        candidates = frappe.db.sql(
            """
            SELECT name
            FROM `tabHD Ticket`
            WHERE custom_service_area = %s
              AND creation >= %s
              AND creation <= %s
              AND custom_data_request_first_completed_on IS NULL
            ORDER BY creation ASC, name ASC
            LIMIT %s OFFSET %s
            """,
            (
                SERVICE_AREA,
                activation,
                cutoff,
                PAGE_SIZE,
                offset,
            ),
            as_dict=True,
        )

        if not candidates:
            break

        for row in candidates:
            scanned += 1

            if dry_run:
                continue

            names = capture_escalation_intents(
                str(row["name"]),
                now=now,
            )

            inserted += len(names)

        offset += len(candidates)

        if len(candidates) < PAGE_SIZE:
            break

    return {
        "state": "dry_run" if dry_run else "processed",
        "scanned": scanned,
        "inserted": inserted,
    }
