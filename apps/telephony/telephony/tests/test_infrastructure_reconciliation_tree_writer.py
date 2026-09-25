import unittest
from unittest import mock

from frappe.utils.nestedset import (
    NestedSetRecursionError,
)

from telephony.scripts.infrastructure_reconciliation import (
    plan_location_reconciliation,
)
from telephony.scripts.infrastructure_reconciliation_adapter import (
    LocationDatabaseReconciliationPlan,
    plan_location_provenance,
)
from telephony.scripts import (
    infrastructure_reconciliation_tree_writer,
)


class TestLocationV2ParentMoveWriter(
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
        import_version="BOSCHENDAL-KMZ-2026-02",
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

    def _doc(
        self,
        parent_location="Boschendal - Buildings",
    ):
        doc = mock.Mock()
        doc.get.side_effect = (
            lambda fieldname:
            parent_location
            if fieldname == "parent_location"
            else None
        )
        doc.old_parent = None
        doc.parent_location = parent_location
        return doc

    @mock.patch.object(
        infrastructure_reconciliation_tree_writer,
        "update_nsm",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "get_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe,
        "get_doc",
    )
    def test_parent_move_updates_parent_then_nested_set(
        self,
        get_doc,
        get_value,
        set_value,
        update_nsm,
    ):
        stored = self._stored()

        desired = self._desired(
            parent_location="Boschendal - Other",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
        )

        doc = self._doc()
        get_doc.return_value = doc

        parent_state = mock.Mock()
        parent_state.is_group = 1
        get_value.return_value = parent_state

        calls = mock.Mock()
        calls.attach_mock(
            set_value,
            "set_value",
        )
        calls.attach_mock(
            update_nsm,
            "update_nsm",
        )

        result = (
            infrastructure_reconciliation_tree_writer
            .apply_existing_location_parent_move(
                "kmz123",
                stored,
                plan,
            )
        )

        get_doc.assert_called_once_with(
            "Location",
            "kmz123",
        )

        get_value.assert_called_once_with(
            "Location",
            "Boschendal - Other",
            [
                "name",
                "is_group",
            ],
            as_dict=True,
        )

        self.assertEqual(
            doc.old_parent,
            "Boschendal - Buildings",
        )

        self.assertEqual(
            doc.parent_location,
            "Boschendal - Other",
        )

        set_value.assert_called_once_with(
            "Location",
            "kmz123",
            "parent_location",
            "Boschendal - Other",
            update_modified=False,
        )

        update_nsm.assert_called_once_with(
            doc
        )

        self.assertEqual(
            calls.mock_calls,
            [
                mock.call.set_value(
                    "Location",
                    "kmz123",
                    "parent_location",
                    "Boschendal - Other",
                    update_modified=False,
                ),
                mock.call.update_nsm(
                    doc
                ),
            ],
        )

        self.assertEqual(
            result.location_id,
            "kmz123",
        )

        self.assertEqual(
            result.old_parent,
            "Boschendal - Buildings",
        )

        self.assertEqual(
            result.new_parent,
            "Boschendal - Other",
        )

    @mock.patch.object(
        infrastructure_reconciliation_tree_writer,
        "update_nsm",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "get_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe,
        "get_doc",
    )
    def test_move_to_root_does_not_require_parent_lookup(
        self,
        get_doc,
        get_value,
        set_value,
        update_nsm,
    ):
        stored = self._stored()

        desired = self._desired(
            parent_location=None,
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
        )

        doc = self._doc()
        get_doc.return_value = doc

        result = (
            infrastructure_reconciliation_tree_writer
            .apply_existing_location_parent_move(
                "kmz123",
                stored,
                plan,
            )
        )

        get_value.assert_not_called()

        self.assertEqual(
            doc.old_parent,
            "Boschendal - Buildings",
        )

        self.assertEqual(
            doc.parent_location,
            "",
        )

        set_value.assert_called_once_with(
            "Location",
            "kmz123",
            "parent_location",
            "",
            update_modified=False,
        )

        update_nsm.assert_called_once_with(
            doc
        )

        self.assertIsNone(
            result.new_parent
        )

    @mock.patch.object(
        infrastructure_reconciliation_tree_writer,
        "update_nsm",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "get_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe,
        "get_doc",
    )
    def test_stale_live_parent_is_refused(
        self,
        get_doc,
        get_value,
        set_value,
        update_nsm,
    ):
        stored = self._stored()

        desired = self._desired(
            parent_location="Boschendal - Other",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
        )

        get_doc.return_value = self._doc(
            parent_location="Boschendal - Network Nodes",
        )

        with self.assertRaisesRegex(
            ValueError,
            "Stored Location parent is stale",
        ):
            (
                infrastructure_reconciliation_tree_writer
                .apply_existing_location_parent_move(
                    "kmz123",
                    stored,
                    plan,
                )
            )

        get_value.assert_not_called()
        set_value.assert_not_called()
        update_nsm.assert_not_called()

    @mock.patch.object(
        infrastructure_reconciliation_tree_writer,
        "update_nsm",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "get_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe,
        "get_doc",
    )
    def test_missing_target_parent_is_refused(
        self,
        get_doc,
        get_value,
        set_value,
        update_nsm,
    ):
        stored = self._stored()

        desired = self._desired(
            parent_location="Missing Parent",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
        )

        get_doc.return_value = self._doc()
        get_value.return_value = None

        with self.assertRaisesRegex(
            ValueError,
            "Target parent Location does not exist",
        ):
            (
                infrastructure_reconciliation_tree_writer
                .apply_existing_location_parent_move(
                    "kmz123",
                    stored,
                    plan,
                )
            )

        set_value.assert_not_called()
        update_nsm.assert_not_called()

    @mock.patch.object(
        infrastructure_reconciliation_tree_writer,
        "update_nsm",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "get_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe,
        "get_doc",
    )
    def test_non_group_target_parent_is_refused(
        self,
        get_doc,
        get_value,
        set_value,
        update_nsm,
    ):
        stored = self._stored()

        desired = self._desired(
            parent_location="Leaf Location",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
        )

        get_doc.return_value = self._doc()

        parent_state = mock.Mock()
        parent_state.is_group = 0
        get_value.return_value = parent_state

        with self.assertRaisesRegex(
            ValueError,
            "Target parent Location is not a group",
        ):
            (
                infrastructure_reconciliation_tree_writer
                .apply_existing_location_parent_move(
                    "kmz123",
                    stored,
                    plan,
                )
            )

        set_value.assert_not_called()
        update_nsm.assert_not_called()

    @mock.patch.object(
        infrastructure_reconciliation_tree_writer,
        "update_nsm",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "get_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe,
        "get_doc",
    )
    def test_additional_changed_fields_are_refused(
        self,
        get_doc,
        get_value,
        set_value,
        update_nsm,
    ):
        stored = self._stored(
            custom_lifecycle_state=None,
        )

        desired = self._desired(
            parent_location="Boschendal - Other",
            custom_lifecycle_state="Planned",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
        )

        with self.assertRaisesRegex(
            ValueError,
            "does not yet support additional changed fields",
        ):
            (
                infrastructure_reconciliation_tree_writer
                .apply_existing_location_parent_move(
                    "kmz123",
                    stored,
                    plan,
                )
            )

        get_doc.assert_not_called()
        get_value.assert_not_called()
        set_value.assert_not_called()
        update_nsm.assert_not_called()

    @mock.patch.object(
        infrastructure_reconciliation_tree_writer,
        "update_nsm",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "get_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe,
        "get_doc",
    )
    def test_nested_set_recursion_error_is_propagated(
        self,
        get_doc,
        get_value,
        set_value,
        update_nsm,
    ):
        stored = self._stored()

        desired = self._desired(
            parent_location="Boschendal - Other",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
        )

        doc = self._doc()
        get_doc.return_value = doc

        parent_state = mock.Mock()
        parent_state.is_group = 1
        get_value.return_value = parent_state

        update_nsm.side_effect = (
            NestedSetRecursionError(
                "recursive move rejected"
            )
        )

        with self.assertRaises(
            NestedSetRecursionError
        ):
            (
                infrastructure_reconciliation_tree_writer
                .apply_existing_location_parent_move(
                    "kmz123",
                    stored,
                    plan,
                )
            )

        set_value.assert_called_once()
        update_nsm.assert_called_once_with(
            doc
        )

    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "rollback",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "commit",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer,
        "update_nsm",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "set_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe.db,
        "get_value",
    )
    @mock.patch.object(
        infrastructure_reconciliation_tree_writer.frappe,
        "get_doc",
    )
    def test_parent_move_writer_does_not_own_transaction(
        self,
        get_doc,
        get_value,
        set_value,
        update_nsm,
        commit,
        rollback,
    ):
        stored = self._stored()

        desired = self._desired(
            parent_location="Boschendal - Other",
        )

        plan = self._plan(
            "kmz123",
            desired,
            stored,
        )

        doc = self._doc()
        get_doc.return_value = doc

        parent_state = mock.Mock()
        parent_state.is_group = 1
        get_value.return_value = parent_state

        (
            infrastructure_reconciliation_tree_writer
            .apply_existing_location_parent_move(
                "kmz123",
                stored,
                plan,
            )
        )

        set_value.assert_called_once()
        update_nsm.assert_called_once()

        commit.assert_not_called()
        rollback.assert_not_called()
