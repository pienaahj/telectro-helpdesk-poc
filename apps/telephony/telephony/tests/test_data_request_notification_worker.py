"""Permanent transactional worker regressions.

All database transactions and dispatcher calls are mocked.
"""

import unittest

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from telephony import data_request_notification_worker as worker


NAME = "TDRN-ESC89-TEST"


class TestTransactionalWorker(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 11, 5, 12, 0)
        self.activation = self.now - timedelta(hours=2)

        self.row = {
            "name": NAME,
            "creation": self.now - timedelta(minutes=10),
            "delivery_state": "Pending",
            "attempt_count": 0,
            "last_attempt_on": None,
            "next_attempt_on": None,
            "in_app_state": "Pending",
            "notification_log": None,
            "email_state": "Pending",
            "email_queue": None,
        }

        self.db = Mock()
        self.db.sql.return_value = [self.row]

        self.conf = {
            worker.ACTIVATION_KEY: self.activation,
        }

        self.dispatch = Mock(return_value={
            "delivery_state": "Processing",
            "email_queue": "EQ-TEST",
            "notification_log": "NL-TEST",
        })

        patches = [
            patch.object(worker.frappe, "db", self.db),
            patch.object(worker.frappe, "conf", self.conf),
            patch.object(
                worker.frappe.utils,
                "get_datetime",
                side_effect=lambda value: value,
            ),
            patch.object(
                worker.frappe.utils,
                "now_datetime",
                return_value=self.now,
            ),
            patch.object(
                worker,
                "dispatch_notification_intent",
                self.dispatch,
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def process(self, **kwargs):
        kwargs.setdefault("now", self.now)
        return worker.process_due_notification_intent(
            NAME, **kwargs
        )

    def assert_not_processed(self):
        self.dispatch.assert_not_called()
        self.db.set_value.assert_not_called()
        self.db.commit.assert_not_called()

    def assert_row_locked(self):
        self.assertGreaterEqual(
            self.db.sql.call_count, 1
        )

        first = self.db.sql.call_args_list[0]

        self.assertIn("FOR UPDATE", first.args[0])
        self.assertEqual(first.args[1], (NAME,))
        self.assertTrue(first.kwargs["as_dict"])

    def test_disabled_fails_closed(self):
        self.conf.clear()

        result = self.process()

        self.assertEqual(result["state"], "disabled")
        self.db.sql.assert_not_called()
        self.assert_not_processed()

    def test_empty_identity_rejected(self):
        with self.assertRaises(ValueError):
            worker.process_due_notification_intent("")

        self.db.sql.assert_not_called()

    def test_timezone_aware_values_rejected(self):
        aware = self.now.replace(tzinfo=timezone.utc)

        with self.assertRaises(ValueError):
            self.process(now=aware)

        self.conf[worker.ACTIVATION_KEY] = aware

        with self.assertRaises(ValueError):
            self.process()

        self.db.sql.assert_not_called()

    def test_missing_intent_rolls_back(self):
        self.db.sql.return_value = []

        result = self.process()

        self.assertEqual(result["state"], "missing")
        self.db.rollback.assert_called_once()
        self.assert_not_processed()

    def test_creation_outside_activation_excluded(self):
        for created in (
            self.activation - timedelta(seconds=1),
            self.now + timedelta(seconds=1),
        ):
            with self.subTest(created=created):
                self.row["creation"] = created

                result = self.process()

                self.assertEqual(
                    result["state"], "not_due"
                )

        self.assert_not_processed()

    def test_pending_future_deadline_not_due(self):
        self.row["next_attempt_on"] = (
            self.now + timedelta(minutes=1)
        )

        self.assertEqual(
            self.process()["state"], "not_due"
        )

        self.assert_not_processed()

    def test_retry_requires_due_deadline(self):
        self.row["delivery_state"] = "Retry"

        self.assertEqual(
            self.process()["state"], "not_due"
        )

        self.row["next_attempt_on"] = self.now

        self.assertEqual(
            self.process()["state"], "Processing"
        )

        self.dispatch.assert_called_once_with(NAME)

    def test_processing_stale_recovery(self):
        self.row["delivery_state"] = "Processing"
        self.row["last_attempt_on"] = (
            self.now - timedelta(minutes=5)
        )

        self.assertEqual(
            self.process()["state"], "Processing"
        )

        self.dispatch.assert_called_once_with(NAME)

    def test_processing_respects_future_deadline(self):
        self.row["delivery_state"] = "Processing"
        self.row["next_attempt_on"] = (
            self.now + timedelta(seconds=1)
        )

        self.assertEqual(
            self.process()["state"], "not_due"
        )

        self.assert_not_processed()

    def test_terminal_states_not_due(self):
        for state in ("Complete", "Failed"):
            with self.subTest(state=state):
                self.row["delivery_state"] = state

                self.assertEqual(
                    self.process()["state"], "not_due"
                )

        self.assert_not_processed()

    def test_success_commits_processing_poll(self):
        self.row["attempt_count"] = 2

        result = self.process()

        self.assertEqual(result["state"], "Processing")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(
            result["next_attempt_on"],
            self.now + timedelta(minutes=5),
        )

        self.assert_row_locked()

        self.db.set_value.assert_called_once()

        fields = self.db.set_value.call_args.args[2]

        self.assertEqual(
            fields["delivery_state"], "Processing"
        )
        self.assertEqual(fields["attempt_count"], 2)

        self.db.commit.assert_called_once()
        self.db.rollback.assert_not_called()

    def test_success_commits_complete(self):
        self.dispatch.return_value["delivery_state"] = (
            "Complete"
        )

        result = self.process()

        self.assertEqual(result["state"], "Complete")
        self.assertIsNone(result["next_attempt_on"])

        self.db.commit.assert_called_once()
        self.db.rollback.assert_not_called()

    def test_native_failure_records_backoff(self):
        self.dispatch.return_value["delivery_state"] = (
            "Retry"
        )

        result = self.process()

        self.assertEqual(result["state"], "Retry")
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["next_attempt_on"],
            self.now + timedelta(minutes=1),
        )

        fields = self.db.set_value.call_args.args[2]

        self.assertEqual(
            fields["last_error"],
            "NATIVE_EMAIL_FAILURE",
        )

        self.db.commit.assert_called_once()

    def test_exception_rolls_back_then_records_retry(self):
        self.dispatch.side_effect = RuntimeError(
            "Simulated delivery failure"
        )

        result = self.process()

        self.assertEqual(result["state"], "Retry")
        self.assertEqual(
            result["failure_code"], "DISPATCH_ERROR"
        )
        self.assertEqual(result["attempt_count"], 1)

        self.assertEqual(self.db.sql.call_count, 2)
        self.db.rollback.assert_called_once()
        self.db.commit.assert_called_once()

        operations = [
            entry[0] for entry in self.db.method_calls
        ]

        self.assertLess(
            operations.index("rollback"),
            operations.index("set_value"),
        )

    def test_revoked_permission_terminal(self):
        self.dispatch.side_effect = (
            worker.frappe.PermissionError(
                "Authorization revoked"
            )
        )

        result = self.process()

        self.assertEqual(result["state"], "Failed")
        self.assertEqual(
            result["failure_code"],
            "AUTHORIZATION_REVOKED",
        )
        self.assertIsNone(result["next_attempt_on"])

        self.db.rollback.assert_called_once()
        self.db.commit.assert_called_once()

    def test_concurrent_progress_not_overwritten(self):
        changed = dict(self.row)
        changed["attempt_count"] = 1

        self.db.sql.side_effect = [
            [self.row],
            [changed],
        ]

        self.dispatch.side_effect = RuntimeError(
            "Simulated worker failure"
        )

        result = self.process()

        self.assertEqual(result["state"], "superseded")

        self.assertEqual(self.db.rollback.call_count, 2)
        self.db.commit.assert_not_called()
        self.db.set_value.assert_not_called()

    def test_failure_recording_error_rolls_back(self):
        self.dispatch.side_effect = RuntimeError(
            "Delivery failed"
        )

        self.db.set_value.side_effect = RuntimeError(
            "Failure recording failed"
        )

        with self.assertRaisesRegex(
            RuntimeError, "Failure recording failed"
        ):
            self.process()

        self.assertEqual(self.db.rollback.call_count, 2)
        self.db.commit.assert_not_called()

    def test_lock_error_propagates(self):
        self.db.sql.side_effect = RuntimeError(
            "Database lock failed"
        )

        with self.assertRaisesRegex(
            RuntimeError, "Database lock failed"
        ):
            self.process()

        self.db.rollback.assert_called_once()
        self.assert_not_processed()

    def test_default_site_clock_used(self):
        result = worker.process_due_notification_intent(
            NAME
        )

        self.assertEqual(result["state"], "Processing")

        worker.frappe.utils.now_datetime.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
