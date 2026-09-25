from dataclasses import dataclass

import frappe

from telephony.scripts.infrastructure_reconciliation import (
    LOCATION_V2_AUTHORITATIVE_FIELDS,
    LOCATION_V2_PROVENANCE_FIELDS,
    LocationReconciliationPlan,
    plan_location_reconciliation,
)


LOCATION_V2_DATABASE_FIELDS = (
    LOCATION_V2_AUTHORITATIVE_FIELDS
    + LOCATION_V2_PROVENANCE_FIELDS
)


@dataclass(frozen=True)
class LocationProvenancePlan:
    first_seen_import: str
    last_seen_import: str
    last_changed_import: str | None


@dataclass(frozen=True)
class LocationDatabaseReconciliationPlan:
    reconciliation: LocationReconciliationPlan
    provenance: LocationProvenancePlan


def _required_text(value, label):
    value = (value or "").strip()

    if not value:
        raise ValueError(
            f"{label} is required"
        )

    return value


def get_stored_location_state(location_id):
    location_id = _required_text(
        location_id,
        "Location ID",
    )

    row = frappe.db.get_value(
        "Location",
        location_id,
        list(LOCATION_V2_DATABASE_FIELDS),
        as_dict=True,
    )

    if row is None:
        return None

    return dict(row)


def plan_location_provenance(
    reconciliation,
    stored,
    import_version,
):
    import_version = _required_text(
        import_version,
        "Infrastructure import version",
    )

    if reconciliation.state == "NEW":
        return LocationProvenancePlan(
            first_seen_import=import_version,
            last_seen_import=import_version,
            last_changed_import=import_version,
        )

    if stored is None:
        raise ValueError(
            "Stored Location state is required for "
            f"{reconciliation.state} reconciliation"
        )

    first_seen_import = (
        stored.get("custom_first_seen_import")
        or import_version
    )

    if reconciliation.state == "UNCHANGED":
        last_changed_import = stored.get(
            "custom_last_changed_import"
        )
    elif reconciliation.state == "CHANGED":
        last_changed_import = import_version
    else:
        raise ValueError(
            "Unsupported Location reconciliation state: "
            f"{reconciliation.state}"
        )

    return LocationProvenancePlan(
        first_seen_import=first_seen_import,
        last_seen_import=import_version,
        last_changed_import=last_changed_import,
    )


def plan_stored_location_reconciliation(
    location_id,
    desired,
    import_version,
):
    location_id = _required_text(
        location_id,
        "Location ID",
    )

    stored = get_stored_location_state(
        location_id
    )

    reconciliation = plan_location_reconciliation(
        location_id,
        desired,
        stored,
    )

    provenance = plan_location_provenance(
        reconciliation,
        stored,
        import_version,
    )

    return LocationDatabaseReconciliationPlan(
        reconciliation=reconciliation,
        provenance=provenance,
    )
