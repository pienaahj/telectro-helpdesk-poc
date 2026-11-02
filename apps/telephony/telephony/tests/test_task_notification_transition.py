"""Contract tests for verified task-ownership notification capture.

No database, mail transport, or Frappe runtime is required.
"""

import importlib
import sys
import types
import unittest
from unittest import mock

transition = importlib.import_module(
    "telephony.task_notification_transition"
)


class TestTaskNotificationTransition(unittest.TestCase):

    def setUp(self):
        self.outbox = types.ModuleType(
            "telephony.task_notification_outbox"
        )

        self.capture = mock.Mock(
            return_value={
                "ok": True,
                "created": True,
                "event_key": "a" * 64,
                "error": "",
            }
        )

        self.outbox.capture_task_notification_intent_safely = (
            self.capture
        )

        self.patch = mock.patch.dict(
            sys.modules,
            {
                "telephony.task_notification_outbox":
                    self.outbox
            },
        )
        self.patch.start()

        self.arguments = {
            "ticket": "100",
            "action": "assignment",
            "previous_owner": "",
            "recipient": "tech@example.invalid",
            "event_id": "todo-123",
            "transition_confirmed": True,
            "actor_user": "coordinator@example.invalid",
            "note": "New task responsibility",
        }

    def tearDown(self):
        self.patch.stop()

    def execute(self, **overrides):
        arguments = dict(self.arguments)
        arguments.update(overrides)

        return transition.capture_verified_task_ownership_transition(
            **arguments
        )

    def assert_skipped(self, result):
        self.assertEqual(
            result,
            {
                "ok": True,
                "created": False,
                "event_key": None,
                "error": "",
            },
        )
        self.capture.assert_not_called()

    def test_initial_assignment_captures_once(self):
        result = self.execute()

        self.assertTrue(result["ok"])
        self.assertTrue(result["created"])

        self.capture.assert_called_once_with(
            ticket="100",
            action="assignment",
            event_id="todo-123",
            recipient="tech@example.invalid",
            actor_user="coordinator@example.invalid",
            note="New task responsibility",
        )

    def test_claim_from_pool_captures(self):
        result = self.execute(
            action="claim",
            previous_owner="",
            event_id="claim-456",
        )

        self.assertTrue(result["created"])
        self.assertEqual(
            self.capture.call_args.kwargs["action"],
            "claim",
        )
        self.assertEqual(
            self.capture.call_args.kwargs["event_id"],
            "claim-456",
        )

    def test_controlled_handoff_captures(self):
        result = self.execute(
            action="handoff",
            previous_owner="other@example.invalid",
            event_id="handoff-789",
        )

        self.assertTrue(result["created"])
        self.assertEqual(
            self.capture.call_args.kwargs["action"],
            "handoff",
        )

    def test_unconfirmed_transition_never_captures(self):
        self.assert_skipped(
            self.execute(transition_confirmed=False)
        )

    def test_failed_claim_never_captures(self):
        self.assert_skipped(
            self.execute(
                action="claim",
                transition_confirmed=False,
            )
        )

    def test_unchanged_owner_never_captures(self):
        self.assert_skipped(
            self.execute(
                previous_owner="tech@example.invalid",
            )
        )

    def test_owner_comparison_is_case_insensitive(self):
        self.assert_skipped(
            self.execute(
                previous_owner=" TECH@EXAMPLE.INVALID ",
            )
        )

    def test_missing_recipient_never_captures(self):
        self.assert_skipped(
            self.execute(recipient="")
        )

    def test_share_context_is_not_an_ownership_transition(self):
        self.assert_skipped(
            self.execute(
                action="share_context",
                previous_owner="other@example.invalid",
            )
        )

    def test_unknown_action_never_captures(self):
        self.assert_skipped(
            self.execute(action="repair")
        )

    def test_different_real_events_keep_distinct_event_ids(self):
        self.execute(event_id="todo-123")
        self.execute(event_id="todo-456")

        self.assertEqual(self.capture.call_count, 2)

        recorded = [
            call.kwargs["event_id"]
            for call in self.capture.call_args_list
        ]

        self.assertEqual(
            recorded,
            ["todo-123", "todo-456"],
        )

    def test_capture_failure_is_reported(self):
        failure = {
            "ok": False,
            "created": False,
            "event_key": None,
            "error": "capture_failed",
        }

        self.capture.return_value = failure

        self.assertEqual(self.execute(), failure)

    def test_failed_savepoint_is_reported(self):
        failure = {
            "ok": False,
            "created": False,
            "event_key": None,
            "error": "savepoint_failed",
        }

        self.capture.return_value = failure

        self.assertEqual(self.execute(), failure)

    def test_failed_transaction_restoration_propagates(self):
        self.capture.side_effect = RuntimeError(
            "Cannot restore savepoint"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Cannot restore savepoint",
        ):
            self.execute()


if __name__ == "__main__":
    unittest.main()
