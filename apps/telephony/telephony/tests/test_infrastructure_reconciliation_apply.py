import unittest
from unittest import mock

from telephony.scripts.infrastructure_reconciliation import (
    LocationFieldChange,
    LocationReconciliationPlan,
)
from telephony.scripts.infrastructure_reconciliation_adapter import (
    LocationDatabaseReconciliationPlan,
    LocationProvenancePlan,
)
from telephony.scripts.infrastructure_reconciliation_batch import (
    LocationBatchEntryPlan,
    LocationBatchPlan,
    LocationScopeMembership,
    _freeze_desired,
)
from telephony.scripts import (
    infrastructure_reconciliation_apply,
)


class TestLocationV2ApplyCoordinator(
    unittest.TestCase
):
    IMPORT_VERSION = "BOSCHENDAL-KMZ-2026-01"
    SCOPE_KEY = "BOSCHENDAL-INFRASTRUCTURE"

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

    def _stored(self, **overrides):
        values = self._desired()

        values.update(
            {
                "custom_first_seen_import":
                    self.IMPORT_VERSION,
                "custom_last_seen_import":
                    self.IMPORT_VERSION,
                "custom_last_changed_import":
                    self.IMPORT_VERSION,
            }
        )

        values.update(overrides)
        return values

    def _database_plan(
        self,
        location_id,
        state,
        changes=(),
        *,
        first_seen=None,
        last_seen=None,
        last_changed=None,
    ):
        first_seen = (
            first_seen
            if first_seen is not None
            else self.IMPORT_VERSION
        )

        last_seen = (
            last_seen
            if last_seen is not None
            else self.IMPORT_VERSION
        )

        last_changed = (
            last_changed
            if last_changed is not None
            else self.IMPORT_VERSION
        )

        return LocationDatabaseReconciliationPlan(
            reconciliation=LocationReconciliationPlan(
                location_id=location_id,
                state=state,
                changes=tuple(changes),
            ),
            provenance=LocationProvenancePlan(
                first_seen_import=first_seen,
                last_seen_import=last_seen,
                last_changed_import=last_changed,
            ),
        )

    def _entry(
        self,
        location_id,
        state,
        changes=(),
        **desired_overrides,
    ):
        desired = self._desired(
            **desired_overrides
        )

        return LocationBatchEntryPlan(
            location_id=location_id,
            desired_values=_freeze_desired(
                desired
            ),
            database_plan=self._database_plan(
                location_id,
                state,
                changes,
            ),
        )

    def _batch(
        self,
        entries=(),
        *,
        new_stages=(),
        prerequisites=(),
        missing=(),
    ):
        membership = LocationScopeMembership(
            scope_key=self.SCOPE_KEY,
            import_versions=(),
            versioned_location_ids=(),
            legacy_location_ids=(),
            known_location_ids=tuple(
                sorted(
                    {
                        entry.location_id
                        for entry in entries
                    }
                    | set(missing)
                )
            ),
        )

        return LocationBatchPlan(
            scope_key=self.SCOPE_KEY,
            import_version=self.IMPORT_VERSION,
            membership=membership,
            entries=tuple(entries),
            new_stages=tuple(new_stages),
            external_prerequisites=tuple(
                prerequisites
            ),
            missing_location_ids=tuple(
                missing
            ),
        )

    @mock.patch.object(
        infrastructure_reconciliation_apply.frappe.db,
        "get_value",
    )
    def test_validated_import_batch_is_accepted(
        self,
        get_value,
    ):
        get_value.return_value = {
            "name": self.IMPORT_VERSION,
            "scope_key": self.SCOPE_KEY,
            "status": "Validated",
        }

        plan = self._batch()

        result = (
            infrastructure_reconciliation_apply
            ._validate_import_batch(
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

        self.assertEqual(
            result["status"],
            "Validated",
        )

    @mock.patch.object(
        infrastructure_reconciliation_apply.frappe.db,
        "get_value",
    )
    def test_non_validated_import_batch_is_refused(
        self,
        get_value,
    ):
        get_value.return_value = {
            "name": self.IMPORT_VERSION,
            "scope_key": self.SCOPE_KEY,
            "status": "Draft",
        }

        with self.assertRaisesRegex(
            ValueError,
            "must be Validated before apply",
        ):
            (
                infrastructure_reconciliation_apply
                ._validate_import_batch(
                    self._batch()
                )
            )

    @mock.patch.object(
        infrastructure_reconciliation_apply,
        "get_stored_location_state",
    )
    def test_stale_batch_plan_is_refused(
        self,
        get_stored,
    ):
        entry = self._entry(
            "kmz001",
            "UNCHANGED",
            location_name="Office",
        )

        get_stored.return_value = self._stored(
            location_name="Office",
            custom_lifecycle_state="Planned",
        )

        with self.assertRaisesRegex(
            ValueError,
            "batch plan is stale",
        ):
            (
                infrastructure_reconciliation_apply
                ._refresh_entry_plan(
                    entry,
                    self.IMPORT_VERSION,
                )
            )

    def test_unsupported_apply_policies_are_refused(
        self,
    ):
        cases = (
            (
                "existing geometry",
                self._entry(
                    "kmz001",
                    "CHANGED",
                    changes=(
                        LocationFieldChange(
                            fieldname="location",
                            stored_value=None,
                            desired_value=(
                                '{"type":"FeatureCollection",'
                                '"features":[]}'
                            ),
                        ),
                    ),
                    location=(
                        '{"type":"FeatureCollection",'
                        '"features":[]}'
                    ),
                ),
                "does not yet support existing changes",
            ),
            (
                "existing is_group",
                self._entry(
                    "kmz002",
                    "CHANGED",
                    changes=(
                        LocationFieldChange(
                            fieldname="is_group",
                            stored_value=0,
                            desired_value=1,
                        ),
                    ),
                    is_group=1,
                ),
                "does not yet support existing changes",
            ),
            (
                "parent plus ordinary",
                self._entry(
                    "kmz003",
                    "CHANGED",
                    changes=(
                        LocationFieldChange(
                            fieldname="parent_location",
                            stored_value=(
                                "Boschendal - Buildings"
                            ),
                            desired_value=(
                                "Boschendal - Other"
                            ),
                        ),
                        LocationFieldChange(
                            fieldname=(
                                "custom_lifecycle_state"
                            ),
                            stored_value=None,
                            desired_value="Planned",
                        ),
                    ),
                    parent_location=(
                        "Boschendal - Other"
                    ),
                    custom_lifecycle_state="Planned",
                ),
                "parent move must be the only",
            ),
            (
                "NEW geometry",
                self._entry(
                    "kmz004",
                    "NEW",
                    location=(
                        '{"type":"FeatureCollection",'
                        '"features":[]}'
                    ),
                ),
                "NEW geometry is not yet supported",
            ),
        )

        for label, entry, message in cases:
            with self.subTest(
                case=label
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    message,
                ):
                    (
                        infrastructure_reconciliation_apply
                        ._validate_apply_policy(
                            self._batch(
                                entries=(
                                    entry,
                                )
                            )
                        )
                    )

    @mock.patch.object(
        infrastructure_reconciliation_apply.frappe.db,
        "set_value",
    )
    def test_new_v2_fields_write_semantics_and_provenance(
        self,
        set_value,
    ):
        entry = self._entry(
            "kmz-new",
            "NEW",
            location_name="New Location",
            custom_lifecycle_state="Planned",
            custom_infrastructure_class="Fibre",
        )

        (
            infrastructure_reconciliation_apply
            ._apply_new_v2_fields(
                entry
            )
        )

        set_value.assert_called_once_with(
            "Location",
            "kmz-new",
            {
                "custom_infrastructure_class":
                    "Fibre",
                "custom_lifecycle_state":
                    "Planned",
                "custom_customer_visibility":
                    "Customer-safe",
                "custom_ticket_selectability":
                    "Selectable",
                "custom_first_seen_import":
                    self.IMPORT_VERSION,
                "custom_last_seen_import":
                    self.IMPORT_VERSION,
                "custom_last_changed_import":
                    self.IMPORT_VERSION,
            },
            update_modified=False,
        )

    @mock.patch.object(
        infrastructure_reconciliation_apply,
        "apply_existing_location_plan",
    )
    @mock.patch.object(
        infrastructure_reconciliation_apply,
        "apply_existing_location_parent_move",
    )
    def test_parent_move_dispatches_tree_then_provenance(
        self,
        parent_move,
        existing_writer,
    ):
        change = LocationFieldChange(
            fieldname="parent_location",
            stored_value="Boschendal - Buildings",
            desired_value="Boschendal - Other",
        )

        entry = self._entry(
            "kmz001",
            "CHANGED",
            changes=(
                change,
            ),
            parent_location="Boschendal - Other",
        )

        stored = self._stored(
            parent_location="Boschendal - Buildings",
        )

        fresh_plan = entry.database_plan

        (
            infrastructure_reconciliation_apply
            ._apply_existing_entries(
                self._batch(
                    entries=(
                        entry,
                    )
                ),
                {
                    "kmz001": (
                        stored,
                        fresh_plan,
                    ),
                },
            )
        )

        parent_move.assert_called_once_with(
            "kmz001",
            stored,
            fresh_plan,
        )

        existing_writer.assert_called_once()

        (
            writer_location_id,
            writer_stored,
            provenance_plan,
        ) = existing_writer.call_args.args

        self.assertEqual(
            writer_location_id,
            "kmz001",
        )

        self.assertIs(
            writer_stored,
            stored,
        )

        self.assertEqual(
            provenance_plan
            .reconciliation
            .state,
            "UNCHANGED",
        )

        self.assertEqual(
            provenance_plan
            .reconciliation
            .changes,
            (),
        )

        self.assertEqual(
            provenance_plan.provenance,
            fresh_plan.provenance,
        )

    @mock.patch.object(
        infrastructure_reconciliation_apply.frappe.db,
        "get_value",
    )
    def test_missing_location_cannot_be_marked_seen(
        self,
        get_value,
    ):
        plan = self._batch(
            missing=(
                "kmz-missing",
            )
        )

        get_value.return_value = (
            self.IMPORT_VERSION
        )

        with self.assertRaisesRegex(
            ValueError,
            "incorrectly marked seen",
        ):
            (
                infrastructure_reconciliation_apply
                ._verify_missing_not_seen(
                    plan
                )
            )

    @mock.patch.object(
        infrastructure_reconciliation_apply,
        "now_datetime",
    )
    @mock.patch.object(
        infrastructure_reconciliation_apply.frappe.db,
        "set_value",
    )
    def test_import_is_marked_applied_inside_batch(
        self,
        set_value,
        now_datetime,
    ):
        timestamp = "2026-09-23 16:30:00"
        now_datetime.return_value = timestamp

        plan = self._batch(
            entries=(
                self._entry(
                    "kmz001",
                    "UNCHANGED",
                ),
                self._entry(
                    "kmz002",
                    "CHANGED",
                    changes=(
                        LocationFieldChange(
                            fieldname=(
                                "custom_lifecycle_state"
                            ),
                            stored_value=None,
                            desired_value="Planned",
                        ),
                    ),
                    custom_lifecycle_state="Planned",
                ),
            )
        )

        (
            infrastructure_reconciliation_apply
            ._mark_import_applied(
                plan
            )
        )

        set_value.assert_called_once_with(
            "TELECTRO Infrastructure Import",
            self.IMPORT_VERSION,
            {
                "status": "Applied",
                "imported_on": timestamp,
                "location_count": 2,
            },
            update_modified=False,
        )

    def test_successful_mixed_batch_commits_once(
        self,
    ):
        new_entry = self._entry(
            "kmz-new",
            "NEW",
            location_name="New",
        )

        unchanged_entry = self._entry(
            "kmz-unchanged",
            "UNCHANGED",
            location_name="Unchanged",
        )

        changed_entry = self._entry(
            "kmz-changed",
            "CHANGED",
            changes=(
                LocationFieldChange(
                    fieldname=(
                        "custom_lifecycle_state"
                    ),
                    stored_value=None,
                    desired_value="Planned",
                ),
            ),
            location_name="Changed",
            custom_lifecycle_state="Planned",
        )

        parent_entry = self._entry(
            "kmz-parent-move",
            "CHANGED",
            changes=(
                LocationFieldChange(
                    fieldname="parent_location",
                    stored_value=(
                        "Boschendal - Buildings"
                    ),
                    desired_value=(
                        "Boschendal - Other"
                    ),
                ),
            ),
            location_name="Moved",
            parent_location="Boschendal - Other",
        )

        plan = self._batch(
            entries=(
                new_entry,
                unchanged_entry,
                changed_entry,
                parent_entry,
            ),
            new_stages=(
                (
                    mock.sentinel.release_row,
                ),
            ),
            prerequisites=(
                "Boschendal",
            ),
            missing=(
                "kmz-missing",
            ),
        )

        with (
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_validate_import_batch",
            ) as validate_batch,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_validate_apply_policy",
            ) as validate_policy,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_refresh_batch_plan",
                return_value={},
            ) as refresh,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "apply_release_stages",
                return_value={
                    "inserted_count": 1,
                },
            ) as apply_new,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_apply_new_v2_fields",
            ) as apply_new_fields,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_apply_existing_entries",
            ) as apply_existing,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "verify_release_postflight",
            ) as verify_new,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_verify_entry",
            ) as verify_entry,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_verify_missing_not_seen",
            ) as verify_missing,
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_mark_import_applied",
            ) as mark_applied,
            mock.patch.object(
                infrastructure_reconciliation_apply.frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_apply.frappe.db,
                "rollback",
            ) as rollback,
        ):
            result = (
                infrastructure_reconciliation_apply
                .run_location_batch_apply(
                    plan,
                    expected_site=(
                        infrastructure_reconciliation_apply
                        .frappe.local.site
                    ),
                    commit=1,
                )
            )

        validate_batch.assert_called_once_with(
            plan
        )

        validate_policy.assert_called_once_with(
            plan
        )

        refresh.assert_called_once_with(
            plan
        )

        apply_new.assert_called_once()

        apply_new_fields.assert_called_once_with(
            new_entry
        )

        apply_existing.assert_called_once_with(
            plan,
            {},
        )

        verify_new.assert_called_once()

        self.assertEqual(
            verify_entry.call_count,
            4,
        )

        verify_missing.assert_called_once_with(
            plan
        )

        mark_applied.assert_called_once_with(
            plan
        )

        commit.assert_called_once_with()
        rollback.assert_not_called()

        self.assertTrue(
            result.committed
        )

        self.assertEqual(
            result.new_count,
            1,
        )

        self.assertEqual(
            result.unchanged_count,
            1,
        )

        self.assertEqual(
            result.changed_count,
            2,
        )

        self.assertEqual(
            result.missing_count,
            1,
        )

        self.assertEqual(
            result.verified_count,
            4,
        )

    def test_new_insert_count_mismatch_rolls_back(
        self,
    ):
        new_entry = self._entry(
            "kmz-new",
            "NEW",
            location_name="New",
        )

        plan = self._batch(
            entries=(
                new_entry,
            ),
            new_stages=(
                (
                    mock.sentinel.release_row,
                ),
            ),
        )

        with (
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_validate_import_batch",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_validate_apply_policy",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_refresh_batch_plan",
                return_value={},
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "apply_release_stages",
                return_value={
                    "inserted_count": 0,
                },
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_apply_new_v2_fields",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_apply_existing_entries",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "verify_release_postflight",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_verify_entry",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_verify_missing_not_seen",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_mark_import_applied",
            ) as mark_applied,
            mock.patch.object(
                infrastructure_reconciliation_apply.frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_apply.frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "NEW insert count mismatch",
            ):
                (
                    infrastructure_reconciliation_apply
                    .run_location_batch_apply(
                        plan,
                        expected_site=(
                            infrastructure_reconciliation_apply
                            .frappe.local.site
                        ),
                        commit=1,
                    )
                )

        mark_applied.assert_not_called()
        commit.assert_not_called()
        rollback.assert_called_once_with()

    def test_writer_failure_rolls_back(
        self,
    ):
        entry = self._entry(
            "kmz001",
            "UNCHANGED",
        )

        plan = self._batch(
            entries=(
                entry,
            )
        )

        with (
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_validate_import_batch",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_validate_apply_policy",
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_refresh_batch_plan",
                return_value={},
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply,
                "_apply_existing_entries",
                side_effect=RuntimeError(
                    "writer failed"
                ),
            ),
            mock.patch.object(
                infrastructure_reconciliation_apply.frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                infrastructure_reconciliation_apply.frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "writer failed",
            ):
                (
                    infrastructure_reconciliation_apply
                    .run_location_batch_apply(
                        plan,
                        expected_site=(
                            infrastructure_reconciliation_apply
                            .frappe.local.site
                        ),
                        commit=1,
                    )
                )

        commit.assert_not_called()
        rollback.assert_called_once_with()

    @mock.patch.object(
        infrastructure_reconciliation_apply.frappe.db,
        "rollback",
    )
    @mock.patch.object(
        infrastructure_reconciliation_apply.frappe.db,
        "commit",
    )
    def test_commit_flag_is_mandatory(
        self,
        commit,
        rollback,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "without commit=1",
        ):
            (
                infrastructure_reconciliation_apply
                .run_location_batch_apply(
                    self._batch(),
                    expected_site=(
                        infrastructure_reconciliation_apply
                        .frappe.local.site
                    ),
                    commit=0,
                )
            )

        commit.assert_not_called()
        rollback.assert_not_called()
