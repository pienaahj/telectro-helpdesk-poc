import tempfile
import unittest
from pathlib import Path
from unittest import mock

from telephony.scripts import (
    boschendal_location_v2_desired,
)
from telephony.scripts.import_location_release import (
    LocationReleaseRow,
)


class TestBoschendalLocationV2Desired(
    unittest.TestCase
):
    def _row(
        self,
        name="kmz001",
        *,
        parent="Boschendal - Other",
        source="Boschendal.kmz",
    ):
        return LocationReleaseRow(
            name=name,
            location_name="Other: Test",
            parent_location=parent,
            is_container=0,
            is_group=0,
            latitude=-33.9,
            longitude=18.9,
            area_uom=None,
            location=None,
            custom_kmz_source=source,
            custom_kmz_folder_path=(
                "Boschendal / Boschendal / Other"
            ),
            custom_kmz_geometry_type="Point",
            custom_kmz_description=None,
            custom_kmz_metadata_json=None,
        )

    def test_desired_row_defaults_are_conservative(
        self,
    ):
        row = self._row()

        desired = (
            boschendal_location_v2_desired
            ._desired_from_release_row(
                row
            )
        )

        self.assertIsNone(
            desired[
                "custom_customer"
            ]
        )

        self.assertIsNone(
            desired[
                "custom_infrastructure_class"
            ]
        )

        self.assertIsNone(
            desired[
                "custom_lifecycle_state"
            ]
        )

        self.assertIsNone(
            desired[
                "custom_customer_visibility"
            ]
        )

        self.assertIsNone(
            desired[
                "custom_ticket_selectability"
            ]
        )

    def test_hash_mismatch_is_refused(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(
                tempdir
            ) / "stage02.csv"

            path.write_text(
                "tampered\n"
            )

            with self.assertRaisesRegex(
                ValueError,
                "release hash mismatch",
            ):
                (
                    boschendal_location_v2_desired
                    .build_boschendal_location_v2_desired(
                        path
                    )
                )

    @mock.patch.object(
        boschendal_location_v2_desired,
        "_sha256",
        return_value=(
            boschendal_location_v2_desired
            .BOSCHENDAL_STAGE02_SHA256
        ),
    )
    @mock.patch.object(
        boschendal_location_v2_desired,
        "parse_release_file",
    )
    def test_wrong_row_count_is_refused(
        self,
        parse_release_file,
        _sha256,
    ):
        parse_release_file.return_value = [
            self._row()
        ]

        with self.assertRaisesRegex(
            ValueError,
            "row count",
        ):
            (
                boschendal_location_v2_desired
                .build_boschendal_location_v2_desired(
                    "unused.csv"
                )
            )

    @mock.patch.object(
        boschendal_location_v2_desired,
        "_sha256",
        return_value=(
            boschendal_location_v2_desired
            .BOSCHENDAL_STAGE02_SHA256
        ),
    )
    @mock.patch.object(
        boschendal_location_v2_desired,
        "parse_release_file",
    )
    def test_unexpected_parent_is_refused(
        self,
        parse_release_file,
        _sha256,
    ):
        rows = [
            self._row(
                name=f"kmz{i:03d}"
            )
            for i in range(
                262
            )
        ]

        rows[0] = self._row(
            name="kmz000",
            parent="Unexpected Parent",
        )

        parse_release_file.return_value = rows

        with self.assertRaisesRegex(
            ValueError,
            "Unexpected Boschendal Stage-02 parent",
        ):
            (
                boschendal_location_v2_desired
                .build_boschendal_location_v2_desired(
                    "unused.csv"
                )
            )

    @mock.patch.object(
        boschendal_location_v2_desired,
        "_sha256",
        return_value=(
            boschendal_location_v2_desired
            .BOSCHENDAL_STAGE02_SHA256
        ),
    )
    @mock.patch.object(
        boschendal_location_v2_desired,
        "parse_release_file",
    )
    def test_wrong_source_marker_is_refused(
        self,
        parse_release_file,
        _sha256,
    ):
        rows = [
            self._row(
                name=f"kmz{i:03d}"
            )
            for i in range(
                262
            )
        ]

        rows[0] = self._row(
            name="kmz000",
            source="Wrong.kmz",
        )

        parse_release_file.return_value = rows

        with self.assertRaisesRegex(
            ValueError,
            "Unexpected Boschendal source marker",
        ):
            (
                boschendal_location_v2_desired
                .build_boschendal_location_v2_desired(
                    "unused.csv"
                )
            )

    @mock.patch.object(
        boschendal_location_v2_desired,
        "_sha256",
        return_value=(
            boschendal_location_v2_desired
            .BOSCHENDAL_STAGE02_SHA256
        ),
    )
    @mock.patch.object(
        boschendal_location_v2_desired,
        "parse_release_file",
    )
    def test_duplicate_canonical_id_is_refused(
        self,
        parse_release_file,
        _sha256,
    ):
        rows = [
            self._row(
                name=f"kmz{i:03d}"
            )
            for i in range(
                261
            )
        ]

        rows.append(
            self._row(
                name="kmz000"
            )
        )

        parse_release_file.return_value = rows

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate Boschendal canonical Location ID",
        ):
            (
                boschendal_location_v2_desired
                .build_boschendal_location_v2_desired(
                    "unused.csv"
                )
            )

    @mock.patch.object(
        boschendal_location_v2_desired,
        "_sha256",
        return_value=(
            boschendal_location_v2_desired
            .BOSCHENDAL_STAGE02_SHA256
        ),
    )
    @mock.patch.object(
        boschendal_location_v2_desired,
        "parse_release_file",
    )
    def test_required_cabinet_id_is_enforced(
        self,
        parse_release_file,
        _sha256,
    ):
        rows = [
            self._row(
                name=f"kmz{i:03d}"
            )
            for i in range(
                262
            )
        ]

        parse_release_file.return_value = rows

        with self.assertRaisesRegex(
            ValueError,
            "15U Cabinet Location is missing",
        ):
            (
                boschendal_location_v2_desired
                .build_boschendal_location_v2_desired(
                    "unused.csv"
                )
            )

    @mock.patch.object(
        boschendal_location_v2_desired,
        "_sha256",
        return_value=(
            boschendal_location_v2_desired
            .BOSCHENDAL_STAGE02_SHA256
        ),
    )
    @mock.patch.object(
        boschendal_location_v2_desired,
        "parse_release_file",
    )
    def test_required_proposed_fibre_ids_are_enforced(
        self,
        parse_release_file,
        _sha256,
    ):
        cabinet_id = (
            boschendal_location_v2_desired
            .BOSCHENDAL_NETWORK_CABINET_ID
        )

        rows = [
            self._row(
                name=cabinet_id
            )
        ]

        rows.extend(
            self._row(
                name=f"kmz{i:03d}"
            )
            for i in range(
                261
            )
        )

        parse_release_file.return_value = rows

        with self.assertRaisesRegex(
            ValueError,
            "Proposed Fibre Locations are missing",
        ):
            (
                boschendal_location_v2_desired
                .build_boschendal_location_v2_desired(
                    "unused.csv"
                )
            )

    @mock.patch.object(
        boschendal_location_v2_desired,
        "_sha256",
        return_value=(
            boschendal_location_v2_desired
            .BOSCHENDAL_STAGE02_SHA256
        ),
    )
    @mock.patch.object(
        boschendal_location_v2_desired,
        "parse_release_file",
    )
    def test_explicit_semantic_overrides_are_applied(
        self,
        parse_release_file,
        _sha256,
    ):
        cabinet_id = (
            boschendal_location_v2_desired
            .BOSCHENDAL_NETWORK_CABINET_ID
        )

        proposed_ids = sorted(
            boschendal_location_v2_desired
            .BOSCHENDAL_PROPOSED_FIBRE_IDS
        )

        required_ids = [
            cabinet_id,
            *proposed_ids,
        ]

        filler_count = (
            boschendal_location_v2_desired
            .BOSCHENDAL_STAGE02_ROW_COUNT
            - len(required_ids)
        )

        rows = [
            self._row(
                name=location_id
            )
            for location_id in required_ids
        ]

        rows.extend(
            self._row(
                name=f"kmzfiller{i:03d}"
            )
            for i in range(
                filler_count
            )
        )

        parse_release_file.return_value = rows

        desired = (
            boschendal_location_v2_desired
            .build_boschendal_location_v2_desired(
                "unused.csv"
            )
        )

        self.assertEqual(
            desired[
                cabinet_id
            ][
                "custom_infrastructure_class"
            ],
            "Network Cabinet",
        )

        for location_id in proposed_ids:
            self.assertEqual(
                desired[
                    location_id
                ][
                    "custom_lifecycle_state"
                ],
                "Planned",
            )

        planned_ids = {
            location_id
            for location_id, values
            in desired.items()
            if (
                values[
                    "custom_lifecycle_state"
                ]
                == "Planned"
            )
        }

        self.assertEqual(
            planned_ids,
            set(proposed_ids),
        )
