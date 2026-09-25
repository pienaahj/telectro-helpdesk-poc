import unittest
from unittest import mock

from telephony.scripts.infrastructure_reconciliation_batch import (
    LocationBatchPlan,
    LocationScopeMembership,
)
from telephony.scripts import (
    infrastructure_import_lifecycle,
)


class TestInfrastructureImportLifecycle(
    unittest.TestCase
):
    IMPORT_VERSION = "BOSCHENDAL-KMZ-2026-01"
    SCOPE_KEY = "BOSCHENDAL-INFRASTRUCTURE"
    CUSTOMER = "Boschendal"

    def _plan(
        self,
        *,
        import_version=None,
        scope_key=None,
        entry_count=0,
    ):
        import_version = (
            import_version
            or self.IMPORT_VERSION
        )

        scope_key = (
            scope_key
            or self.SCOPE_KEY
        )

        membership = LocationScopeMembership(
            scope_key=scope_key,
            import_versions=(),
            versioned_location_ids=(),
            legacy_location_ids=(),
            known_location_ids=(),
        )

        entries = tuple(
            mock.sentinel.entry
            for _ in range(
                entry_count
            )
        )

        return LocationBatchPlan(
            scope_key=scope_key,
            import_version=import_version,
            membership=membership,
            entries=entries,
            new_stages=(),
            external_prerequisites=(),
            missing_location_ids=(),
        )

    @mock.patch.object(
        infrastructure_import_lifecycle.frappe,
        "get_doc",
    )
    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "exists",
    )
    def test_register_creates_draft_batch(
        self,
        exists,
        get_doc,
    ):
        exists.return_value = False

        doc = mock.Mock()
        doc.name = self.IMPORT_VERSION
        doc.scope_key = self.SCOPE_KEY
        doc.customer = self.CUSTOMER
        doc.source_type = "KMZ"

        get_doc.return_value = doc

        result = (
            infrastructure_import_lifecycle
            .register_infrastructure_import(
                self.IMPORT_VERSION,
                self.SCOPE_KEY,
                self.CUSTOMER,
                "KMZ",
                source_filename=(
                    "Boschendal.kmz"
                ),
                source_hash="abc123",
                source_received_on=(
                    "2026-09-23"
                ),
                importer_version="location-v2",
                notes="Initial formal batch",
            )
        )

        exists.assert_called_once_with(
            "TELECTRO Infrastructure Import",
            self.IMPORT_VERSION,
        )

        get_doc.assert_called_once_with(
            {
                "doctype":
                    "TELECTRO Infrastructure Import",
                "import_version":
                    self.IMPORT_VERSION,
                "scope_key":
                    self.SCOPE_KEY,
                "customer":
                    self.CUSTOMER,
                "source_type":
                    "KMZ",
                "source_filename":
                    "Boschendal.kmz",
                "source_hash":
                    "abc123",
                "source_received_on":
                    "2026-09-23",
                "importer_version":
                    "location-v2",
                "status":
                    "Draft",
                "notes":
                    "Initial formal batch",
            }
        )

        doc.insert.assert_called_once_with(
            ignore_permissions=True
        )

        self.assertEqual(
            result.import_version,
            self.IMPORT_VERSION,
        )

        self.assertEqual(
            result.scope_key,
            self.SCOPE_KEY,
        )

        self.assertEqual(
            result.customer,
            self.CUSTOMER,
        )

        self.assertEqual(
            result.source_type,
            "KMZ",
        )

    @mock.patch.object(
        infrastructure_import_lifecycle.frappe,
        "get_doc",
    )
    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "exists",
    )
    def test_duplicate_import_version_is_refused(
        self,
        exists,
        get_doc,
    ):
        exists.return_value = True

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            (
                infrastructure_import_lifecycle
                .register_infrastructure_import(
                    self.IMPORT_VERSION,
                    self.SCOPE_KEY,
                    self.CUSTOMER,
                    "KMZ",
                )
            )

        get_doc.assert_not_called()

    @mock.patch.object(
        infrastructure_import_lifecycle.frappe,
        "get_doc",
    )
    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "exists",
    )
    def test_unsupported_source_type_is_refused(
        self,
        exists,
        get_doc,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported infrastructure source type",
        ):
            (
                infrastructure_import_lifecycle
                .register_infrastructure_import(
                    self.IMPORT_VERSION,
                    self.SCOPE_KEY,
                    self.CUSTOMER,
                    "PDF",
                )
            )

        exists.assert_not_called()
        get_doc.assert_not_called()

    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "get_value",
    )
    def test_draft_batch_validates_with_plan_counts(
        self,
        get_value,
        set_value,
    ):
        get_value.return_value = {
            "name": self.IMPORT_VERSION,
            "scope_key": self.SCOPE_KEY,
            "status": "Draft",
        }

        plan = self._plan(
            entry_count=262
        )

        result = (
            infrastructure_import_lifecycle
            .validate_infrastructure_import(
                plan
            )
        )

        get_value.assert_called_once_with(
            "TELECTRO Infrastructure Import",
            self.IMPORT_VERSION,
            [
                "name",
                "scope_key",
                "status",
            ],
            as_dict=True,
        )

        set_value.assert_called_once_with(
            "TELECTRO Infrastructure Import",
            self.IMPORT_VERSION,
            {
                "status": "Validated",
                "record_count": 262,
                "location_count": 262,
            },
            update_modified=False,
        )

        self.assertEqual(
            result.import_version,
            self.IMPORT_VERSION,
        )

        self.assertEqual(
            result.scope_key,
            self.SCOPE_KEY,
        )

        self.assertEqual(
            result.status,
            "Validated",
        )

        self.assertEqual(
            result.record_count,
            262,
        )

        self.assertEqual(
            result.location_count,
            262,
        )

    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "get_value",
    )
    def test_missing_batch_is_refused(
        self,
        get_value,
        set_value,
    ):
        get_value.return_value = None

        with self.assertRaisesRegex(
            ValueError,
            "does not exist",
        ):
            (
                infrastructure_import_lifecycle
                .validate_infrastructure_import(
                    self._plan()
                )
            )

        set_value.assert_not_called()

    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "get_value",
    )
    def test_scope_mismatch_is_refused(
        self,
        get_value,
        set_value,
    ):
        get_value.return_value = {
            "name": self.IMPORT_VERSION,
            "scope_key": "WRONG-SCOPE",
            "status": "Draft",
        }

        with self.assertRaisesRegex(
            ValueError,
            "scope mismatch",
        ):
            (
                infrastructure_import_lifecycle
                .validate_infrastructure_import(
                    self._plan()
                )
            )

        set_value.assert_not_called()

    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_import_lifecycle.frappe.db,
        "get_value",
    )
    def test_non_draft_batch_is_refused(
        self,
        get_value,
        set_value,
    ):
        get_value.return_value = {
            "name": self.IMPORT_VERSION,
            "scope_key": self.SCOPE_KEY,
            "status": "Validated",
        }

        with self.assertRaisesRegex(
            ValueError,
            "must be Draft before validation",
        ):
            (
                infrastructure_import_lifecycle
                .validate_infrastructure_import(
                    self._plan()
                )
            )

        set_value.assert_not_called()

    def test_validation_requires_batch_plan(
        self,
    ):
        with self.assertRaisesRegex(
            TypeError,
            "plan must be a LocationBatchPlan",
        ):
            (
                infrastructure_import_lifecycle
                .validate_infrastructure_import(
                    object()
                )
            )
