"""Regressions for durable unhandled notification failure backoff.

All database operations are mocked. No delivery is performed.
"""

import unittest

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, call, patch

from telephony import data_request_notification_worker as worker


class TestUnhandledNotificationFailure(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 11, 5, 15, 0, 0)
        self.activation = datetime(2026, 11, 5, 14, 0, 0)

        self.conf = {
            worker.ACTIVATION_KEY: "2026-11-05 14:00:00",
        }

        self.db = Mock()
        self.row = {"attempt_count": 0}

        self.plan = {
            "delivery_state": "Retry",
            "attempt_count": 1,
            "next_attempt_on": self.now + timedelta(minutes=1),
        }

        patches = [
            patch.object(worker.frappe, "conf", self.conf),
            patch.object(worker.frappe, "db", self.db),
            patch.object(
                worker,
                "_lock_intent",
                return_value=self.row,
            ),
            patch.object(
                worker,
                "_due",
                return_value=True,
            ),
            patch.object(
                worker,
                "plan_worker_failure",
                return_value=self.plan,
            ),
            patch.object(
                worker.frappe.utils,
                "now_datetime",
                return_value=self.now,
            ),
        ]

        started = [item.start() for item in patches]

        for item in patches:
            self.addCleanup(item.stop)

        (
            _,
            _,
            self.lock,
            self.due,
            self.policy,
            self.clock,
        ) = started

    def record(self, name="ESC123-INTENT", **kwargs):
        return worker.record_unhandled_notification_failure(
            name,
            **kwargs,
        )

    def test_due_intent_persists_retry(self):
        result = self.record(now=self.now)

        self.lock.assert_called_once_with("ESC123-INTENT")
        self.due.assert_called_once_with(
            self.row,
            self.activation,
            self.now,
        )

        self.policy.assert_called_once_with(
            now=self.now,
            attempt_count=0,
            failure_code="DISPATCH_ERROR",
        )

        self.db.set_value.assert_called_once_with(
            worker.DOCTYPE,
            "ESC123-INTENT",
            self.plan,
        )

        self.db.commit.assert_called_once_with()
        self.db.rollback.assert_not_called()

        self.assertEqual(result["state"], "Retry")
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["next_attempt_on"],
            self.plan["next_attempt_on"],
        )
        self.assertEqual(
            result["failure_code"],
            "DISPATCH_ERROR",
        )

    def test_existing_attempt_count_forwarded(self):
        self.row["attempt_count"] = 3

        self.record(now=self.now)

        self.policy.assert_called_once_with(
            now=self.now,
            attempt_count=3,
            failure_code="DISPATCH_ERROR",
        )

    def test_terminal_failed_state_persists(self):
        self.row["attempt_count"] = 4

        self.plan = {
            "delivery_state": "Failed",
            "attempt_count": 5,
            "next_attempt_on": None,
        }

        self.policy.return_value = self.plan

        result = self.record(now=self.now)

        self.assertEqual(result["state"], "Failed")
        self.assertEqual(result["attempt_count"], 5)
        self.assertIsNone(result["next_attempt_on"])

        self.db.set_value.assert_called_once_with(
            worker.DOCTYPE,
            "ESC123-INTENT",
            self.plan,
        )

        self.db.commit.assert_called_once_with()

    def test_disabled_activation_prevents_work(self):
        self.conf.clear()

        result = self.record(now=self.now)

        self.assertEqual(result["state"], "disabled")

        self.lock.assert_not_called()
        self.policy.assert_not_called()
        self.db.set_value.assert_not_called()
        self.db.commit.assert_not_called()

    def test_empty_identity_rejected(self):
        for name in ("", "   ", None):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.record(name, now=self.now)

        self.lock.assert_not_called()
        self.db.commit.assert_not_called()

    def test_missing_intent_does_not_write(self):
        self.lock.return_value = None

        result = self.record(now=self.now)

        self.assertEqual(result["state"], "missing")

        self.due.assert_not_called()
        self.policy.assert_not_called()
        self.db.set_value.assert_not_called()
        self.db.commit.assert_not_called()
        self.db.rollback.assert_called_once_with()

    def test_superseded_intent_is_not_overwritten(self):
        self.due.return_value = False

        result = self.record(now=self.now)

        self.assertEqual(result["state"], "superseded")

        self.policy.assert_not_called()
        self.db.set_value.assert_not_called()
        self.db.commit.assert_not_called()
        self.db.rollback.assert_called_once_with()

    def test_identity_is_normalized(self):
        result = self.record("  ESC123-INTENT  ", now=self.now)

        self.assertEqual(result["intent"], "ESC123-INTENT")
        self.lock.assert_called_once_with("ESC123-INTENT")

    def test_default_clock_is_used(self):
        self.record()

        self.clock.assert_called_once_with()

        self.policy.assert_called_once_with(
            now=self.now,
            attempt_count=0,
            failure_code="DISPATCH_ERROR",
        )

    def test_timezone_aware_clock_rejected(self):
        aware = self.now.replace(tzinfo=timezone.utc)

        with self.assertRaises(ValueError):
            self.record(now=aware)

        self.lock.assert_not_called()
        self.policy.assert_not_called()
        self.db.commit.assert_not_called()

    def test_lock_failure_rolls_back(self):
        self.lock.side_effect = RuntimeError(
            "Simulated lock failure"
        )

        with self.assertRaisesRegex(
            RuntimeError, "Simulated lock failure"
        ):
            self.record(now=self.now)

        self.db.rollback.assert_called_once_with()
        self.db.commit.assert_not_called()

    def test_policy_failure_rolls_back(self):
        self.policy.side_effect = RuntimeError(
            "Simulated policy failure"
        )

        with self.assertRaisesRegex(
            RuntimeError, "Simulated policy failure"
        ):
            self.record(now=self.now)

        self.db.rollback.assert_called_once_with()
        self.db.set_value.assert_not_called()
        self.db.commit.assert_not_called()

    def test_database_write_failure_rolls_back(self):
        self.db.set_value.side_effect = RuntimeError(
            "Simulated write failure"
        )

        with self.assertRaisesRegex(
            RuntimeError, "Simulated write failure"
        ):
            self.record(now=self.now)

        self.db.rollback.assert_called_once_with()
        self.db.commit.assert_not_called()

    def test_commit_failure_rolls_back(self):
        self.db.commit.side_effect = RuntimeError(
            "Simulated commit failure"
        )

        with self.assertRaisesRegex(
            RuntimeError, "Simulated commit failure"
        ):
            self.record(now=self.now)

        self.db.commit.assert_called_once_with()
        self.db.rollback.assert_called_once_with()

    def test_lock_recheck_policy_write_commit_order(self):
        operations = Mock()

        operations.attach_mock(self.lock, "lock")
        operations.attach_mock(self.due, "due")
        operations.attach_mock(self.policy, "policy")
        operations.attach_mock(self.db.set_value, "write")
        operations.attach_mock(self.db.commit, "commit")

        self.record(now=self.now)

        self.assertEqual(
            operations.mock_calls,
            [
                call.lock("ESC123-INTENT"),
                call.due(
                    self.row,
                    self.activation,
                    self.now,
                ),
                call.policy(
                    now=self.now,
                    attempt_count=0,
                    failure_code="DISPATCH_ERROR",
                ),
                call.write(
                    worker.DOCTYPE,
                    "ESC123-INTENT",
                    self.plan,
                ),
                call.commit(),
            ],
        )


if __name__ == "__main__":
    unittest.main()
