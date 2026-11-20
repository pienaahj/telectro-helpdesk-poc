"""Isolated ownership checks: no Frappe initialization or database."""

import copy
import unittest
from types import MappingProxyType

from telephony.time_booking_identity import TechnicianBookingIdentity
from telephony.time_booking_ownership import (
    BookingOwnershipError,
    authorize_child,
    authorize_parent,
)


class TestBookingOwnership(unittest.TestCase):
    def setUp(self):
        self.identity = TechnicianBookingIdentity("tech", "EMP-1", "Company")
        self.child = {
            "doctype": "Timesheet Detail", "name": "ROW-1", "parent": "TS-1",
            "parenttype": "Timesheet", "parentfield": "time_logs",
            "custom_work_context": "", "hours": 0.75,
        }
        self.parent = {
            "doctype": "Timesheet", "name": "TS-1",
            "custom_telectro_booking_origin": "Phase 2",
            "employee": "EMP-1", "company": "Company", "user": "tech",
            "owner": "someone-else", "docstatus": 0,
            "time_logs": [copy.deepcopy(self.child)],
        }

    def denied_parent(self, parent, **kwargs):
        with self.assertRaises(BookingOwnershipError) as caught:
            authorize_parent(self.identity, parent, **kwargs)
        self.assertEqual(str(caught.exception), "Booking access is not permitted.")

    def denied_child(self, child, **kwargs):
        with self.assertRaises(BookingOwnershipError) as caught:
            authorize_child(self.identity, self.parent, child, **kwargs)
        self.assertEqual(str(caught.exception), "Booking access is not permitted.")

    def test_owned_marked_draft(self):
        self.assertIsNone(authorize_parent(self.identity, self.parent))
        self.assertIsNone(authorize_parent(
            self.identity, self.parent, operation="correct",
            proposed=copy.deepcopy(self.parent),
        ))

    def test_foreign_employee_even_when_owner_matches(self):
        self.denied_parent({**self.parent, "employee": "FOREIGN-EMP", "owner": "tech"})

    def test_foreign_company_and_user(self):
        for key in ["company", "user"]:
            with self.subTest(key=key):
                self.denied_parent({**self.parent, key: "FOREIGN"})

    def test_missing_or_false_provenance(self):
        for value in [None, "", " ", "Native", "phase 2", False, True]:
            with self.subTest(value=value):
                self.denied_parent({
                    **self.parent, "custom_telectro_booking_origin": value,
                })
        parent = copy.deepcopy(self.parent)
        del parent["custom_telectro_booking_origin"]
        self.denied_parent(parent)

    def test_submitted_cancelled_reads_and_correction_denials(self):
        for status in [1, 2]:
            with self.subTest(status=status):
                parent = {**self.parent, "docstatus": status}
                self.assertIsNone(authorize_parent(self.identity, parent))
                self.denied_parent(parent, operation="correct")

    def test_proposed_identity_provenance_name_or_status_reassignment(self):
        for key, value in [
            ("employee", "FOREIGN-EMP"), ("company", "FOREIGN-COMPANY"),
            ("user", "FOREIGN-USER"), ("custom_telectro_booking_origin", ""),
            ("name", "OTHER-TS"), ("docstatus", 1),
        ]:
            with self.subTest(key=key):
                self.denied_parent(
                    self.parent, operation="correct",
                    proposed={**self.parent, key: value},
                )

    def test_saved_identity_checked_before_proposed_identity(self):
        self.denied_parent(
            {**self.parent, "employee": "FOREIGN"},
            operation="correct", proposed=self.parent,
        )

    def test_invalid_operations_and_statuses(self):
        for operation in ["delete", "submit", "cancel", "", None]:
            with self.subTest(operation=operation):
                self.denied_parent(self.parent, operation=operation)
        for status in [None, "0", True, -1, 3]:
            with self.subTest(status=status):
                self.denied_parent({**self.parent, "docstatus": status})
        self.denied_parent(self.parent, proposed=self.parent)

    def test_valid_child_and_correction(self):
        self.assertIsNone(authorize_child(self.identity, self.parent, self.child))
        self.assertIsNone(authorize_child(
            self.identity, self.parent, {**self.child, "hours": 1},
            operation="correct", proposed_parent=copy.deepcopy(self.parent),
        ))

    def test_foreign_child_even_with_matching_submitted_parent(self):
        self.denied_child({**self.child, "name": "FOREIGN-ROW"})

    def test_wrong_child_parent_type_field_or_doctype(self):
        for key in ["parent", "parenttype", "parentfield", "doctype", "name"]:
            with self.subTest(key=key):
                self.denied_child({**self.child, key: "FOREIGN"})

    def test_child_requires_authorized_parent(self):
        self.parent["employee"] = "FOREIGN"
        self.denied_child(self.child)

    def test_duplicate_persisted_child_identities(self):
        self.parent["time_logs"].append(copy.deepcopy(self.child))
        self.denied_child(self.child)

    def test_reparented_persisted_child(self):
        self.parent["time_logs"][0]["parent"] = "OTHER-TS"
        self.denied_child(self.child)

    def test_duplicate_reparented_or_foreign_proposed_children(self):
        for rows in [
            [self.child, self.child],
            [{**self.child, "parent": "OTHER"}],
            [{**self.child, "name": "FOREIGN"}],
            [],
        ]:
            with self.subTest(rows=rows):
                self.denied_child(
                    self.child, operation="correct",
                    proposed_parent={**self.parent, "time_logs": rows},
                )

    def test_malformed_parent_and_children_fail_closed(self):
        for parent in [{}, {**self.parent, "doctype": "Other"},
                       {**self.parent, "name": ""}]:
            with self.subTest(parent=parent):
                self.denied_parent(parent)
        for rows in [None, {}, [None], [{**self.child, "name": None}]]:
            with self.subTest(rows=rows):
                self.parent["time_logs"] = rows
                self.denied_child(self.child)

    def test_legacy_blank_context_unchanged_on_denial(self):
        parent = copy.deepcopy(self.parent)
        del parent["custom_telectro_booking_origin"]
        before = copy.deepcopy(parent)
        self.denied_parent(MappingProxyType(parent))
        self.assertEqual(parent, before)
        self.assertEqual(parent["time_logs"][0]["custom_work_context"], "")

    def test_generic_denial_contains_no_sensitive_identifiers(self):
        foreign = {**self.parent, "name": "SECRET-TS", "employee": "SECRET-EMP",
                   "company": "SECRET-COMPANY"}
        with self.assertRaises(BookingOwnershipError) as caught:
            authorize_parent(self.identity, foreign)
        self.assertEqual(str(caught.exception), "Booking access is not permitted.")
        self.assertNotIn("SECRET", str(caught.exception))
        with self.assertRaises(BookingOwnershipError) as caught:
            authorize_child(self.identity, self.parent, {**self.child, "name": "SECRET-ROW"})
        self.assertNotIn("SECRET", str(caught.exception))

    def test_inputs_unchanged_on_success_and_failure(self):
        before = copy.deepcopy((self.parent, self.child))
        self.assertIsNone(authorize_child(
            self.identity, MappingProxyType(self.parent), MappingProxyType(self.child)
        ))
        self.assertEqual((self.parent, self.child), before)
        invalid = {**self.child, "parent": "FOREIGN"}
        invalid_before = copy.deepcopy(invalid)
        self.denied_child(MappingProxyType(invalid))
        self.assertEqual(invalid, invalid_before)
        self.assertEqual((self.parent, self.child), before)

    def test_invalid_identity_rejected(self):
        for identity in [None, TechnicianBookingIdentity("", "EMP-1", "Company")]:
            with self.subTest(identity=identity):
                with self.assertRaises(BookingOwnershipError):
                    authorize_parent(identity, self.parent)


    def test_submitted_cancellation_and_replacement_authorization(self):
        submitted = {**self.parent, "docstatus": 1}

        for operation in ("cancel_submitted", "replace_submitted"):
            with self.subTest(operation=operation):
                self.assertIsNone(
                    authorize_parent(
                        self.identity,
                        submitted,
                        operation=operation,
                    )
                )
                self.assertIsNone(
                    authorize_child(
                        self.identity,
                        submitted,
                        self.child,
                        operation=operation,
                    )
                )

    def test_submitted_operations_reject_invalid_state_and_identity(self):
        for operation in ("cancel_submitted", "replace_submitted"):
            for status in (0, 2):
                with self.subTest(operation=operation, status=status):
                    self.denied_parent(
                        {**self.parent, "docstatus": status},
                        operation=operation,
                    )

            submitted = {**self.parent, "docstatus": 1}

            for field in (
                "employee",
                "company",
                "user",
                "custom_telectro_booking_origin",
            ):
                with self.subTest(operation=operation, field=field):
                    self.denied_parent(
                        {**submitted, field: "FOREIGN"},
                        operation=operation,
                    )

if __name__ == "__main__":
    unittest.main()
