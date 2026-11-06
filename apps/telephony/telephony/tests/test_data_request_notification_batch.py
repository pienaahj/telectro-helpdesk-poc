"""Permanent regressions for Data Request notification batches.

Selection, worker execution and transaction rollback are mocked.
No database, email transport or scheduler operations are performed.
"""

import unittest

from datetime import datetime
from unittest.mock import Mock, call, patch

from telephony import data_request_notification_batch as batch


class TestNotificationBatch(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 11, 5, 15, 0)

        self.selector = Mock(return_value={
            "state": "ready",
            "intents": ["A", "B"],
            "selected": 2,
        })

        self.worker = Mock(return_value={
            "state": "Processing",
        })

        self.db = Mock()
        self.reporter = Mock(return_value="ERROR-ESC117")
        self.backoff = Mock(return_value={"state": "Retry"})

        patches = [
            patch.object(
                batch,
                "select_due_notification_intents",
                self.selector,
            ),
            patch.object(
                batch,
                "process_due_notification_intent",
                self.worker,
            ),
            patch.object(
                batch,
                "persist_unhandled_batch_error",
                self.reporter,
            ),
            patch.object(
                batch,
                "record_unhandled_notification_failure",
                self.backoff,
            ),
            patch.object(
                batch.frappe,
                "db",
                self.db,
            ),
            patch.object(
                batch.frappe.utils,
                "now_datetime",
                return_value=self.now,
            ),
            patch.object(
                batch.frappe.utils,
                "get_datetime",
                side_effect=lambda value: value,
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def candidates(self, names, state="ready", selected=None):
        if selected is None:
            selected = len(names)

        self.selector.return_value = {
            "state": state,
            "intents": names,
            "selected": selected,
        }

    def run_batch(self, **kwargs):
        return batch.run_notification_delivery_batch(**kwargs)

    def assert_no_worker_activity(self):
        self.worker.assert_not_called()
        self.reporter.assert_not_called()
        self.db.rollback.assert_not_called()
        self.db.commit.assert_not_called()

    def test_disabled_selection_fails_closed(self):
        self.candidates([], state="disabled")

        result = self.run_batch()

        self.assertEqual(result["state"], "disabled")
        self.assertEqual(result["selected"], 0)
        self.assertEqual(result["attempted"], 0)
        self.assert_no_worker_activity()

    def test_not_due_selection_fails_closed(self):
        self.candidates([], state="not_due")

        result = self.run_batch()

        self.assertEqual(result["state"], "not_due")
        self.assertEqual(result["attempted"], 0)
        self.assert_no_worker_activity()

    def test_empty_ready_batch(self):
        self.candidates([])

        result = self.run_batch()

        self.assertEqual(result["state"], "processed")
        self.assertEqual(result["selected"], 0)
        self.assertEqual(result["attempted"], 0)
        self.assertEqual(result["outcomes"], [])
        self.assert_no_worker_activity()

    def test_dry_run_never_dispatches(self):
        result = self.run_batch(dry_run=True, limit=2)

        self.assertEqual(result["state"], "dry_run")
        self.assertEqual(result["selected"], 2)
        self.assertEqual(result["attempted"], 0)
        self.assertEqual(result["outcomes"], [])

        self.selector.assert_called_once_with(
            now=self.now,
            limit=2,
        )

        self.assert_no_worker_activity()

    def test_disabled_dry_run_keeps_gate(self):
        self.candidates([], state="disabled")

        result = self.run_batch(dry_run=True)

        self.assertEqual(result["state"], "disabled")
        self.assert_no_worker_activity()

    def test_invalid_limits_rejected(self):
        invalid = (
            0,
            -1,
            batch.MAX_BATCH + 1,
            True,
            False,
            1.5,
            "10",
            None,
        )

        for limit in invalid:
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    self.run_batch(limit=limit)

        self.selector.assert_not_called()
        self.assert_no_worker_activity()

    def test_maximum_limit_allowed(self):
        self.candidates([])

        result = self.run_batch(limit=batch.MAX_BATCH)

        self.assertEqual(result["state"], "processed")

        self.selector.assert_called_once_with(
            now=self.now,
            limit=batch.MAX_BATCH,
        )

    def test_invalid_dry_run_type_rejected(self):
        for value in (0, 1, "true", None, []):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.run_batch(dry_run=value)

        self.selector.assert_not_called()
        self.assert_no_worker_activity()

    def test_unknown_selector_state_rejected(self):
        self.candidates([], state="unexpected")

        with self.assertRaises(ValueError):
            self.run_batch()

        self.assert_no_worker_activity()

    def test_non_list_candidates_rejected(self):
        self.candidates(("A", "B"))

        with self.assertRaises(ValueError):
            self.run_batch()

        self.assert_no_worker_activity()

    def test_candidates_exceed_requested_limit(self):
        self.candidates(["A", "B", "C"])

        with self.assertRaises(ValueError):
            self.run_batch(limit=2)

        self.assert_no_worker_activity()

    def test_duplicate_candidate_names_rejected(self):
        self.candidates(["A", "A"])

        with self.assertRaises(ValueError):
            self.run_batch()

        self.assert_no_worker_activity()

    def test_selected_count_mismatch_rejected(self):
        self.candidates(["A", "B"], selected=1)

        with self.assertRaises(ValueError):
            self.run_batch()

        self.assert_no_worker_activity()

    def test_mixed_outcomes_counted(self):
        states = {
            "A": "Processing",
            "B": "Complete",
            "C": "Retry",
            "D": "Failed",
            "E": "missing",
            "F": "not_due",
            "G": "superseded",
        }

        self.candidates(list(states))

        self.worker.side_effect = (
            lambda name, **kwargs: {
                "state": states[name],
            }
        )

        result = self.run_batch(limit=7)

        self.assertEqual(result["state"], "processed")
        self.assertEqual(result["selected"], 7)
        self.assertEqual(result["attempted"], 7)

        for counter in (
            "processing",
            "complete",
            "retry",
            "failed",
        ):
            self.assertEqual(result[counter], 1)

        self.assertEqual(result["skipped"], 3)
        self.assertEqual(result["errors"], 0)

        self.assertEqual(
            [item["state"] for item in result["outcomes"]],
            list(states.values()),
        )

        self.db.rollback.assert_not_called()

    def test_worker_order_and_frozen_clock(self):
        self.candidates(["A", "B", "C"])

        result = self.run_batch(limit=3)

        self.assertEqual(result["attempted"], 3)

        self.assertEqual(
            [call.args[0] for call in self.worker.call_args_list],
            ["A", "B", "C"],
        )

        for call in self.worker.call_args_list:
            self.assertEqual(
                call.kwargs,
                {"now": self.now},
            )

    def test_exception_rolls_back_and_continues(self):
        self.candidates(["A", "BAD", "C"])

        def dispatch(name, **kwargs):
            if name == "BAD":
                raise RuntimeError("Simulated worker error")

            return {"state": "Complete"}

        self.worker.side_effect = dispatch

        result = self.run_batch(limit=3)

        self.assertEqual(result["state"], "partial_failure")
        self.assertEqual(result["attempted"], 3)
        self.assertEqual(result["complete"], 2)
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["error_intents"], ["BAD"])

        self.db.rollback.assert_called_once_with()

        self.assertEqual(
            [item["state"] for item in result["outcomes"]],
            ["Complete", "error", "Complete"],
        )

    def test_multiple_exceptions_are_isolated(self):
        self.candidates(["BAD1", "BAD2", "GOOD"])

        def dispatch(name, **kwargs):
            if name.startswith("BAD"):
                raise RuntimeError("Simulated failure")

            return {"state": "Complete"}

        self.worker.side_effect = dispatch

        result = self.run_batch(limit=3)

        self.assertEqual(result["state"], "partial_failure")
        self.assertEqual(result["errors"], 2)
        self.assertEqual(result["complete"], 1)
        self.assertEqual(result["attempted"], 3)

        self.assertEqual(
            result["error_intents"],
            ["BAD1", "BAD2"],
        )

        self.assertEqual(self.db.rollback.call_count, 2)

    def test_invalid_worker_response_isolated(self):
        self.candidates(["BAD", "GOOD"])

        def dispatch(name, **kwargs):
            if name == "BAD":
                return None

            return {"state": "Complete"}

        self.worker.side_effect = dispatch

        result = self.run_batch(limit=2)

        self.assertEqual(result["state"], "partial_failure")
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["complete"], 1)

        self.db.rollback.assert_called_once_with()

    def test_unknown_worker_outcome_isolated(self):
        self.candidates(["BAD", "GOOD"])

        def dispatch(name, **kwargs):
            return {
                "state": (
                    "unexpected"
                    if name == "BAD"
                    else "Complete"
                ),
            }

        self.worker.side_effect = dispatch

        result = self.run_batch(limit=2)

        self.assertEqual(result["state"], "partial_failure")
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["complete"], 1)

        self.db.rollback.assert_called_once_with()

    def test_deactivation_stops_remaining_candidates(self):
        self.candidates(["A", "B", "C"])

        states = {
            "A": "Processing",
            "B": "disabled",
            "C": "Complete",
        }

        self.worker.side_effect = (
            lambda name, **kwargs: {
                "state": states[name],
            }
        )

        result = self.run_batch(limit=3)

        self.assertEqual(result["state"], "deactivated")
        self.assertEqual(result["selected"], 3)
        self.assertEqual(result["attempted"], 2)
        self.assertEqual(result["processing"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"], 0)

        self.assertEqual(
            [call.args[0] for call in self.worker.call_args_list],
            ["A", "B"],
        )

    def test_deactivation_on_first_intent(self):
        self.worker.return_value = {
            "state": "disabled",
        }

        result = self.run_batch(limit=2)

        self.assertEqual(result["state"], "deactivated")
        self.assertEqual(result["attempted"], 1)
        self.assertEqual(result["skipped"], 1)

        self.worker.assert_called_once_with(
            "A",
            now=self.now,
        )

    def test_explicit_clock_conversion(self):
        self.candidates(["A"])

        supplied = "2026-11-05 15:00:00"

        with patch.object(
            batch.frappe.utils,
            "get_datetime",
            return_value=self.now,
        ) as converter:
            result = self.run_batch(
                now=supplied,
                limit=1,
            )

        converter.assert_called_once_with(supplied)

        self.assertEqual(result["attempted"], 1)

        self.worker.assert_called_once_with(
            "A",
            now=self.now,
        )

    def test_default_clock_used(self):
        self.candidates(["A"])

        result = self.run_batch(limit=1)

        self.assertEqual(result["attempted"], 1)

        batch.frappe.utils.now_datetime.assert_called_once_with()

        batch.frappe.utils.get_datetime.assert_not_called()


    def test_rollback_precedes_durable_reporting(self):
        self.candidates(["BAD", "GOOD"])

        def dispatch(name, **kwargs):
            if name == "BAD":
                raise RuntimeError("Simulated failure")
            return {"state": "Complete"}

        self.worker.side_effect = dispatch

        operations = Mock()
        operations.attach_mock(
            self.db.rollback, "rollback"
        )
        operations.attach_mock(
            self.reporter, "report"
        )
        operations.attach_mock(
            self.backoff, "backoff"
        )

        result = self.run_batch(limit=2)

        self.assertEqual(
            operations.mock_calls,
            [
                call.rollback(),
                call.report("BAD"),
                call.backoff("BAD", now=self.now),
            ],
        )

        self.assertEqual(result["state"], "partial_failure")
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["complete"], 1)

        self.assertEqual(
            result["outcomes"],
            [
                {
                    "intent": "BAD",
                    "state": "error",
                    "error_log": "ERROR-ESC117",
                    "failure_state": "Retry",
                },
                {
                    "intent": "GOOD",
                    "state": "Complete",
                },
            ],
        )

    def test_multiple_failures_are_logged_separately(self):
        self.candidates(["BAD1", "BAD2"])

        self.worker.side_effect = RuntimeError(
            "Simulated delivery failure"
        )

        self.reporter.side_effect = [
            "ERROR-1",
            "ERROR-2",
        ]

        result = self.run_batch(limit=2)

        self.assertEqual(result["errors"], 2)
        self.assertEqual(result["attempted"], 2)
        self.assertEqual(
            self.reporter.call_args_list,
            [
                call("BAD1"),
                call("BAD2"),
            ],
        )

        self.assertEqual(
            result["outcomes"],
            [
                {
                    "intent": "BAD1",
                    "state": "error",
                    "error_log": "ERROR-1",
                    "failure_state": "Retry",
                },
                {
                    "intent": "BAD2",
                    "state": "error",
                    "error_log": "ERROR-2",
                    "failure_state": "Retry",
                },
            ],
        )

        self.assertEqual(self.db.rollback.call_count, 2)
        self.assertEqual(
            self.backoff.call_args_list,
            [
                call("BAD1", now=self.now),
                call("BAD2", now=self.now),
            ],
        )

    def test_reporting_failure_aborts_batch(self):
        self.candidates(["BAD", "GOOD"])

        self.worker.side_effect = RuntimeError(
            "Simulated worker failure"
        )

        self.reporter.side_effect = RuntimeError(
            "Notification batch error-log persistence failed"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Notification batch error-log persistence failed",
        ):
            self.run_batch(limit=2)

        self.db.rollback.assert_called_once_with()
        self.reporter.assert_called_once_with("BAD")
        self.backoff.assert_not_called()

        # The second intent must not run when operational
        # failure evidence could not be persisted.
        self.worker.assert_called_once_with(
            "BAD",
            now=self.now,
        )

    def test_successful_batch_does_not_log_errors(self):
        self.candidates(["A", "B"])

        self.worker.return_value = {
            "state": "Complete",
        }

        result = self.run_batch(limit=2)

        self.assertEqual(result["state"], "processed")
        self.assertEqual(result["complete"], 2)
        self.assertEqual(result["errors"], 0)

        self.reporter.assert_not_called()
        self.backoff.assert_not_called()
        self.db.rollback.assert_not_called()


    def test_terminal_failed_backoff_state_recorded(self):
        self.candidates(["BAD", "GOOD"])

        def dispatch(name, **kwargs):
            if name == "BAD":
                raise RuntimeError("Simulated failure")
            return {"state": "Complete"}

        self.worker.side_effect = dispatch
        self.backoff.return_value = {"state": "Failed"}

        result = self.run_batch(limit=2)

        self.assertEqual(result["state"], "partial_failure")
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["complete"], 1)
        self.assertEqual(
            result["outcomes"][0]["failure_state"],
            "Failed",
        )

        self.backoff.assert_called_once_with(
            "BAD",
            now=self.now,
        )

    def test_superseded_failure_does_not_abort_batch(self):
        self.candidates(["BAD", "GOOD"])

        def dispatch(name, **kwargs):
            if name == "BAD":
                raise RuntimeError("Simulated failure")
            return {"state": "Complete"}

        self.worker.side_effect = dispatch

        # Another worker may have advanced the intent
        # before the backoff helper acquires its row lock.
        self.backoff.return_value = {
            "state": "superseded",
        }

        result = self.run_batch(limit=2)

        self.assertEqual(result["state"], "partial_failure")
        self.assertEqual(result["complete"], 1)
        self.assertEqual(result["errors"], 1)
        self.assertEqual(
            result["outcomes"][0]["failure_state"],
            "superseded",
        )

        self.backoff.assert_called_once_with(
            "BAD",
            now=self.now,
        )

    def test_backoff_persistence_failure_aborts_batch(self):
        self.candidates(["BAD", "GOOD"])

        self.worker.side_effect = RuntimeError(
            "Simulated worker failure"
        )

        self.backoff.side_effect = RuntimeError(
            "Simulated durable backoff persistence failure"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Simulated durable backoff persistence failure",
        ):
            self.run_batch(limit=2)

        self.db.rollback.assert_called_once_with()
        self.reporter.assert_called_once_with("BAD")
        self.backoff.assert_called_once_with(
            "BAD",
            now=self.now,
        )

        # Do not proceed to GOOD when the failure state
        # could not be persisted.
        self.worker.assert_called_once_with(
            "BAD",
            now=self.now,
        )

    def test_invalid_backoff_result_aborts_batch(self):
        self.candidates(["BAD", "GOOD"])

        self.worker.side_effect = RuntimeError(
            "Simulated worker failure"
        )

        self.backoff.return_value = {
            "state": "unexpected",
        }

        with self.assertRaisesRegex(
            RuntimeError,
            "Unexpected durable notification failure state",
        ):
            self.run_batch(limit=2)

        self.reporter.assert_called_once_with("BAD")
        self.backoff.assert_called_once_with(
            "BAD",
            now=self.now,
        )

        self.worker.assert_called_once_with(
            "BAD",
            now=self.now,
        )


if __name__ == "__main__":
    unittest.main()
