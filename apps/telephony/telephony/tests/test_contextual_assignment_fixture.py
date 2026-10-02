import json
import unittest

import frappe

from telephony import hooks as telephony_hooks


FIELD_NAME = "HD Ticket-custom_contextual_assignment_hold"


class TestContextualAssignmentHoldFixture(unittest.TestCase):
    def test_hold_field_is_defined_as_hidden_system_state(self):
        fixture_path = frappe.get_app_path(
            "telephony",
            "fixtures",
            "custom_field.json",
        )

        with open(fixture_path) as handle:
            rows = json.load(handle)

        row = next(
            (
                row
                for row in rows
                if row.get("name") == FIELD_NAME
            ),
            None,
        )

        self.assertIsNotNone(row)

        self.assertEqual(row.get("dt"), "HD Ticket")
        self.assertEqual(
            row.get("fieldname"),
            "custom_contextual_assignment_hold",
        )
        self.assertEqual(
            row.get("label"),
            "Contextual Assignment Hold",
        )
        self.assertEqual(row.get("fieldtype"), "Check")
        self.assertEqual(row.get("default"), "0")
        self.assertEqual(row.get("hidden"), 1)
        self.assertEqual(row.get("read_only"), 1)
        self.assertEqual(row.get("no_copy"), 1)

    def test_hold_field_is_whitelisted_for_custom_field_fixture(self):
        custom_field_fixture = next(
            (
                fixture
                for fixture in telephony_hooks.fixtures
                if fixture.get("dt") == "Custom Field"
            ),
            None,
        )

        self.assertIsNotNone(custom_field_fixture)

        filters = custom_field_fixture.get("filters") or []

        names = []

        for fixture_filter in filters:
            if (
                len(fixture_filter) >= 3
                and fixture_filter[0] == "name"
                and fixture_filter[1] == "in"
            ):
                names.extend(fixture_filter[2] or [])

        self.assertIn(FIELD_NAME, names)

    def test_contextual_assignment_durability_hook_is_registered_after_hd_team_durability(
        self,
    ):
        hd_team_hook = (
            "telephony.setup.hd_team_durability.after_migrate"
        )

        contextual_hook = (
            "telephony.setup.contextual_assignment_durability."
            "after_migrate"
        )

        self.assertEqual(
            telephony_hooks.after_migrate.count(
                contextual_hook
            ),
            1,
        )

        self.assertIn(
            hd_team_hook,
            telephony_hooks.after_migrate,
        )

        self.assertLess(
            telephony_hooks.after_migrate.index(
                hd_team_hook
            ),
            telephony_hooks.after_migrate.index(
                contextual_hook
            ),
        )

if __name__ == "__main__":
    unittest.main()
