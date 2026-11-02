import importlib
import sys
import unittest
from unittest import mock


class TestTaskNotificationCaptureBoundary(unittest.TestCase):

    def setUp(self):
        self.frappe = mock.MagicMock()

        sys.modules.pop(
            "telephony.task_notification_outbox", None
        )

        with mock.patch.dict(
            sys.modules, {"frappe": self.frappe}
        ):
            self.outbox = importlib.import_module(
                "telephony.task_notification_outbox"
            )

        self.arguments = {
            "ticket": "911",
            "action": "assignment",
            "event_id": "TODO-001",
            "recipient": "tech.alfa@local.test",
            "actor_user": "supervisor@local.test",
            "note": "Please investigate",
        }

    def tearDown(self):
        sys.modules.pop(
            "telephony.task_notification_outbox", None
        )

    def capture(self):
        return (
            self.outbox.capture_task_notification_intent_safely(
                **self.arguments
            )
        )

    def savepoint_name(self):
        self.frappe.db.savepoint.assert_called_once()
        args, kwargs = self.frappe.db.savepoint.call_args

        self.assertFalse(kwargs)
        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], str))
        self.assertTrue(args[0])

        return args[0]

    def test_successful_capture_preserves_transaction(self):
        response = {
            "created": True,
            "event_key": "a" * 64,
        }

        with mock.patch.object(
            self.outbox,
            "capture_task_notification_intent",
            return_value=response,
        ) as capture:
            result = self.capture()

        self.assertTrue(result["ok"])
        self.assertTrue(result["created"])
        self.assertEqual(result["event_key"], "a" * 64)

        capture.assert_called_once_with(**self.arguments)
        self.savepoint_name()

        self.frappe.db.rollback.assert_not_called()
        self.frappe.db.commit.assert_not_called()
        self.frappe.sendmail.assert_not_called()
        self.frappe.enqueue.assert_not_called()

    def test_duplicate_capture_is_not_a_failure(self):
        response = {
            "created": False,
            "event_key": "a" * 64,
        }

        with mock.patch.object(
            self.outbox,
            "capture_task_notification_intent",
            return_value=response,
        ):
            result = self.capture()

        self.assertTrue(result["ok"])
        self.assertFalse(result["created"])

        self.savepoint_name()
        self.frappe.db.rollback.assert_not_called()

    def test_capture_exception_rolls_back_savepoint(self):
        with mock.patch.object(
            self.outbox,
            "capture_task_notification_intent",
            side_effect=RuntimeError("Capture failed"),
        ):
            result = self.capture()

        self.assertFalse(result["ok"])
        self.assertFalse(result["created"])

        name = self.savepoint_name()

        self.frappe.db.rollback.assert_called_once_with(
            save_point=name
        )

        self.frappe.logger.return_value.exception.assert_called_once()

        self.frappe.db.commit.assert_not_called()
        self.frappe.sendmail.assert_not_called()
        self.frappe.enqueue.assert_not_called()

    def test_savepoint_failure_skips_capture(self):
        self.frappe.db.savepoint.side_effect = RuntimeError(
            "Savepoint unavailable"
        )

        with mock.patch.object(
            self.outbox,
            "capture_task_notification_intent",
        ) as capture:
            result = self.capture()

        self.assertFalse(result["ok"])
        self.assertFalse(result["created"])

        capture.assert_not_called()
        self.frappe.db.rollback.assert_not_called()
        self.frappe.db.commit.assert_not_called()

    def test_failed_rollback_propagates(self):
        self.frappe.db.rollback.side_effect = RuntimeError(
            "Cannot restore savepoint"
        )

        with mock.patch.object(
            self.outbox,
            "capture_task_notification_intent",
            side_effect=RuntimeError("Insert failed"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "Cannot restore savepoint"
            ):
                self.capture()

        self.savepoint_name()
        self.frappe.db.rollback.assert_called_once()
        self.frappe.db.commit.assert_not_called()

    def test_logging_failure_does_not_break_safe_rollback(self):
        self.frappe.logger.return_value.exception.side_effect = (
            RuntimeError("Logging unavailable")
        )

        with mock.patch.object(
            self.outbox,
            "capture_task_notification_intent",
            side_effect=RuntimeError("Insert failed"),
        ):
            result = self.capture()

        self.assertFalse(result["ok"])
        self.assertFalse(result["created"])

        name = self.savepoint_name()

        self.frappe.db.rollback.assert_called_once_with(
            save_point=name
        )

        self.frappe.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
