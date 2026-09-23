from collections.abc import Mapping
from dataclasses import dataclass


LOCATION_V2_AUTHORITATIVE_FIELDS = (
    "location_name",
    "parent_location",
    "is_container",
    "is_group",
    "latitude",
    "longitude",
    "area_uom",
    "location",
    "custom_kmz_source",
    "custom_kmz_folder_path",
    "custom_kmz_geometry_type",
    "custom_kmz_description",
    "custom_kmz_metadata_json",
    "custom_infrastructure_class",
    "custom_lifecycle_state",
    "custom_customer_visibility",
    "custom_ticket_selectability",
)

LOCATION_V2_PROVENANCE_FIELDS = (
    "custom_first_seen_import",
    "custom_last_seen_import",
    "custom_last_changed_import",
)

INTEGER_FIELDS = {
    "is_container",
    "is_group",
}

FLOAT_FIELDS = {
    "latitude",
    "longitude",
}


@dataclass(frozen=True)
class LocationFieldChange:
    fieldname: str
    stored_value: object
    desired_value: object


@dataclass(frozen=True)
class LocationReconciliationPlan:
    location_id: str
    state: str
    changes: tuple[LocationFieldChange, ...]


def _require_authoritative_fields(values, *, label):
    missing = [
        fieldname
        for fieldname in LOCATION_V2_AUTHORITATIVE_FIELDS
        if fieldname not in values
    ]

    if missing:
        raise ValueError(
            f"{label} Location state is missing "
            f"authoritative fields: {', '.join(missing)}"
        )


def _normalize_for_compare(fieldname, value):
    if fieldname in INTEGER_FIELDS:
        return int(value or 0)

    if fieldname in FLOAT_FIELDS:
        if value is None or value == "":
            return None

        return float(value)

    return value


def plan_location_reconciliation(
    location_id,
    desired,
    stored,
):
    location_id = (location_id or "").strip()

    if not location_id:
        raise ValueError(
            "Location reconciliation requires a canonical "
            "Location ID"
        )

    if not isinstance(desired, Mapping):
        raise TypeError(
            "desired Location state must be a mapping"
        )

    _require_authoritative_fields(
        desired,
        label="desired",
    )

    if stored is None:
        return LocationReconciliationPlan(
            location_id=location_id,
            state="NEW",
            changes=(),
        )

    if not isinstance(stored, Mapping):
        raise TypeError(
            "stored Location state must be a mapping or None"
        )

    _require_authoritative_fields(
        stored,
        label="stored",
    )

    changes = []

    for fieldname in LOCATION_V2_AUTHORITATIVE_FIELDS:
        stored_value = stored[fieldname]
        desired_value = desired[fieldname]

        stored_compare = _normalize_for_compare(
            fieldname,
            stored_value,
        )

        desired_compare = _normalize_for_compare(
            fieldname,
            desired_value,
        )

        if stored_compare == desired_compare:
            continue

        changes.append(
            LocationFieldChange(
                fieldname=fieldname,
                stored_value=stored_value,
                desired_value=desired_value,
            )
        )

    state = (
        "CHANGED"
        if changes
        else "UNCHANGED"
    )

    return LocationReconciliationPlan(
        location_id=location_id,
        state=state,
        changes=tuple(changes),
    )
