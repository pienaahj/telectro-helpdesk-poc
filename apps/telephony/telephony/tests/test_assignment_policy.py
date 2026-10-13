import unittest
from unittest import mock

from telephony import assignment_policy

def _reject(message):
    raise ValueError(str(message))

def policy_row(name, scope, mode):
    return {
        "name": name,
        "coverage_scope": scope,
        "customer": None,
        "campus": None,
        "service_area": "CCTV",
        "assignment_mode": mode,
    }


class TestAssignmentPolicyResolver(unittest.TestCase):

    def setUp(self):
        get_all_patch = mock.patch.object(
            assignment_policy.frappe,
            "get_all",
            return_value=[],
        )
        self.get_all = get_all_patch.start()
        self.addCleanup(get_all_patch.stop)

        throw_patch = mock.patch.object(
            assignment_policy.frappe,
            "throw",
            side_effect=_reject,
        )
        self.throw = throw_patch.start()
        self.addCleanup(throw_patch.stop)

    def test_no_matching_policy_preserves_fallback(self):
        result = assignment_policy.get_matching_assignment_policy(
            customer="Boschendal",
            campus="Boschendal",
            service_area="CCTV",
        )

        self.assertIsNone(result)

        scopes = [
            call.kwargs["filters"]["coverage_scope"]
            for call in self.get_all.call_args_list
        ]

        self.assertEqual(
            scopes,
            [
                "Customer/Campus",
                "Campus",
                "Customer",
                "Default",
            ],
        )

    def test_customer_campus_policy_has_highest_precedence(self):
        self.get_all.return_value = [
            policy_row(
                "TAP-BOSCHENDAL-CAMPUS",
                "Customer/Campus",
                "Round Robin",
            )
        ]

        result = assignment_policy.get_matching_assignment_policy(
            customer="Boschendal",
            campus="Boschendal",
            service_area="CCTV",
        )

        self.assertEqual(result["assignment_mode"], "Round Robin")
        self.assertEqual(result["name"], "TAP-BOSCHENDAL-CAMPUS")

        self.get_all.assert_called_once()

        filters = self.get_all.call_args.kwargs["filters"]

        self.assertEqual(filters["customer"], "Boschendal")
        self.assertEqual(filters["campus"], "Boschendal")
        self.assertEqual(filters["service_area"], "CCTV")
        self.assertEqual(filters["enabled"], 1)

    def test_campus_policy_precedes_customer_policy(self):
        def lookup(doctype, filters, **kwargs):
            if filters["coverage_scope"] == "Campus":
                return [
                    policy_row(
                        "TAP-CAMPUS",
                        "Campus",
                        "Round Robin",
                    )
                ]
            return []

        self.get_all.side_effect = lookup

        result = assignment_policy.get_matching_assignment_policy(
            customer="Boschendal",
            campus="Boschendal",
            service_area="CCTV",
        )

        self.assertEqual(result["name"], "TAP-CAMPUS")

        scopes = [
            call.kwargs["filters"]["coverage_scope"]
            for call in self.get_all.call_args_list
        ]

        self.assertEqual(scopes, ["Customer/Campus", "Campus"])

    def test_customer_policy_applies_after_campus_fallback(self):
        def lookup(doctype, filters, **kwargs):
            if filters["coverage_scope"] == "Customer":
                return [
                    policy_row(
                        "TAP-EMERALD",
                        "Customer",
                        "True Pool",
                    )
                ]
            return []

        self.get_all.side_effect = lookup

        result = assignment_policy.get_matching_assignment_policy(
            customer="Emerald Life",
            campus="Emerald Life - Head Office",
            service_area="CCTV",
        )

        self.assertEqual(result["assignment_mode"], "True Pool")

        scopes = [
            call.kwargs["filters"]["coverage_scope"]
            for call in self.get_all.call_args_list
        ]

        self.assertEqual(
            scopes,
            ["Customer/Campus", "Campus", "Customer"],
        )

    def test_default_policy_applies_without_context(self):
        self.get_all.return_value = [
            policy_row(
                "TAP-DEFAULT",
                "Default",
                "True Pool",
            )
        ]

        result = assignment_policy.get_matching_assignment_policy(
            customer=None,
            campus=None,
            service_area="CCTV",
        )

        self.assertEqual(result["name"], "TAP-DEFAULT")
        self.get_all.assert_called_once()

        filters = self.get_all.call_args.kwargs["filters"]

        self.assertEqual(filters["coverage_scope"], "Default")

    def test_customer_isolation(self):
        def lookup(doctype, filters, **kwargs):
            if (
                filters["coverage_scope"] == "Customer"
                and filters.get("customer") == "Boschendal"
            ):
                return [
                    policy_row(
                        "TAP-BOSCHENDAL",
                        "Customer",
                        "Round Robin",
                    )
                ]
            return []

        self.get_all.side_effect = lookup

        boschendal = assignment_policy.get_matching_assignment_policy(
            customer="Boschendal",
            campus=None,
            service_area="CCTV",
        )

        emerald = assignment_policy.get_matching_assignment_policy(
            customer="Emerald Life",
            campus=None,
            service_area="CCTV",
        )

        self.assertEqual(
            boschendal["assignment_mode"],
            "Round Robin",
        )
        self.assertIsNone(emerald)

    def test_blank_service_area_returns_no_policy(self):
        result = assignment_policy.get_matching_assignment_policy(
            customer="Boschendal",
            campus="Boschendal",
            service_area="",
        )

        self.assertIsNone(result)
        self.get_all.assert_not_called()

    def test_duplicate_enabled_policy_fails_closed(self):
        self.get_all.return_value = [
            policy_row("TAP-001", "Customer", "True Pool"),
            policy_row("TAP-002", "Customer", "Round Robin"),
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Conflicting enabled Assignment Policies",
        ):
            assignment_policy.get_matching_assignment_policy(
                customer="Emerald Life",
                campus=None,
                service_area="CCTV",
            )

    def test_invalid_assignment_mode_fails_closed(self):
        self.get_all.return_value = [
            policy_row(
                "TAP-INVALID",
                "Customer",
                "Prefer Technician",
            )
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Invalid Assignment Mode",
        ):
            assignment_policy.get_matching_assignment_policy(
                customer="Emerald Life",
                campus=None,
                service_area="CCTV",
            )

    def test_ticket_wrapper_uses_existing_context(self):
        context = {
            "ticket": "HD-TEST",
            "customer": "Boschendal",
            "campus": "Boschendal",
            "service_area": "CCTV",
        }

        with (
            mock.patch.object(
                assignment_policy,
                "get_ticket_context",
                return_value=context,
            ) as get_context,
            mock.patch.object(
                assignment_policy,
                "get_matching_assignment_policy",
                return_value=None,
            ) as resolve,
        ):
            result = assignment_policy.get_ticket_assignment_policy(
                "HD-TEST"
            )

        self.assertIsNone(result)
        get_context.assert_called_once_with("HD-TEST")

        resolve.assert_called_once_with(
            customer="Boschendal",
            campus="Boschendal",
            service_area="CCTV",
        )

    def test_missing_policy_table_preserves_pre_migration_fallback(self):
        with (
            mock.patch.object(
                assignment_policy.frappe.db,
                "table_exists",
                return_value=False,
            ) as table_exists,
            mock.patch.object(
                assignment_policy.frappe,
                "get_all",
            ) as get_all,
        ):
            result = assignment_policy.get_matching_assignment_policy(
                customer="Emerald Life",
                campus="EL-SITE-024",
                service_area="CCTV",
            )

        self.assertIsNone(result)

        table_exists.assert_called_once_with(
            assignment_policy.POLICY_DOCTYPE
        )

        get_all.assert_not_called()


class TestCCTVIncompleteContextGuard(unittest.TestCase):
    """Incomplete CCTV context must not enter automatic native fallback."""

    def test_cctv_context_completeness(self):
        scenarios = [
            (
                "missing_customer_and_campus",
                "",
                "",
                "",
                "CCTV",
                True,
            ),
            (
                "boschendal_missing_campus",
                "Boschendal",
                "",
                "",
                "CCTV",
                True,
            ),
            (
                "boschendal_missing_customer",
                "",
                "",
                "Boschendal",
                "CCTV",
                True,
            ),
            (
                "whitespace_only_customer_and_campus",
                "   ",
                "",
                "   ",
                "CCTV",
                True,
            ),
            (
                "boschendal_complete_erp_customer",
                "Boschendal",
                "",
                "Boschendal",
                "CCTV",
                False,
            ),
            (
                "boschendal_complete_hd_customer",
                "",
                "Boschendal",
                "Boschendal",
                "CCTV",
                False,
            ),
            (
                "emerald_life_complete",
                "Emerald Life",
                "",
                "EL-SITE-001",
                "CCTV",
                False,
            ),
            (
                "other_customer_complete",
                "Another Customer",
                "",
                "Another Campus",
                "CCTV",
                False,
            ),
            (
                "non_cctv_incomplete",
                "",
                "",
                "",
                "PABX",
                False,
            ),
        ]

        for (
            label,
            erp_customer,
            hd_customer,
            campus,
            service_area,
            expected_hold,
        ) in scenarios:
            with self.subTest(context=label):
                ticket = {
                    "custom_customer": erp_customer,
                    "customer": hd_customer,
                    "custom_site_group": campus,
                    "custom_service_area": service_area,
                    "agent_group": service_area,
                }

                actual_hold = (
                    assignment_policy.requires_cctv_context_triage(
                        ticket
                    )
                )

                self.assertEqual(actual_hold, expected_hold)

if __name__ == "__main__":
    unittest.main()
