"""Isolated identity tests using the actual audience classifier and fake reads."""

import copy
import importlib.util
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call, patch

from telephony.time_booking_identity import (
    TechnicianBookingIdentity,
    TechnicianIdentityError,
    resolve_current_technician_identity,
)


TECH = "TELECTRO-POC Role - Tech"


def load_actual_classifier():
    """Import unchanged policy source with unrelated application imports stubbed."""
    helper = ModuleType("helpdesk.utils")
    helper.get_customer = Mock(side_effect=AssertionError("No customer lookup"))
    guard = ModuleType("telephony.telectro_ticket_edit_guard")
    guard.validate_ticket_edit_rights = Mock(
        side_effect=AssertionError("No ticket validation")
    )
    path = Path(__file__).resolve().parents[1] / "customer_communication_privacy.py"
    spec = importlib.util.spec_from_file_location("_identity_classifier_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "frappe": ModuleType("frappe"),
        "helpdesk.utils": helper,
        "telephony.telectro_ticket_edit_guard": guard,
    }):
        spec.loader.exec_module(module)
    return module


class TestTechnicianIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = load_actual_classifier()

    def setUp(self):
        self.user = "tech@example.test"
        self.account = {"name": self.user, "enabled": 1, "user_type": "System User"}
        self.employee = {
            "name": "EMP-1", "user_id": self.user, "status": "Active",
            "docstatus": 0, "company": "Telectro",
        }
        self.roles = [TECH]
        self.employees = [self.employee]
        self.company = "Telectro"
        self.fake = SimpleNamespace(
            session=SimpleNamespace(user=self.user),
            db=SimpleNamespace(get_value=Mock(side_effect=self.get_value)),
            get_all=Mock(side_effect=self.get_all),
        )
        self.patcher = patch.dict(sys.modules, {
            "frappe": self.fake,
            "telephony.customer_communication_privacy": self.classifier,
        })
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def get_value(self, doctype, *args, **kwargs):
        if doctype == "User":
            return self.account
        if doctype == "Company":
            return self.company
        self.fail("Unexpected read: " + doctype)

    def get_all(self, doctype, **kwargs):
        if doctype == "Has Role":
            return self.roles
        if doctype == "Employee":
            return self.employees
        self.fail("Unexpected list read: " + doctype)

    def denied(self):
        with self.assertRaises(TechnicianIdentityError) as result:
            resolve_current_technician_identity()
        self.assertEqual(str(result.exception),
                         "Technician booking identity is unavailable.")

    def test_success_and_immutable_minimal_output(self):
        result = resolve_current_technician_identity()
        self.assertEqual(result, TechnicianBookingIdentity(self.user, "EMP-1", "Telectro"))
        self.assertEqual(asdict(result), {
            "user": self.user, "employee": "EMP-1", "company": "Telectro",
        })
        with self.assertRaises(FrozenInstanceError):
            result.company = "Other"

    def test_missing_blank_guest_and_administrator(self):
        for user in [None, "", "   ", "Guest", "Administrator"]:
            with self.subTest(user=user):
                self.fake.session.user = user
                self.denied()
        self.fake.db.get_value.assert_not_called()
        self.fake.get_all.assert_not_called()

    def test_missing_session_user(self):
        del self.fake.session.user
        self.denied()
        self.fake.db.get_value.assert_not_called()

    def test_missing_disabled_and_website_user(self):
        for account in [None, {}, {**self.account, "enabled": 0},
                        {**self.account, "user_type": "Website User"},
                        {**self.account, "name": "other@example.test"}]:
            with self.subTest(account=account):
                self.account = account
                self.denied()
        self.fake.get_all.assert_not_called()

    def test_missing_technician_role_and_no_admin_bypass(self):
        for roles in [[], ["System Manager"], ["Pilot Admin"],
                      ["TELECTRO-POC Role - Coordinator Ops"]]:
            with self.subTest(roles=roles):
                self.roles = roles
                self.denied()
        self.assertTrue(all(c.args[0] == "Has Role"
                            for c in self.fake.get_all.call_args_list))
        self.assertTrue(all(c.args[0] == "User"
                            for c in self.fake.db.get_value.call_args_list))

    def test_internal_role_combinations(self):
        for extra in ["System Manager", "Pilot Admin",
                      "TELECTRO-POC Role - Coordinator Ops",
                      "TELECTRO-POC Role - Supervisor Governance"]:
            with self.subTest(extra=extra):
                self.roles = [TECH, extra]
                self.assertEqual(resolve_current_technician_identity().employee, "EMP-1")

    def test_actual_classifier_audiences(self):
        classify = self.classifier.classify_actor_roles
        for roles, expected in [
            ([TECH], "internal"), (["Customer"], "unknown"),
            (["TELECTRO-POC Role - Partner"], "partner"),
            (["TELECTRO-POC Role - Partner Creator"], "partner"),
            ([TECH, "Customer"], "unknown"),
            ([TECH, "TELECTRO-POC Role - Partner"], "unknown"),
            ([], "unknown"),
        ]:
            with self.subTest(roles=roles):
                self.assertEqual(classify(roles), expected)
        self.assertEqual(classify(["Customer"], linked_hd_customers=["C"]), "customer")

    def test_customer_partner_mixed_and_unknown_rejected(self):
        for roles in [
            ["Customer"], ["TELECTRO-POC Role - Partner"], [],
            [TECH, "Customer"], [TECH, "TELECTRO-POC Role - Partner"],
            [TECH, "TELECTRO-POC Role - Partner Creator"],
        ]:
            with self.subTest(roles=roles):
                self.roles = roles
                self.denied()
        self.assertTrue(all(c.args[0] == "Has Role"
                            for c in self.fake.get_all.call_args_list))

    def test_zero_and_multiple_employee_matches(self):
        for employees in [[], [self.employee, {**self.employee, "name": "EMP-2"}]]:
            with self.subTest(employees=employees):
                self.employees = employees
                self.denied()
        self.assertTrue(all(c.args[0] == "User"
                            for c in self.fake.db.get_value.call_args_list))

    def test_inactive_cancelled_and_inconsistent_employee(self):
        for changes in [
            {"status": "Inactive"}, {"status": "Suspended"}, {"status": "Left"},
            {"docstatus": 2}, {"docstatus": None},
            {"user_id": "other@example.test"}, {"name": ""},
        ]:
            with self.subTest(changes=changes):
                self.employees = [{**self.employee, **changes}]
                self.denied()
        self.assertTrue(all(c.args[0] == "User"
                            for c in self.fake.db.get_value.call_args_list))

    def test_missing_and_dangling_company(self):
        for company in [None, "", "   "]:
            with self.subTest(company=company):
                self.employees = [{**self.employee, "company": company}]
                self.denied()
        self.assertTrue(all(c.args[0] == "User"
                            for c in self.fake.db.get_value.call_args_list))
        self.employees = [self.employee]
        self.company = None
        self.denied()
        self.company = "Different"
        self.denied()

    def test_exact_read_contract(self):
        self.assertIsInstance(resolve_current_technician_identity(), TechnicianBookingIdentity)
        self.assertEqual(self.fake.db.get_value.call_args_list, [
            call("User", self.user, ["name", "enabled", "user_type"], as_dict=True),
            call("Company", "Telectro", "name"),
        ])
        self.assertEqual(self.fake.get_all.call_args_list, [
            call("Has Role", filters={
                "parent": self.user, "parenttype": "User", "parentfield": "roles",
            }, pluck="role", limit_page_length=0),
            call("Employee", filters={
                "user_id": self.user, "status": "Active", "docstatus": ["<", 2],
            }, fields=["name", "user_id", "status", "docstatus", "company"],
                 order_by="name asc", limit_page_length=2),
        ])

    def test_no_session_or_input_mutation_and_no_write_capabilities(self):
        before = copy.deepcopy((vars(self.fake.session), self.account,
                                self.roles, self.employees))
        self.assertIsInstance(resolve_current_technician_identity(), TechnicianBookingIdentity)
        self.assertEqual((vars(self.fake.session), self.account,
                          self.roles, self.employees), before)
        self.assertEqual(set(vars(self.fake)), {"session", "db", "get_all"})
        self.assertEqual(set(vars(self.fake.db)), {"get_value"})

    def test_rechecks_identity_each_invocation(self):
        self.assertIsInstance(resolve_current_technician_identity(), TechnicianBookingIdentity)
        self.account["enabled"] = 0
        self.denied()
        self.assertEqual(self.fake.db.get_value.call_count, 3)

    def test_database_exceptions_propagate(self):
        error = RuntimeError("database unavailable")
        self.fake.db.get_value.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            resolve_current_technician_identity()
        self.assertIs(caught.exception, error)
        self.fake.get_all.assert_not_called()

    def test_employee_query_exceptions_propagate(self):
        def read(doctype, **kwargs):
            if doctype == "Employee":
                raise RuntimeError("employee read unavailable")
            return self.roles
        self.fake.get_all.side_effect = read
        with self.assertRaisesRegex(RuntimeError, "employee read unavailable"):
            resolve_current_technician_identity()
        self.assertEqual(self.fake.db.get_value.call_count, 1)

    def test_no_identity_override_arguments(self):
        with self.assertRaises(TypeError):
            resolve_current_technician_identity(user="other")
        self.fake.db.get_value.assert_not_called()


if __name__ == "__main__":
    unittest.main()
