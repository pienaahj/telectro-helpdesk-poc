import importlib
import sys
import unittest
from unittest import mock

from telephony.task_notification_policy import (
    task_notification_event_key,
)


class TestTaskNotificationLockingRead(unittest.TestCase):

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
            ticket="911",
            action="assignment",
            event_id="TODO-001",
            recipient="tech.alfa@local.test",
        )

        self.matching_row = {
            "event_key": self.key,
            "ticket": "911",
            "action": "assignment",
            "event_id": "TODO-001",
            "recipient": "tech.alfa@local.test",
        }

        self.frappe.db.exists.return_value = True

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

    def test_preexisting_event_uses_current_read(self):
        # A stale snapshot cannot see the committed row.
        # A locking read can.
        def lookup(*args, **kwargs):
            if kwargs.get("for_update") is True:
                return dict(self.matching_row)
            return None

        self.frappe.db.get_value.side_effect = lookup

        result = self.capture()

        self.assertFalse(result["created"])
        self.assertEqual(result["event_key"], self.key)

        self.frappe.db.get_value.assert_called_once()
        self.assertTrue(
            self.frappe.db.get_value.call_args.kwargs.get(
                "for_update"
            )
        )

    def test_duplicate_insert_uses_current_read(self):
        self.frappe.db.exists.side_effect = [
            False, True
        ]

        document = mock.MagicMock()
        document.insert.side_effect = (
            self.frappe.DuplicateEntryError(
                "Concurrent duplicate key"
            )
        )
        self.frappe.get_doc.return_value = document

        def lookup(*args, **kwargs):
            if kwargs.get("for_update") is True:
                return dict(self.matching_row)
            return None

        self.frappe.db.get_value.side_effect = lookup

        result = self.capture()

        self.assertFalse(result["created"])
        self.assertEqual(result["event_key"], self.key)

        self.assertTrue(
            self.frappe.db.get_value.call_args.kwargs.get(
                "for_update"
            )
        )

    def test_current_conflicting_identity_fails_closed(self):
        conflicting = dict(self.matching_row)
        conflicting["recipient"] = "tech.bravo@local.test"

        # Simulate an old matching snapshot and a newer
        # conflicting row visible to a locking read.
        def lookup(*args, **kwargs):
            if kwargs.get("for_update") is True:
                return conflicting
            return dict(self.matching_row)

        self.frappe.db.get_value.side_effect = lookup

        with self.assertRaises(ValueError):
            self.capture()

        self.frappe.get_doc.assert_not_called()

    def test_database_read_error_is_not_suppressed(self):
        self.frappe.db.get_value.side_effect = (
            RuntimeError("Database locking read failed")
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Database locking read failed",
        ):
            self.capture()

        self.frappe.db.commit.assert_not_called()
        self.frappe.sendmail.assert_not_called()
        self.frappe.enqueue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
