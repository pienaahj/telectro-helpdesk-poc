import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2]),
)

frappe_stub = types.ModuleType("frappe")
frappe_stub.DuplicateEntryError = type(
    "DuplicateEntryError", (Exception,), {}
)

with mock.patch.dict(sys.modules, {"frappe": frappe_stub}):
    module = importlib.import_module(
        "telephony.data_request_arrival_outbox"
    )


class FakeDatabase:
    def __init__(self):
        self.intents = {}
        self.users = {}

    def get_value(self, doctype, name, fields, as_dict=False):
        assert as_dict is True

        if doctype == "User":
            return self.users.get(name)

        if doctype == module.DOCTYPE:
            return self.intents.get(name)

        raise AssertionError(doctype)


class FakeIntent:
    def __init__(self, data, database, *, race=False, error=None):
        self.data = data
        self.db = database
        self.race = race
        self.error = error

    def insert(self, ignore_permissions=False):
        assert ignore_permissions is True

        if self.error:
            raise self.error

        name = self.data["intent_id"]

        if name in self.db.intents or self.race:
            if self.race:
                self.db.intents[name] = {
                    key: self.data[key]
                    for key in ("ticket", "recipient", "event")
                }

            raise frappe_stub.DuplicateEntryError(name)

        self.db.intents[name] = {
            key: self.data[key]
            for key in ("ticket", "recipient", "event")
        }


class TestArrivalOutbox(unittest.TestCase):
    def setUp(self):
        self.db = FakeDatabase()

        self.team = {
            "users": [
                {"user": "tech.bravo"},
                {"user": "tech.alfa"},
            ]
        }

        self.created = []
        self.race = False
        self.error = None

        frappe_stub.db = self.db
        frappe_stub.get_doc = mock.Mock(
            side_effect=self.get_doc
        )

        self.ticket = types.SimpleNamespace(
            doctype="HD Ticket",
            name="950",
            get={
                "custom_service_area": "Data Request",
                "agent_group": "Data Provisioning",
                "status": "Open",
            }.get,
        )

        for user in ("tech.bravo", "tech.alfa"):
            self.db.users[user] = {
                "enabled": 1,
                "email": user + "@example.invalid",
                "user_type": "System User",
            }

    def get_doc(self, *args):
        if args == ("HD Team", "Data Provisioning"):
            return self.team

        if len(args) == 1 and isinstance(args[0], dict):
            self.created.append(args[0])

            return FakeIntent(
                args[0],
                self.db,
                race=self.race,
                error=self.error,
            )

        raise AssertionError(args)

    def test_two_intents_and_pending_states(self):
        result = module.capture_arrival_intents(self.ticket)

        self.assertEqual(len(result), 2)
        self.assertEqual(len(self.db.intents), 2)

        self.assertEqual(
            [row["recipient"] for row in self.created],
            ["tech.alfa", "tech.bravo"],
        )

        for row in self.created:
            self.assertEqual(
                (
                    row["delivery_state"],
                    row["in_app_state"],
                    row["email_state"],
                ),
                ("Pending", "Pending", "Pending"),
            )

            self.assertNotIn("_assign", row)

    def test_repeat_is_idempotent(self):
        original = module.capture_arrival_intents(self.ticket)

        self.assertEqual(
            module.capture_arrival_intents(self.ticket),
            [],
        )

        self.assertEqual(len(self.db.intents), 2)
        self.assertEqual(len(self.created), 2)
        self.assertEqual(len(original), 2)

    def test_duplicate_at_insert_race_is_idempotent(self):
        self.race = True

        self.assertEqual(
            module.capture_arrival_intents(self.ticket),
            [],
        )

        self.assertEqual(len(self.db.intents), 2)

    def test_identity_collision_raises(self):
        original = module.capture_arrival_intents(self.ticket)

        self.db.intents[original[0]]["recipient"] = "wrong-user"

        with self.assertRaisesRegex(
            ValueError, "identity collision"
        ):
            module.capture_arrival_intents(self.ticket)

    def test_unexpected_insert_failure_propagates(self):
        self.error = RuntimeError("Database unavailable")

        with self.assertRaisesRegex(
            RuntimeError, "Database unavailable"
        ):
            module.capture_arrival_intents(self.ticket)

    def test_non_ticket_does_not_query_team(self):
        self.ticket.doctype = "ToDo"

        self.assertEqual(
            module.capture_arrival_intents(self.ticket),
            [],
        )

        frappe_stub.get_doc.assert_not_called()

    def test_other_area_is_ignored(self):
        self.ticket.get = {
            "custom_service_area": "Routing",
        }.get

        self.assertEqual(
            module.capture_arrival_intents(self.ticket),
            [],
        )

        frappe_stub.get_doc.assert_not_called()

    def test_wrong_team_is_ignored(self):
        self.ticket.get = {
            "custom_service_area": "Data Request",
            "agent_group": "Helpdesk Team",
        }.get

        self.assertEqual(
            module.capture_arrival_intents(self.ticket),
            [],
        )

        frappe_stub.get_doc.assert_not_called()

    def test_non_open_ticket_is_ignored(self):
        self.ticket.get = {
            "custom_service_area": "Data Request",
            "agent_group": "Data Provisioning",
            "status": "Resolved",
        }.get

        self.assertEqual(
            module.capture_arrival_intents(self.ticket),
            [],
        )

        frappe_stub.get_doc.assert_not_called()

    def test_empty_team_no_intents(self):
        self.team["users"] = []

        self.assertEqual(
            module.capture_arrival_intents(self.ticket),
            [],
        )

        self.assertFalse(self.db.intents)

    def test_disabled_user_excluded(self):
        self.db.users["tech.bravo"]["enabled"] = 0

        self.assertEqual(
            len(module.capture_arrival_intents(self.ticket)),
            1,
        )

        self.assertEqual(
            self.created[0]["recipient"],
            "tech.alfa",
        )

    def test_website_user_excluded(self):
        self.db.users["tech.bravo"]["user_type"] = "Website User"

        self.assertEqual(
            len(module.capture_arrival_intents(self.ticket)),
            1,
        )

    def test_missing_email_excluded(self):
        self.db.users["tech.bravo"]["email"] = ""

        self.assertEqual(
            len(module.capture_arrival_intents(self.ticket)),
            1,
        )

    def test_missing_user_excluded(self):
        del self.db.users["tech.bravo"]

        self.assertEqual(
            len(module.capture_arrival_intents(self.ticket)),
            1,
        )

    def test_duplicate_members_deduplicated(self):
        self.team["users"].append({"user": "tech.alfa"})

        self.assertEqual(
            len(module.capture_arrival_intents(self.ticket)),
            2,
        )

    def test_blank_ticket_name_raises(self):
        self.ticket.name = ""

        with self.assertRaisesRegex(
            ValueError, "name is required"
        ):
            module.capture_arrival_intents(self.ticket)


if __name__ == "__main__":
    unittest.main()
