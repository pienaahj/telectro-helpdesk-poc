import csv
import tempfile
import unittest
from pathlib import Path

from telephony.scripts import (
    simple_site_campus_v2_desired,
)


class TestSimpleSiteCampusV2Desired(
    unittest.TestCase
):
    def _write_source(
        self,
        path,
        rows,
    ):
        fieldnames = [
            "site_id",
            "site_name",
            "latitude",
            "longitude",
            "active",
            "source_alias",
            "notes",
        ]

        with Path(path).open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
            )

            writer.writeheader()
            writer.writerows(
                rows
            )

    def _rows(self):
        return [
            {
                "site_id":
                    "TEST-SITE-001",
                "site_name":
                    "Head Office",
                "latitude":
                    "-33.8817",
                "longitude":
                    "18.6355",
                "active":
                    "1",
                "source_alias":
                    "HQ",
                "notes":
                    "",
            },
            {
                "site_id":
                    "TEST-SITE-002",
                "site_name":
                    "Branch One",
                "latitude":
                    "-26.1234",
                "longitude":
                    "28.1234",
                "active":
                    "yes",
                "source_alias":
                    "",
                "notes":
                    "",
            },
        ]

    def _build(
        self,
        path,
        *,
        rows=None,
        expected_hash=None,
        expected_count=None,
    ):
        if rows is None:
            rows = self._rows()

        self._write_source(
            path,
            rows,
        )

        if expected_hash is None:
            expected_hash = (
                simple_site_campus_v2_desired
                ._sha256(
                    path
                )
            )

        if expected_count is None:
            expected_count = len(
                rows
            )

        return (
            simple_site_campus_v2_desired
            .build_simple_site_campus_v2_desired(
                path,
                expected_sha256=(
                    expected_hash
                ),
                expected_row_count=(
                    expected_count
                ),
                customer="Example Customer",
                location_name_prefix=(
                    "Example Customer - "
                ),
            )
        )

    def test_builds_campus_desired_state(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            path = (
                Path(tempdir)
                / "sites.csv"
            )

            desired = self._build(
                path
            )

        self.assertEqual(
            set(desired),
            {
                "TEST-SITE-001",
                "TEST-SITE-002",
            },
        )

        head_office = desired[
            "TEST-SITE-001"
        ]

        self.assertEqual(
            head_office[
                "location_name"
            ],
            "Example Customer - Head Office",
        )

        self.assertEqual(
            head_office[
                "parent_location"
            ],
            "Pilot Sites",
        )

        self.assertEqual(
            head_office[
                "custom_customer"
            ],
            "Example Customer",
        )

        self.assertEqual(
            head_office[
                "custom_lifecycle_state"
            ],
            "Operational",
        )

        self.assertEqual(
            head_office[
                "custom_customer_visibility"
            ],
            "Customer-safe",
        )

        self.assertEqual(
            head_office[
                "custom_ticket_selectability"
            ],
            "Selectable",
        )

        self.assertEqual(
            head_office[
                "custom_kmz_geometry_type"
            ],
            "Point",
        )

        self.assertIsNone(
            head_office[
                "location"
            ]
        )

        self.assertIsNone(
            head_office[
                "custom_kmz_source"
            ]
        )

    def test_extra_source_columns_are_allowed(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            path = (
                Path(tempdir)
                / "sites.csv"
            )

            desired = self._build(
                path
            )

        self.assertEqual(
            len(desired),
            2,
        )

    def test_hash_mismatch_is_refused(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            path = (
                Path(tempdir)
                / "sites.csv"
            )

            with self.assertRaisesRegex(
                ValueError,
                "hash mismatch",
            ):
                self._build(
                    path,
                    expected_hash=(
                        "0" * 64
                    ),
                )

    def test_wrong_row_count_is_refused(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            path = (
                Path(tempdir)
                / "sites.csv"
            )

            with self.assertRaisesRegex(
                ValueError,
                "row count",
            ):
                self._build(
                    path,
                    expected_count=3,
                )

    def test_duplicate_site_id_is_refused(
        self,
    ):
        rows = self._rows()

        rows[1][
            "site_id"
        ] = "TEST-SITE-001"

        with tempfile.TemporaryDirectory() as tempdir:
            path = (
                Path(tempdir)
                / "sites.csv"
            )

            with self.assertRaisesRegex(
                ValueError,
                "Duplicate simple-site ID",
            ):
                self._build(
                    path,
                    rows=rows,
                )

    def test_duplicate_location_name_is_refused(
        self,
    ):
        rows = self._rows()

        rows[1][
            "site_name"
        ] = "Head Office"

        with tempfile.TemporaryDirectory() as tempdir:
            path = (
                Path(tempdir)
                / "sites.csv"
            )

            with self.assertRaisesRegex(
                ValueError,
                "Duplicate simple-site Location Name",
            ):
                self._build(
                    path,
                    rows=rows,
                )

    def test_inactive_site_is_refused(
        self,
    ):
        rows = self._rows()

        rows[1][
            "active"
        ] = "0"

        with tempfile.TemporaryDirectory() as tempdir:
            path = (
                Path(tempdir)
                / "sites.csv"
            )

            with self.assertRaisesRegex(
                ValueError,
                "inactive site",
            ):
                self._build(
                    path,
                    rows=rows,
                )

    def test_invalid_coordinates_are_refused(
        self,
    ):
        rows = self._rows()

        rows[0][
            "latitude"
        ] = "-123.0"

        with tempfile.TemporaryDirectory() as tempdir:
            path = (
                Path(tempdir)
                / "sites.csv"
            )

            with self.assertRaisesRegex(
                ValueError,
                "outside valid range",
            ):
                self._build(
                    path,
                    rows=rows,
                )
