"""Activation-gated Data Request notification scheduler entry point.

The verified selector owns activation gating.
The bounded batch and individual workers own processing.
No direct transaction commits or message delivery occur here.
"""

from telephony.data_request_notification_batch import (
    run_notification_delivery_batch,
)


def run(*, dry_run=False):
    """Execute one bounded notification delivery batch."""

    return run_notification_delivery_batch(
        dry_run=dry_run,
    )
