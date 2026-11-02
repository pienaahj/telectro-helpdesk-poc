import importlib
import sys
import unittest
from unittest import mock


class TestTaskNotificationOutbox(unittest.TestCase):

    def setUp(self):
        self.frappe = mock.MagicMock()

        class DuplicateEntryError(Exception):
            pass

        self.frappe.DuplicateEntryError = DuplicateEntryError

        class UniqueValidationError(Exception):
            pass

        self.frappe.UniqueValidationError = UniqueValidationError
        self.frappe.db.exists.return_value = False

        def stored_event(
            doctype, name, fields,
            as_dict=False, for_update=False,
        ):
            self.assertEqual(
                doctype, "TELECTRO Task Notification Intent"
            )
            self.assertTrue(as_dict)
            self.assertTrue(for_update)

            return {
                "event_key": name,
                "ticket": "911",
                "action": "assignment",
                "event_id": "TODO-001",
                "recipient": "tech.alfa@local.test",
            }

        self.frappe.db.get_value.side_effect = stored_event

        self.records = []

        def get_doc(payload):
            document = mock.MagicMock()

            def insert(**kwargs):
                self.records.append(dict(payload))

            document.insert.side_effect = insert
            return document

        self.frappe.get_doc.side_effect = get_doc

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

    def capture(self, **overrides):
        values = {
            "ticket": "911",
            "action": "assignment",
            "event_id": "TODO-001",
            "recipient": "tech.alfa@local.test",
            "actor_user": "supervisor@local.test",
            "note": "Please investigate",
        }
        values.update(overrides)

        return self.outbox.capture_task_notification_intent(
            **values
        )

    def test_new_event_creates_pending_intent(self):
        result = self.capture()

        self.assertTrue(result["created"])
        self.assertEqual(len(self.records), 1)

        row = self.records[0]

        self.assertEqual(
            row["doctype"],
            "TELECTRO Task Notification Intent",
        )
        self.assertEqual(row["name"], result["event_key"])
        self.assertEqual(row["event_key"], result["event_key"])
        self.assertEqual(row["ticket"], "911")
        self.assertEqual(
            row["recipient"], "tech.alfa@local.test"
        )
        self.assertEqual(row["action"], "assignment")
        self.assertEqual(row["event_id"], "TODO-001")
        self.assertEqual(
            row["actor_user"], "supervisor@local.test"
        )
        self.assertEqual(row["note"], "Please investigate")
        self.assertEqual(row["status"], "Pending")
        self.assertEqual(row["attempt_count"], 0)

    def test_existing_event_is_not_inserted_again(self):
        self.frappe.db.exists.return_value = True

        result = self.capture()

        self.assertFalse(result["created"])
        self.assertEqual(self.records, [])
        self.frappe.get_doc.assert_not_called()

    def test_distinct_events_get_distinct_identities(self):
        first = self.capture(event_id="TODO-001")
        second = self.capture(event_id="TODO-002")
        third = self.capture(
            event_id="TODO-002",
            recipient="tech.bravo@local.test",
        )

        self.assertEqual(len(self.records), 3)
        self.assertEqual(len({
            first["event_key"],
            second["event_key"],
            third["event_key"],
        }), 3)

    def test_share_context_is_separate_from_assignment(self):
        assignment = self.capture()

        shared = self.capture(
            action="share_context",
            event_id="SHARE-001",
            recipient="tech.bravo@local.test",
        )

        self.assertNotEqual(
            assignment["event_key"],
            shared["event_key"],
        )
        self.assertEqual(
            self.records[1]["action"],
            "share_context",
        )
        self.frappe.db.set_value.assert_not_called()
        self.frappe.db.sql.assert_not_called()

    def test_duplicate_insert_race_is_idempotent(self):
        self.frappe.db.exists.side_effect = [
            False, True
        ]

        def duplicate_document(payload):
            document = mock.MagicMock()
            document.insert.side_effect = (
                self.frappe.DuplicateEntryError(
                    "Duplicate notification event"
                )
            )
            return document

        self.frappe.get_doc.side_effect = duplicate_document

        result = self.capture()

        self.assertFalse(result["created"])
        self.assertTrue(result["event_key"])
        self.frappe.db.commit.assert_not_called()

    def test_invalid_events_fail_without_side_effects(self):
        for field in (
            "ticket", "action", "event_id", "recipient"
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.capture(**{field: ""})

        with self.assertRaises(ValueError):
            self.capture(action="unexpected")

        self.frappe.get_doc.assert_not_called()
        self.frappe.db.commit.assert_not_called()
        self.frappe.sendmail.assert_not_called()
        self.frappe.enqueue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
