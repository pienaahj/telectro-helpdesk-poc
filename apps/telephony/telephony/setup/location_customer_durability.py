from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe


PILOT_SITES_ROOT = "Pilot Sites"


def _get_default_campus_relationships() -> list[dict[str, Any]]:
    return frappe.get_all(
        "Customer",
        filters={
            "custom_default_campus": ["is", "set"],
        },
        fields=[
            "name",
            "custom_default_campus",
        ],
        order_by="name asc",
    )


def _get_campus_state(
    campus_name: str,
) -> dict[str, Any] | None:
    return frappe.db.get_value(
        "Location",
        campus_name,
        [
            "name",
            "parent_location",
            "is_group",
            "custom_customer",
        ],
        as_dict=True,
    )


def verify_location_customer_ownership() -> dict[str, Any]:
    relationships = (
        _get_default_campus_relationships()
    )

    customers_by_campus: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for row in relationships:
        campus = (
            row.get("custom_default_campus")
            or ""
        ).strip()

        if not campus:
            continue

        customers_by_campus[campus].append(
            row["name"]
        )

    issues: list[dict[str, Any]] = []
    reconcilable: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []

    for campus_name in sorted(
        customers_by_campus
    ):
        customers = tuple(
            sorted(
                customers_by_campus[
                    campus_name
                ]
            )
        )

        if len(customers) != 1:
            issues.append(
                {
                    "type":
                        "ambiguous_default_campus_ownership",
                    "campus": campus_name,
                    "customers": customers,
                }
            )
            continue

        customer = customers[0]
        campus = _get_campus_state(
            campus_name
        )

        if campus is None:
            issues.append(
                {
                    "type":
                        "missing_default_campus_location",
                    "campus": campus_name,
                    "customer": customer,
                }
            )
            continue

        if (
            campus.get("parent_location")
            != PILOT_SITES_ROOT
            or not int(
                campus.get("is_group") or 0
            )
        ):
            issues.append(
                {
                    "type":
                        "invalid_default_campus_location",
                    "campus": campus_name,
                    "customer": customer,
                    "parent_location":
                        campus.get(
                            "parent_location"
                        ),
                    "is_group": int(
                        campus.get(
                            "is_group"
                        ) or 0
                    ),
                }
            )
            continue

        actual_customer = (
            campus.get("custom_customer")
            or ""
        ).strip()

        if not actual_customer:
            reconcilable.append(
                {
                    "campus": campus_name,
                    "customer": customer,
                }
            )
            continue

        if actual_customer != customer:
            issues.append(
                {
                    "type":
                        "campus_customer_conflict",
                    "campus": campus_name,
                    "expected_customer":
                        customer,
                    "actual_customer":
                        actual_customer,
                }
            )
            continue

        verified.append(
            {
                "campus": campus_name,
                "customer": customer,
            }
        )

    return {
        "ok": not issues,
        "site": frappe.local.site,
        "relationship_count":
            len(relationships),
        "verified_count":
            len(verified),
        "reconcilable_count":
            len(reconcilable),
        "issue_count": len(issues),
        "verified": verified,
        "reconcilable": reconcilable,
        "issues": issues,
    }

def ensure_location_customer_ownership() -> dict[str, Any]:
    """
    Establish missing Campus Customer ownership only where the
    existing Customer default-Campus relationship is unambiguous.

    Existing conflicts are never rewritten.
    """
    before = verify_location_customer_ownership()

    if before["issues"]:
        frappe.throw(
            "Location Customer ownership reconciliation stopped "
            "because conflicting or invalid state was found:\n"
            + frappe.as_json(
                before["issues"],
                indent=2,
            ),
            title="Location Customer Ownership Conflict",
        )

    changed: list[dict[str, Any]] = []

    for row in before["reconcilable"]:
        frappe.db.set_value(
            "Location",
            row["campus"],
            "custom_customer",
            row["customer"],
            update_modified=False,
        )

        changed.append(
            {
                "action":
                    "establish_customer_ownership",
                "campus": row["campus"],
                "customer": row["customer"],
            }
        )

    after = verify_location_customer_ownership()

    if (
        not after["ok"]
        or after["reconcilable_count"]
    ):
        frappe.throw(
            "Location Customer ownership reconciliation "
            "did not reach the expected state:\n"
            + frappe.as_json(
                {
                    "issues": after["issues"],
                    "reconcilable":
                        after["reconcilable"],
                },
                indent=2,
            ),
            title=(
                "Location Customer Ownership "
                "Verification Failed"
            ),
        )

    return {
        "ok": True,
        "site": after["site"],
        "changed_count": len(changed),
        "changed": changed,
        "verification": after,
    }

def apply_location_customer_ownership() -> dict[str, Any]:
    """Explicit transactional entry point for deliberate operator use."""
    try:
        result = ensure_location_customer_ownership()
        frappe.db.commit()
        return result
    except Exception:
        frappe.db.rollback()
        raise

def after_migrate() -> dict[str, Any]:
    """Ensure Campus Customer ownership after each migration."""

    result = ensure_location_customer_ownership()

    frappe.logger("telephony").info(
        "Location Customer ownership verified: %s changed",
        result["changed_count"],
    )

    return result
