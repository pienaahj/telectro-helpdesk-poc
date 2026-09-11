from __future__ import annotations

from typing import Any

import frappe


ARCHIVED_STATUS_NAME = "Archived"

ARCHIVED_STATUS_SPEC = {
    "label_agent": "Archived",
    "enabled": 1,
    "category": "Resolved",
    "order": 5,
    "color": "Gray",
    "different_view": 0,
    "label_customer": "",
}


def _normalise_status_value(fieldname: str, value: Any) -> Any:
    if fieldname in {"enabled", "different_view", "order"}:
        return int(value or 0)

    if fieldname == "label_customer":
        return value or ""

    return value


def _get_archived_status_state() -> dict[str, Any] | None:
    return frappe.db.get_value(
        "HD Ticket Status",
        ARCHIVED_STATUS_NAME,
        [
            "name",
            "label_agent",
            "enabled",
            "category",
            "order",
            "color",
            "different_view",
            "label_customer",
        ],
        as_dict=True,
    )


def _get_archived_label_conflict() -> dict[str, Any] | None:
    rows = frappe.get_all(
        "HD Ticket Status",
        filters={
            "label_agent": ARCHIVED_STATUS_NAME,
            "name": ["!=", ARCHIVED_STATUS_NAME],
        },
        fields=[
            "name",
            "label_agent",
            "enabled",
            "category",
            "order",
            "color",
            "different_view",
            "label_customer",
        ],
        limit_page_length=2,
    )

    if not rows:
        return None

    return rows[0]


def verify_archived_status() -> dict[str, Any]:
    """Return a read-only verification of the Telectro Archived status."""

    status = _get_archived_status_state()
    issues: list[dict[str, Any]] = []

    if status is None:
        label_conflict = _get_archived_label_conflict()

        if label_conflict is not None:
            issues.append(
                {
                    "type": "archived_status_name_conflict",
                    "expected_name": ARCHIVED_STATUS_NAME,
                    "actual_name": label_conflict.get("name"),
                }
            )
        else:
            issues.append(
                {
                    "type": "missing_archived_status",
                    "status": ARCHIVED_STATUS_NAME,
                }
            )

        return {
            "ok": False,
            "site": frappe.local.site,
            "status": None,
            "expected": dict(ARCHIVED_STATUS_SPEC),
            "issue_count": len(issues),
            "issues": issues,
        }

    for fieldname, expected in ARCHIVED_STATUS_SPEC.items():
        actual = _normalise_status_value(
            fieldname,
            status.get(fieldname),
        )

        if actual == expected:
            continue

        issues.append(
            {
                "type": "archived_status_field_mismatch",
                "field": fieldname,
                "expected": expected,
                "actual": actual,
            }
        )

    return {
        "ok": not issues,
        "site": frappe.local.site,
        "status": dict(status),
        "expected": dict(ARCHIVED_STATUS_SPEC),
        "issue_count": len(issues),
        "issues": issues,
    }


def ensure_archived_status() -> dict[str, Any]:
    """
    Ensure the canonical Telectro Archived ticket status exists.

    Only a genuinely missing Archived status is reconciled automatically.
    Existing conflicting state is deliberately not rewritten.
    """

    before = verify_archived_status()

    reconcilable_issue_types = {
        "missing_archived_status",
    }

    unexpected_issues = [
        issue
        for issue in before["issues"]
        if issue["type"] not in reconcilable_issue_types
    ]

    if unexpected_issues:
        frappe.throw(
            "Archived status reconciliation stopped because unexpected "
            "state was found:\n"
            + frappe.as_json(unexpected_issues, indent=2),
            title="Archived Status Conflict",
        )

    changed: list[dict[str, Any]] = []

    if not frappe.db.exists(
        "HD Ticket Status",
        ARCHIVED_STATUS_NAME,
    ):
        status = frappe.new_doc("HD Ticket Status")

        for fieldname, value in ARCHIVED_STATUS_SPEC.items():
            setattr(status, fieldname, value)

        status.insert()

        changed.append(
            {
                "action": "create",
                "status": ARCHIVED_STATUS_NAME,
            }
        )

    after = verify_archived_status()

    if not after["ok"]:
        frappe.throw(
            "Archived status reconciliation did not reach the expected "
            "state:\n"
            + frappe.as_json(after["issues"], indent=2),
            title="Archived Status Verification Failed",
        )

    return {
        "ok": True,
        "site": after["site"],
        "changed_count": len(changed),
        "changed": changed,
        "verification": after,
    }


def apply_archived_status() -> dict[str, Any]:
    """Explicit transactional entry point for deliberate operator use."""

    try:
        result = ensure_archived_status()
        frappe.db.commit()
        return result
    except Exception:
        frappe.db.rollback()
        raise


def after_migrate() -> dict[str, Any]:
    """Ensure the Telectro Archived status exists after each migration."""

    result = ensure_archived_status()

    frappe.logger("telephony").info(
        "Archived HD Ticket Status verified: %s changed",
        result["changed_count"],
    )

    return result
