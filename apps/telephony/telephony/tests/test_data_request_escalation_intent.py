"""Permanent Data Request escalation-intent regressions."""

import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

escalation = runpy.run_path(
    str(ROOT / "data_request_escalation_intent.py")
)
arrival = runpy.run_path(
    str(ROOT / "data_request_arrival.py")
)

identity = escalation["escalation_intent_name"]
plan = escalation["plan_escalation_intents"]

TICKET = "956"
USER = "coordinator@example.test"


class EscalationIntentTests(unittest.TestCase):

    def test_deterministic_identity(self):
        self.assertEqual(
            identity(TICKET, USER),
            identity(TICKET, USER),
        )

    def test_arrival_identity_separation(self):
        self.assertNotEqual(
            identity(TICKET, USER),
            arrival["intent_name"](TICKET, USER),
        )

    def test_ticket_isolation(self):
        self.assertNotEqual(
            identity("956", USER),
            identity("957", USER),
        )

    def test_recipient_isolation(self):
        self.assertNotEqual(
            identity(TICKET, USER),
            identity(TICKET, "other@example.test"),
        )

    def test_deduplication(self):
        items = plan(
            ticket_name=TICKET,
            recipients=[USER, USER],
            eligible_user=lambda user: True,
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["event"], "escalation")

    def test_excluded_system_users(self):
        items = plan(
            ticket_name=TICKET,
            recipients=["Administrator", "Guest", USER],
            eligible_user=lambda user: True,
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["recipient"], USER)

    def test_ineligible_recipient(self):
        items = plan(
            ticket_name=TICKET,
            recipients=[USER],
            eligible_user=lambda user: False,
        )
        self.assertEqual(items, [])

    def test_missing_ticket_rejected(self):
        with self.assertRaises(ValueError):
            plan(
                ticket_name="",
                recipients=[USER],
                eligible_user=lambda user: True,
            )

    def test_missing_eligibility_callback_rejected(self):
        with self.assertRaises(TypeError):
            plan(
                ticket_name=TICKET,
                recipients=[USER],
                eligible_user=None,
            )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        EscalationIntentTests
    )

    result = unittest.TextTestRunner(verbosity=2).run(suite)

    assert result.wasSuccessful()
    assert result.testsRun == 9

    print("ESC_20_REGRESSION_COUNT=9")
    print("ESC_20_PERSISTENT_REGRESSIONS=PASS")
