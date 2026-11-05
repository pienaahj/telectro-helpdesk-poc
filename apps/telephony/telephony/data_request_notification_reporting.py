"""Durable error reporting for Data Request notification batches.

Contract:
- Caller must roll back the failed worker transaction first.
- Store only a fixed error classification and internal intent ID.
- Use native MyISAM persistence without committing the caller's transaction.
- Propagate reporting failures so they cannot be silently ignored.

No raw exception, traceback or customer communication is accepted.
"""

import frappe

from telephony.data_request_notification_delivery import DOCTYPE


ERROR_LOG_TITLE = "Telectro Data Request notification batch"
ERROR_CODE = "UNHANDLED_BATCH_EXCEPTION"


def persist_unhandled_batch_error(intent_name):
    """Persist a sanitized native Error Log after caller rollback."""

    if (
        not isinstance(intent_name, str)
        or not intent_name
        or len(intent_name) > 140
        or intent_name != intent_name.strip()
        or any(
            ord(char) < 32 or ord(char) == 127
            for char in intent_name
        )
    ):
        raise ValueError("Invalid notification intent reference")

    try:
        record = frappe.get_doc({
            "doctype": "Error Log",
            "method": ERROR_LOG_TITLE,
            "error": ERROR_CODE,
            "reference_doctype": DOCTYPE,
            "reference_name": intent_name,
        })

        record.insert(ignore_permissions=True)

        # Error Log uses MyISAM on the validated DEV site.
        # Its insert persists without committing InnoDB work.
        # Never commit the caller's connection here.
        return record.name

    except Exception:
        # The caller owns its InnoDB transaction.
        # A MyISAM insert cannot be undone with rollback.
        # Do not expose raw database or exception details
        # through the operational reporting API.
        raise RuntimeError(
            "Notification batch error-log persistence failed"
        ) from None
