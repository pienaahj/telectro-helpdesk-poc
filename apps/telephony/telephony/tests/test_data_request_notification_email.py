"""Regression tests for transactional Data Request email queueing."""

import unittest
from unittest.mock import Mock, patch

import frappe

from telephony import data_request_notification_email as delivery


INTENT = "TDRN-ESC71-TEST"
TICKET = "956"
QUEUE = "EQ-ESC71-TEST"
USER = "coordinator.test@local.test"
ADDRESS = "coordinator.test@local.test"


class FakeDoc(dict):
    def __init__(self, name, **fields):
        super().__init__(fields)
        self.name = name

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


class TestEmailQueueing(unittest.TestCase):

    def setUp(self):
        self.db = Mock()
        self.db.sql.return_value = [{"name": INTENT}]
        self.db.get_value.return_value = ADDRESS
        self.db.commit.side_effect = AssertionError(
            "Email queueing must not commit"
        )

        self.intent = FakeDoc(
            INTENT,
            ticket=TICKET,
            recipient=USER,
            event="arrival",
            email_state="Pending",
            email_queue=None,
        )

        self.ticket = FakeDoc(
            TICKET,
            custom_service_area="Data Request",
            agent_group="Data Provisioning",
        )

        self.queue = FakeDoc(
            QUEUE,
            reference_doctype=delivery.DOCTYPE,
            reference_name=INTENT,
            communication=None,
        )

        self.sendmail = Mock(return_value=self.queue)
        self.authorize = Mock()

        patches = [
            patch.object(delivery.frappe, "db", self.db),
            patch.object(
                delivery.frappe,
                "get_doc",
                side_effect=self.get_doc,
            ),
            patch.object(
                delivery.frappe,
                "sendmail",
                self.sendmail,
            ),
            patch.object(
                delivery,
                "_require_authorized_recipient",
                self.authorize,
            ),
            patch.object(
                delivery.frappe.utils,
                "get_url",
                return_value="https://dev.example.test",
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def get_doc(self, doctype, name):
        if doctype == delivery.DOCTYPE and name == INTENT:
            return self.intent

        if doctype == "HD Ticket" and name == TICKET:
            return self.ticket

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

    def assert_queued(self):
        self.assert_locked()

        self.authorize.assert_called_once_with(
            self.intent,
            self.ticket,
        )

        self.sendmail.assert_called_once()

        kwargs = self.sendmail.call_args.kwargs

        self.assertEqual(kwargs["recipients"], [ADDRESS])
        self.assertTrue(kwargs["delayed"])
        self.assertFalse(kwargs["queue_separately"])
        self.assertEqual(
            kwargs["reference_doctype"],
            delivery.DOCTYPE,
        )
        self.assertEqual(kwargs["reference_name"], INTENT)
        self.assertIsNone(kwargs["communication"])
        self.assertTrue(kwargs["is_notification"])
        self.assertEqual(kwargs["add_unsubscribe_link"], 0)

        self.db.set_value.assert_called_once_with(
            delivery.DOCTYPE,
            INTENT,
            {
                "email_queue": QUEUE,
                "email_state": "Queued",
            },
        )

        self.db.commit.assert_not_called()

    def test_arrival_creates_queue(self):
        result = delivery.queue_intent_email(INTENT)

        self.assertEqual(result, QUEUE)
        self.assertIn(
            "New Data Request",
            self.sendmail.call_args.kwargs["subject"],
        )
        self.assert_queued()

    def test_escalation_creates_queue(self):
        self.intent["event"] = "escalation"

        result = delivery.queue_intent_email(INTENT)

        self.assertEqual(result, QUEUE)
        self.assertIn(
            "Data Request escalation",
            self.sendmail.call_args.kwargs["subject"],
        )
        self.assert_queued()

    def test_queued_email_is_reused(self):
        self.intent["email_state"] = "Queued"
        self.intent["email_queue"] = QUEUE

        self.assertEqual(
            delivery.queue_intent_email(INTENT),
            QUEUE,
        )

        self.assert_locked()
        self.sendmail.assert_not_called()
        self.authorize.assert_not_called()
        self.db.set_value.assert_not_called()

    def test_sent_email_is_reused(self):
        self.intent["email_state"] = "Sent"
        self.intent["email_queue"] = QUEUE

        self.assertEqual(
            delivery.queue_intent_email(INTENT),
            QUEUE,
        )

        self.sendmail.assert_not_called()
        self.db.set_value.assert_not_called()

    def test_empty_intent_is_rejected(self):
        with self.assertRaises(ValueError):
            delivery.queue_intent_email("")

        self.db.sql.assert_not_called()

    def test_missing_intent_is_rejected(self):
        self.db.sql.return_value = []

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_queued_state_requires_reference(self):
        self.intent["email_state"] = "Queued"

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_existing_queue_identity_mismatch(self):
        self.intent["email_state"] = "Queued"
        self.intent["email_queue"] = QUEUE
        self.queue["reference_name"] = "OTHER-INTENT"

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_existing_queue_communication_rejected(self):
        self.intent["email_state"] = "Queued"
        self.intent["email_queue"] = QUEUE
        self.queue["communication"] = "COMM-TEST"

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_pending_with_existing_queue_rejected(self):
        self.intent["email_queue"] = QUEUE

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_failed_with_existing_queue_rejected(self):
        self.intent["email_state"] = "Failed"
        self.intent["email_queue"] = QUEUE

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_unexpected_email_state_rejected(self):
        self.intent["email_state"] = "Skipped"

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_revoked_authority_rejected(self):
        self.authorize.side_effect = frappe.PermissionError(
            "Recipient access revoked"
        )

        with self.assertRaises(frappe.PermissionError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_invalid_email_address_rejected(self):
        self.db.get_value.return_value = "invalid-email"

        with self.assertRaises(frappe.PermissionError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_unsupported_event_rejected(self):
        self.intent["event"] = "unsupported"

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_not_called()

    def test_empty_sendmail_result_rejected(self):
        self.sendmail.return_value = []

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.db.set_value.assert_not_called()

    def test_created_queue_identity_mismatch(self):
        self.queue["reference_name"] = "OTHER-INTENT"

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.db.set_value.assert_not_called()

    def test_created_queue_communication_rejected(self):
        self.queue["communication"] = "COMM-TEST"

        with self.assertRaises(ValueError):
            delivery.queue_intent_email(INTENT)

        self.db.set_value.assert_not_called()

    def test_intent_update_failure_propagates(self):
        self.db.set_value.side_effect = RuntimeError(
            "Intent update failed"
        )

        with self.assertRaises(RuntimeError):
            delivery.queue_intent_email(INTENT)

        self.sendmail.assert_called_once()
        self.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
