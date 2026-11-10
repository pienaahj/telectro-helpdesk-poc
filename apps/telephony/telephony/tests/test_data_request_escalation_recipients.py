
"""Permanent authorization regressions for Data Request escalation."""

import runpy
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_request_escalation_recipients.py"
SETTING = "telectro_data_request_escalation_recipients"

fake = ModuleType("frappe")
fake.conf = {}
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
        self.profiles = {
            user: SimpleNamespace(
                enabled=1,
                user_type="System User",
                email=user,
            )
            for user in (
                "hendrik@local.test",
                "coordinator.test@local.test",
                "sean@telectro.co.za",
            )
        }

        fake.conf.clear()
        fake.conf[SETTING] = ["hendrik@local.test"]

        fake.get_all.reset_mock()
        fake.db.get_value.reset_mock(
            return_value=True,
            side_effect=True,
        )
        fake.has_permission.reset_mock(
            return_value=True,
            side_effect=True,
        )

        fake.db.get_value.side_effect = (
            lambda doctype, user, fields, as_dict:
            self.profiles.get(user)
        )
        fake.has_permission.return_value = True

        self.ticket = Ticket()

    def test_only_configured_accounts_selected(self):
        self.assertEqual(
            resolve(self.ticket),
            ["hendrik@local.test"],
        )
        fake.get_all.assert_not_called()

    def test_missing_or_empty_configuration_fails_closed(self):
        for configured in (None, []):
            with self.subTest(configured=configured):
                fake.conf.clear()
                if configured is not None:
                    fake.conf[SETTING] = configured

                self.assertEqual(resolve(self.ticket), [])

    def test_malformed_configuration_rejected(self):
        for configured in (
            "hendrik@local.test",
            {"recipient": "hendrik@local.test"},
            [None],
        ):
            with self.subTest(configured=configured):
                fake.conf[SETTING] = configured
                with self.assertRaises(ValueError):
                    resolve(self.ticket)

    def test_duplicate_recipients_normalized(self):
        fake.conf[SETTING] = [
            " sean@telectro.co.za ",
            "hendrik@local.test",
            "sean@telectro.co.za",
            "",
        ]

        self.assertEqual(
            resolve(self.ticket),
            [
                "hendrik@local.test",
                "sean@telectro.co.za",
            ],
        )

    def test_explicit_recipient_does_not_require_role(self):
        # The explicit allowlist replaces role-based expansion.
        self.assertEqual(
            resolve(self.ticket),
            ["hendrik@local.test"],
        )
        fake.get_all.assert_not_called()

    def test_disabled_account_excluded(self):
        self.profiles["hendrik@local.test"].enabled = 0

        self.assertEqual(resolve(self.ticket), [])

    def test_website_account_excluded(self):
        self.profiles[
            "hendrik@local.test"
        ].user_type = "Website User"

        self.assertEqual(resolve(self.ticket), [])

    def test_invalid_email_excluded(self):
        self.profiles["hendrik@local.test"].email = "invalid"

        self.assertEqual(resolve(self.ticket), [])

    def test_missing_user_excluded(self):
        del self.profiles["hendrik@local.test"]

        self.assertEqual(resolve(self.ticket), [])

    def test_permission_denial_excluded(self):
        fake.has_permission.return_value = False

        self.assertEqual(resolve(self.ticket), [])

    def test_system_accounts_excluded(self):
        fake.conf[SETTING] = [
            "Administrator",
            "Guest",
            "hendrik@local.test",
        ]

        self.assertEqual(
            resolve(self.ticket),
            ["hendrik@local.test"],
        )

    def test_other_service_area_excluded(self):
        self.assertEqual(resolve(Ticket("PABX")), [])
        fake.db.get_value.assert_not_called()

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
    assert result.testsRun == 13

    print("ESC_27_REGRESSION_COUNT=13")
    print("ESC_27_RECIPIENT_AUTHORIZATION=PASS")
