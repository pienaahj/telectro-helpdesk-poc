import unittest
from unittest import mock

from telephony.ftelephony.doctype.telectro_assignment_policy import (
    telectro_assignment_policy as policy_module,
)


PolicyController = policy_module.TELECTROAssignmentPolicy


def _reject(message):
    raise ValueError(str(message))


class PolicyHarness:
    """
    Exercise the real controller validation methods without requiring
    the new DocType to exist in the DEV database yet.
    """

    validate = PolicyController.validate
    _normalize_fields = PolicyController._normalize_fields
    _validate_scope_requirements = (
        PolicyController._validate_scope_requirements
    )
    _validate_assignment_mode = (
        PolicyController._validate_assignment_mode
    )
    _validate_enabled_uniqueness = (
        PolicyController._validate_enabled_uniqueness
    )

    def __init__(self, **overrides):
        values = {
            "name": "TAP-TEST-001",
            "enabled": 1,
            "coverage_scope": "Customer",
            "customer": "Emerald Life",
            "campus": None,
            "service_area": "CCTV",
            "assignment_mode": "True Pool",
        }
        values.update(overrides)
        self.__dict__.update(values)


class TestAssignmentPolicyController(unittest.TestCase):
    def setUp(self):
        throw_patch = mock.patch.object(
            policy_module.frappe,
            "throw",
            side_effect=_reject,
        )
        throw_patch.start()
        self.addCleanup(throw_patch.stop)

        get_all_patch = mock.patch.object(
            policy_module.frappe,
            "get_all",
            return_value=[],
        )
        self.get_all = get_all_patch.start()
        self.addCleanup(get_all_patch.stop)

    def test_valid_scopes_and_assignment_modes(self):
        contexts = [
            ("Customer/Campus", "Boschendal", "Boschendal"),
            ("Customer", "Emerald Life", None),
            ("Campus", None, "Boschendal"),
            ("Default", None, None),
        ]

        for scope, customer, campus in contexts:
            for mode in ("Round Robin", "True Pool"):
                with self.subTest(scope=scope, mode=mode):
                    policy = PolicyHarness(
                        coverage_scope=scope,
                        customer=customer,
                        campus=campus,
                        assignment_mode=mode,
                    )
                    policy.validate()

    def test_fields_are_normalized(self):
        policy = PolicyHarness(
            enabled=None,
            coverage_scope=" Customer ",
            customer=" Emerald Life ",
            campus=" ",
            service_area=" CCTV ",
            assignment_mode=" True Pool ",
        )

        policy.validate()

        self.assertEqual(policy.enabled, 1)
        self.assertEqual(policy.coverage_scope, "Customer")
        self.assertEqual(policy.customer, "Emerald Life")
        self.assertIsNone(policy.campus)
        self.assertEqual(policy.service_area, "CCTV")
        self.assertEqual(policy.assignment_mode, "True Pool")

    def test_invalid_scope_is_rejected(self):
        policy = PolicyHarness(coverage_scope="Unknown")

        with self.assertRaisesRegex(ValueError, "Coverage Scope"):
            policy.validate()

    def test_required_context_fields_are_enforced(self):
        cases = [
            ("Customer/Campus", None, "Boschendal"),
            ("Customer/Campus", "Boschendal", None),
            ("Customer", None, None),
            ("Campus", None, None),
        ]

        for scope, customer, campus in cases:
            with self.subTest(scope=scope, customer=customer, campus=campus):
                policy = PolicyHarness(
                    coverage_scope=scope,
                    customer=customer,
                    campus=campus,
                )

                with self.assertRaises(ValueError):
                    policy.validate()

    def test_irrelevant_context_fields_are_rejected(self):
        cases = [
            ("Customer", "Emerald Life", "Boschendal"),
            ("Campus", "Emerald Life", "Boschendal"),
            ("Default", "Emerald Life", None),
            ("Default", None, "Boschendal"),
        ]

        for scope, customer, campus in cases:
            with self.subTest(scope=scope, customer=customer, campus=campus):
                policy = PolicyHarness(
                    coverage_scope=scope,
                    customer=customer,
                    campus=campus,
                )

                with self.assertRaises(ValueError):
                    policy.validate()

    def test_service_area_is_required(self):
        policy = PolicyHarness(service_area=" ")

        with self.assertRaisesRegex(ValueError, "Service Area"):
            policy.validate()

    def test_assignment_mode_is_restricted(self):
        policy = PolicyHarness(assignment_mode="Prefer Jacques")

        with self.assertRaisesRegex(ValueError, "Assignment Mode"):
            policy.validate()

    def test_duplicate_enabled_policy_is_rejected(self):
        self.get_all.return_value = [
            {
                "name": "TAP-EXISTING",
                "customer": "Emerald Life",
                "campus": None,
            }
        ]

        policy = PolicyHarness()

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            policy.validate()

        self.get_all.assert_called_once_with(
            "TELECTRO Assignment Policy",
            filters={
                "enabled": 1,
                "coverage_scope": "Customer",
                "service_area": "CCTV",
            },
            fields=["name", "customer", "campus"],
        )

    def test_policy_can_update_itself(self):
        self.get_all.return_value = [
            {
                "name": "TAP-TEST-001",
                "customer": "Emerald Life",
                "campus": None,
            }
        ]

        PolicyHarness().validate()

    def test_distinct_customer_policy_is_allowed(self):
        self.get_all.return_value = [
            {
                "name": "TAP-EMERALD",
                "customer": "Emerald Life",
                "campus": None,
            }
        ]

        policy = PolicyHarness(
            name="TAP-BOSCHENDAL",
            customer="Boschendal",
            assignment_mode="Round Robin",
        )

        policy.validate()

    def test_disabled_policy_does_not_check_uniqueness(self):
        policy = PolicyHarness(enabled=0)

        policy.validate()

        self.get_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
