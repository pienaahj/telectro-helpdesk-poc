import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2]),
)

from telephony.data_request_arrival import (
    intent_name,
    plan_arrival_intents,
)


class TestDataRequestArrivalContract(unittest.TestCase):
    def plan(self, members, eligible=lambda user: True,
             area="Data Request", ticket="950"):
        return plan_arrival_intents(
            ticket_name=ticket,
            service_area=area,
            members=members,
            eligible_user=eligible,
        )

    def test_two_specialists_receive_two_intents(self):
        rows = self.plan(["tech.bravo", "tech.alfa"])
        self.assertEqual(
            [row["recipient"] for row in rows],
            ["tech.alfa", "tech.bravo"],
        )

    def test_duplicate_members_are_deduplicated(self):
        rows = self.plan([
            "tech.alfa", "tech.alfa", "tech.bravo"
        ])
        self.assertEqual(len(rows), 2)

    def test_repeated_planning_has_stable_identifiers(self):
        first = self.plan(["tech.alfa", "tech.bravo"])
        second = self.plan(["tech.bravo", "tech.alfa"])
        self.assertEqual(first, second)

    def test_different_tickets_have_different_identifiers(self):
        first = self.plan(["tech.alfa"], ticket="950")
        second = self.plan(["tech.alfa"], ticket="951")
        self.assertNotEqual(first[0]["name"], second[0]["name"])

    def test_different_recipients_have_different_identifiers(self):
        rows = self.plan(["tech.alfa", "tech.bravo"])
        self.assertNotEqual(rows[0]["name"], rows[1]["name"])

    def test_non_data_request_is_ignored(self):
        def should_not_be_called(user):
            raise AssertionError("Eligibility called for other area")

        self.assertEqual(
            self.plan(
                ["tech.alfa"],
                eligible=should_not_be_called,
                area="Routing",
            ),
            [],
        )

    def test_empty_team_produces_no_intents(self):
        self.assertEqual(self.plan([]), [])
        self.assertEqual(self.plan(None), [])

    def test_disabled_or_ineligible_user_is_excluded(self):
        rows = self.plan(
            ["tech.alfa", "tech.bravo"],
            eligible=lambda user: user == "tech.alfa",
        )
        self.assertEqual(
            [row["recipient"] for row in rows],
            ["tech.alfa"],
        )

    def test_system_accounts_and_blanks_are_excluded(self):
        rows = self.plan([
            "Administrator", "Guest", None, "", " ",
            "tech.alfa",
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["recipient"], "tech.alfa")

    def test_blank_ticket_produces_no_intents(self):
        self.assertEqual(
            self.plan(["tech.alfa"], ticket=""),
            [],
        )

    def test_invalid_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            intent_name("", "tech.alfa")
        with self.assertRaises(ValueError):
            intent_name("950", "")

    def test_contract_does_not_contain_assignment(self):
        rows = self.plan(["tech.alfa", "tech.bravo"])
        for row in rows:
            self.assertEqual(
                set(row),
                {"name", "ticket", "recipient", "event"},
            )
            self.assertEqual(row["event"], "arrival")
            self.assertTrue(row["name"].startswith("TDRN-"))

    def test_eligibility_failure_is_not_silently_ignored(self):
        def failing_lookup(user):
            raise RuntimeError("User lookup failed")

        with self.assertRaises(RuntimeError):
            self.plan(
                ["tech.alfa"],
                eligible=failing_lookup,
            )


if __name__ == "__main__":
    unittest.main()
