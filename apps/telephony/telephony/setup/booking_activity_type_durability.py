"""Provision the Activity Type masters used by technician time booking."""

import frappe

from telephony.time_booking_activity_types import BOOKING_ACTIVITY_TYPES


def after_migrate() -> list[str]:
    """Insert missing masters and leave existing records untouched."""
    inserted = []

    for activity_type in BOOKING_ACTIVITY_TYPES:
        if frappe.db.exists("Activity Type", activity_type):
            continue

        frappe.get_doc({
            "doctype": "Activity Type",
            "activity_type": activity_type,
            "disabled": 0,
        }).insert(ignore_permissions=True)
        inserted.append(activity_type)

    return inserted
