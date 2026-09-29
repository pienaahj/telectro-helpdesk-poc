import csv
import hashlib
from pathlib import Path


REQUIRED_SOURCE_COLUMNS = frozenset(
    {
        "site_id",
        "site_name",
        "latitude",
        "longitude",
        "active",
    }
)


def _sha256(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _required_text(value, label):
    value = (value or "").strip()

    if not value:
        raise ValueError(
            f"{label} is required"
        )

    return value


def _required_float(
    value,
    label,
    *,
    minimum,
    maximum,
):
    text = _required_text(
        value,
        label,
    )

    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(
            f"{label} must be numeric: {text!r}"
        ) from exc

    if (
        number < minimum
        or number > maximum
    ):
        raise ValueError(
            f"{label} is outside valid range: "
            f"{number}"
        )

    return number


def _require_active(value):
    text = _required_text(
        value,
        "active",
    ).lower()

    if text in {
        "1",
        "true",
        "yes",
    }:
        return None

    if text in {
        "0",
        "false",
        "no",
    }:
        raise ValueError(
            "Simple-site Campus source contains "
            "an inactive site"
        )

    raise ValueError(
        "active must be one of "
        "1/0, true/false, yes/no"
    )


def _read_source_rows(path):
    path = Path(path)

    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        fieldnames = set(
            reader.fieldnames or ()
        )

        missing_columns = (
            REQUIRED_SOURCE_COLUMNS
            - fieldnames
        )

        if missing_columns:
            raise ValueError(
                "Simple-site source is missing "
                "required columns: "
                + ", ".join(
                    sorted(
                        missing_columns
                    )
                )
            )

        return [
            dict(row)
            for row in reader
        ]


def build_simple_site_campus_v2_desired(
    source_path,
    *,
    expected_sha256,
    expected_row_count,
    customer,
    location_name_prefix,
    parent_location="Pilot Sites",
):
    source_path = Path(
        source_path
    )

    expected_sha256 = _required_text(
        expected_sha256,
        "Expected source SHA-256",
    ).lower()

    customer = _required_text(
        customer,
        "Customer",
    )

    location_name_prefix = _required_text(
        location_name_prefix,
        "Location Name prefix",
    )

    parent_location = _required_text(
        parent_location,
        "Campus parent Location",
    )

    if (
        not isinstance(
            expected_row_count,
            int,
        )
        or expected_row_count <= 0
    ):
        raise ValueError(
            "Expected row count must be "
            "a positive integer"
        )

    actual_hash = _sha256(
        source_path
    )

    if actual_hash != expected_sha256:
        raise ValueError(
            "Simple-site source hash mismatch: "
            f"actual={actual_hash} "
            f"expected={expected_sha256}"
        )

    rows = _read_source_rows(
        source_path
    )

    if len(rows) != expected_row_count:
        raise ValueError(
            "Unexpected simple-site source "
            "row count: "
            f"actual={len(rows)} "
            f"expected={expected_row_count}"
        )

    desired_by_id = {}
    location_names = set()

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        site_id = _required_text(
            row.get("site_id"),
            (
                "site_id at CSV row "
                f"{row_number}"
            ),
        )

        site_name = _required_text(
            row.get("site_name"),
            (
                "site_name at CSV row "
                f"{row_number}"
            ),
        )

        _require_active(
            row.get("active")
        )

        latitude = _required_float(
            row.get("latitude"),
            (
                "latitude at CSV row "
                f"{row_number}"
            ),
            minimum=-90,
            maximum=90,
        )

        longitude = _required_float(
            row.get("longitude"),
            (
                "longitude at CSV row "
                f"{row_number}"
            ),
            minimum=-180,
            maximum=180,
        )

        location_name = (
            location_name_prefix
            + " "
            + site_name
        )

        if site_id in desired_by_id:
            raise ValueError(
                "Duplicate simple-site ID: "
                f"{site_id}"
            )

        if location_name in location_names:
            raise ValueError(
                "Duplicate simple-site "
                "Location Name: "
                f"{location_name}"
            )

        desired_by_id[
            site_id
        ] = {
            "location_name":
                location_name,
            "parent_location":
                parent_location,
            "is_container":
                0,
            "is_group":
                1,
            "latitude":
                latitude,
            "longitude":
                longitude,
            "area_uom":
                None,
            "location":
                None,
            "custom_kmz_source":
                None,
            "custom_kmz_folder_path":
                None,
            "custom_kmz_geometry_type":
                "Point",
            "custom_kmz_description":
                None,
            "custom_kmz_metadata_json":
                None,
            "custom_customer":
                customer,
            "custom_infrastructure_class":
                None,
            "custom_lifecycle_state":
                "Operational",
            "custom_customer_visibility":
                "Customer-safe",
            "custom_ticket_selectability":
                "Selectable",
        }

        location_names.add(
            location_name
        )

    return desired_by_id
