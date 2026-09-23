from collections.abc import Mapping
from dataclasses import dataclass

import frappe
from frappe.utils.nestedset import update_nsm

from telephony.scripts.infrastructure_reconciliation_adapter import (
    LocationDatabaseReconciliationPlan,
)


@dataclass(frozen=True)
class LocationParentMoveResult:
    location_id: str
    old_parent: str | None
    new_parent: str | None


def _required_text(value, label):
    value = (value or "").strip()

    if not value:
        raise ValueError(
            f"{label} is required"
        )

    return value


def _normalise_parent(value):
    value = (value or "").strip()

    return value or None


def apply_existing_location_parent_move(
    location_id,
    stored,
    plan,
):
    location_id = _required_text(
        location_id,
        "Location ID",
    )

    if not isinstance(
        plan,
        LocationDatabaseReconciliationPlan,
    ):
        raise TypeError(
            "plan must be a "
            "LocationDatabaseReconciliationPlan"
        )

    if plan.reconciliation.location_id != location_id:
        raise ValueError(
            "Location reconciliation plan ID mismatch: "
            f"plan={plan.reconciliation.location_id!r} "
            f"requested={location_id!r}"
        )

    if plan.reconciliation.state != "CHANGED":
        raise ValueError(
            "Location parent move requires "
            "CHANGED reconciliation state"
        )

    if not isinstance(stored, Mapping):
        raise TypeError(
            "stored Location state must be a mapping"
        )

    changes = tuple(
        plan.reconciliation.changes
    )

    parent_changes = tuple(
        change
        for change in changes
        if change.fieldname == "parent_location"
    )

    if len(parent_changes) != 1:
        raise ValueError(
            "Location parent move requires exactly one "
            "parent_location change"
        )

    other_changes = tuple(
        change.fieldname
        for change in changes
        if change.fieldname != "parent_location"
    )

    if other_changes:
        raise ValueError(
            "Location parent-move writer does not yet "
            "support additional changed fields: "
            + ", ".join(other_changes)
        )

    old_parent = _normalise_parent(
        stored.get("parent_location")
    )

    new_parent = _normalise_parent(
        parent_changes[0].desired_value
    )

    if old_parent == new_parent:
        raise ValueError(
            "Location parent move has no effective "
            "parent change"
        )

    doc = frappe.get_doc(
        "Location",
        location_id,
    )

    live_parent = _normalise_parent(
        doc.get("parent_location")
    )

    if live_parent != old_parent:
        raise ValueError(
            "Stored Location parent is stale: "
            f"stored={old_parent!r} "
            f"live={live_parent!r}"
        )

    if new_parent:
        parent_state = frappe.db.get_value(
            "Location",
            new_parent,
            [
                "name",
                "is_group",
            ],
            as_dict=True,
        )

        if parent_state is None:
            raise ValueError(
                "Target parent Location does not exist: "
                f"{new_parent}"
            )

        if not parent_state.is_group:
            raise ValueError(
                "Target parent Location is not a group: "
                f"{new_parent}"
            )

    doc.old_parent = old_parent or ""
    doc.parent_location = new_parent or ""

    frappe.db.set_value(
        "Location",
        location_id,
        "parent_location",
        new_parent or "",
        update_modified=False,
    )

    update_nsm(doc)

    return LocationParentMoveResult(
        location_id=location_id,
        old_parent=old_parent,
        new_parent=new_parent,
    )
