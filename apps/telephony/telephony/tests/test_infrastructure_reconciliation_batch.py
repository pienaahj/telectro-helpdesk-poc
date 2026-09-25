import unittest
from unittest import mock

from telephony.scripts.infrastructure_reconciliation import (
    LocationReconciliationPlan,
)
from telephony.scripts.infrastructure_reconciliation_adapter import (
    LocationDatabaseReconciliationPlan,
    LocationProvenancePlan,
)
from telephony.scripts import (
    infrastructure_reconciliation_batch,
)


class TestLocationV2BatchPlanner(unittest.TestCase):
    def _desired(self, **overrides):
        values = {
            "location_name": "Buildings: Office",
            "parent_location": "Boschendal - Buildings",
            "is_container": 0,
            "is_group": 0,
            "latitude": -33.900001,
            "longitude": 18.900001,
            "area_uom": None,
            "location": None,
            "custom_kmz_source": "Boschendal.kmz",
            "custom_kmz_folder_path": (
                "Boschendal / Buildings"
            ),
            "custom_kmz_geometry_type": "Point",
            "custom_kmz_description": "Office",
            "custom_kmz_metadata_json": (
                '{"pts_count":1}'
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

    def _database_plan(
        self,
        location_id,
        state,
    ):
        return LocationDatabaseReconciliationPlan(
            reconciliation=LocationReconciliationPlan(
                location_id=location_id,
                state=state,
                changes=(),
            ),
            provenance=LocationProvenancePlan(
                first_seen_import=(
                    "BOSCHENDAL-KMZ-2026-01"
                ),
                last_seen_import=(
                    "BOSCHENDAL-KMZ-2026-01"
                ),
                last_changed_import=(
                    "BOSCHENDAL-KMZ-2026-01"
                ),
            ),
        )

    def _entry(
        self,
        location_id,
        state,
        **desired_overrides,
    ):
        desired = self._desired(
            **desired_overrides
        )

        return (
            infrastructure_reconciliation_batch
            .LocationBatchEntryPlan(
                location_id=location_id,
                desired_values=(
                    infrastructure_reconciliation_batch
                    ._freeze_desired(
                        desired
                    )
                ),
                database_plan=self._database_plan(
                    location_id,
                    state,
                ),
            )
        )

    @mock.patch.object(
        infrastructure_reconciliation_batch.frappe,
        "get_all",
    )
    def test_scope_membership_combines_versioned_and_legacy_ids(
        self,
        get_all,
    ):
        get_all.side_effect = [
            [
                "BOSCHENDAL-KMZ-2026-02",
                "BOSCHENDAL-KMZ-2026-01",
            ],
            [
                "kmz002",
                "kmz001",
            ],
            [
                "kmz003",
                "kmz002",
            ],
        ]

        result = (
            infrastructure_reconciliation_batch
            .get_location_scope_membership(
                "BOSCHENDAL-INFRASTRUCTURE",
                legacy_source="Boschendal.kmz",
            )
        )

        self.assertEqual(
            result.import_versions,
            (
                "BOSCHENDAL-KMZ-2026-01",
                "BOSCHENDAL-KMZ-2026-02",
            ),
        )

        self.assertEqual(
            result.versioned_location_ids,
            (
                "kmz001",
                "kmz002",
            ),
        )

        self.assertEqual(
            result.legacy_location_ids,
            (
                "kmz002",
                "kmz003",
            ),
        )

        self.assertEqual(
            result.known_location_ids,
            (
                "kmz001",
                "kmz002",
                "kmz003",
            ),
        )

        self.assertEqual(
            get_all.call_count,
            3,
        )

    @mock.patch.object(
        infrastructure_reconciliation_batch.frappe,
        "get_all",
    )
    def test_first_import_membership_uses_legacy_bootstrap(
        self,
        get_all,
    ):
        get_all.side_effect = [
            [],
            [
                "kmz003",
                "kmz001",
                "kmz002",
            ],
        ]

        result = (
            infrastructure_reconciliation_batch
            .get_location_scope_membership(
                "BOSCHENDAL-INFRASTRUCTURE",
                legacy_source="Boschendal.kmz",
            )
        )

        self.assertEqual(
            result.import_versions,
            (),
        )

        self.assertEqual(
            result.versioned_location_ids,
            (),
        )

        self.assertEqual(
            result.legacy_location_ids,
            (
                "kmz001",
                "kmz002",
                "kmz003",
            ),
        )

        self.assertEqual(
            result.known_location_ids,
            (
                "kmz001",
                "kmz002",
                "kmz003",
            ),
        )

        self.assertEqual(
            get_all.call_count,
            2,
        )

    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "_build_new_stages",
    )
    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "plan_stored_location_reconciliation",
    )
    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "get_location_scope_membership",
    )
    def test_batch_detects_missing_from_known_scope(
        self,
        get_membership,
        plan_stored,
        build_new_stages,
    ):
        get_membership.return_value = (
            infrastructure_reconciliation_batch
            .LocationScopeMembership(
                scope_key=(
                    "BOSCHENDAL-INFRASTRUCTURE"
                ),
                import_versions=(),
                versioned_location_ids=(),
                legacy_location_ids=(
                    "kmz001",
                    "kmz002",
                    "kmz003",
                ),
                known_location_ids=(
                    "kmz001",
                    "kmz002",
                    "kmz003",
                ),
            )
        )

        plan_stored.side_effect = [
            self._database_plan(
                "kmz001",
                "UNCHANGED",
            ),
            self._database_plan(
                "kmz002",
                "CHANGED",
            ),
        ]

        build_new_stages.return_value = (
            (),
            (),
        )

        result = (
            infrastructure_reconciliation_batch
            .plan_location_batch(
                {
                    "kmz001": self._desired(
                        location_name="One"
                    ),
                    "kmz002": self._desired(
                        location_name="Two"
                    ),
                },
                "BOSCHENDAL-INFRASTRUCTURE",
                "BOSCHENDAL-KMZ-2026-01",
                legacy_source="Boschendal.kmz",
            )
        )

        self.assertEqual(
            result.missing_location_ids,
            (
                "kmz003",
            ),
        )

        self.assertEqual(
            tuple(
                entry.database_plan
                .reconciliation
                .state
                for entry in result.entries
            ),
            (
                "UNCHANGED",
                "CHANGED",
            ),
        )

    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "validate_target_preflight",
    )
    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "validate_release_stages",
    )
    def test_new_rows_are_staged_parent_before_child(
        self,
        validate_stages,
        validate_target,
    ):
        group = self._entry(
            "kmz-group",
            "NEW",
            location_name="New Group",
            parent_location="Boschendal",
            is_group=1,
        )

        child = self._entry(
            "kmz-child",
            "NEW",
            location_name="New Child",
            parent_location="kmz-group",
            is_group=0,
        )

        stages, prerequisites = (
            infrastructure_reconciliation_batch
            ._build_new_stages(
                (
                    child,
                    group,
                )
            )
        )

        self.assertEqual(
            len(stages),
            2,
        )

        self.assertEqual(
            tuple(
                row.name
                for row in stages[0]
            ),
            (
                "kmz-group",
            ),
        )

        self.assertEqual(
            tuple(
                row.name
                for row in stages[1]
            ),
            (
                "kmz-child",
            ),
        )

        self.assertEqual(
            prerequisites,
            (
                "Boschendal",
            ),
        )

        validate_stages.assert_called_once_with(
            stages,
            {
                "Boschendal",
            },
        )

        validate_target.assert_called_once_with(
            stages,
            {
                "Boschendal",
            },
        )

    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "validate_target_preflight",
    )
    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "validate_release_stages",
    )
    def test_existing_only_batch_skips_v1_new_preflight(
        self,
        validate_stages,
        validate_target,
    ):
        entries = (
            self._entry(
                "kmz001",
                "UNCHANGED",
                location_name="One",
            ),
            self._entry(
                "kmz002",
                "CHANGED",
                location_name="Two",
            ),
        )

        result = (
            infrastructure_reconciliation_batch
            ._build_new_stages(
                entries
            )
        )

        self.assertEqual(
            result,
            (
                (),
                (),
            ),
        )

        validate_stages.assert_not_called()
        validate_target.assert_not_called()

    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "validate_target_preflight",
    )
    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "validate_release_stages",
    )
    def test_new_parent_must_be_group(
        self,
        validate_stages,
        validate_target,
    ):
        parent = self._entry(
            "kmz-parent",
            "NEW",
            location_name="Parent",
            parent_location="Boschendal",
            is_group=0,
        )

        child = self._entry(
            "kmz-child",
            "NEW",
            location_name="Child",
            parent_location="kmz-parent",
        )

        with self.assertRaisesRegex(
            ValueError,
            "NEW Location parent must be a group",
        ):
            (
                infrastructure_reconciliation_batch
                ._build_new_stages(
                    (
                        parent,
                        child,
                    )
                )
            )

        validate_stages.assert_not_called()
        validate_target.assert_not_called()

    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "validate_target_preflight",
    )
    @mock.patch.object(
        infrastructure_reconciliation_batch,
        "validate_release_stages",
    )
    def test_new_parent_cycle_is_refused(
        self,
        validate_stages,
        validate_target,
    ):
        first = self._entry(
            "kmz-first",
            "NEW",
            location_name="First",
            parent_location="kmz-second",
            is_group=1,
        )

        second = self._entry(
            "kmz-second",
            "NEW",
            location_name="Second",
            parent_location="kmz-first",
            is_group=1,
        )

        with self.assertRaisesRegex(
            ValueError,
            "cyclic or unresolved NEW parent dependency",
        ):
            (
                infrastructure_reconciliation_batch
                ._build_new_stages(
                    (
                        first,
                        second,
                    )
                )
            )

        validate_stages.assert_not_called()
        validate_target.assert_not_called()

    def test_duplicate_location_name_is_refused(self):
        entries = (
            self._entry(
                "kmz001",
                "UNCHANGED",
                location_name="Duplicate",
            ),
            self._entry(
                "kmz002",
                "UNCHANGED",
                location_name="Duplicate",
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "duplicate Location Name in V2 batch",
        ):
            (
                infrastructure_reconciliation_batch
                ._validate_batch_identity(
                    entries
                )
            )

    def test_id_location_name_cross_collision_is_refused(
        self,
    ):
        entries = (
            self._entry(
                "kmz001",
                "UNCHANGED",
                location_name="Readable One",
            ),
            self._entry(
                "kmz002",
                "UNCHANGED",
                location_name="kmz001",
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "Location ID / Location Name collision",
        ):
            (
                infrastructure_reconciliation_batch
                ._validate_batch_identity(
                    entries
                )
            )
