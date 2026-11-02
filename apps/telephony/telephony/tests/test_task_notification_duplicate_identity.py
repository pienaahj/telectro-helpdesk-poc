import importlib
import sys
import unittest
from unittest import mock

from telephony.task_notification_policy import (
    task_notification_event_key,
)


class TestTaskNotificationDuplicateIdentity(unittest.TestCase):

    def setUp(self):
        self.frappe = mock.MagicMock()

        class DuplicateEntryError(Exception):
            pass

        class UniqueValidationError(Exception):
            pass

        self.frappe.DuplicateEntryError = DuplicateEntryError
        self.frappe.UniqueValidationError = UniqueValidationError

        self.arguments = {
            "ticket": "911",
            "action": "assignment",
            "event_id": "TODO-001",
            "recipient": "tech.alfa@local.test",
            "actor_user": "supervisor@local.test",
            "note": "Please investigate",
        }

        self.key = task_notification_event_key(
            **{
                name: self.arguments[name]
                for name in (
                    "ticket", "action",
                    "event_id", "recipient",
                )
            }
        )

        self.row = {
            "name": self.key,
            "event_key": self.key,
            "ticket": "911",
            "action": "assignment",
            "event_id": "TODO-001",
            "recipient": "tech.alfa@local.test",
        }

        self.frappe.db.get_value.return_value = dict(self.row)

        sys.modules.pop(
            "telephony.task_notification_outbox", None
        )

        with mock.patch.dict(
            sys.modules, {"frappe": self.frappe}
        ):
            self.outbox = importlib.import_module(
                "telephony.task_notification_outbox"
            )

    def tearDown(self):
        sys.modules.pop(
            "telephony.task_notification_outbox", None
        )

    def capture(self):
        return self.outbox.capture_task_notification_intent(
            **self.arguments
        )

    def simulate_collision(self, exception_type, row=None):
        self.frappe.db.exists.side_effect = [False, True]

        if row is not None:
            self.frappe.db.get_value.return_value = row

        document = mock.MagicMock()
        document.insert.side_effect = exception_type(
            "Duplicate database key"
        )
        self.frappe.get_doc.return_value = document

    def test_same_event_unique_key_is_idempotent(self):
        self.simulate_collision(
            self.frappe.UniqueValidationError
        )

        result = self.capture()

        self.assertFalse(result["created"])
        self.assertEqual(result["event_key"], self.key)

        self.frappe.db.get_value.assert_called_once()
        self.frappe.db.commit.assert_not_called()
        self.frappe.sendmail.assert_not_called()

    def test_same_event_primary_key_verifies_stored_row(self):
        self.simulate_collision(
            self.frappe.DuplicateEntryError
        )

        result = self.capture()

        self.assertFalse(result["created"])
        self.assertEqual(result["event_key"], self.key)

        # Merely finding an existing name is insufficient.
        self.frappe.db.get_value.assert_called_once()

    def test_primary_key_identity_mismatch_is_not_suppressed(self):
        conflicting = dict(self.row)
        conflicting["recipient"] = "tech.bravo@local.test"

        self.simulate_collision(
            self.frappe.DuplicateEntryError,
            conflicting,
        )

        with self.assertRaises(
            self.frappe.DuplicateEntryError
        ):
            self.capture()

    def test_preexisting_key_identity_mismatch_fails_closed(self):
        conflicting = dict(self.row)
        conflicting["event_id"] = "TODO-DIFFERENT"

        self.frappe.db.exists.return_value = True
        self.frappe.db.get_value.return_value = conflicting

        with self.assertRaises(ValueError):
            self.capture()

        self.frappe.get_doc.assert_not_called()

    def test_unrelated_unique_key_conflict_propagates(self):
        conflicting = dict(self.row)
        conflicting["ticket"] = "912"

        self.simulate_collision(
            self.frappe.UniqueValidationError,
            conflicting,
        )

        with self.assertRaises(
            self.frappe.UniqueValidationError
        ):
            self.capture()

    def test_missing_collision_row_propagates(self):
        self.simulate_collision(
            self.frappe.UniqueValidationError
        )

        self.frappe.db.exists.side_effect = [False, False]
        self.frappe.db.get_value.return_value = None

        with self.assertRaises(
            self.frappe.UniqueValidationError
        ):
            self.capture()

        self.frappe.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
