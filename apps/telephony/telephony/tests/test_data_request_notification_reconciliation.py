"""Regression tests for Data Request Email Queue reconciliation."""

import unittest
from unittest.mock import Mock, patch

from telephony import data_request_notification_reconciliation as recon
from telephony.data_request_notification_delivery import DOCTYPE


INTENT = "TDRN-ESC74-TEST"
QUEUE = "EQ-ESC74-TEST"


class FakeDoc(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


class TestEmailReconciliation(unittest.TestCase):

    def setUp(self):
        self.db = Mock()
        self.db.sql.return_value = [{"name": INTENT}]
        self.db.commit.side_effect = AssertionError(
            "Reconciliation must not commit"
        )

        self.intent = FakeDoc(
            email_state="Queued",
            email_queue=QUEUE,
        )

        self.queue = FakeDoc(
            reference_doctype=DOCTYPE,
            reference_name=INTENT,
            communication=None,
            status="Not Sent",
        )

        self.sendmail = Mock(
            side_effect=AssertionError(
                "Reconciliation must not queue email"
            )
        )

        patches = [
            patch.object(recon.frappe, "db", self.db),
            patch.object(
                recon.frappe,
                "get_doc",
                side_effect=self.get_doc,
            ),
            patch.object(
                recon.frappe,
                "sendmail",
                self.sendmail,
            ),
            patch.object(
                recon.frappe,
                "enqueue",
                side_effect=AssertionError(
                    "Reconciliation must not enqueue jobs"
                ),
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def tearDown(self):
        self.db.commit.assert_not_called()
        self.sendmail.assert_not_called()

    def get_doc(self, doctype, name):
        if doctype == DOCTYPE and name == INTENT:
            return self.intent

        if doctype == "Email Queue" and name == QUEUE:
            return self.queue

        raise AssertionError(
            f"Unexpected get_doc({doctype!r}, {name!r})"
        )

    def assert_locked(self):
        self.db.sql.assert_called_once()

        query, params = self.db.sql.call_args.args[:2]

        self.assertIn("FOR UPDATE", query)
        self.assertEqual(params, (INTENT,))

    def assert_reconciled(self, expected_state, changed):
        result = recon.reconcile_intent_email_state(INTENT)

        self.assertEqual(result["intent"], INTENT)
        self.assertEqual(result["email_queue"], QUEUE)
        self.assertEqual(
            result["queue_status"],
            self.queue["status"],
        )
        self.assertEqual(
            result["email_state"],
            expected_state,
        )
        self.assertIs(result["changed"], changed)

        self.assert_locked()

        if changed:
            self.db.set_value.assert_called_once_with(
                DOCTYPE,
                INTENT,
                "email_state",
                expected_state,
            )
        else:
            self.db.set_value.assert_not_called()

    def test_not_sent_remains_queued(self):
        self.queue["status"] = "Not Sent"
        self.assert_reconciled("Queued", False)

    def test_sending_remains_queued(self):
        self.queue["status"] = "Sending"
        self.assert_reconciled("Queued", False)

    def test_sent_updates_intent(self):
        self.queue["status"] = "Sent"
        self.assert_reconciled("Sent", True)

    def test_partially_sent_marks_failed(self):
        self.queue["status"] = "Partially Sent"
        self.assert_reconciled("Failed", True)

    def test_error_marks_failed(self):
        self.queue["status"] = "Error"
        self.assert_reconciled("Failed", True)

    def test_failed_queue_can_return_to_queued(self):
        self.intent["email_state"] = "Failed"
        self.queue["status"] = "Not Sent"

        self.assert_reconciled("Queued", True)

    def test_failed_error_remains_failed(self):
        self.intent["email_state"] = "Failed"
        self.queue["status"] = "Error"

        self.assert_reconciled("Failed", False)

    def test_sent_remains_sent(self):
        self.intent["email_state"] = "Sent"
        self.queue["status"] = "Sent"

        self.assert_reconciled("Sent", False)

    def test_sent_cannot_be_downgraded(self):
        for status in ("Not Sent", "Sending", "Error"):
            with self.subTest(status=status):
                self.intent["email_state"] = "Sent"
                self.queue["status"] = status
                self.db.reset_mock()

                with self.assertRaises(ValueError):
                    recon.reconcile_intent_email_state(INTENT)

                self.db.set_value.assert_not_called()

    def test_empty_intent_rejected(self):
        with self.assertRaises(ValueError):
            recon.reconcile_intent_email_state("")

        self.db.sql.assert_not_called()

    def test_missing_intent_rejected(self):
        self.db.sql.return_value = []

        with self.assertRaises(ValueError):
            recon.reconcile_intent_email_state(INTENT)

        self.db.set_value.assert_not_called()

    def test_pending_state_rejected(self):
        self.intent["email_state"] = "Pending"

        with self.assertRaises(ValueError):
            recon.reconcile_intent_email_state(INTENT)

        self.db.set_value.assert_not_called()

    def test_missing_queue_reference_rejected(self):
        self.intent["email_queue"] = None

        with self.assertRaises(ValueError):
            recon.reconcile_intent_email_state(INTENT)

        self.db.set_value.assert_not_called()

    def test_wrong_queue_doctype_rejected(self):
        self.queue["reference_doctype"] = "HD Ticket"

        with self.assertRaises(ValueError):
            recon.reconcile_intent_email_state(INTENT)

        self.db.set_value.assert_not_called()

    def test_wrong_queue_reference_rejected(self):
        self.queue["reference_name"] = "OTHER-INTENT"

        with self.assertRaises(ValueError):
            recon.reconcile_intent_email_state(INTENT)

        self.db.set_value.assert_not_called()

    def test_linked_communication_rejected(self):
        self.queue["communication"] = "COMM-TEST"

        with self.assertRaises(ValueError):
            recon.reconcile_intent_email_state(INTENT)

        self.db.set_value.assert_not_called()

    def test_unknown_native_status_rejected(self):
        self.queue["status"] = "Delivered"

        with self.assertRaises(ValueError):
            recon.reconcile_intent_email_state(INTENT)

        self.db.set_value.assert_not_called()

    def test_persistence_failure_propagates(self):
        self.queue["status"] = "Sent"
        self.db.set_value.side_effect = RuntimeError(
            "Database update failed"
        )

        with self.assertRaises(RuntimeError):
            recon.reconcile_intent_email_state(INTENT)


if __name__ == "__main__":
    unittest.main()
