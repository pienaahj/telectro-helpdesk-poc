"""Transactional in-app notification recording regressions."""

import unittest
from unittest.mock import Mock, patch

import frappe

from telephony import data_request_notification_delivery as delivery


INTENT = "TDRN-ESC-TEST"
TICKET = "956"
LOG = "NL-ESC-TEST"
USER = "coordinator.test@local.test"


class FakeDoc(dict):
    def __init__(self, name, **fields):
        super().__init__(fields)
        self.name = name
        self.insert = Mock()


class TestInAppRecording(unittest.TestCase):

    def setUp(self):
        self.db = Mock()
        self.db.sql.return_value = [{"name": INTENT}]
        self.db.exists.return_value = True
        self.db.commit.side_effect = AssertionError(
            "Delivery must not commit"
        )

        self.intent = FakeDoc(
            INTENT,
            ticket=TICKET,
            recipient=USER,
            event="arrival",
            in_app_state="Pending",
            notification_log=None,
        )

        self.ticket = FakeDoc(
            TICKET,
            custom_service_area="Data Request",
            agent_group="Data Provisioning",
        )

        self.notification = FakeDoc(LOG)
        self.payload = None

        db_patch = patch.dict(
            delivery.frappe.__dict__,
            {"db": self.db},
        )
        db_patch.start()
        self.addCleanup(db_patch.stop)

        doc_patch = patch.object(
            delivery.frappe,
            "get_doc",
            side_effect=self.get_doc,
        )
        self.get_doc_mock = doc_patch.start()
        self.addCleanup(doc_patch.stop)

        auth_patch = patch.object(
            delivery,
            "_require_authorized_recipient",
        )
        self.authorize = auth_patch.start()
        self.addCleanup(auth_patch.stop)

        email_patch = patch.object(
            delivery.frappe,
            "sendmail",
            side_effect=AssertionError(
                "In-app delivery must not send email"
            ),
        )
        email_patch.start()
        self.addCleanup(email_patch.stop)

    def get_doc(self, doctype, name=None):
        if isinstance(doctype, dict):
            assert doctype["doctype"] == "Notification Log"
            self.payload = doctype
            return self.notification

        if doctype == delivery.DOCTYPE and name == INTENT:
            return self.intent

        if doctype == "HD Ticket" and name == TICKET:
            return self.ticket

        raise AssertionError(
            f"Unexpected get_doc: {doctype!r}, {name!r}"
        )

    def assert_locked(self):
        self.db.sql.assert_called_once()

        query, params = self.db.sql.call_args.args[:2]

        self.assertIn("FOR UPDATE", query)
        self.assertEqual(params, (INTENT,))

    def assert_recorded(self):
        self.notification.insert.assert_called_once_with(
            ignore_permissions=True
        )

        self.db.set_value.assert_called_once_with(
            delivery.DOCTYPE,
            INTENT,
            {
                "notification_log": LOG,
                "in_app_state": "Recorded",
            },
        )

        self.assertEqual(self.payload["type"], "Alert")
        self.assertEqual(self.payload["for_user"], USER)
        self.assertEqual(
            self.payload["document_type"],
            "HD Ticket",
        )
        self.assertEqual(
            self.payload["document_name"],
            TICKET,
        )

        self.db.commit.assert_not_called()

    def test_arrival_creates_one_alert(self):
        result = delivery.record_in_app_alert(INTENT)

        self.assertEqual(result, LOG)
        self.assertIn("New Data Request", self.payload["subject"])
        self.assert_locked()
        self.assert_recorded()

        self.authorize.assert_called_once_with(
            self.intent,
            self.ticket,
        )

    def test_escalation_creates_one_alert(self):
        self.intent["event"] = "escalation"

        result = delivery.record_in_app_alert(INTENT)

        self.assertEqual(result, LOG)
        self.assertIn(
            "exceeded ten minutes",
            self.payload["subject"],
        )
        self.assert_recorded()

    def test_recorded_alert_is_reused(self):
        self.intent["in_app_state"] = "Recorded"
        self.intent["notification_log"] = LOG

        self.assertEqual(
            delivery.record_in_app_alert(INTENT),
            LOG,
        )

        self.assert_locked()
        self.db.exists.assert_called_once_with(
            "Notification Log",
            LOG,
        )
        self.notification.insert.assert_not_called()
        self.db.set_value.assert_not_called()
        self.authorize.assert_not_called()

    def test_empty_intent_is_rejected(self):
        with self.assertRaises(ValueError):
            delivery.record_in_app_alert("")

        self.db.sql.assert_not_called()

    def test_missing_intent_is_rejected(self):
        self.db.sql.return_value = []

        with self.assertRaises(ValueError):
            delivery.record_in_app_alert(INTENT)

        self.db.set_value.assert_not_called()

    def test_recorded_state_requires_log_reference(self):
        self.intent["in_app_state"] = "Recorded"

        with self.assertRaises(ValueError):
            delivery.record_in_app_alert(INTENT)

        self.db.set_value.assert_not_called()

    def test_recorded_state_requires_existing_log(self):
        self.intent["in_app_state"] = "Recorded"
        self.intent["notification_log"] = LOG
        self.db.exists.return_value = False

        with self.assertRaises(ValueError):
            delivery.record_in_app_alert(INTENT)

        self.db.set_value.assert_not_called()

    def test_unexpected_state_is_rejected(self):
        self.intent["in_app_state"] = "Processing"

        with self.assertRaises(ValueError):
            delivery.record_in_app_alert(INTENT)

        self.db.set_value.assert_not_called()

    def test_pending_state_rejects_orphan_reference(self):
        self.intent["notification_log"] = LOG

        with self.assertRaises(ValueError):
            delivery.record_in_app_alert(INTENT)

        self.notification.insert.assert_not_called()

    def test_failed_state_can_retry(self):
        self.intent["in_app_state"] = "Failed"

        self.assertEqual(
            delivery.record_in_app_alert(INTENT),
            LOG,
        )

        self.assert_recorded()

    def test_revoked_authority_prevents_creation(self):
        self.authorize.side_effect = frappe.PermissionError(
            "Access revoked"
        )

        with self.assertRaises(frappe.PermissionError):
            delivery.record_in_app_alert(INTENT)

        self.notification.insert.assert_not_called()
        self.db.set_value.assert_not_called()

    def test_notification_insert_failure_propagates(self):
        self.notification.insert.side_effect = RuntimeError(
            "Notification insert failed"
        )

        with self.assertRaises(RuntimeError):
            delivery.record_in_app_alert(INTENT)

        self.db.set_value.assert_not_called()
        self.db.commit.assert_not_called()

    def test_intent_update_failure_propagates(self):
        self.db.set_value.side_effect = RuntimeError(
            "Intent update failed"
        )

        with self.assertRaises(RuntimeError):
            delivery.record_in_app_alert(INTENT)

        self.notification.insert.assert_called_once()
        self.db.commit.assert_not_called()

    def test_unsupported_event_does_not_create_alert(self):
        self.intent["event"] = "unsupported"

        with self.assertRaises(ValueError):
            delivery.record_in_app_alert(INTENT)

        self.notification.insert.assert_not_called()
        self.db.set_value.assert_not_called()


if __name__ == "__main__":
    unittest.main()
