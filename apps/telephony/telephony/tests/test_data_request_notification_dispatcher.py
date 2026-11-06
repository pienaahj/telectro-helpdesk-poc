"""Permanent regressions for the Data Request notification dispatcher."""

import unittest
from unittest.mock import Mock, patch

from telephony import data_request_notification_dispatcher as dispatcher


INTENT = "TDRN-ESC76-TEST"
LOG = "NL-ESC76-TEST"
QUEUE = "EQ-ESC76-TEST"


class TestNotificationDispatcher(unittest.TestCase):

    def setUp(self):
        self.intent = {
            "event": "arrival",
            "delivery_state": "Pending",
            "in_app_state": "Pending",
            "notification_log": None,
            "email_state": "Pending",
            "email_queue": None,
        }

        self.native_email_state = "Queued"

        self.db = Mock()
        self.db.sql.return_value = [{"name": INTENT}]
        self.db.set_value.side_effect = self.persist
        self.db.commit.side_effect = AssertionError(
            "Dispatcher must not commit"
        )
        self.db.rollback.side_effect = AssertionError(
            "Dispatcher must not roll back"
        )

        patches = [
            patch.object(dispatcher.frappe, "db", self.db),
            patch.object(
                dispatcher.frappe,
                "get_doc",
                side_effect=self.get_doc,
            ),
            patch.object(
                dispatcher,
                "record_in_app_alert",
                side_effect=self.record,
            ),
            patch.object(
                dispatcher,
                "queue_intent_email",
                side_effect=self.queue,
            ),
            patch.object(
                dispatcher,
                "reconcile_intent_email_state",
                side_effect=self.reconcile,
            ),
            patch.object(
                dispatcher.frappe,
                "sendmail",
                side_effect=AssertionError(
                    "Dispatcher must not send email directly"
                ),
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        self.record_mock = dispatcher.record_in_app_alert
        self.queue_mock = dispatcher.queue_intent_email
        self.reconcile_mock = dispatcher.reconcile_intent_email_state

    def tearDown(self):
        self.db.commit.assert_not_called()
        self.db.rollback.assert_not_called()

    def get_doc(self, doctype, name):
        assert doctype == dispatcher.DOCTYPE
        assert name == INTENT
        return self.intent

    def persist(self, doctype, name, field, value):
        assert doctype == dispatcher.DOCTYPE
        assert name == INTENT
        assert field == "delivery_state"
        self.intent[field] = value

    def record(self, name):
        assert name == INTENT
        self.intent["in_app_state"] = "Recorded"
        self.intent["notification_log"] = LOG
        return LOG

    def queue(self, name):
        assert name == INTENT
        self.intent["email_queue"] = QUEUE
        self.intent["email_state"] = "Queued"
        return QUEUE

    def reconcile(self, name):
        assert name == INTENT
        assert self.intent["email_queue"] == QUEUE

        self.intent["email_state"] = self.native_email_state

        return {
            "email_queue": QUEUE,
            "email_state": self.native_email_state,
        }

    def existing_queue(self, state="Queued"):
        self.intent.update({
            "delivery_state": "Processing",
            "in_app_state": "Recorded",
            "notification_log": LOG,
            "email_state": state,
            "email_queue": QUEUE,
        })

    def assert_locked(self):
        self.db.sql.assert_called_once()

        query, params = self.db.sql.call_args.args[:2]

        self.assertIn("FOR UPDATE", query)
        self.assertEqual(params, (INTENT,))

    def assert_result(self, expected_state, changed):
        result = dispatcher.dispatch_notification_intent(INTENT)

        self.assertEqual(result["intent"], INTENT)
        self.assertEqual(result["event"], self.intent["event"])
        self.assertEqual(result["notification_log"], LOG)
        self.assertEqual(result["email_queue"], QUEUE)
        self.assertEqual(
            result["email_state"],
            self.native_email_state,
        )
        self.assertEqual(
            result["delivery_state"],
            expected_state,
        )
        self.assertIs(result["changed"], changed)

        self.assertEqual(
            self.intent["delivery_state"],
            expected_state,
        )

        self.assert_locked()
        self.record_mock.assert_called_once_with(INTENT)
        self.reconcile_mock.assert_called_once_with(INTENT)

        if changed:
            self.db.set_value.assert_called_once_with(
                dispatcher.DOCTYPE,
                INTENT,
                "delivery_state",
                expected_state,
            )
        else:
            self.db.set_value.assert_not_called()

    def test_pending_records_and_queues(self):
        self.assert_result("Processing", True)
        self.queue_mock.assert_called_once_with(INTENT)

    def test_existing_queue_is_reconciled(self):
        self.existing_queue()

        self.assert_result("Processing", False)
        self.queue_mock.assert_not_called()

    def test_native_sent_marks_complete(self):
        self.existing_queue()
        self.native_email_state = "Sent"

        self.assert_result("Complete", True)
        self.queue_mock.assert_not_called()

    def test_native_error_marks_retry(self):
        self.existing_queue()
        self.native_email_state = "Failed"

        self.assert_result("Retry", True)
        self.queue_mock.assert_not_called()

    def test_partially_sent_maps_to_retry(self):
        self.existing_queue()
        self.native_email_state = "Failed"

        self.assert_result("Retry", True)
        self.queue_mock.assert_not_called()

    def test_failed_existing_queue_is_reconciled(self):
        self.existing_queue("Failed")
        self.intent["delivery_state"] = "Retry"

        self.assert_result("Processing", True)
        self.queue_mock.assert_not_called()

    def test_failed_without_queue_can_be_queued(self):
        self.intent["email_state"] = "Failed"
        self.intent["delivery_state"] = "Retry"

        self.assert_result("Processing", True)
        self.queue_mock.assert_called_once_with(INTENT)

    def test_complete_cannot_be_downgraded(self):
        self.existing_queue()
        self.intent["delivery_state"] = "Complete"

        with self.assertRaises(ValueError):
            dispatcher.dispatch_notification_intent(INTENT)

        self.db.set_value.assert_not_called()
        self.queue_mock.assert_not_called()

    def test_complete_remains_complete(self):
        self.existing_queue("Sent")
        self.intent["delivery_state"] = "Complete"
        self.native_email_state = "Sent"

        self.assert_result("Complete", False)
        self.queue_mock.assert_not_called()

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            dispatcher.dispatch_notification_intent("")

        self.db.sql.assert_not_called()

    def test_missing_intent_rejected(self):
        self.db.sql.return_value = []

        with self.assertRaises(ValueError):
            dispatcher.dispatch_notification_intent(INTENT)

        self.record_mock.assert_not_called()

    def test_invalid_preconditions_rejected(self):
        cases = [
            ("event", "unexpected"),
            ("delivery_state", "Unknown"),
            ("in_app_state", "Unknown"),
            ("email_state", "Unknown"),
            ("email_state", "Skipped"),
        ]

        original = self.intent.copy()

        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.intent.clear()
                self.intent.update(original)
                self.intent[field] = value

                with self.assertRaises(ValueError):
                    dispatcher.dispatch_notification_intent(
                        INTENT
                    )

                self.record_mock.assert_not_called()

    def test_inconsistent_queue_references_rejected(self):
        cases = [
            ("Pending", QUEUE),
            ("Queued", None),
            ("Sent", None),
        ]

        for state, queue in cases:
            with self.subTest(state=state, queue=queue):
                self.intent["email_state"] = state
                self.intent["email_queue"] = queue

                with self.assertRaises(ValueError):
                    dispatcher.dispatch_notification_intent(
                        INTENT
                    )

                self.record_mock.assert_not_called()

    def test_missing_recorded_alert_rejected(self):
        self.record_mock.side_effect = lambda name: LOG

        with self.assertRaises(ValueError):
            dispatcher.dispatch_notification_intent(INTENT)

        self.db.set_value.assert_not_called()

    def test_notification_identity_mismatch_rejected(self):
        def wrong_record(name):
            self.intent["in_app_state"] = "Recorded"
            self.intent["notification_log"] = "OTHER-LOG"
            return LOG

        self.record_mock.side_effect = wrong_record

        with self.assertRaises(ValueError):
            dispatcher.dispatch_notification_intent(INTENT)

        self.db.set_value.assert_not_called()

    def test_reconciliation_state_mismatch_rejected(self):
        self.reconcile_mock.side_effect = lambda name: {
            "email_queue": QUEUE,
            "email_state": "Sent",
        }

        with self.assertRaises(ValueError):
            dispatcher.dispatch_notification_intent(INTENT)

        self.db.set_value.assert_not_called()

    def test_recording_failure_propagates(self):
        self.record_mock.side_effect = RuntimeError(
            "Recording failed"
        )

        with self.assertRaises(RuntimeError):
            dispatcher.dispatch_notification_intent(INTENT)

        self.queue_mock.assert_not_called()
        self.db.set_value.assert_not_called()

    def test_queue_failure_propagates(self):
        self.queue_mock.side_effect = RuntimeError(
            "Queue creation failed"
        )

        with self.assertRaises(RuntimeError):
            dispatcher.dispatch_notification_intent(INTENT)

        self.reconcile_mock.assert_not_called()
        self.db.set_value.assert_not_called()

    def test_reconciliation_failure_propagates(self):
        self.existing_queue()
        self.reconcile_mock.side_effect = RuntimeError(
            "Reconciliation failed"
        )

        with self.assertRaises(RuntimeError):
            dispatcher.dispatch_notification_intent(INTENT)

        self.queue_mock.assert_not_called()
        self.db.set_value.assert_not_called()

    def test_delivery_state_update_failure_propagates(self):
        self.db.set_value.side_effect = RuntimeError(
            "Delivery state update failed"
        )

        with self.assertRaises(RuntimeError):
            dispatcher.dispatch_notification_intent(INTENT)


if __name__ == "__main__":
    unittest.main()
