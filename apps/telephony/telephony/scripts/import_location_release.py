import csv
from dataclasses import dataclass
from pathlib import Path
import frappe


V1_HEADER = (
    "ID",
    "Location Name",
    "Parent Location",
    "Is Container",
    "Is Group",
    "Latitude",
    "Longitude",
    "Area UOM",
    "Location",
    "KMZ Source",
    "KMZ Folder Path",
    "KMZ Geometry Type",
    "KMZ Description",
    "KMZ Metadata (JSON)",
)


@dataclass(frozen=True)
class LocationReleaseRow:
    name: str
    location_name: str
    parent_location: str | None
    is_container: int
    is_group: int
    latitude: float | None
    longitude: float | None
    area_uom: str | None
    location: str | None
    custom_kmz_source: str | None
    custom_kmz_folder_path: str | None
    custom_kmz_geometry_type: str | None
    custom_kmz_description: str | None
    custom_kmz_metadata_json: str | None


def _optional_text(value):
    value = (value or "").strip()
    return value or None

def _optional_verbatim(value):
    if value is None or value == "":
        return None

    return value

def _required_text(value, fieldname):
    value = (value or "").strip()

    if not value:
        raise ValueError(
            f"Missing required field: {fieldname}"
        )

    return value


def _check(value, fieldname):
    value = (value or "").strip()

    if value not in {"0", "1"}:
        raise ValueError(
            f"{fieldname} must be 0 or 1"
        )

    return int(value)


def _optional_float(value, fieldname):
    value = (value or "").strip()

    if not value:
        return None

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{fieldname} must be numeric"
        ) from exc


def parse_release_file(path):
    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        actual_header = reader.fieldnames or []

        if actual_header != list(V1_HEADER):
            raise ValueError(
                "Location release header does not match "
                "the V1 contract"
            )

        rows = []

        seen_ids = set()
        seen_location_names = set()

        for line_number, raw in enumerate(
            reader,
            start=2,
        ):
            if (
                None in raw
                or any(
                    raw.get(fieldname) is None
                    for fieldname in V1_HEADER
                )
            ):
                raise ValueError(
                    "Location release row has incorrect "
                    f"column count at line {line_number}"
                )
            name = _required_text(
                raw["ID"],
                "ID",
            )

            location_name = _required_text(
                raw["Location Name"],
                "Location Name",
            )

            if name in seen_ids:
                raise ValueError(
                    f"duplicate ID at line {line_number}: "
                    f"{name}"
                )

            if location_name in seen_location_names:
                raise ValueError(
                    "duplicate Location Name at line "
                    f"{line_number}: {location_name}"
                )

            seen_ids.add(name)
            seen_location_names.add(
                location_name
            )

            rows.append(
                LocationReleaseRow(
                    name=name,
                    location_name=location_name,
                    parent_location=_optional_text(
                        raw["Parent Location"]
                    ),
                    is_container=_check(
                        raw["Is Container"],
                        "Is Container",
                    ),
                    is_group=_check(
                        raw["Is Group"],
                        "Is Group",
                    ),
                    latitude=_optional_float(
                        raw["Latitude"],
                        "Latitude",
                    ),
                    longitude=_optional_float(
                        raw["Longitude"],
                        "Longitude",
                    ),
                    area_uom=_optional_text(
                        raw["Area UOM"]
                    ),
                    location=_optional_verbatim(
                        raw["Location"]
                    ),
                    custom_kmz_source=_optional_verbatim(
                        raw["KMZ Source"]
                    ),
                    custom_kmz_folder_path=(
                        _optional_verbatim(
                            raw["KMZ Folder Path"]
                        )
                    ),
                    custom_kmz_geometry_type=(
                        _optional_text(
                            raw["KMZ Geometry Type"]
                        )
                    ),
                    custom_kmz_description=(
                        _optional_verbatim(
                            raw["KMZ Description"]
                        )
                    ),
                    custom_kmz_metadata_json=(
                        _optional_verbatim(
                            raw["KMZ Metadata (JSON)"]
                        )
                    ),
                )
            )

    return rows


def validate_release_stages(
    stages,
    external_prerequisites,
):
    available_parents = set(
        external_prerequisites or set()
    )

    seen_ids = set()
    seen_location_names = set()

    for stage_number, rows in enumerate(stages):
        stage_ids = set()
        stage_location_names = set()

        for row in rows:
            if row.name in seen_ids:
                raise ValueError(
                    "duplicate ID across release stages: "
                    f"{row.name}"
                )

            if row.name in stage_ids:
                raise ValueError(
                    "duplicate ID within release stage: "
                    f"{row.name}"
                )

            if (
                row.name != row.location_name
                and (
                    row.name in seen_location_names
                    or row.name in stage_location_names
                    or row.location_name in seen_ids
                    or row.location_name in stage_ids
                )
            ):
                raise ValueError(
                    "Location ID / Location Name collision "
                    "across release rows: "
                    f"{row.name!r} / "
                    f"{row.location_name!r}"
                )

            if row.location_name in seen_location_names:
                raise ValueError(
                    "duplicate Location Name across "
                    "release stages: "
                    f"{row.location_name}"
                )

            if (
                row.parent_location
                and row.parent_location
                not in available_parents
            ):
                raise ValueError(
                    f"Location {row.name!r} has parent "
                    f"{row.parent_location!r} which is "
                    "not available from an earlier stage "
                    "or external prerequisite"
                )

            stage_ids.add(row.name)
            stage_location_names.add(
                row.location_name
            )

        seen_ids.update(stage_ids)
        available_parents.update(stage_ids)
        seen_location_names.update(
            stage_location_names
        )

    return None

def insert_release_row(row):
    doc = frappe.get_doc(
        {
            "doctype": "Location",
            "location_name": row.location_name,
            "parent_location": row.parent_location,
            "is_container": row.is_container,
            "is_group": row.is_group,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "area_uom": row.area_uom,
            "location": row.location,
            "custom_kmz_source":
                row.custom_kmz_source,
            "custom_kmz_folder_path":
                row.custom_kmz_folder_path,
            "custom_kmz_geometry_type":
                row.custom_kmz_geometry_type,
            "custom_kmz_description":
                row.custom_kmz_description,
            "custom_kmz_metadata_json":
                row.custom_kmz_metadata_json,
        }
    )

    doc.insert(
        ignore_permissions=True,
        set_name=row.name,
    )

    frappe.db.set_value(
        "Location",
        row.name,
        {
            "location_name": row.location_name,
            "latitude": row.latitude,
            "longitude": row.longitude,
        },
        update_modified=False,
    )

    return row.name

def verify_release_row(row):
    fields = [
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
    ]

    stored = frappe.db.get_value(
        "Location",
        row.name,
        fields,
        as_dict=True,
    )

    if not stored:
        raise ValueError(
            "Missing stored Location after release insert: "
            f"{row.name}"
        )

    expected = {
        "location_name": row.location_name,
        "parent_location": row.parent_location,
        "is_container": row.is_container,
        "is_group": row.is_group,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "area_uom": row.area_uom,
        "location": row.location,
        "custom_kmz_source":
            row.custom_kmz_source,
        "custom_kmz_folder_path":
            row.custom_kmz_folder_path,
        "custom_kmz_geometry_type":
            row.custom_kmz_geometry_type,
        "custom_kmz_description":
            row.custom_kmz_description,
        "custom_kmz_metadata_json":
            row.custom_kmz_metadata_json,
    }

    for fieldname in fields:
        actual = stored.get(fieldname)
        wanted = expected[fieldname]

        if fieldname in {
            "is_container",
            "is_group",
        }:
            actual = int(actual or 0)
            wanted = int(wanted or 0)

        if fieldname in {
            "latitude",
            "longitude",
        }:
            actual = (
                None
                if actual is None
                else float(actual)
            )

            wanted = (
                None
                if wanted is None
                else float(wanted)
            )

        if actual != wanted:
            raise ValueError(
                "Stored Location authoritative field "
                "mismatch: "
                f"{row.name} {fieldname} "
                f"actual={actual!r} "
                f"expected={wanted!r}"
            )

    return None

def apply_release_stages(
    stages,
    *,
    external_prerequisites,
    expected_site,
):
    if frappe.local.site != expected_site:
        raise ValueError(
            "Location release target site mismatch: "
            f"actual={frappe.local.site!r} "
            f"expected={expected_site!r}"
        )

    stages = [
        list(stage)
        for stage in stages
    ]

    validate_release_stages(
        stages,
        external_prerequisites=external_prerequisites,
    )

    validate_target_preflight(
        stages,
        external_prerequisites=external_prerequisites,
    )

    stage_counts = []
    inserted_count = 0

    for stage in stages:
        stage_counts.append(
            len(stage)
        )

        for row in stage:
            insert_release_row(row)
            verify_release_row(row)

            inserted_count += 1

    return {
        "inserted_count": inserted_count,
        "stage_counts": stage_counts,
    }

def validate_target_preflight(
    stages,
    external_prerequisites,
):
    prerequisites = set(
        external_prerequisites or set()
    )

    for prerequisite in sorted(prerequisites):
        if not frappe.db.exists(
            "Location",
            prerequisite,
        ):
            raise ValueError(
                "Missing target Location prerequisite: "
                f"{prerequisite}"
            )

        is_group = frappe.db.get_value(
            "Location",
            prerequisite,
            "is_group",
        )

        if not int(is_group or 0):
            raise ValueError(
                "Target Location prerequisite must be "
                f"a group: {prerequisite}"
            )

    for rows in stages:
        for row in rows:
            if frappe.db.exists(
                "Location",
                row.name,
            ):
                raise ValueError(
                    "Location ID collision on target: "
                    f"{row.name}"
                )

            existing_label = frappe.db.get_value(
                "Location",
                {
                    "location_name":
                        row.location_name,
                },
                "name",
            )

            if existing_label:
                raise ValueError(
                    "Location Name collision on target: "
                    f"{row.location_name}"
                )

            existing_autoname = frappe.db.get_value(
                "Location",
                {
                    "location_name": row.name,
                },
                "name",
            )

            if existing_autoname:
                raise ValueError(
                    "Location autoname collision on "
                    f"target: {row.name}"
                )

    return None
