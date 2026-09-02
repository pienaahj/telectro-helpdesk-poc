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

class TestLocationReleaseInsertPrimitive(
    unittest.TestCase
):
    def _row(self):
        return import_location_release.LocationReleaseRow(
            name="kmz123",
            location_name="Buildings: Office",
            parent_location="Boschendal - Buildings",
            is_container=0,
            is_group=0,
            latitude=-33.900001,
            longitude=18.900001,
            area_uom=None,
            location=(
                '{"type":"FeatureCollection",'
                '"features":[]}'
            ),
            custom_kmz_source="boschendal.kmz",
            custom_kmz_folder_path=(
                "Boschendal / Buildings"
            ),
            custom_kmz_geometry_type="Point",
            custom_kmz_description="Office",
            custom_kmz_metadata_json=(
                '{"pts_count":1}'
            ),
        )

    def _frappe(self):
        patcher = mock.patch.object(
            import_location_release,
            "frappe",
        )

        frappe_mock = patcher.start()
        self.addCleanup(patcher.stop)

        doc_mock = mock.Mock()
        frappe_mock.get_doc.return_value = doc_mock

        return frappe_mock, doc_mock

    def test_insert_uses_canonical_id_and_release_fields(
        self,
    ):
        frappe_mock, doc_mock = self._frappe()

        row = self._row()

        result = (
            import_location_release
            .insert_release_row(row)
        )

        frappe_mock.get_doc.assert_called_once_with(
            {
                "doctype": "Location",
                "location_name": "Buildings: Office",
                "parent_location":
                    "Boschendal - Buildings",
                "is_container": 0,
                "is_group": 0,
                "latitude": -33.900001,
                "longitude": 18.900001,
                "area_uom": None,
                "location": (
                    '{"type":"FeatureCollection",'
                    '"features":[]}'
                ),
                "custom_kmz_source":
                    "boschendal.kmz",
                "custom_kmz_folder_path":
                    "Boschendal / Buildings",
                "custom_kmz_geometry_type":
                    "Point",
                "custom_kmz_description":
                    "Office",
                "custom_kmz_metadata_json":
                    '{"pts_count":1}',
            }
        )

        doc_mock.insert.assert_called_once_with(
            ignore_permissions=True,
            set_name="kmz123",
        )

        self.assertEqual(
            result,
            "kmz123",
        )

    def test_insert_restores_authoritative_fields_after_insert(
        self,
    ):
        frappe_mock, doc_mock = self._frappe()

        row = self._row()

        (
            import_location_release
            .insert_release_row(row)
        )

        doc_mock.insert.assert_called_once()

        frappe_mock.db.set_value.assert_called_once_with(
            "Location",
            "kmz123",
            {
                "location_name": "Buildings: Office",
                "latitude": -33.900001,
                "longitude": 18.900001,
            },
            update_modified=False,
        )

    def test_insert_does_not_manage_transaction(
        self,
    ):
        frappe_mock, _ = self._frappe()

        (
            import_location_release
            .insert_release_row(
                self._row()
            )
        )

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

class TestLocationReleaseStoredRowVerification(
    unittest.TestCase
):
    def _row(self):
        return import_location_release.LocationReleaseRow(
            name="kmz123",
            location_name="Buildings: Office",
            parent_location="Boschendal - Buildings",
            is_container=0,
            is_group=0,
            latitude=-33.900001,
            longitude=18.900001,
            area_uom=None,
            location=(
                '{"type":"FeatureCollection",'
                '"features":[]}'
            ),
            custom_kmz_source="boschendal.kmz",
            custom_kmz_folder_path=(
                "Boschendal / Buildings"
            ),
            custom_kmz_geometry_type="Point",
            custom_kmz_description="Office",
            custom_kmz_metadata_json=(
                '{"pts_count":1}'
            ),
        )

    def _stored(self):
        return {
            "location_name": "Buildings: Office",
            "parent_location": "Boschendal - Buildings",
            "is_container": 0,
            "is_group": 0,
            "latitude": -33.900001,
            "longitude": 18.900001,
            "area_uom": None,
            "location": (
                '{"type":"FeatureCollection",'
                '"features":[]}'
            ),
            "custom_kmz_source": "boschendal.kmz",
            "custom_kmz_folder_path": (
                "Boschendal / Buildings"
            ),
            "custom_kmz_geometry_type": "Point",
            "custom_kmz_description": "Office",
            "custom_kmz_metadata_json": (
                '{"pts_count":1}'
            ),
        }

    def _frappe(self):
        patcher = mock.patch.object(
            import_location_release,
            "frappe",
        )

        frappe_mock = patcher.start()
        self.addCleanup(patcher.stop)

        return frappe_mock

    def test_verify_accepts_exact_stored_row(self):
        frappe_mock = self._frappe()

        frappe_mock.db.get_value.return_value = (
            self._stored()
        )

        result = (
            import_location_release
            .verify_release_row(
                self._row()
            )
        )

        self.assertIsNone(result)

        frappe_mock.db.get_value.assert_called_once_with(
            "Location",
            "kmz123",
            [
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
            ],
            as_dict=True,
        )

    def test_verify_rejects_missing_stored_row(self):
        frappe_mock = self._frappe()

        frappe_mock.db.get_value.return_value = None

        with self.assertRaisesRegex(
            ValueError,
            "Missing stored Location",
        ):
            (
                import_location_release
                .verify_release_row(
                    self._row()
                )
            )

    def test_verify_rejects_authoritative_field_mismatch(
        self,
    ):
        mismatches = {
            "location_name": "Wrong Label",
            "parent_location": "Wrong Parent",
            "is_container": 1,
            "is_group": 1,
            "latitude": -33.8,
            "longitude": 18.8,
            "area_uom": "Square Meter",
            "location": "{}",
            "custom_kmz_source": "wrong.kmz",
            "custom_kmz_folder_path": "Wrong / Path",
            "custom_kmz_geometry_type": "Polygon",
            "custom_kmz_description": "Wrong",
            "custom_kmz_metadata_json": "{}",
        }

        for fieldname, wrong_value in (
            mismatches.items()
        ):
            with self.subTest(fieldname=fieldname):
                frappe_mock = self._frappe()

                stored = self._stored()
                stored[fieldname] = wrong_value

                frappe_mock.db.get_value.return_value = (
                    stored
                )

                with self.assertRaisesRegex(
                    ValueError,
                    "mismatch",
                ):
                    (
                        import_location_release
                        .verify_release_row(
                            self._row()
                        )
                    )

    def test_verify_is_read_only(self):
        frappe_mock = self._frappe()

        frappe_mock.db.get_value.return_value = (
            self._stored()
        )

        (
            import_location_release
            .verify_release_row(
                self._row()
            )
        )

        frappe_mock.get_doc.assert_not_called()
        frappe_mock.db.set_value.assert_not_called()
        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

class TestLocationReleaseStageApplication(
    unittest.TestCase
):
    def _row(
        self,
        name,
        location_name=None,
        parent_location="Pilot Sites",
    ):
        return import_location_release.LocationReleaseRow(
            name=name,
            location_name=(
                location_name
                or name
            ),
            parent_location=parent_location,
            is_container=0,
            is_group=1,
            latitude=0.0,
            longitude=0.0,
            area_uom=None,
            location=None,
            custom_kmz_source=None,
            custom_kmz_folder_path=None,
            custom_kmz_geometry_type="Point",
            custom_kmz_description=None,
            custom_kmz_metadata_json=None,
        )

    def _frappe(self, site="location-roundtrip"):
        patcher = mock.patch.object(
            import_location_release,
            "frappe",
        )

        frappe_mock = patcher.start()
        self.addCleanup(patcher.stop)

        frappe_mock.local.site = site

        return frappe_mock

    def test_apply_runs_preflights_before_rows(self):
        self._frappe()

        row = self._row(
            "Boschendal",
        )

        calls = []

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
                side_effect=lambda *args, **kwargs:
                    calls.append("release-preflight"),
            ),
            mock.patch.object(
                import_location_release,
                "validate_target_preflight",
                side_effect=lambda *args, **kwargs:
                    calls.append("target-preflight"),
            ),
            mock.patch.object(
                import_location_release,
                "insert_release_row",
                side_effect=lambda value:
                    calls.append(
                        f"insert:{value.name}"
                    ),
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_row",
                side_effect=lambda value:
                    calls.append(
                        f"verify:{value.name}"
                    ),
            ),
        ):
            import_location_release.apply_release_stages(
                [[row]],
                external_prerequisites={
                    "Pilot Sites",
                },
                expected_site="location-roundtrip",
            )

        self.assertEqual(
            calls,
            [
                "release-preflight",
                "target-preflight",
                "insert:Boschendal",
                "verify:Boschendal",
            ],
        )

    def test_apply_preserves_stage_and_row_order(self):
        self._frappe()

        root = self._row(
            "Boschendal",
        )

        group = self._row(
            "Boschendal - Buildings",
            parent_location="Boschendal",
        )

        leaf = self._row(
            "kmz123",
            location_name="Buildings: Office",
            parent_location="Boschendal - Buildings",
        )

        inserted = []
        verified = []

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ),
            mock.patch.object(
                import_location_release,
                "validate_target_preflight",
            ),
            mock.patch.object(
                import_location_release,
                "insert_release_row",
                side_effect=lambda row:
                    inserted.append(row.name),
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_row",
                side_effect=lambda row:
                    verified.append(row.name),
            ),
        ):
            result = (
                import_location_release
                .apply_release_stages(
                    [
                        [root],
                        [group],
                        [leaf],
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                    expected_site="location-roundtrip",
                )
            )

        self.assertEqual(
            inserted,
            [
                "Boschendal",
                "Boschendal - Buildings",
                "kmz123",
            ],
        )

        self.assertEqual(
            verified,
            inserted,
        )

        self.assertEqual(
            result,
            {
                "inserted_count": 3,
                "stage_counts": [1, 1, 1],
            },
        )

    def test_apply_refuses_wrong_site_before_preflight_or_write(
        self,
    ):
        frappe_mock = self._frappe(
            site="frontend",
        )

        row = self._row(
            "Boschendal",
        )

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ) as release_preflight,
            mock.patch.object(
                import_location_release,
                "validate_target_preflight",
            ) as target_preflight,
            mock.patch.object(
                import_location_release,
                "insert_release_row",
            ) as insert_row,
            self.assertRaisesRegex(
                ValueError,
                "site",
            ),
        ):
            (
                import_location_release
                .apply_release_stages(
                    [[row]],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                    expected_site="location-roundtrip",
                )
            )

        release_preflight.assert_not_called()
        target_preflight.assert_not_called()
        insert_row.assert_not_called()

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

    def test_apply_stops_immediately_on_verification_failure(
        self,
    ):
        frappe_mock = self._frappe()

        first = self._row(
            "Boschendal",
        )

        second = self._row(
            "Boschendal - Buildings",
            parent_location="Boschendal",
        )

        inserted = []

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ),
            mock.patch.object(
                import_location_release,
                "validate_target_preflight",
            ),
            mock.patch.object(
                import_location_release,
                "insert_release_row",
                side_effect=lambda row:
                    inserted.append(row.name),
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_row",
                side_effect=ValueError(
                    "stored row mismatch"
                ),
            ),
            self.assertRaisesRegex(
                ValueError,
                "stored row mismatch",
            ),
        ):
            (
                import_location_release
                .apply_release_stages(
                    [
                        [first],
                        [second],
                    ],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                    expected_site="location-roundtrip",
                )
            )

        self.assertEqual(
            inserted,
            ["Boschendal"],
        )

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

    def test_apply_does_not_manage_transaction(self):
        frappe_mock = self._frappe()

        row = self._row(
            "Boschendal",
        )

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ),
            mock.patch.object(
                import_location_release,
                "validate_target_preflight",
            ),
            mock.patch.object(
                import_location_release,
                "insert_release_row",
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_row",
            ),
        ):
            (
                import_location_release
                .apply_release_stages(
                    [[row]],
                    external_prerequisites={
                        "Pilot Sites",
                    },
                    expected_site="location-roundtrip",
                )
            )

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

class TestLocationReleasePostflight(
    unittest.TestCase
):
    def _row(
        self,
        name,
        *,
        location_name=None,
        parent_location="Pilot Sites",
    ):
        return import_location_release.LocationReleaseRow(
            name=name,
            location_name=location_name or name,
            parent_location=parent_location,
            is_container=0,
            is_group=1,
            latitude=0.0,
            longitude=0.0,
            area_uom=None,
            location=None,
            custom_kmz_source=None,
            custom_kmz_folder_path=None,
            custom_kmz_geometry_type="Point",
            custom_kmz_description=None,
            custom_kmz_metadata_json=None,
        )

    def _frappe(self, tree):
        patcher = mock.patch.object(
            import_location_release,
            "frappe",
        )

        frappe_mock = patcher.start()
        self.addCleanup(patcher.stop)

        def get_value(
            doctype,
            name,
            fields,
            as_dict=False,
        ):
            self.assertEqual(
                doctype,
                "Location",
            )
            self.assertEqual(
                fields,
                [
                    "parent_location",
                    "lft",
                    "rgt",
                ],
            )
            self.assertTrue(as_dict)

            value = tree.get(name)

            if value is None:
                return None

            return dict(value)

        frappe_mock.db.get_value.side_effect = (
            get_value
        )

        return frappe_mock

    def _tree(self):
        return {
            "Pilot Sites": {
                "parent_location": None,
                "lft": 1,
                "rgt": 8,
            },
            "Boschendal": {
                "parent_location": "Pilot Sites",
                "lft": 2,
                "rgt": 7,
            },
            "Boschendal - Buildings": {
                "parent_location": "Boschendal",
                "lft": 3,
                "rgt": 6,
            },
            "kmz123": {
                "parent_location":
                    "Boschendal - Buildings",
                "lft": 4,
                "rgt": 5,
            },
        }

    def _stages(self):
        root = self._row(
            "Boschendal",
        )

        group = self._row(
            "Boschendal - Buildings",
            parent_location="Boschendal",
        )

        leaf = self._row(
            "kmz123",
            location_name="Buildings: Office",
            parent_location="Boschendal - Buildings",
        )

        return [
            [root],
            [group],
            [leaf],
        ]

    def test_postflight_reverifies_all_rows(
        self,
    ):
        self._frappe(
            self._tree()
        )

        stages = self._stages()

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ) as validate,
            mock.patch.object(
                import_location_release,
                "verify_release_row",
            ) as verify,
        ):
            result = (
                import_location_release
                .verify_release_postflight(
                    stages,
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

        validate.assert_called_once_with(
            stages,
            external_prerequisites={
                "Pilot Sites",
            },
        )

        self.assertEqual(
            [
                call.args[0].name
                for call in verify.call_args_list
            ],
            [
                "Boschendal",
                "Boschendal - Buildings",
                "kmz123",
            ],
        )

        self.assertEqual(
            result,
            {
                "verified_count": 3,
                "stage_counts": [1, 1, 1],
            },
        )

    def test_postflight_rejects_broken_nested_set_edge(
        self,
    ):
        tree = self._tree()

        tree["kmz123"] = {
            "parent_location":
                "Boschendal - Buildings",
            "lft": 8,
            "rgt": 9,
        }

        self._frappe(tree)

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_row",
            ),
            self.assertRaisesRegex(
                ValueError,
                "nested-set",
            ),
        ):
            (
                import_location_release
                .verify_release_postflight(
                    self._stages(),
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

    def test_postflight_rejects_missing_tree_row(
        self,
    ):
        tree = self._tree()
        del tree["kmz123"]

        self._frappe(tree)

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_row",
            ),
            self.assertRaisesRegex(
                ValueError,
                "Missing stored Location",
            ),
        ):
            (
                import_location_release
                .verify_release_postflight(
                    self._stages(),
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

    def test_postflight_is_read_only(self):
        frappe_mock = self._frappe(
            self._tree()
        )

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_row",
            ),
        ):
            (
                import_location_release
                .verify_release_postflight(
                    self._stages(),
                    external_prerequisites={
                        "Pilot Sites",
                    },
                )
            )

        frappe_mock.get_doc.assert_not_called()
        frappe_mock.db.set_value.assert_not_called()
        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

class TestLocationReleaseRun(
    unittest.TestCase
):
    def _row(self):
        return import_location_release.LocationReleaseRow(
            name="Boschendal",
            location_name="Boschendal",
            parent_location="Pilot Sites",
            is_container=0,
            is_group=1,
            latitude=0.0,
            longitude=0.0,
            area_uom=None,
            location=None,
            custom_kmz_source=None,
            custom_kmz_folder_path=None,
            custom_kmz_geometry_type="Point",
            custom_kmz_description=None,
            custom_kmz_metadata_json=None,
        )

    def _frappe(self, site="location-roundtrip"):
        patcher = mock.patch.object(
            import_location_release,
            "frappe",
        )

        frappe_mock = patcher.start()
        self.addCleanup(patcher.stop)

        frappe_mock.local.site = site

        return frappe_mock

    def test_run_refuses_uncommitted_write_mode(self):
        frappe_mock = self._frappe()

        with self.assertRaisesRegex(
            ValueError,
            "Refusing uncommitted write mode",
        ):
            import_location_release.run(
                [[self._row()]],
                external_prerequisites={
                    "Pilot Sites",
                },
                expected_site="location-roundtrip",
                dry_run=0,
                commit=0,
            )

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

    def test_run_refuses_wrong_site_before_preflight(
        self,
    ):
        frappe_mock = self._frappe(
            site="frontend",
        )

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
            ) as release_preflight,
            mock.patch.object(
                import_location_release,
                "validate_target_preflight",
            ) as target_preflight,
            mock.patch.object(
                import_location_release,
                "apply_release_stages",
            ) as apply_stages,
            self.assertRaisesRegex(
                ValueError,
                "site",
            ),
        ):
            import_location_release.run(
                [[self._row()]],
                external_prerequisites={
                    "Pilot Sites",
                },
                expected_site="location-roundtrip",
                dry_run=1,
                commit=0,
            )

        release_preflight.assert_not_called()
        target_preflight.assert_not_called()
        apply_stages.assert_not_called()

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

    def test_run_dry_run_is_read_only(self):
        frappe_mock = self._frappe()

        row = self._row()
        stages = [[row]]

        calls = []

        with (
            mock.patch.object(
                import_location_release,
                "validate_release_stages",
                side_effect=lambda *args, **kwargs:
                    calls.append("release-preflight"),
            ),
            mock.patch.object(
                import_location_release,
                "validate_target_preflight",
                side_effect=lambda *args, **kwargs:
                    calls.append("target-preflight"),
            ),
            mock.patch.object(
                import_location_release,
                "apply_release_stages",
            ) as apply_stages,
            mock.patch.object(
                import_location_release,
                "verify_release_postflight",
            ) as postflight,
        ):
            result = import_location_release.run(
                stages,
                external_prerequisites={
                    "Pilot Sites",
                },
                expected_site="location-roundtrip",
                dry_run=1,
                commit=0,
            )

        self.assertEqual(
            calls,
            [
                "release-preflight",
                "target-preflight",
            ],
        )

        apply_stages.assert_not_called()
        postflight.assert_not_called()

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

        self.assertEqual(
            result,
            {
                "ok": True,
                "dry_run": True,
                "row_count": 1,
                "stage_counts": [1],
            },
        )

    def test_run_commit_applies_postflights_then_commits(
        self,
    ):
        frappe_mock = self._frappe()

        row = self._row()
        stages = [[row]]

        calls = []

        with (
            mock.patch.object(
                import_location_release,
                "apply_release_stages",
                side_effect=lambda *args, **kwargs: (
                    calls.append("apply")
                    or {
                        "inserted_count": 1,
                        "stage_counts": [1],
                    }
                ),
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_postflight",
                side_effect=lambda *args, **kwargs: (
                    calls.append("postflight")
                    or {
                        "verified_count": 1,
                        "stage_counts": [1],
                    }
                ),
            ),
        ):
            frappe_mock.db.commit.side_effect = (
                lambda:
                    calls.append("commit")
            )

            result = import_location_release.run(
                stages,
                external_prerequisites={
                    "Pilot Sites",
                },
                expected_site="location-roundtrip",
                dry_run=1,
                commit=1,
            )

        self.assertEqual(
            calls,
            [
                "apply",
                "postflight",
                "commit",
            ],
        )

        frappe_mock.db.rollback.assert_not_called()

        self.assertEqual(
            result,
            {
                "ok": True,
                "committed": True,
                "inserted_count": 1,
                "verified_count": 1,
                "stage_counts": [1],
            },
        )

    def test_run_rolls_back_on_apply_failure(self):
        frappe_mock = self._frappe()

        with (
            mock.patch.object(
                import_location_release,
                "apply_release_stages",
                side_effect=ValueError(
                    "apply failed"
                ),
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_postflight",
            ) as postflight,
            self.assertRaisesRegex(
                ValueError,
                "apply failed",
            ),
        ):
            import_location_release.run(
                [[self._row()]],
                external_prerequisites={
                    "Pilot Sites",
                },
                expected_site="location-roundtrip",
                commit=1,
            )

        postflight.assert_not_called()

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_called_once_with()

    def test_run_rolls_back_on_postflight_failure(
        self,
    ):
        frappe_mock = self._frappe()

        with (
            mock.patch.object(
                import_location_release,
                "apply_release_stages",
                return_value={
                    "inserted_count": 1,
                    "stage_counts": [1],
                },
            ),
            mock.patch.object(
                import_location_release,
                "verify_release_postflight",
                side_effect=ValueError(
                    "postflight failed"
                ),
            ),
            self.assertRaisesRegex(
                ValueError,
                "postflight failed",
            ),
        ):
            import_location_release.run(
                [[self._row()]],
                external_prerequisites={
                    "Pilot Sites",
                },
                expected_site="location-roundtrip",
                commit=1,
            )

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_called_once_with()

if __name__ == "__main__":
    unittest.main()
