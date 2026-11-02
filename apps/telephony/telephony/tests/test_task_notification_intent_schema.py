import json
import unittest
from pathlib import Path


SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "ftelephony"
    / "doctype"
    / "telectro_task_notification_intent"
    / "telectro_task_notification_intent.json"
)


def load_schema():
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def fields(document):
    return {
        field["fieldname"]: field
        for field in document["fields"]
    }


class TestTaskNotificationIntentSchema(unittest.TestCase):

    def test_doctype_identity_and_naming(self):
        doc = load_schema()

        self.assertEqual(
            doc["name"],
            "TELECTRO Task Notification Intent",
        )
        self.assertEqual(doc["module"], "FTelephony")
        self.assertEqual(doc["doctype"], "DocType")
        self.assertEqual(doc["engine"], "InnoDB")
        self.assertEqual(
            doc["autoname"], "field:event_key"
        )
        self.assertFalse(doc.get("istable", 0))

    def test_event_identity_is_unique_and_complete(self):
        f = fields(load_schema())

        self.assertEqual(f["event_key"]["fieldtype"], "Data")
        self.assertEqual(f["event_key"].get("unique"), 1)
        self.assertEqual(f["event_key"].get("reqd"), 1)

        for field, fieldtype in {
            "ticket": "Link",
            "action": "Select",
            "event_id": "Data",
            "recipient": "Link",
            "actor_user": "Link",
            "note": "Small Text",
        }.items():
            self.assertEqual(f[field]["fieldtype"], fieldtype)

        self.assertEqual(f["ticket"]["options"], "HD Ticket")
        self.assertEqual(f["recipient"]["options"], "User")
        self.assertEqual(f["actor_user"]["options"], "User")

        actions = set(f["action"]["options"].splitlines())

        self.assertEqual(actions, {
            "assignment",
            "claim",
            "handoff",
            "share_context",
        })

        for field in ("ticket", "action", "event_id", "recipient"):
            self.assertEqual(f[field].get("reqd"), 1)

    def test_initial_state_is_pending(self):
        f = fields(load_schema())

        self.assertEqual(f["status"]["fieldtype"], "Select")
        self.assertEqual(f["status"]["default"], "Pending")

        self.assertTrue({
            "Pending", "Processing", "Retry",
            "Completed", "Failed",
        }.issubset(set(f["status"]["options"].splitlines())))

        self.assertEqual(f["attempt_count"]["fieldtype"], "Int")
        self.assertEqual(
            str(f["attempt_count"]["default"]), "0"
        )

    def test_in_app_and_email_states_are_separate(self):
        f = fields(load_schema())

        self.assertEqual(f["in_app_status"]["fieldtype"], "Select")
        self.assertEqual(f["email_status"]["fieldtype"], "Select")

        self.assertEqual(f["in_app_status"]["default"], "Pending")
        self.assertEqual(f["email_status"]["default"], "Pending")

        self.assertTrue({
            "Pending", "Created", "Retry", "Failed",
        }.issubset(
            set(f["in_app_status"]["options"].splitlines())
        ))

        self.assertTrue({
            "Pending", "Queued", "TransportAccepted",
            "Retry", "Failed",
        }.issubset(
            set(f["email_status"]["options"].splitlines())
        ))

        self.assertEqual(
            f["notification_log"]["options"], "Notification Log"
        )
        self.assertEqual(
            f["email_queue"]["options"], "Email Queue"
        )

    def test_retry_and_delivery_evidence_fields(self):
        f = fields(load_schema())

        for field in (
            "last_attempt_at",
            "next_attempt_at",
            "email_transport_accepted_at",
        ):
            self.assertEqual(f[field]["fieldtype"], "Datetime")

        self.assertEqual(
            f["last_error"]["fieldtype"], "Long Text"
        )

    def test_operational_permissions_are_read_only(self):
        doc = load_schema()
        permissions = doc["permissions"]

        self.assertTrue(permissions)

        approved = {
            "System Manager",
            "Pilot Admin",
        }

        for permission in permissions:
            self.assertIn(permission["role"], approved)
            self.assertEqual(permission.get("create", 0), 0)
            self.assertEqual(permission.get("write", 0), 0)
            self.assertEqual(permission.get("delete", 0), 0)
            self.assertEqual(permission.get("share", 0), 0)


if __name__ == "__main__":
    unittest.main()
