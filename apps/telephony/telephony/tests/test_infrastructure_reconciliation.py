import unittest

from telephony.scripts import infrastructure_reconciliation


class TestLocationV2ReconciliationPlanner(unittest.TestCase):
    def _state(self, **overrides):
        values = {
            "location_name": "Buildings: Office",
            "parent_location": "Boschendal - Buildings",
            "is_container": 0,
            "is_group": 0,
            "latitude": -33.900001,
            "longitude": 18.900001,
            "area_uom": None,
            "location": (
                '{"type":"FeatureCollection","features":[]}'
            ),
            "custom_kmz_source": "Boschendal.kmz",
            "custom_kmz_folder_path": (
                "Boschendal / Buildings"
            ),
            "custom_kmz_geometry_type": "Point",
            "custom_kmz_description": "Office",
            "custom_kmz_metadata_json": (
                '{"pts_count":1}'
            ),
            "custom_location_semantics": (
                "Physical Location"
            ),
            "custom_infrastructure_class": None,
            "custom_lifecycle_state": None,
            "custom_customer_visibility": (
                "Customer-safe"
            ),
            "custom_ticket_selectability": (
                "Selectable"
            ),
        }

        values.update(overrides)
        return values

    def test_new_when_canonical_location_does_not_exist(self):
        result = (
            infrastructure_reconciliation
            .plan_location_reconciliation(
                "kmz123",
                self._state(),
                None,
            )
        )

        self.assertEqual(
            result.location_id,
            "kmz123",
        )

        self.assertEqual(
            result.state,
            "NEW",
        )

        self.assertEqual(
            result.changes,
            (),
        )

    def test_unchanged_when_authoritative_state_matches(self):
        desired = self._state()
        stored = self._state()

        result = (
            infrastructure_reconciliation
            .plan_location_reconciliation(
                "kmz123",
                desired,
                stored,
            )
        )

        self.assertEqual(
            result.state,
            "UNCHANGED",
        )

        self.assertEqual(
            result.changes,
            (),
        )

    def test_numeric_representations_compare_equal(self):
        desired = self._state(
            is_container=0,
            is_group=0,
            latitude=-33.900001,
            longitude=18.900001,
        )

        stored = self._state(
            is_container="0",
            is_group=False,
            latitude="-33.900001",
            longitude="18.900001",
        )

        result = (
            infrastructure_reconciliation
            .plan_location_reconciliation(
                "kmz123",
                desired,
                stored,
            )
        )

        self.assertEqual(
            result.state,
            "UNCHANGED",
        )

        self.assertEqual(
            result.changes,
            (),
        )

    def test_single_authoritative_change_is_reported(self):
        desired = self._state(
            custom_lifecycle_state="Planned",
        )

        stored = self._state(
            custom_lifecycle_state=None,
        )

        result = (
            infrastructure_reconciliation
            .plan_location_reconciliation(
                "kmz123",
                desired,
                stored,
            )
        )

        self.assertEqual(
            result.state,
            "CHANGED",
        )

        self.assertEqual(
            len(result.changes),
            1,
        )

        change = result.changes[0]

        self.assertEqual(
            change.fieldname,
            "custom_lifecycle_state",
        )

        self.assertIsNone(
            change.stored_value,
        )

        self.assertEqual(
            change.desired_value,
            "Planned",
        )

    def test_multiple_changes_follow_authoritative_field_order(
        self,
    ):
        desired = self._state(
            location_name="Buildings: New Office",
            custom_infrastructure_class="Building",
            custom_ticket_selectability="Not Selectable",
        )

        stored = self._state()

        result = (
            infrastructure_reconciliation
            .plan_location_reconciliation(
                "kmz123",
                desired,
                stored,
            )
        )

        self.assertEqual(
            result.state,
            "CHANGED",
        )

        self.assertEqual(
            [
                change.fieldname
                for change in result.changes
            ],
            [
                "location_name",
                "custom_infrastructure_class",
                "custom_ticket_selectability",
            ],
        )

    def test_provenance_differences_do_not_create_change(self):
        desired = self._state()
        stored = self._state()

        desired.update(
            {
                "custom_first_seen_import":
                    "BOSCHENDAL-KMZ-2026-01",
                "custom_last_seen_import":
                    "BOSCHENDAL-KMZ-2026-02",
                "custom_last_changed_import":
                    "BOSCHENDAL-KMZ-2026-02",
            }
        )

        stored.update(
            {
                "custom_first_seen_import":
                    "BOSCHENDAL-KMZ-2026-01",
                "custom_last_seen_import":
                    "BOSCHENDAL-KMZ-2026-01",
                "custom_last_changed_import":
                    "BOSCHENDAL-KMZ-2026-01",
            }
        )

        result = (
            infrastructure_reconciliation
            .plan_location_reconciliation(
                "kmz123",
                desired,
                stored,
            )
        )

        self.assertEqual(
            result.state,
            "UNCHANGED",
        )

        self.assertEqual(
            result.changes,
            (),
        )

    def test_missing_desired_authoritative_field_is_refused(
        self,
    ):
        desired = self._state()

        del desired[
            "custom_ticket_selectability"
        ]

        with self.assertRaisesRegex(
            ValueError,
            "desired Location state is missing "
            "authoritative fields: "
            "custom_ticket_selectability",
        ):
            (
                infrastructure_reconciliation
                .plan_location_reconciliation(
                    "kmz123",
                    desired,
                    self._state(),
                )
            )

    def test_missing_stored_authoritative_field_is_refused(
        self,
    ):
        stored = self._state()

        del stored[
            "custom_infrastructure_class"
        ]

        with self.assertRaisesRegex(
            ValueError,
            "stored Location state is missing "
            "authoritative fields: "
            "custom_infrastructure_class",
        ):
            (
                infrastructure_reconciliation
                .plan_location_reconciliation(
                    "kmz123",
                    self._state(),
                    stored,
                )
            )

    def test_blank_canonical_location_id_is_refused(self):
        with self.assertRaisesRegex(
            ValueError,
            "Location reconciliation requires "
            "a canonical Location ID",
        ):
            (
                infrastructure_reconciliation
                .plan_location_reconciliation(
                    "   ",
                    self._state(),
                    None,
                )
            )
