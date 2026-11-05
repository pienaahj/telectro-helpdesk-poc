"""Permanent authorization regressions for Coordinator escalation."""

import runpy
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_request_escalation_recipients.py"

fake = ModuleType("frappe")
fake.get_all = Mock()
fake.db = SimpleNamespace(get_value=Mock())
fake.has_permission = Mock()

with patch.dict(sys.modules, {"frappe": fake}):
    resolve = runpy.run_path(str(SOURCE))[
        "resolve_coordinator_recipients"
    ]


class Ticket:
    doctype = "HD Ticket"

    def __init__(self, area="Data Request"):
        self.area = area

    def get(self, field):
        if field == "custom_service_area":
            return self.area
        return None


class RecipientTests(unittest.TestCase):

    def setUp(self):
        self.users = [
            "tech.alfa@local.test",
            "hendrik@local.test",
            "ops.test@local.test",
            "coordinator.test@local.test",
            "ops.test@local.test",
            "Administrator",
            "Guest",
        ]

        self.profiles = {}

        for user in self.users:
            if user in ("Administrator", "Guest"):
                continue

            self.profiles[user] = SimpleNamespace(
                enabled=1,
                user_type="System User",
                email=user,
            )

        self.denied = set()

        fake.get_all.reset_mock()
        fake.db.get_value.reset_mock()
        fake.has_permission.reset_mock()

        fake.get_all.side_effect = (
            lambda doctype, **kwargs: self.users
        )

        fake.db.get_value.side_effect = (
            lambda doctype, user, fields, as_dict:
            self.profiles.get(user)
        )

        fake.has_permission.side_effect = (
            lambda doctype, ptype, doc, user:
            user not in self.denied
        )

        self.ticket = Ticket()

    def test_authorized_coordinators(self):
        result = resolve(self.ticket)

        self.assertEqual(result, sorted(self.profiles))

    def test_correct_functional_role(self):
        resolve(self.ticket)

        fake.get_all.assert_called_once_with(
            "Has Role",
            filters={
                "role": "TELECTRO-POC Role - Coordinator Ops",
                "parenttype": "User",
            },
            pluck="parent",
        )

    def test_disabled_user_excluded(self):
        self.profiles["ops.test@local.test"].enabled = 0

        self.assertNotIn(
            "ops.test@local.test",
            resolve(self.ticket),
        )

    def test_website_user_excluded(self):
        self.profiles["ops.test@local.test"].user_type = "Website User"

        self.assertNotIn(
            "ops.test@local.test",
            resolve(self.ticket),
        )

    def test_invalid_email_excluded(self):
        self.profiles["ops.test@local.test"].email = "invalid"

        self.assertNotIn(
            "ops.test@local.test",
            resolve(self.ticket),
        )

    def test_permission_denial_excluded(self):
        self.denied.add("ops.test@local.test")

        self.assertNotIn(
            "ops.test@local.test",
            resolve(self.ticket),
        )

    def test_missing_user_excluded(self):
        del self.profiles["ops.test@local.test"]

        self.assertNotIn(
            "ops.test@local.test",
            resolve(self.ticket),
        )

    def test_non_coordinator_excluded(self):
        self.users = []

        self.assertEqual(resolve(self.ticket), [])

    def test_other_service_area_excluded(self):
        ticket = Ticket("PABX")

        self.assertEqual(resolve(ticket), [])
        fake.get_all.assert_not_called()

    def test_wrong_doctype_rejected(self):
        ticket = Ticket()
        ticket.doctype = "HD Customer"

        with self.assertRaises(ValueError):
            resolve(ticket)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        RecipientTests
    )

    result = unittest.TextTestRunner(verbosity=2).run(suite)

    assert result.wasSuccessful()
    assert result.testsRun == 10

    print("ESC_27_REGRESSION_COUNT=10")
    print("ESC_27_RECIPIENT_AUTHORIZATION=PASS")
