import unittest
from unittest import mock

from telephony.scripts import infrastructure_reconciliation_adapter


class TestLocationV2DatabaseAdapter(unittest.TestCase):
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

    @mock.patch.object(
        infrastructure_reconciliation_adapter.frappe.db,
        "get_value",
    )
    def test_get_stored_location_state_reads_exact_database_fields(
        self,
        get_value,
    ):
        stored = self._stored()
        get_value.return_value = stored

        result = (
            infrastructure_reconciliation_adapter
            .get_stored_location_state(
                "kmz123"
            )
        )

        get_value.assert_called_once_with(
            "Location",
            "kmz123",
            list(
                infrastructure_reconciliation_adapter
                .LOCATION_V2_DATABASE_FIELDS
            ),
            as_dict=True,
        )

        self.assertEqual(
            result,
            stored,
        )

    @mock.patch.object(
        infrastructure_reconciliation_adapter.frappe.db,
        "get_value",
    )
    def test_missing_location_returns_none(
        self,
        get_value,
    ):
        get_value.return_value = None

        result = (
            infrastructure_reconciliation_adapter
            .get_stored_location_state(
                "kmz123"
            )
        )

        self.assertIsNone(result)

    @mock.patch.object(
        infrastructure_reconciliation_adapter.frappe.db,
        "get_value",
    )
    def test_new_location_sets_all_provenance_to_current_import(
        self,
        get_value,
    ):
        get_value.return_value = None

        result = (
            infrastructure_reconciliation_adapter
            .plan_stored_location_reconciliation(
                "kmz123",
                self._desired(),
                "BOSCHENDAL-KMZ-2026-01",
            )
        )

        self.assertEqual(
            result.reconciliation.state,
            "NEW",
        )

        self.assertEqual(
            result.provenance.first_seen_import,
            "BOSCHENDAL-KMZ-2026-01",
        )

        self.assertEqual(
            result.provenance.last_seen_import,
            "BOSCHENDAL-KMZ-2026-01",
        )

        self.assertEqual(
            result.provenance.last_changed_import,
            "BOSCHENDAL-KMZ-2026-01",
        )

    @mock.patch.object(
        infrastructure_reconciliation_adapter.frappe.db,
        "get_value",
    )
    def test_unchanged_location_preserves_existing_provenance(
        self,
        get_value,
    ):
        get_value.return_value = self._stored()

        result = (
            infrastructure_reconciliation_adapter
            .plan_stored_location_reconciliation(
                "kmz123",
                self._desired(),
                "BOSCHENDAL-KMZ-2026-02",
            )
        )

        self.assertEqual(
            result.reconciliation.state,
            "UNCHANGED",
        )

        self.assertEqual(
            result.provenance.first_seen_import,
            "BOSCHENDAL-KMZ-2026-01",
        )

        self.assertEqual(
            result.provenance.last_seen_import,
            "BOSCHENDAL-KMZ-2026-02",
        )

        self.assertEqual(
            result.provenance.last_changed_import,
            "BOSCHENDAL-KMZ-2026-01",
        )

    @mock.patch.object(
        infrastructure_reconciliation_adapter.frappe.db,
        "get_value",
    )
    def test_changed_location_advances_last_changed_import(
        self,
        get_value,
    ):
        get_value.return_value = self._stored(
            custom_lifecycle_state=None,
        )

        desired = self._desired(
            custom_lifecycle_state="Planned",
        )

        result = (
            infrastructure_reconciliation_adapter
            .plan_stored_location_reconciliation(
                "kmz123",
                desired,
                "BOSCHENDAL-KMZ-2026-02",
            )
        )

        self.assertEqual(
            result.reconciliation.state,
            "CHANGED",
        )

        self.assertEqual(
            result.provenance.first_seen_import,
            "BOSCHENDAL-KMZ-2026-01",
        )

        self.assertEqual(
            result.provenance.last_seen_import,
            "BOSCHENDAL-KMZ-2026-02",
        )

        self.assertEqual(
            result.provenance.last_changed_import,
            "BOSCHENDAL-KMZ-2026-02",
        )

    @mock.patch.object(
        infrastructure_reconciliation_adapter.frappe.db,
        "get_value",
    )
    def test_legacy_unchanged_location_initialises_first_seen_only(
        self,
        get_value,
    ):
        get_value.return_value = self._stored(
            custom_first_seen_import=None,
            custom_last_seen_import=None,
            custom_last_changed_import=None,
        )

        result = (
            infrastructure_reconciliation_adapter
            .plan_stored_location_reconciliation(
                "kmz123",
                self._desired(),
                "BOSCHENDAL-KMZ-2026-01",
            )
        )

        self.assertEqual(
            result.reconciliation.state,
            "UNCHANGED",
        )

        self.assertEqual(
            result.provenance.first_seen_import,
            "BOSCHENDAL-KMZ-2026-01",
        )

        self.assertEqual(
            result.provenance.last_seen_import,
            "BOSCHENDAL-KMZ-2026-01",
        )

        self.assertIsNone(
            result.provenance.last_changed_import,
        )

    def test_blank_import_version_is_refused(self):
        reconciliation = mock.Mock(
            state="NEW"
        )

        with self.assertRaisesRegex(
            ValueError,
            "Infrastructure import version is required",
        ):
            (
                infrastructure_reconciliation_adapter
                .plan_location_provenance(
                    reconciliation,
                    None,
                    "   ",
                )
            )
