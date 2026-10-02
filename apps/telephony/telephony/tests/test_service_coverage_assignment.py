import unittest
from unittest import mock

from telephony import service_coverage


class TestContextualTeamAssignment(unittest.TestCase):
    def test_no_matching_coverage_leaves_native_team_path_untouched(self):
        with mock.patch.object(
            service_coverage,
            "get_matching_coverage_rows_for_ticket",
            return_value=[],
        ):
            result = service_coverage.resolve_contextual_team_assignment(
                "TEST-NO-COVERAGE",
                [
                    "pierre@telectro.co.za",
                    "sean@telectro.co.za",
                ],
                last_user="pierre@telectro.co.za",
            )

        self.assertFalse(result["coverage_applies"])
        self.assertEqual(result["eligible_users"], [])
        self.assertEqual(result["selected_user"], "")

    def test_matching_coverage_is_intersected_with_native_team_membership(self):
        coverage_rows = [
            {
                "user": "sean@telectro.co.za",
                "coverage_role": "Eligible",
                "priority": 100,
            },
            {
                "user": "outside.team@telectro.co.za",
                "coverage_role": "Eligible",
                "priority": 100,
            },
        ]

        with mock.patch.object(
            service_coverage,
            "get_matching_coverage_rows_for_ticket",
            return_value=coverage_rows,
        ):
            result = service_coverage.resolve_contextual_team_assignment(
                "TEST-INTERSECTION",
                [
                    "pierre@telectro.co.za",
                    "sean@telectro.co.za",
                    "armandt@telectro.co.za",
                ],
            )

        self.assertTrue(result["coverage_applies"])
        self.assertEqual(
            result["eligible_users"],
            ["sean@telectro.co.za"],
        )
        self.assertEqual(
            result["selected_user"],
            "sean@telectro.co.za",
        )

    def test_native_team_order_controls_contextual_rotation(self):
        coverage_rows = [
            {
                "user": "kyle@telectro.co.za",
                "coverage_role": "Primary",
                "priority": 1,
            },
            {
                "user": "armandt@telectro.co.za",
                "coverage_role": "Backup",
                "priority": 999,
            },
            {
                "user": "pierre@telectro.co.za",
                "coverage_role": "Eligible",
                "priority": 50,
            },
        ]

        with mock.patch.object(
            service_coverage,
            "get_matching_coverage_rows_for_ticket",
            return_value=coverage_rows,
        ):
            result = service_coverage.resolve_contextual_team_assignment(
                "TEST-NATIVE-ORDER",
                [
                    "pierre@telectro.co.za",
                    "sean@telectro.co.za",
                    "armandt@telectro.co.za",
                    "kyle@telectro.co.za",
                ],
                last_user="sean@telectro.co.za",
            )

        self.assertEqual(
            result["eligible_users"],
            [
                "pierre@telectro.co.za",
                "armandt@telectro.co.za",
                "kyle@telectro.co.za",
            ],
        )
        self.assertEqual(
            result["selected_user"],
            "armandt@telectro.co.za",
        )

    def test_last_user_inside_team_but_outside_coverage_advances_to_next_eligible(self):
        coverage_rows = [
            {"user": "armandt@telectro.co.za"},
            {"user": "kyle@telectro.co.za"},
        ]

        with mock.patch.object(
            service_coverage,
            "get_matching_coverage_rows_for_ticket",
            return_value=coverage_rows,
        ):
            result = service_coverage.resolve_contextual_team_assignment(
                "TEST-SKIP-NON-COVERED-LAST",
                [
                    "pierre@telectro.co.za",
                    "sean@telectro.co.za",
                    "armandt@telectro.co.za",
                    "kyle@telectro.co.za",
                ],
                last_user="sean@telectro.co.za",
            )

        self.assertEqual(
            result["selected_user"],
            "armandt@telectro.co.za",
        )

    def test_contextual_rotation_wraps_in_native_team_order(self):
        coverage_rows = [
            {"user": "pierre@telectro.co.za"},
            {"user": "armandt@telectro.co.za"},
            {"user": "kyle@telectro.co.za"},
        ]

        with mock.patch.object(
            service_coverage,
            "get_matching_coverage_rows_for_ticket",
            return_value=coverage_rows,
        ):
            result = service_coverage.resolve_contextual_team_assignment(
                "TEST-WRAP",
                [
                    "pierre@telectro.co.za",
                    "sean@telectro.co.za",
                    "armandt@telectro.co.za",
                    "kyle@telectro.co.za",
                ],
                last_user="kyle@telectro.co.za",
            )

        self.assertEqual(
            result["selected_user"],
            "pierre@telectro.co.za",
        )

    def test_unknown_last_user_starts_with_first_eligible_native_team_member(self):
        coverage_rows = [
            {"user": "armandt@telectro.co.za"},
            {"user": "kyle@telectro.co.za"},
        ]

        with mock.patch.object(
            service_coverage,
            "get_matching_coverage_rows_for_ticket",
            return_value=coverage_rows,
        ):
            result = service_coverage.resolve_contextual_team_assignment(
                "TEST-UNKNOWN-LAST",
                [
                    "pierre@telectro.co.za",
                    "sean@telectro.co.za",
                    "armandt@telectro.co.za",
                    "kyle@telectro.co.za",
                ],
                last_user="old.user@telectro.co.za",
            )

        self.assertEqual(
            result["selected_user"],
            "armandt@telectro.co.za",
        )

    def test_matching_coverage_with_empty_intersection_does_not_fall_back(self):
        coverage_rows = [
            {"user": "outside.team@telectro.co.za"},
        ]

        with mock.patch.object(
            service_coverage,
            "get_matching_coverage_rows_for_ticket",
            return_value=coverage_rows,
        ):
            result = service_coverage.resolve_contextual_team_assignment(
                "TEST-EMPTY-INTERSECTION",
                [
                    "pierre@telectro.co.za",
                    "sean@telectro.co.za",
                ],
            )

        self.assertTrue(result["coverage_applies"])
        self.assertEqual(result["eligible_users"], [])
        self.assertEqual(result["selected_user"], "")

    def test_duplicate_coverage_rows_do_not_duplicate_assignment_population(self):
        coverage_rows = [
            {"user": "pierre@telectro.co.za"},
            {"user": "pierre@telectro.co.za"},
            {"user": "sean@telectro.co.za"},
        ]

        with mock.patch.object(
            service_coverage,
            "get_matching_coverage_rows_for_ticket",
            return_value=coverage_rows,
        ):
            result = service_coverage.resolve_contextual_team_assignment(
                "TEST-DUPLICATES",
                [
                    "pierre@telectro.co.za",
                    "sean@telectro.co.za",
                ],
            )

        self.assertEqual(
            result["eligible_users"],
            [
                "pierre@telectro.co.za",
                "sean@telectro.co.za",
            ],
        )

if __name__ == "__main__":
    unittest.main()
