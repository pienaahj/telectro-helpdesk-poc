
import unittest
from unittest import mock

from telephony import native_team_assignment


class TestNativeTeamAssignmentState(unittest.TestCase):
    def test_disabled_rule_returns_empty_assignment_population(self):
        rule_name = "TEST-CCTV-ASSIGNMENT-RULE"

        with mock.patch.object(
            native_team_assignment,
            "frappe",
        ) as frappe_mock:
            frappe_mock.db.get_value.side_effect = [
                rule_name,
                {
                    "disabled": 1,
                    "last_user": "tech.bravo@local.test",
                },
            ]

            result = native_team_assignment.native_team_assignment_state(
                "CCTV"
            )

        self.assertEqual(
            result,
            {
                "rule": "",
                "users": [],
                "last_user": "",
            },
        )

        self.assertEqual(
            frappe_mock.db.get_value.call_args_list,
            [
                mock.call(
                    "HD Team",
                    "CCTV",
                    "assignment_rule",
                ),
                mock.call(
                    "Assignment Rule",
                    rule_name,
                    ["disabled", "last_user"],
                    as_dict=True,
                ),
            ],
        )

        frappe_mock.get_all.assert_not_called()
