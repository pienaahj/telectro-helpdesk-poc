import hashlib
from pathlib import Path

from telephony.scripts.import_location_release import (
    parse_release_file,
)


BOSCHENDAL_STAGE02_SHA256 = (
    "2d18ed5b54a54398dcc2b3d5aa5898f"
    "4a26d63617ab4cb32e02c70f0a9892570"
)

BOSCHENDAL_STAGE02_ROW_COUNT = 262

BOSCHENDAL_STAGE01_PARENTS = frozenset(
    {
        "Boschendal - Areas",
        "Boschendal - Buildings",
        "Boschendal - Links",
        "Boschendal - Network Nodes",
        "Boschendal - Other",
        "Boschendal - Residents",
    }
)

BOSCHENDAL_PROPOSED_FIBRE_IDS = frozenset(
    {
        "kmz102cf5ee70bc000f74d3a97c",
        "kmz3b80d7497b324c460f11872c",
        "kmz6c463c2a4d96d231db58bf64",
        "kmzb96db025f34406893d8823d2",
        "kmzc70f07c05f7b32a524be83ba",
    }
)

BOSCHENDAL_NETWORK_CABINET_ID = (
    "kmz611ab1020c9ffcd84c08db73"
)

BOSCHENDAL_SOURCE_NAME = "Boschendal.kmz"


def _sha256(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _desired_from_release_row(row):
    return {
        "location_name":
            row.location_name,
        "parent_location":
            row.parent_location,
        "is_container":
            row.is_container,
        "is_group":
            row.is_group,
        "latitude":
            row.latitude,
        "longitude":
            row.longitude,
        "area_uom":
            row.area_uom,
        "location":
            row.location,
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
        "custom_infrastructure_class":
            None,
        "custom_lifecycle_state":
            None,
        "custom_customer_visibility":
            None,
        "custom_ticket_selectability":
            None,
    }


def build_boschendal_location_v2_desired(
    stage02_path,
):
    stage02_path = Path(
        stage02_path
    )

    actual_hash = _sha256(
        stage02_path
    )

    if (
        actual_hash
        != BOSCHENDAL_STAGE02_SHA256
    ):
        raise ValueError(
            "Boschendal Stage-02 release hash "
            "mismatch: "
            f"actual={actual_hash} "
            f"expected="
            f"{BOSCHENDAL_STAGE02_SHA256}"
        )

    rows = parse_release_file(
        stage02_path
    )

    if (
        len(rows)
        != BOSCHENDAL_STAGE02_ROW_COUNT
    ):
        raise ValueError(
            "Unexpected Boschendal Stage-02 "
            "row count: "
            f"{len(rows)}"
        )

    desired_by_id = {}

    for row in rows:
        if row.name in desired_by_id:
            raise ValueError(
                "Duplicate Boschendal canonical "
                f"Location ID: {row.name}"
            )

        if (
            row.parent_location
            not in BOSCHENDAL_STAGE01_PARENTS
        ):
            raise ValueError(
                "Unexpected Boschendal Stage-02 "
                "parent: "
                f"{row.name} -> "
                f"{row.parent_location!r}"
            )

        if (
            row.custom_kmz_source
            != BOSCHENDAL_SOURCE_NAME
        ):
            raise ValueError(
                "Unexpected Boschendal source "
                "marker: "
                f"{row.name} "
                f"{row.custom_kmz_source!r}"
            )

        desired_by_id[
            row.name
        ] = _desired_from_release_row(
            row
        )

    actual_ids = set(
        desired_by_id
    )

    if (
        BOSCHENDAL_NETWORK_CABINET_ID
        not in actual_ids
    ):
        raise ValueError(
            "Canonical Boschendal 15U Cabinet "
            "Location is missing"
        )

    missing_proposed = (
        BOSCHENDAL_PROPOSED_FIBRE_IDS
        - actual_ids
    )

    if missing_proposed:
        raise ValueError(
            "Canonical Boschendal Proposed Fibre "
            "Locations are missing: "
            + ", ".join(
                sorted(
                    missing_proposed
                )
            )
        )

    desired_by_id[
        BOSCHENDAL_NETWORK_CABINET_ID
    ][
        "custom_infrastructure_class"
    ] = "Network Cabinet"

    for location_id in (
        BOSCHENDAL_PROPOSED_FIBRE_IDS
    ):
        desired_by_id[
            location_id
        ][
            "custom_lifecycle_state"
        ] = "Planned"

    return desired_by_id
