from collections.abc import Mapping
from dataclasses import dataclass

import frappe

from telephony.scripts.import_location_release import (
    LocationReleaseRow,
    validate_release_stages,
    validate_target_preflight,
)
from telephony.scripts.infrastructure_reconciliation import (
    LOCATION_V2_AUTHORITATIVE_FIELDS,
)
from telephony.scripts.infrastructure_reconciliation_adapter import (
    LocationDatabaseReconciliationPlan,
    plan_stored_location_reconciliation,
)


@dataclass(frozen=True)
class LocationScopeMembership:
    scope_key: str
    import_versions: tuple[str, ...]
    versioned_location_ids: tuple[str, ...]
    legacy_location_ids: tuple[str, ...]
    known_location_ids: tuple[str, ...]


@dataclass(frozen=True)
class LocationBatchEntryPlan:
    location_id: str
    desired_values: tuple[tuple[str, object], ...]
    database_plan: LocationDatabaseReconciliationPlan


@dataclass(frozen=True)
class LocationBatchPlan:
    scope_key: str
    import_version: str
    membership: LocationScopeMembership
    entries: tuple[LocationBatchEntryPlan, ...]
    new_stages: tuple[
        tuple[LocationReleaseRow, ...],
        ...,
    ]
    external_prerequisites: tuple[str, ...]
    missing_location_ids: tuple[str, ...]


def _required_text(value, label):
    value = (value or "").strip()

    if not value:
        raise ValueError(
            f"{label} is required"
        )

    return value


def _optional_text(value):
    value = (value or "").strip()
    return value or None


def get_location_scope_membership(
    scope_key,
    legacy_source=None,
):
    scope_key = _required_text(
        scope_key,
        "Infrastructure scope key",
    )

    legacy_source = _optional_text(
        legacy_source
    )

    import_versions = tuple(
        sorted(
            frappe.get_all(
                "TELECTRO Infrastructure Import",
                filters={
                    "scope_key": scope_key,
                },
                pluck="name",
            )
        )
    )

    versioned_location_ids = ()

    if import_versions:
        versioned_location_ids = tuple(
            sorted(
                frappe.get_all(
                    "Location",
                    filters={
                        "custom_first_seen_import": [
                            "in",
                            list(import_versions),
                        ],
                    },
                    pluck="name",
                )
            )
        )

    legacy_location_ids = ()

    if legacy_source:
        legacy_location_ids = tuple(
            sorted(
                frappe.get_all(
                    "Location",
                    filters={
                        "custom_kmz_source":
                            legacy_source,
                    },
                    pluck="name",
                )
            )
        )

    known_location_ids = tuple(
        sorted(
            set(versioned_location_ids)
            | set(legacy_location_ids)
        )
    )

    return LocationScopeMembership(
        scope_key=scope_key,
        import_versions=import_versions,
        versioned_location_ids=(
            versioned_location_ids
        ),
        legacy_location_ids=(
            legacy_location_ids
        ),
        known_location_ids=known_location_ids,
    )


def _freeze_desired(desired):
    return tuple(
        (
            fieldname,
            desired[fieldname],
        )
        for fieldname
        in LOCATION_V2_AUTHORITATIVE_FIELDS
    )


def _desired_dict(entry):
    return dict(
        entry.desired_values
    )


def _validate_batch_identity(entries):
    ids = set()
    labels = set()

    for entry in entries:
        location_id = entry.location_id
        desired = _desired_dict(entry)

        location_name = _required_text(
            desired.get("location_name"),
            (
                "Location Name for "
                f"{location_id}"
            ),
        )

        if location_id in ids:
            raise ValueError(
                "duplicate Location ID in V2 batch: "
                f"{location_id}"
            )

        if location_name in labels:
            raise ValueError(
                "duplicate Location Name in V2 batch: "
                f"{location_name}"
            )

        ids.add(location_id)
        labels.add(location_name)

    for entry in entries:
        desired = _desired_dict(entry)

        location_id = entry.location_id
        location_name = desired[
            "location_name"
        ]

        if (
            location_id != location_name
            and (
                location_id in labels
                or location_name in ids
            )
        ):
            raise ValueError(
                "Location ID / Location Name collision "
                "across V2 batch: "
                f"{location_id!r} / "
                f"{location_name!r}"
            )


def _to_release_row(entry):
    desired = _desired_dict(entry)

    return LocationReleaseRow(
        name=entry.location_id,
        location_name=_required_text(
            desired["location_name"],
            "Location Name",
        ),
        parent_location=_optional_text(
            desired["parent_location"]
        ),
        is_container=int(
            desired["is_container"] or 0
        ),
        is_group=int(
            desired["is_group"] or 0
        ),
        latitude=desired["latitude"],
        longitude=desired["longitude"],
        area_uom=_optional_text(
            desired["area_uom"]
        ),
        location=desired["location"],
        custom_kmz_source=_optional_text(
            desired["custom_kmz_source"]
        ),
        custom_kmz_folder_path=_optional_text(
            desired[
                "custom_kmz_folder_path"
            ]
        ),
        custom_kmz_geometry_type=_optional_text(
            desired[
                "custom_kmz_geometry_type"
            ]
        ),
        custom_kmz_description=_optional_text(
            desired[
                "custom_kmz_description"
            ]
        ),
        custom_kmz_metadata_json=desired[
            "custom_kmz_metadata_json"
        ],
    )


def _build_new_stages(entries):
    new_rows = {
        entry.location_id:
            _to_release_row(entry)
        for entry in entries
        if (
            entry.database_plan
            .reconciliation
            .state
            == "NEW"
        )
    }

    if not new_rows:
        return (), ()

    new_ids = set(
        new_rows
    )

    external_prerequisites = set()

    for row in new_rows.values():
        parent = row.parent_location

        if not parent:
            continue

        if parent in new_ids:
            parent_row = new_rows[
                parent
            ]

            if not int(
                parent_row.is_group or 0
            ):
                raise ValueError(
                    "NEW Location parent must be "
                    "a group: "
                    f"{parent}"
                )
        else:
            external_prerequisites.add(
                parent
            )

    remaining = dict(
        new_rows
    )

    available_new_parents = set()
    stages = []

    while remaining:
        ready_ids = []

        for location_id, row in (
            remaining.items()
        ):
            parent = row.parent_location

            if (
                not parent
                or parent not in new_ids
                or parent
                in available_new_parents
            ):
                ready_ids.append(
                    location_id
                )

        ready_ids.sort()

        if not ready_ids:
            unresolved = ", ".join(
                sorted(remaining)
            )

            raise ValueError(
                "Unable to stage NEW Locations; "
                "cyclic or unresolved NEW parent "
                "dependency: "
                f"{unresolved}"
            )

        stage = tuple(
            remaining[
                location_id
            ]
            for location_id
            in ready_ids
        )

        stages.append(
            stage
        )

        for location_id in ready_ids:
            available_new_parents.add(
                location_id
            )

            del remaining[
                location_id
            ]

    stages = tuple(
        stages
    )

    external_prerequisites = tuple(
        sorted(
            external_prerequisites
        )
    )

    validate_release_stages(
        stages,
        set(
            external_prerequisites
        ),
    )

    validate_target_preflight(
        stages,
        set(
            external_prerequisites
        ),
    )

    return (
        stages,
        external_prerequisites,
    )


def plan_location_batch(
    desired_by_id,
    scope_key,
    import_version,
    legacy_source=None,
):
    if not isinstance(
        desired_by_id,
        Mapping,
    ):
        raise TypeError(
            "desired_by_id must be a mapping"
        )

    scope_key = _required_text(
        scope_key,
        "Infrastructure scope key",
    )

    import_version = _required_text(
        import_version,
        "Infrastructure import version",
    )

    membership = (
        get_location_scope_membership(
            scope_key,
            legacy_source=legacy_source,
        )
    )

    entries = []

    seen_ids = set()

    for raw_location_id in sorted(
        desired_by_id,
        key=lambda value: str(value),
    ):
        location_id = _required_text(
            raw_location_id,
            "Location ID",
        )

        if location_id in seen_ids:
            raise ValueError(
                "duplicate normalized Location ID "
                "in V2 batch: "
                f"{location_id}"
            )

        seen_ids.add(
            location_id
        )

        desired = desired_by_id[
            raw_location_id
        ]

        if not isinstance(
            desired,
            Mapping,
        ):
            raise TypeError(
                "desired Location state must be "
                "a mapping: "
                f"{location_id}"
            )

        database_plan = (
            plan_stored_location_reconciliation(
                location_id,
                desired,
                import_version,
            )
        )

        entries.append(
            LocationBatchEntryPlan(
                location_id=location_id,
                desired_values=_freeze_desired(
                    desired
                ),
                database_plan=database_plan,
            )
        )

    entries = tuple(
        entries
    )

    _validate_batch_identity(
        entries
    )

    desired_ids = {
        entry.location_id
        for entry in entries
    }

    missing_location_ids = tuple(
        sorted(
            set(
                membership
                .known_location_ids
            )
            - desired_ids
        )
    )

    (
        new_stages,
        external_prerequisites,
    ) = _build_new_stages(
        entries
    )

    return LocationBatchPlan(
        scope_key=scope_key,
        import_version=import_version,
        membership=membership,
        entries=entries,
        new_stages=new_stages,
        external_prerequisites=(
            external_prerequisites
        ),
        missing_location_ids=(
            missing_location_ids
        ),
    )
