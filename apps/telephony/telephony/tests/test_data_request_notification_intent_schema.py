import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = (
    ROOT / "ftelephony" / "doctype"
    / "telectro_data_request_notification_intent"
)
SCHEMA = DIRECTORY / "telectro_data_request_notification_intent.json"
CONTROLLER = DIRECTORY / "telectro_data_request_notification_intent.py"


class TestDataRequestNotificationIntentSchema(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA.read_text())
        cls.fields = {
            row["fieldname"]: row
            for row in cls.schema["fields"]
        }

    def test_correct_doctype_identity(self):
        self.assertEqual(
            self.schema["name"],
            "TELECTRO Data Request Notification Intent",
        )
        self.assertEqual(self.schema["module"], "FTelephony")
        self.assertEqual(self.schema["istable"], 0)

    def test_deterministic_unique_name(self):
        self.assertEqual(
            self.schema["autoname"],
            "field:intent_id",
        )
        self.assertEqual(self.fields["intent_id"]["unique"], 1)
        self.assertEqual(self.fields["intent_id"]["reqd"], 1)

    def test_ticket_and_recipient_are_required_links(self):
        for name, target in (
            ("ticket", "HD Ticket"),
            ("recipient", "User"),
        ):
            field = self.fields[name]
            self.assertEqual(field["fieldtype"], "Link")
            self.assertEqual(field["options"], target)
            self.assertEqual(field["reqd"], 1)

    def test_arrival_event(self):
        field = self.fields["event"]
        self.assertEqual(field["default"], "arrival")
        self.assertEqual(
            field["options"].splitlines(),
            ["arrival", "escalation"],
        )
        self.assertEqual(field["reqd"], 1)

    def test_delivery_starts_pending(self):
        for name in (
            "delivery_state",
            "in_app_state",
            "email_state",
        ):
            self.assertEqual(
                self.fields[name]["default"],
                "Pending",
            )

    def test_email_queued_is_not_email_sent(self):
        options = self.fields["email_state"]["options"].splitlines()
        self.assertIn("Queued", options)
        self.assertIn("Sent", options)
        self.assertNotEqual(
            options.index("Queued"),
            options.index("Sent"),
        )

    def test_delivery_audit_fields_exist(self):
        for name in (
            "notification_log",
            "email_queue",
            "attempt_count",
            "last_attempt_on",
            "next_attempt_on",
            "last_error",
        ):
            self.assertIn(name, self.fields)

    def test_no_manual_mutation_permissions(self):
        roles = {
            row["role"]
            for row in self.schema["permissions"]
        }
        self.assertEqual(
            roles,
            {"System Manager", "Pilot Admin"},
        )
        for permission in self.schema["permissions"]:
            self.assertEqual(permission["read"], 1)
            for action in ("create", "write", "delete", "share"):
                self.assertEqual(permission[action], 0)

    def test_no_automatic_delivery_hook(self):
        source = CONTROLLER.read_text()
        ast.parse(source)
        self.assertNotIn("frappe.sendmail(", source)
        self.assertNotIn("frappe.enqueue(", source)
        self.assertNotIn("def after_insert(", source)
        self.assertNotIn("def on_update(", source)


if __name__ == "__main__":
    unittest.main()
