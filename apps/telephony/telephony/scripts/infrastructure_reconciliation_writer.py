from collections.abc import Mapping
from dataclasses import dataclass

import frappe

from telephony.scripts.infrastructure_reconciliation_adapter import (
    LocationDatabaseReconciliationPlan,
)


LOCATION_V2_ORDINARY_WRITE_FIELDS = (
    "location_name",
    "is_container",
    "latitude",
    "longitude",
    "area_uom",
    "custom_kmz_source",
    "custom_kmz_folder_path",
    "custom_kmz_geometry_type",
    "custom_kmz_description",
    "custom_kmz_metadata_json",
    "custom_location_semantics",
    "custom_infrastructure_class",
    "custom_lifecycle_state",
    "custom_customer_visibility",
    "custom_ticket_selectability",
)

LOCATION_V2_DEFERRED_WRITE_FIELDS = (
    "parent_location",
    "is_group",
    "location",
)

LOCATION_V2_PROVENANCE_WRITE_FIELDS = (
    "custom_first_seen_import",
    "custom_last_seen_import",
    "custom_last_changed_import",
)


@dataclass(frozen=True)
class LocationWriteResult:
    location_id: str
    reconciliation_state: str
    updated_fields: tuple[str, ...]


def _required_text(value, label):
    value = (value or "").strip()

    if not value:
        raise ValueError(
            f"{label} is required"
        )

    return value


def apply_existing_location_plan(
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

    state = plan.reconciliation.state

    if state == "NEW":
        raise ValueError(
            "Location V2 writer does not yet support "
            "NEW Location creation"
        )

    if state not in {
        "UNCHANGED",
        "CHANGED",
    }:
        raise ValueError(
            "Unsupported Location reconciliation state: "
            f"{state}"
        )

    if not isinstance(stored, Mapping):
        raise TypeError(
            "stored Location state must be a mapping "
            "for existing Location reconciliation"
        )

    changed_fields = [
        change.fieldname
        for change in plan.reconciliation.changes
    ]

    deferred_fields = [
        fieldname
        for fieldname in changed_fields
        if fieldname
        in LOCATION_V2_DEFERRED_WRITE_FIELDS
    ]

    if deferred_fields:
        raise ValueError(
            "Location V2 writer does not yet support "
            "changes to deferred fields: "
            + ", ".join(deferred_fields)
        )

    unsupported_fields = [
        fieldname
        for fieldname in changed_fields
        if fieldname
        not in LOCATION_V2_ORDINARY_WRITE_FIELDS
    ]

    if unsupported_fields:
        raise ValueError(
            "Location V2 writer has no mutation policy "
            "for fields: "
            + ", ".join(unsupported_fields)
        )

    updates = {}

    for change in plan.reconciliation.changes:
        updates[
            change.fieldname
        ] = change.desired_value

    provenance_values = {
        "custom_first_seen_import":
            plan.provenance.first_seen_import,
        "custom_last_seen_import":
            plan.provenance.last_seen_import,
        "custom_last_changed_import":
            plan.provenance.last_changed_import,
    }

    for fieldname in (
        LOCATION_V2_PROVENANCE_WRITE_FIELDS
    ):
        desired_value = provenance_values[
            fieldname
        ]

        if stored.get(fieldname) == desired_value:
            continue

        updates[fieldname] = desired_value

    if updates:
        frappe.db.set_value(
            "Location",
            location_id,
            updates,
            update_modified=False,
        )

    return LocationWriteResult(
        location_id=location_id,
        reconciliation_state=state,
        updated_fields=tuple(
            updates.keys()
        ),
    )
