import importlib
import sys
import unittest
from unittest import mock

from telephony.task_notification_policy import (
    task_notification_event_key,
)


class TestTaskNotificationStaleDuplicate(unittest.TestCase):

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

        self.event_key = task_notification_event_key(
            ticket="911",
            action="assignment",
            event_id="TODO-001",
            recipient="tech.alfa@local.test",
        )

        self.stored_row = {
            "event_key": self.event_key,
            "ticket": "911",
            "action": "assignment",
            "event_id": "TODO-001",
            "recipient": "tech.alfa@local.test",
        }

        # Both ordinary existence checks see an old snapshot.
        self.frappe.db.exists.return_value = False

        self.frappe.db.get_value.side_effect = (
            self.current_read
        )

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

    def current_read(self, *args, **kwargs):
        if kwargs.get("for_update") is True:
            return self.stored_row
        return None

    def simulate_collision(self, exception_type):
        document = mock.MagicMock()

        document.insert.side_effect = exception_type(
            "Concurrent notification key collision"
        )

        self.frappe.get_doc.return_value = document

    def capture(self):
        return self.outbox.capture_task_notification_intent(
            **self.arguments
        )

    def assert_current_read(self):
        self.frappe.db.get_value.assert_called_once()

        self.assertTrue(
            self.frappe.db.get_value.call_args.kwargs.get(
                "for_update"
            )
        )

    def test_stale_snapshot_primary_duplicate_is_idempotent(self):
        self.simulate_collision(
            self.frappe.DuplicateEntryError
        )

        result = self.capture()

        self.assertFalse(result["created"])
        self.assertEqual(
            result["event_key"], self.event_key
        )

        self.assert_current_read()

    def test_stale_snapshot_unique_duplicate_is_idempotent(self):
        self.simulate_collision(
            self.frappe.UniqueValidationError
        )

        result = self.capture()

        self.assertFalse(result["created"])
        self.assertEqual(
            result["event_key"], self.event_key
        )

        self.assert_current_read()

    def test_conflicting_current_identity_propagates(self):
        conflicting = dict(self.stored_row)
        conflicting["ticket"] = "912"

        self.stored_row = conflicting

        self.simulate_collision(
            self.frappe.DuplicateEntryError
        )

        with self.assertRaises(
            self.frappe.DuplicateEntryError
        ):
            self.capture()

        # An exception is justified only after checking
        # the actual current identity.
        self.assert_current_read()

    def test_missing_current_row_propagates(self):
        self.stored_row = None

        self.simulate_collision(
            self.frappe.UniqueValidationError
        )

        with self.assertRaises(
            self.frappe.UniqueValidationError
        ):
            self.capture()

        self.assert_current_read()

    def test_no_commit_or_delivery_on_any_path(self):
        for exception_type in (
            self.frappe.DuplicateEntryError,
            self.frappe.UniqueValidationError,
        ):
            with self.subTest(exception_type=exception_type):
                self.simulate_collision(exception_type)

                try:
                    self.capture()
                except exception_type:
                    pass

        self.frappe.db.commit.assert_not_called()
        self.frappe.sendmail.assert_not_called()
        self.frappe.enqueue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
