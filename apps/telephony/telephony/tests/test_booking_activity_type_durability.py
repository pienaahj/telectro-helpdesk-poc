import runpy
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

from telephony.setup import booking_activity_type_durability
from telephony.time_booking_activity_types import BOOKING_ACTIVITY_TYPES


class TestBookingActivityTypeDurability(unittest.TestCase):
    def setUp(self):
        self.records = {}
        self.frappe = Mock()
        self.frappe.db.exists.side_effect = self.exists
        self.frappe.get_doc.side_effect = self.new_document
        patcher = patch.object(booking_activity_type_durability, "frappe", self.frappe)
        patcher.start()
        self.addCleanup(patcher.stop)

    def exists(self, doctype, name):
        self.assertEqual(doctype, "Activity Type")
        return name in self.records

    def new_document(self, values):
        self.assertEqual(values["doctype"], "Activity Type")
        self.assertEqual(values["disabled"], 0)

        def insert(*, ignore_permissions):
            self.assertTrue(ignore_permissions)
            name = values["activity_type"]
            self.assertNotIn(name, self.records)
            self.records[name] = dict(values)

        return Mock(insert=Mock(side_effect=insert))

    def test_catalog_matches_frozen_order_and_spelling(self):
        self.assertEqual(
            BOOKING_ACTIVITY_TYPES,
            (
                "Fault Finding & Diagnosis",
                "Installation & Configuration",
                "Repair & Maintenance",
                "Provisioning & Activation",
                "Testing & Verification",
                "Site Survey & Technical Assessment",
                "Technical Planning & Documentation",
                "Technical Support & Communication",
                "Travel",
                "Technical Training",
                "Other Technical Work",
            ),
        )

    def test_hook_is_registered_once(self):
        frappe = ModuleType("frappe")
        frappe.conf = {}
        hooks_path = Path(__file__).resolve().parents[1] / "hooks.py"
        with patch.dict(sys.modules, {"frappe": frappe}):
            hooks = runpy.run_path(str(hooks_path))

        self.assertEqual(
            hooks["after_migrate"].count(
                "telephony.setup.booking_activity_type_durability.after_migrate"
            ),
            1,
        )

    def test_provisioning_is_repeatable(self):
        self.assertEqual(
            booking_activity_type_durability.after_migrate(),
            list(BOOKING_ACTIVITY_TYPES),
        )
        state = deepcopy(self.records)
        self.frappe.get_doc.reset_mock()

        self.assertEqual(booking_activity_type_durability.after_migrate(), [])
        self.assertEqual(self.records, state)
        self.frappe.get_doc.assert_not_called()

    def test_provisioning_preserves_existing_classifications_and_settings(self):
        self.records.update({
            "Execution": {"activity_type": "Execution", "disabled": 0, "costing_rate": 50},
            "Planning": {"activity_type": "Planning", "disabled": 1},
            "Travel": {"activity_type": "Travel", "disabled": 1, "billing_rate": 150},
        })
        existing = deepcopy(self.records)

        self.assertEqual(
            booking_activity_type_durability.after_migrate(),
            [name for name in BOOKING_ACTIVITY_TYPES if name != "Travel"],
        )
        self.assertEqual({name: self.records[name] for name in existing}, existing)
        self.frappe.db.set_value.assert_not_called()
        self.frappe.delete_doc.assert_not_called()
        self.frappe.rename_doc.assert_not_called()
