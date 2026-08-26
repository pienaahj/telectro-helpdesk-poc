from __future__ import annotations

from typing import Any

import frappe
from helpdesk.setup.file import create_helpdesk_folder


HELPDESK_FOLDER = "Home/Helpdesk"
HELPDESK_FOLDER_NAME = "Helpdesk"
HELPDESK_PARENT_FOLDER = "Home"


def _get_helpdesk_folder() -> dict[str, Any] | None:
    return frappe.db.get_value(
        "File",
        HELPDESK_FOLDER,
        [
            "name",
            "file_name",
            "folder",
            "is_folder",
            "is_private",
        ],
        as_dict=True,
    )


def _get_same_location_rows() -> list[dict[str, Any]]:
    return frappe.get_all(
        "File",
        filters={
            "file_name": HELPDESK_FOLDER_NAME,
            "folder": HELPDESK_PARENT_FOLDER,
        },
        fields=[
            "name",
            "file_name",
            "folder",
            "is_folder",
            "is_private",
        ],
        order_by="creation asc",
    )


def verify_helpdesk_folder() -> dict[str, Any]:
    """Return a read-only verification of the Helpdesk upload folder."""

    parent_exists = bool(
        frappe.db.exists(
            "File",
            HELPDESK_PARENT_FOLDER,
        )
    )

    folder = _get_helpdesk_folder()
    location_rows = _get_same_location_rows()

    issues: list[dict[str, Any]] = []

    if not parent_exists:
        issues.append(
            {
                "type": "missing_parent_folder",
                "folder": HELPDESK_PARENT_FOLDER,
            }
        )

    if folder is None:
        issues.append(
            {
                "type": "missing_helpdesk_folder",
                "folder": HELPDESK_FOLDER,
            }
        )
    else:
        expected = {
            "name": HELPDESK_FOLDER,
            "file_name": HELPDESK_FOLDER_NAME,
            "folder": HELPDESK_PARENT_FOLDER,
            "is_folder": 1,
            "is_private": 0,
        }

        for fieldname, expected_value in expected.items():
            actual_value = folder.get(fieldname)

            if actual_value != expected_value:
                issues.append(
                    {
                        "type": "helpdesk_folder_mismatch",
                        "field": fieldname,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )

    unexpected_location_rows = [
        row
        for row in location_rows
        if row["name"] != HELPDESK_FOLDER
    ]

    if unexpected_location_rows:
        issues.append(
            {
                "type": "unexpected_helpdesk_folder_rows",
                "rows": unexpected_location_rows,
            }
        )

    return {
        "ok": not issues,
        "site": frappe.local.site,
        "folder": HELPDESK_FOLDER,
        "parent_exists": parent_exists,
        "exists": folder is not None,
        "row": folder,
        "location_rows": location_rows,
        "issue_count": len(issues),
        "issues": issues,
    }


def ensure_helpdesk_folder() -> dict[str, Any]:
    """
    Ensure the Helpdesk upload folder exists.

    A genuinely missing folder is recreated through Helpdesk's own setup
    helper. Unexpected or conflicting state is not silently rewritten.
    """

    before = verify_helpdesk_folder()

    if before["ok"]:
        return {
            "ok": True,
            "site": before["site"],
            "changed_count": 0,
            "changed": [],
            "verification": before,
        }

    safe_missing_folder = (
        before["parent_exists"]
        and not before["exists"]
        and not before["location_rows"]
    )

    if not safe_missing_folder:
        frappe.throw(
            "Helpdesk folder reconciliation stopped because "
            "unexpected state was found:\n"
            + frappe.as_json(before["issues"], indent=2),
            title="Helpdesk Folder Conflict",
        )

    create_helpdesk_folder()

    after = verify_helpdesk_folder()

    if not after["ok"]:
        frappe.throw(
            "Helpdesk folder reconciliation did not reach the "
            "expected state:\n"
            + frappe.as_json(after["issues"], indent=2),
            title="Helpdesk Folder Verification Failed",
        )

    return {
        "ok": True,
        "site": after["site"],
        "changed_count": 1,
        "changed": [
            {
                "action": "create",
                "folder": HELPDESK_FOLDER,
            }
        ],
        "verification": after,
    }


def apply_helpdesk_folder() -> dict[str, Any]:
    """
    Explicit transactional entry point for bench execute.

    The after_migrate hook uses the migration transaction. This function is
    for deliberate operator-initiated repair.
    """

    try:
        result = ensure_helpdesk_folder()
        frappe.db.commit()
        return result
    except Exception:
        frappe.db.rollback()
        raise


def after_migrate() -> dict[str, Any]:
    """Restore and verify the Helpdesk upload folder after each migration."""

    result = ensure_helpdesk_folder()

    frappe.logger("telephony").info(
        "Helpdesk folder verified: %s, %s changed",
        HELPDESK_FOLDER,
        result["changed_count"],
    )

    return result
