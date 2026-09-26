import unittest
from unittest import mock

from telephony.scripts.infrastructure_reconciliation import (
    plan_location_reconciliation,
)
from telephony.scripts.infrastructure_reconciliation_adapter import (
    LocationDatabaseReconciliationPlan,
    plan_location_provenance,
)
from telephony.scripts import infrastructure_reconciliation_writer


class TestLocationV2ExistingLocationWriter(
    unittest.TestCase
):
    def _desired(self, **overrides):
        values = {
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
            "custom_kmz_source": "Boschendal.kmz",
            "custom_kmz_folder_path": (
                "Boschendal / Buildings"
            ),
            "custom_kmz_geometry_type": "Point",
            "custom_kmz_description": "Office",
            "custom_kmz_metadata_json": (
                '{"pts_count":1}'
            ),
            "custom_customer": None,
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

    def _stored(self, **overrides):
        values = self._desired()

        values.update(
            {
                "custom_first_seen_import":
                    "BOSCHENDAL-KMZ-2026-01",
                "custom_last_seen_import":
                    "BOSCHENDAL-KMZ-2026-01",
                "custom_last_changed_import":
                    "BOSCHENDAL-KMZ-2026-01",
            }
        )

        values.update(overrides)
        return values

    def _plan(
        self,
        location_id,
        desired,
        stored,
        import_version,
    ):
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

    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "set_value",
    )
    def test_changed_ordinary_field_writes_exact_changes_and_provenance(
        self,
        set_value,
    ):
        stored = self._stored(
            custom_lifecycle_state=None,
        )

        desired = self._desired(
            custom_lifecycle_state="Planned",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
            "BOSCHENDAL-KMZ-2026-02",
        )

        result = (
            infrastructure_reconciliation_writer
            .apply_existing_location_plan(
                "kmz123",
                stored,
                plan,
            )
        )

        set_value.assert_called_once_with(
            "Location",
            "kmz123",
            {
                "custom_lifecycle_state": "Planned",
                "custom_last_seen_import":
                    "BOSCHENDAL-KMZ-2026-02",
                "custom_last_changed_import":
                    "BOSCHENDAL-KMZ-2026-02",
            },
            update_modified=False,
        )

        self.assertEqual(
            result.reconciliation_state,
            "CHANGED",
        )

        self.assertEqual(
            result.updated_fields,
            (
                "custom_lifecycle_state",
                "custom_last_seen_import",
                "custom_last_changed_import",
            ),
        )

    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "set_value",
    )
    def test_customer_ownership_field_writes_as_ordinary_change(
        self,
        set_value,
    ):
        stored = self._stored(
            custom_customer=None,
        )

        desired = self._desired(
            custom_customer="Customer A",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
            "BOSCHENDAL-KMZ-2026-02",
        )

        result = (
            infrastructure_reconciliation_writer
            .apply_existing_location_plan(
                "kmz123",
                stored,
                plan,
            )
        )

        set_value.assert_called_once_with(
            "Location",
            "kmz123",
            {
                "custom_customer": "Customer A",
                "custom_last_seen_import":
                    "BOSCHENDAL-KMZ-2026-02",
                "custom_last_changed_import":
                    "BOSCHENDAL-KMZ-2026-02",
            },
            update_modified=False,
        )

        self.assertEqual(
            result.reconciliation_state,
            "CHANGED",
        )

        self.assertEqual(
            result.updated_fields,
            (
                "custom_customer",
                "custom_last_seen_import",
                "custom_last_changed_import",
            ),
        )

    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "set_value",
    )
    def test_unchanged_location_writes_only_changed_provenance(
        self,
        set_value,
    ):
        stored = self._stored()

        plan = self._plan(
            "kmz123",
            self._desired(),
            stored,
            "BOSCHENDAL-KMZ-2026-02",
        )

        result = (
            infrastructure_reconciliation_writer
            .apply_existing_location_plan(
                "kmz123",
                stored,
                plan,
            )
        )

        set_value.assert_called_once_with(
            "Location",
            "kmz123",
            {
                "custom_last_seen_import":
                    "BOSCHENDAL-KMZ-2026-02",
            },
            update_modified=False,
        )

        self.assertEqual(
            result.reconciliation_state,
            "UNCHANGED",
        )

        self.assertEqual(
            result.updated_fields,
            (
                "custom_last_seen_import",
            ),
        )

    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "set_value",
    )
    def test_fully_current_location_performs_no_write(
        self,
        set_value,
    ):
        stored = self._stored(
            custom_last_seen_import=(
                "BOSCHENDAL-KMZ-2026-02"
            ),
        )

        plan = self._plan(
            "kmz123",
            self._desired(),
            stored,
            "BOSCHENDAL-KMZ-2026-02",
        )

        result = (
            infrastructure_reconciliation_writer
            .apply_existing_location_plan(
                "kmz123",
                stored,
                plan,
            )
        )

        set_value.assert_not_called()

        self.assertEqual(
            result.reconciliation_state,
            "UNCHANGED",
        )

        self.assertEqual(
            result.updated_fields,
            (),
        )

    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "set_value",
    )
    def test_new_location_is_refused(
        self,
        set_value,
    ):
        desired = self._desired()

        plan = self._plan(
            "kmz123",
            desired,
            None,
            "BOSCHENDAL-KMZ-2026-01",
        )

        with self.assertRaisesRegex(
            ValueError,
            "does not yet support NEW Location creation",
        ):
            (
                infrastructure_reconciliation_writer
                .apply_existing_location_plan(
                    "kmz123",
                    None,
                    plan,
                )
            )

        set_value.assert_not_called()

    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "set_value",
    )
    def test_deferred_fields_are_refused(
        self,
        set_value,
    ):
        cases = (
            (
                "parent_location",
                {
                    "parent_location":
                        "Boschendal - Other"
                },
            ),
            (
                "is_group",
                {
                    "is_group": 1
                },
            ),
            (
                "location",
                {
                    "location": (
                        '{"type":"FeatureCollection",'
                        '"features":['
                        '{"type":"Feature",'
                        '"geometry":null,'
                        '"properties":{}}]}'
                    )
                },
            ),
        )

        for fieldname, overrides in cases:
            with self.subTest(
                fieldname=fieldname
            ):
                stored = self._stored()
                desired = self._desired(
                    **overrides
                )

                plan = self._plan(
                    "kmz123",
                    desired,
                    stored,
                    "BOSCHENDAL-KMZ-2026-02",
                )

                with self.assertRaisesRegex(
                    ValueError,
                    (
                        "does not yet support "
                        "changes to deferred fields"
                    ),
                ):
                    (
                        infrastructure_reconciliation_writer
                        .apply_existing_location_plan(
                            "kmz123",
                            stored,
                            plan,
                        )
                    )

                set_value.assert_not_called()
                set_value.reset_mock()

    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "set_value",
    )
    def test_plan_location_id_mismatch_is_refused(
        self,
        set_value,
    ):
        stored = self._stored()

        plan = self._plan(
            "kmz123",
            self._desired(),
            stored,
            "BOSCHENDAL-KMZ-2026-02",
        )

        with self.assertRaisesRegex(
            ValueError,
            "plan ID mismatch",
        ):
            (
                infrastructure_reconciliation_writer
                .apply_existing_location_plan(
                    "kmz999",
                    stored,
                    plan,
                )
            )

        set_value.assert_not_called()

    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "rollback",
    )
    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "commit",
    )
    @mock.patch.object(
        infrastructure_reconciliation_writer.frappe.db,
        "set_value",
    )
    def test_writer_does_not_own_transaction(
        self,
        set_value,
        commit,
        rollback,
    ):
        stored = self._stored(
            custom_lifecycle_state=None,
        )

        desired = self._desired(
            custom_lifecycle_state="Planned",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
            "BOSCHENDAL-KMZ-2026-02",
        )

        (
            infrastructure_reconciliation_writer
            .apply_existing_location_plan(
                "kmz123",
                stored,
                plan,
            )
        )

        set_value.assert_called_once()
        commit.assert_not_called()
        rollback.assert_not_called()
