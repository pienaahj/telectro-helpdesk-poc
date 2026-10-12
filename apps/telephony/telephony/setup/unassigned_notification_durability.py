"""
Durable scope correction for the legacy unassigned-ticket email Notification.

This module modifies only the condition of the existing Notification.
It does not create Notifications or change recipients, enabled state,
subjects, or email delivery configuration.
"""

import frappe


NOTIFICATION_NAME = "TELECTRO-POC Broadcast Unassigned (Routing)"

LEGACY_CONDITION = (
    '(doc.get("_assign") in (None, "", "[]"))'
)

SCOPED_CONDITION = (
    '(doc.get("_assign") in (None, "", "[]"))'
    ' and '
    '(doc.get("custom_service_area") in ("Routing", "PABX"))'
)


def _clean(value):
    return str(value or "").strip()


def ensure_unassigned_notification_scope():
    """
    Narrow the legacy unassigned-ticket broadcast to Routing and PABX.

    Only the known legacy condition may be automatically reconciled.
    Unexpected custom conditions require operator review.

    Transaction ownership remains with the caller.
    """

    if not frappe.db.exists("Notification", NOTIFICATION_NAME):
        return {
            "ok": True,
            "present": False,
            "changed_count": 0,
        }

    current_condition = _clean(
        frappe.db.get_value(
            "Notification",
            NOTIFICATION_NAME,
            "condition",
        )
    )

    if current_condition == SCOPED_CONDITION:
        return {
            "ok": True,
            "present": True,
            "changed_count": 0,
        }

    if current_condition != LEGACY_CONDITION:
        frappe.throw(
            "The unassigned-ticket Notification has an unexpected "
            "condition. Automatic reconciliation has stopped. "
            "Review the existing condition before proceeding.",
            title="Notification Scope Conflict",
        )

    frappe.db.set_value(
        "Notification",
        NOTIFICATION_NAME,
        "condition",
        SCOPED_CONDITION,
        update_modified=False,
    )

    verified_condition = _clean(
        frappe.db.get_value(
            "Notification",
            NOTIFICATION_NAME,
            "condition",
        )
    )

    if verified_condition != SCOPED_CONDITION:
        frappe.throw(
            "The unassigned-ticket Notification condition did not "
            "reach the expected state.",
            title="Notification Scope Verification Failed",
        )

    return {
        "ok": True,
        "present": True,
        "changed_count": 1,
    }


def after_migrate():
    """
    Reconcile the existing Notification after each migration.

    Do not commit here; the migration lifecycle owns the transaction.
    """
    return ensure_unassigned_notification_scope()
