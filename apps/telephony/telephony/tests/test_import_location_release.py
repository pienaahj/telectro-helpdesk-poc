import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from telephony.scripts import import_location_release


EXPECTED_V1_HEADER = [
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
]


class TestLocationReleaseV1Parser(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.root = Path(self.tempdir.name)

    def _write_csv(
        self,
        filename,
        rows,
        header=None,
    ):
        path = self.root / filename

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(
                header or EXPECTED_V1_HEADER
            )
            writer.writerows(rows)

        return path

    def _row(
        self,
        *,
        name="kmz123",
        location_name="Buildings: Office",
        parent_location="Boschendal - Buildings",
        is_container="0",
        is_group="0",
        latitude="-33.900001",
        longitude="18.900001",
    ):
        return [
            name,
            location_name,
            parent_location,
            is_container,
            is_group,
            latitude,
            longitude,
            "",
            '{"type":"FeatureCollection","features":[]}',
            "boschendal.kmz",
            "Boschendal / Buildings",
            "Point",
            "Office",
            '{"pts_count":1}',
        ]

    def test_v1_header_contract_is_exact(self):
        self.assertEqual(
            list(import_location_release.V1_HEADER),
            EXPECTED_V1_HEADER,
        )

    def test_parse_preserves_canonical_id_and_types(self):
        path = self._write_csv(
            "stage.csv",
            [
                self._row(),
            ],
        )

        rows = (
            import_location_release
            .parse_release_file(path)
        )

        self.assertEqual(len(rows), 1)

        row = rows[0]

        self.assertEqual(
            row.name,
            "kmz123",
        )

        self.assertEqual(
            row.location_name,
            "Buildings: Office",
        )

        self.assertEqual(
            row.parent_location,
            "Boschendal - Buildings",
        )

        self.assertEqual(
            row.is_container,
            0,
        )

        self.assertEqual(
            row.is_group,
            0,
        )

        self.assertEqual(
            row.latitude,
            -33.900001,
        )

        self.assertEqual(
            row.longitude,
            18.900001,
        )

        self.assertIsNone(
            row.area_uom,
        )

        self.assertEqual(
            row.location,
            (
                '{"type":"FeatureCollection",'
                '"features":[]}'
            ),
        )

        self.assertEqual(
            row.custom_kmz_source,
            "boschendal.kmz",
        )

        self.assertEqual(
            row.custom_kmz_folder_path,
            "Boschendal / Buildings",
        )

        self.assertEqual(
            row.custom_kmz_geometry_type,
            "Point",
        )

        self.assertEqual(
            row.custom_kmz_description,
            "Office",
        )

        self.assertEqual(
            row.custom_kmz_metadata_json,
            '{"pts_count":1}',
        )

    def test_parse_rejects_non_v1_header(self):
        header = list(EXPECTED_V1_HEADER)
        header[0] = "Record ID"

        path = self._write_csv(
            "bad-header.csv",
            [
                self._row(),
            ],
            header=header,
        )

        with self.assertRaisesRegex(
            ValueError,
            "header",
        ):
            (
                import_location_release
                .parse_release_file(path)
            )

    def test_parse_rejects_duplicate_ids(self):
        path = self._write_csv(
            "duplicate-id.csv",
            [
                self._row(
                    name="kmz123",
                    location_name="Buildings: One",
                ),
                self._row(
                    name="kmz123",
                    location_name="Buildings: Two",
                ),
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "duplicate.*ID",
        ):
            (
                import_location_release
                .parse_release_file(path)
            )

    def test_parse_rejects_duplicate_location_names(
        self,
    ):
        path = self._write_csv(
            "duplicate-label.csv",
            [
                self._row(
                    name="kmz123",
                    location_name="Buildings: Same",
                ),
                self._row(
                    name="kmz456",
                    location_name="Buildings: Same",
                ),
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "duplicate.*Location Name",
        ):
            (
                import_location_release
                .parse_release_file(path)
            )

    def test_parse_rejects_wrong_row_column_count(self):
        extra = self._row() + ["unexpected"]

        path = self._write_csv(
            "extra-column.csv",
            [extra],
        )

        with self.assertRaisesRegex(
            ValueError,
            "column",
        ):
            (
                import_location_release
                .parse_release_file(path)
            )

        missing = self._row()[:-1]

        path = self._write_csv(
            "missing-column.csv",
            [missing],
        )

        with self.assertRaisesRegex(
            ValueError,
            "column",
        ):
            (
                import_location_release
                .parse_release_file(path)
            )

    def test_parse_preserves_authoritative_text_verbatim(
        self,
    ):
        row = self._row()

        row[8] = '  {"type":"FeatureCollection"}  '
        row[9] = "  boschendal.kmz  "
        row[10] = "  Boschendal / Buildings  "
        row[12] = "  Office description  "
        row[13] = '  {"pts_count":1}  '

        path = self._write_csv(
            "verbatim-text.csv",
            [row],
        )

        parsed = (
            import_location_release
            .parse_release_file(path)
        )[0]

        self.assertEqual(
            parsed.location,
            '  {"type":"FeatureCollection"}  ',
        )

        self.assertEqual(
            parsed.custom_kmz_source,
            "  boschendal.kmz  ",
        )

        self.assertEqual(
            parsed.custom_kmz_folder_path,
            "  Boschendal / Buildings  ",
        )

        self.assertEqual(
            parsed.custom_kmz_description,
            "  Office description  ",
        )

        self.assertEqual(
            parsed.custom_kmz_metadata_json,
            '  {"pts_count":1}  ',
        )

class TestLocationReleaseStageContract(
    unittest.TestCase
):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.root = Path(self.tempdir.name)

    def _write_stage(
        self,
        filename,
        rows,
    ):
        path = self.root / filename

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(
                EXPECTED_V1_HEADER
            )
            writer.writerows(rows)

        return (
            import_location_release
            .parse_release_file(path)
        )

    def _row(
        self,
        *,
        name,
        location_name,
        parent_location,
        is_group,
    ):
        return [
            name,
            location_name,
            parent_location,
            "0",
            str(int(is_group)),
            "0",
            "0",
            "",
            "",
            "",
            "",
            "Point",
            "",
            "",
        ]

    def test_stage_contract_accepts_prior_stage_parents(
        self,
    ):
        stage_0 = self._write_stage(
            "stage-00.csv",
            [
                self._row(
                    name="Boschendal",
                    location_name="Boschendal",
                    parent_location="Pilot Sites",
                    is_group=1,
                ),
            ],
        )

        stage_1 = self._write_stage(
            "stage-01.csv",
            [
                self._row(
                    name="Boschendal - Buildings",
                    location_name=(
                        "Boschendal - Buildings"
                    ),
                    parent_location="Boschendal",
                    is_group=1,
                ),
            ],
        )

        stage_2 = self._write_stage(
            "stage-02.csv",
            [
                self._row(
                    name="kmz123",
                    location_name="Buildings: Office",
                    parent_location=(
                        "Boschendal - Buildings"
                    ),
                    is_group=0,
                ),
            ],
        )

        result = (
            import_location_release
            .validate_release_stages(
                [
                    stage_0,
                    stage_1,
                    stage_2,
                ],
                external_prerequisites={
                    "Pilot Sites",
                },
            )
        )

        self.assertIsNone(result)

    def test_stage_contract_rejects_same_stage_parent(
        self,
    ):
        stage_0 = self._write_stage(
            "stage-00.csv",
            [
                self._row(
                    name="Boschendal",
                    location_name="Boschendal",
                    parent_location="Pilot Sites",
                    is_group=1,
                ),
                self._row(
                    name="Boschendal - Buildings",
                    location_name=(
                        "Boschendal - Buildings"
                    ),
                    parent_location="Boschendal",
                    is_group=1,
                ),
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "earlier stage",
        ):
            (
                import_location_release
                .validate_release_stages(
                    [
                        stage_0,
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

    def test_stage_contract_rejects_unknown_parent(
        self,
    ):
        stage_0 = self._write_stage(
            "stage-00.csv",
            [
                self._row(
                    name="Boschendal",
                    location_name="Boschendal",
                    parent_location=(
                        "Missing Prerequisite"
                    ),
                    is_group=1,
                ),
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "parent",
        ):
            (
                import_location_release
                .validate_release_stages(
                    [
                        stage_0,
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )
    def test_stage_contract_rejects_duplicate_location_names_across_stages(
        self,
    ):
        stage_0 = self._write_stage(
            "stage-00.csv",
            [
                self._row(
                    name="root-id",
                    location_name="Duplicate Label",
                    parent_location="Pilot Sites",
                    is_group=1,
                ),
            ],
        )

        stage_1 = self._write_stage(
            "stage-01.csv",
            [
                self._row(
                    name="child-id",
                    location_name="Duplicate Label",
                    parent_location="root-id",
                    is_group=1,
                ),
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "duplicate.*Location Name",
        ):
            (
                import_location_release
                .validate_release_stages(
                    [
                        stage_0,
                        stage_1,
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )
    def test_stage_contract_rejects_cross_id_label_collision(
        self,
    ):
        stage_0 = self._write_stage(
            "stage-00.csv",
            [
                self._row(
                    name="Boschendal",
                    location_name="Boschendal",
                    parent_location="Pilot Sites",
                    is_group=1,
                ),
            ],
        )

        stage_1 = self._write_stage(
            "stage-01.csv",
            [
                self._row(
                    name="kmz123",
                    location_name="Buildings: Office",
                    parent_location="Boschendal",
                    is_group=0,
                ),
            ],
        )

        stage_2 = self._write_stage(
            "stage-02.csv",
            [
                self._row(
                    name="Buildings: Office",
                    location_name="Buildings: Store",
                    parent_location="Boschendal",
                    is_group=0,
                ),
            ],
        )

        with self.assertRaisesRegex(
            ValueError,
            "ID.*Location Name.*collision",
        ):
            (
                import_location_release
                .validate_release_stages(
                    [
                        stage_0,
                        stage_1,
                        stage_2,
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

class TestLocationReleaseTargetPreflight(
    unittest.TestCase
):
    def _row(
        self,
        *,
        name="kmz123",
        location_name="Buildings: Office",
        parent_location="Boschendal - Buildings",
    ):
        return import_location_release.LocationReleaseRow(
            name=name,
            location_name=location_name,
            parent_location=parent_location,
            is_container=0,
            is_group=0,
            latitude=-33.900001,
            longitude=18.900001,
            area_uom=None,
            location=None,
            custom_kmz_source=None,
            custom_kmz_folder_path=None,
            custom_kmz_geometry_type="Point",
            custom_kmz_description=None,
            custom_kmz_metadata_json=None,
        )

    def _frappe(self):
        patcher = mock.patch.object(
            import_location_release,
            "frappe",
            create=True,
        )

        frappe_mock = patcher.start()
        self.addCleanup(patcher.stop)

        frappe_mock.db.exists.return_value = False
        frappe_mock.db.get_value.return_value = None

        return frappe_mock

    def test_target_preflight_accepts_safe_target(self):
        frappe_mock = self._frappe()

        def exists(doctype, name):
            if (
                doctype == "Location"
                and name == "Pilot Sites"
            ):
                return True

            return False

        frappe_mock.db.exists.side_effect = exists

        frappe_mock.db.get_value.side_effect = (
            lambda doctype, name_or_filters, fieldname:
            1
            if (
                doctype == "Location"
                and name_or_filters == "Pilot Sites"
                and fieldname == "is_group"
            )
            else None
        )

        result = (
            import_location_release
            .validate_target_preflight(
                [
                    [self._row()],
                ],
                external_prerequisites={
                    "Pilot Sites",
                },
            )
        )

        self.assertIsNone(result)

        frappe_mock.db.set_value.assert_not_called()
        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

    def test_target_preflight_rejects_missing_prerequisite(
        self,
    ):
        self._frappe()

        with self.assertRaisesRegex(
            ValueError,
            "prerequisite",
        ):
            (
                import_location_release
                .validate_target_preflight(
                    [
                        [self._row()],
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

    def test_target_preflight_rejects_non_group_prerequisite(
        self,
    ):
        frappe_mock = self._frappe()

        frappe_mock.db.exists.side_effect = (
            lambda doctype, name:
            (
                doctype == "Location"
                and name == "Pilot Sites"
            )
        )

        frappe_mock.db.get_value.return_value = 0

        with self.assertRaisesRegex(
            ValueError,
            "group",
        ):
            (
                import_location_release
                .validate_target_preflight(
                    [
                        [self._row()],
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

    def test_target_preflight_rejects_id_collision(
        self,
    ):
        frappe_mock = self._frappe()

        def exists(doctype, name):
            return (
                doctype == "Location"
                and name in {
                    "Pilot Sites",
                    "kmz123",
                }
            )

        frappe_mock.db.exists.side_effect = exists

        frappe_mock.db.get_value.side_effect = (
            lambda doctype, name_or_filters, fieldname:
            1
            if (
                doctype == "Location"
                and name_or_filters == "Pilot Sites"
                and fieldname == "is_group"
            )
            else None
        )

        with self.assertRaisesRegex(
            ValueError,
            "ID.*collision",
        ):
            (
                import_location_release
                .validate_target_preflight(
                    [
                        [self._row()],
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

    def test_target_preflight_rejects_final_label_collision(
        self,
    ):
        frappe_mock = self._frappe()

        frappe_mock.db.exists.side_effect = (
            lambda doctype, name:
            (
                doctype == "Location"
                and name == "Pilot Sites"
            )
        )

        def get_value(
            doctype,
            name_or_filters,
            fieldname,
        ):
            if (
                name_or_filters == "Pilot Sites"
                and fieldname == "is_group"
            ):
                return 1

            if name_or_filters == {
                "location_name": "Buildings: Office",
            }:
                return "existing-location"

            return None

        frappe_mock.db.get_value.side_effect = get_value

        with self.assertRaisesRegex(
            ValueError,
            "Location Name.*collision",
        ):
            (
                import_location_release
                .validate_target_preflight(
                    [
                        [self._row()],
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

    def test_target_preflight_rejects_transient_autoname_collision(
        self,
    ):
        frappe_mock = self._frappe()

        frappe_mock.db.exists.side_effect = (
            lambda doctype, name:
            (
                doctype == "Location"
                and name == "Pilot Sites"
            )
        )

        def get_value(
            doctype,
            name_or_filters,
            fieldname,
        ):
            if (
                name_or_filters == "Pilot Sites"
                and fieldname == "is_group"
            ):
                return 1

            if name_or_filters == {
                "location_name": "kmz123",
            }:
                return "existing-location"

            return None

        frappe_mock.db.get_value.side_effect = get_value

        with self.assertRaisesRegex(
            ValueError,
            "autoname.*collision",
        ):
            (
                import_location_release
                .validate_target_preflight(
                    [
                        [self._row()],
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

if __name__ == "__main__":
    unittest.main()
