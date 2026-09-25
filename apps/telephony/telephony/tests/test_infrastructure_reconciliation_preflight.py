import unittest
from unittest import mock

from telephony.scripts.infrastructure_reconciliation_batch import (
    LocationBatchPlan,
    LocationScopeMembership,
)


class TestInfrastructureReconciliationPreflight(
    unittest.TestCase
):
    IMPORT_VERSION = "BOSCHENDAL-KMZ-2026-01"
    SCOPE_KEY = "BOSCHENDAL-INFRASTRUCTURE"
    CUSTOMER = "Customer B"

    def _plan(
        self,
        *,
        scope_key=None,
        import_version=None,
        entries=(),
        missing_location_ids=(),
    ):
        scope_key = (
            scope_key
            or self.SCOPE_KEY
        )

        import_version = (
            import_version
            or self.IMPORT_VERSION
        )

        membership = LocationScopeMembership(
            scope_key=scope_key,
            import_versions=(),
            versioned_location_ids=(),
            legacy_location_ids=(),
            known_location_ids=(),
        )

        return LocationBatchPlan(
            scope_key=scope_key,
            import_version=import_version,
            membership=membership,
            entries=tuple(entries),
            new_stages=(),
            external_prerequisites=(),
            missing_location_ids=tuple(
                missing_location_ids
            ),
        )

    def test_commit_flag_is_mandatory(
        self,
    ):
        from telephony.scripts import (
            infrastructure_reconciliation_preflight,
        )

        with (
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "without commit=1",
            ):
                (
                    infrastructure_reconciliation_preflight
                    .run_location_batch_preflight(
                        self._plan(),
                        customer=self.CUSTOMER,
                        source_type="KMZ",
                        expected_site=(
                            infrastructure_reconciliation_preflight
                            .frappe.local.site
                        ),
                        commit=0,
                    )
                )

        commit.assert_not_called()
        rollback.assert_not_called()

    def test_target_site_mismatch_is_refused(
        self,
    ):
        from telephony.scripts import (
            infrastructure_reconciliation_preflight,
        )

        with (
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "target site mismatch",
            ):
                (
                    infrastructure_reconciliation_preflight
                    .run_location_batch_preflight(
                        self._plan(),
                        customer=self.CUSTOMER,
                        source_type="KMZ",
                        expected_site=(
                            "definitely-not-current-site"
                        ),
                        commit=1,
                    )
                )

        commit.assert_not_called()
        rollback.assert_not_called()

    def test_successful_preflight_commits_once(
        self,
    ):
        from telephony.scripts import (
            infrastructure_reconciliation_preflight,
        )

        plan = self._plan(
            entries=(
                mock.sentinel.entry_one,
                mock.sentinel.entry_two,
            ),
        )

        registration = mock.Mock()
        registration.import_version = (
            self.IMPORT_VERSION
        )
        registration.scope_key = (
            self.SCOPE_KEY
        )
        registration.customer = (
            self.CUSTOMER
        )
        registration.source_type = "KMZ"

        validation = mock.Mock()
        validation.import_version = (
            self.IMPORT_VERSION
        )
        validation.scope_key = (
            self.SCOPE_KEY
        )
        validation.status = "Validated"
        validation.record_count = 2
        validation.location_count = 2

        with (
            mock.patch.object(
                infrastructure_reconciliation_preflight,
                "register_infrastructure_import",
                return_value=registration,
            ) as register,
            mock.patch.object(
                infrastructure_reconciliation_preflight,
                "validate_infrastructure_import",
                return_value=validation,
            ) as validate,
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "get_value",
                return_value={
                    "name": self.IMPORT_VERSION,
                    "scope_key": self.SCOPE_KEY,
                    "customer": self.CUSTOMER,
                    "source_type": "KMZ",
                    "source_filename": "Boschendal.kmz",
                    "source_hash": "abc123",
                    "importer_version": "location-v2",
                    "status": "Validated",
                    "record_count": 2,
                    "location_count": 2,
                },
            ) as get_value,
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "rollback",
            ) as rollback,
        ):
            result = (
                infrastructure_reconciliation_preflight
                .run_location_batch_preflight(
                    plan,
                    customer=self.CUSTOMER,
                    source_type="KMZ",
                    source_filename="Boschendal.kmz",
                    source_hash="abc123",
                    importer_version="location-v2",
                    expected_site=(
                        infrastructure_reconciliation_preflight
                        .frappe.local.site
                    ),
                    commit=1,
                )
            )

        register.assert_called_once_with(
            self.IMPORT_VERSION,
            self.SCOPE_KEY,
            self.CUSTOMER,
            "KMZ",
            source_filename="Boschendal.kmz",
            source_hash="abc123",
            source_received_on=None,
            importer_version="location-v2",
            notes=None,
        )

        validate.assert_called_once_with(
            plan
        )

        get_value.assert_called_once_with(
            "TELECTRO Infrastructure Import",
            self.IMPORT_VERSION,
            [
                "name",
                "scope_key",
                "customer",
                "source_type",
                "source_filename",
                "source_hash",
                "importer_version",
                "status",
                "record_count",
                "location_count",
            ],
            as_dict=True,
        )

        commit.assert_called_once_with()
        rollback.assert_not_called()

        self.assertTrue(
            result.committed
        )
        self.assertEqual(
            result.import_version,
            self.IMPORT_VERSION,
        )
        self.assertEqual(
            result.status,
            "Validated",
        )
        self.assertEqual(
            result.record_count,
            2,
        )
        self.assertEqual(
            result.location_count,
            2,
        )

    def test_validation_failure_rolls_back(
        self,
    ):
        from telephony.scripts import (
            infrastructure_reconciliation_preflight,
        )

        with (
            mock.patch.object(
                infrastructure_reconciliation_preflight,
                "register_infrastructure_import",
            ),
            mock.patch.object(
                infrastructure_reconciliation_preflight,
                "validate_infrastructure_import",
                side_effect=RuntimeError(
                    "validation failed"
                ),
            ),
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "validation failed",
            ):
                (
                    infrastructure_reconciliation_preflight
                    .run_location_batch_preflight(
                        self._plan(),
                        customer=self.CUSTOMER,
                        source_type="KMZ",
                        expected_site=(
                            infrastructure_reconciliation_preflight
                            .frappe.local.site
                        ),
                        commit=1,
                    )
                )

        commit.assert_not_called()
        rollback.assert_called_once_with()

    def test_post_validation_verification_failure_rolls_back(
        self,
    ):
        from telephony.scripts import (
            infrastructure_reconciliation_preflight,
        )

        plan = self._plan(
            entries=(
                mock.sentinel.entry_one,
                mock.sentinel.entry_two,
            ),
        )

        with (
            mock.patch.object(
                infrastructure_reconciliation_preflight,
                "register_infrastructure_import",
            ),
            mock.patch.object(
                infrastructure_reconciliation_preflight,
                "validate_infrastructure_import",
            ),
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "get_value",
                return_value={
                    "name": self.IMPORT_VERSION,
                    "scope_key": self.SCOPE_KEY,
                    "customer": self.CUSTOMER,
                    "source_type": "KMZ",
                    "source_filename": None,
                    "source_hash": None,
                    "importer_version": None,
                    "status": "Validated",
                    "record_count": 2,
                    "location_count": 999,
                },
            ),
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "preflight verification failed",
            ):
                (
                    infrastructure_reconciliation_preflight
                    .run_location_batch_preflight(
                        plan,
                        customer=self.CUSTOMER,
                        source_type="KMZ",
                        expected_site=(
                            infrastructure_reconciliation_preflight
                            .frappe.local.site
                        ),
                        commit=1,
                    )
                )

        commit.assert_not_called()
        rollback.assert_called_once_with()

    def test_source_hash_verification_failure_rolls_back(
        self,
    ):
        from telephony.scripts import (
            infrastructure_reconciliation_preflight,
        )

        plan = self._plan(
            entries=(
                mock.sentinel.entry_one,
            ),
        )

        with (
            mock.patch.object(
                infrastructure_reconciliation_preflight,
                "register_infrastructure_import",
            ),
            mock.patch.object(
                infrastructure_reconciliation_preflight,
                "validate_infrastructure_import",
            ),
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "get_value",
                return_value={
                    "name": self.IMPORT_VERSION,
                    "scope_key": self.SCOPE_KEY,
                    "customer": self.CUSTOMER,
                    "source_type": "KMZ",
                    "source_filename": "Boschendal.kmz",
                    "source_hash": "abc123",
                    "importer_version": "location-v2",
                    "status": "Validated",
                    "record_count": 2,
                    "location_count": 2,
                },
            ),
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_preflight
                .frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "preflight verification failed",
            ):
                (
                    infrastructure_reconciliation_preflight
                    .run_location_batch_preflight(
                        plan,
                        customer=self.CUSTOMER,
                        source_type="KMZ",
                        source_filename="Boschendal.kmz",
                        source_hash="expected-hash",
                        importer_version="location-v2",
                        expected_site=(
                            infrastructure_reconciliation_preflight
                            .frappe.local.site
                        ),
                        commit=1,
                    )
                )

        commit.assert_not_called()
        rollback.assert_called_once_with()
