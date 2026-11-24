"""No-site tests for Customer consistency at the booking boundary."""

import unittest
from unittest.mock import Mock, patch

import frappe

from telephony.api.time_booking import (
    BookingReferenceDenied,
    _validate_customer_consistency,
)
from telephony.tests.test_time_booking_post import Reference, customer_mapping_sql


class TestBookingCustomerConsistency(unittest.TestCase):
    def setUp(self):
        self.customer = Reference("HD Customer", "HD-A", custom_erp_customer="ERP-A")
        self.current_customer = Reference("HD Customer", "HD-A", **self.customer)
        self.ticket = Reference("HD Ticket", "T")
        self.ticket_links = frappe._dict(name="T", customer="HD-A", custom_customer="ERP-A")
        self.project_customer = "ERP-A"
        self.erp_name = "ERP-A"
        self.reverse_matches = (("HD-A",),)
        self.session_settings = dict(customer_mapping_sql("SHOW SESSION VARIABLES"))
        self.index = customer_mapping_sql("information_schema.STATISTICS")
        self.db = Mock(spec_set=["get_value", "sql", "db_type"])
        self.db.db_type = "mariadb"
        self.db.get_value.side_effect = self.get_value
        self.db.sql.side_effect = self.sql
        self.get_doc = Mock(side_effect=self.get_doc_by_reference)
        for patcher in (
            patch.dict(frappe.__dict__, {"db": self.db}),
            patch.object(frappe, "get_doc", self.get_doc),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def get_value(self, doctype, name, fields, **kwargs):
        if (doctype, name, fields, kwargs) == (
            "HD Ticket", str(self.ticket.name), "*",
            {"as_dict": True, "order_by": None, "for_update": True, "wait": False},
        ):
            return self.ticket_links
        if (doctype, name, fields, kwargs) == (
            "HD Customer", "HD-A", "*",
            {"as_dict": True, "order_by": None, "for_update": True, "wait": False},
        ):
            return self.current_customer
        if (doctype, name, fields, kwargs) == (
            "Customer", "ERP-A", "name", {"order_by": None, "for_update": True, "wait": False},
        ):
            return self.erp_name
        self.fail(f"Unexpected reference lookup for {doctype} {name}")

    def get_doc_by_reference(self, *args):
        if args == ("HD Customer", "HD-A"):
            return self.customer
        if args == ({**self.current_customer, "doctype": "HD Customer"},):
            return self.current_customer
        self.assertEqual(args, ({**self.ticket_links, "doctype": "HD Ticket"},))
        return Reference(
            "HD Ticket", self.ticket_links.name,
            customer=self.ticket_links.customer, custom_customer=self.ticket_links.custom_customer,
        )

    def sql(self, query, params=None):
        if "SHOW SESSION VARIABLES" in query:
            return tuple(self.session_settings.items())
        if "information_schema.STATISTICS" in query:
            self.assertIn("s.INDEX_NAME = 'custom_erp_customer_index'", query)
            return self.index
        self.assertEqual(params, ("ERP-A",))
        return customer_mapping_sql(query, params, matches=self.reverse_matches)

    def used_reverse_query(self):
        return any("FORCE INDEX" in entry.args[0] for entry in self.db.sql.call_args_list)

    def validate(self, context="Helpdesk"):
        _validate_customer_consistency(
            {
                "custom_work_context": context,
                "custom_hd_ticket": str(self.ticket.name) if context == "Helpdesk" else None,
                "custom_hd_customer": "HD-A",
                "project": "PROJECT-A" if context == "Project" else None,
            },
            ticket=self.ticket if context == "Helpdesk" else None,
            project_customer=self.project_customer if context == "Project" else None,
        )

    def assert_denied(self, context="Helpdesk"):
        with self.assertRaises(BookingReferenceDenied) as denied:
            self.validate(context)
        self.assertEqual(str(denied.exception), "Booking reference is unavailable.")

    def test_omitted_customer_requires_no_reference_reads(self):
        for context in ("Helpdesk", "Project", "Customer Support", "Internal"):
            for supplied in ({}, {"custom_hd_customer": None}, {"custom_hd_customer": ""}):
                with self.subTest(context=context, supplied=supplied):
                    _validate_customer_consistency({"custom_work_context": context, **supplied})
        self.get_doc.assert_not_called()
        self.db.get_value.assert_not_called()
        self.db.sql.assert_not_called()

    def test_ticket_accepts_canonical_links_together_or_independently(self):
        for hd_name, erp_name in (
            ("HD-A", "ERP-A"), ("HD-A", None), (None, "ERP-A"),
        ):
            with self.subTest(hd_name=hd_name, erp_name=erp_name):
                self.ticket_links.update(customer=hd_name, custom_customer=erp_name)
                self.validate()

    def test_ticket_rejects_conflicting_canonical_hd_customer(self):
        self.ticket_links["customer"] = "HD-B"
        self.assert_denied()

    def test_ticket_rejects_missing_or_conflicting_forward_mapping(self):
        for mapped_customer in (None, "", "ERP-B"):
            with self.subTest(mapped_customer=mapped_customer):
                self.current_customer["custom_erp_customer"] = mapped_customer
                self.assert_denied()

    def test_standalone_hd_customer_is_allowed_without_erp_authority(self):
        self.customer["custom_erp_customer"] = None
        self.current_customer["custom_erp_customer"] = ""
        for hd_name in (None, "HD-A"):
            with self.subTest(hd_name=hd_name):
                self.ticket_links.update(customer=hd_name, custom_customer=None)
                self.validate()
        self.validate("Customer Support")
        self.assertEqual([call.args[0] for call in self.db.get_value.call_args_list], [
            "HD Ticket", "HD Customer", "HD Ticket", "HD Customer", "HD Customer",
        ])
        self.assertFalse(self.used_reverse_query())

    def test_unlinked_ticket_and_customer_support_validate_existing_mapping(self):
        self.ticket_links.update(customer=None, custom_customer=None)
        for context in ("Helpdesk", "Customer Support"):
            with self.subTest(context=context):
                self.validate(context)
                self.erp_name = None
                self.assert_denied(context)
                self.erp_name = "ERP-A"

    def test_dangling_or_noncanonical_erp_customer_is_denied(self):
        for erp_name in (None, "erp-a"):
            with self.subTest(erp_name=erp_name):
                self.erp_name = erp_name
                self.assert_denied()
                self.assert_denied("Project")

    def test_reverse_mapping_must_uniquely_resolve_the_supplied_hd_customer(self):
        for matches in ((), (("HD-B",),), (("HD-A",), ("HD-B",))):
            with self.subTest(matches=matches):
                self.reverse_matches = matches
                self.assert_denied()
                self.assert_denied("Project")

    def test_project_accepts_matching_customer_and_unique_reverse_mapping(self):
        self.validate("Project")

    def test_project_rejects_missing_or_blank_locked_customer(self):
        for project_customer in (None, "", " ERP-A"):
            with self.subTest(project_customer=project_customer):
                self.project_customer = project_customer
                self.assert_denied("Project")

    def test_project_rejects_missing_or_conflicting_forward_mapping(self):
        for mapped_customer in (None, "ERP-B"):
            with self.subTest(mapped_customer=mapped_customer):
                self.current_customer["custom_erp_customer"] = mapped_customer
                self.assert_denied("Project")

    def test_dangling_or_unreadable_hd_customer_is_denied(self):
        self.get_doc.side_effect = frappe.DoesNotExistError
        self.assert_denied()
        self.get_doc.side_effect = frappe.PermissionError
        self.assert_denied()

    def test_ticket_lock_denies_missing_noncanonical_and_contended_rows(self):
        for locked_row in (None, frappe._dict(name="another-ticket")):
            with self.subTest(locked_row=locked_row):
                self.ticket_links = locked_row
                self.assert_denied()
        for error in (frappe.QueryTimeoutError, frappe.QueryDeadlockError):
            with self.subTest(error=error):
                self.db.get_value.side_effect = error
                self.assert_denied()

    def test_ticket_lock_accepts_canonical_numeric_identity(self):
        self.ticket.name = self.ticket_links.name = 965
        self.validate()

    def test_locked_ticket_read_permission_is_checked_again(self):
        current_ticket = Mock()
        current_ticket.check_permission.side_effect = frappe.PermissionError
        self.get_doc.side_effect = [self.customer, current_ticket]
        self.assert_denied()
        current_ticket.check_permission.assert_called_once_with("read")

    def test_authoritative_mapping_uses_current_forward_link(self):
        self.customer["custom_erp_customer"] = "ERP-STALE"
        self.validate("Helpdesk")
        self.validate("Project")
        self.assertTrue(self.used_reverse_query())

    def test_standalone_candidate_cannot_change_before_lock(self):
        for candidate, actual in ((None, "ERP-A"), ("ERP-A", None), ("ERP-A", "ERP-B")):
            with self.subTest(candidate=candidate, actual=actual):
                self.customer["custom_erp_customer"] = candidate
                self.current_customer["custom_erp_customer"] = actual
                self.assert_denied("Customer Support")
        self.assertFalse(self.used_reverse_query())

    def test_forward_lock_rejects_missing_or_noncanonical_hd_customer(self):
        for locked in (None, Reference("HD Customer", "hd-a")):
            with self.subTest(locked=locked):
                self.current_customer = locked
                self.assert_denied("Project")
        self.assertFalse(self.used_reverse_query())

    def test_locked_hd_customer_read_permission_is_checked_again(self):
        with patch.object(self.current_customer, "check_permission", side_effect=frappe.PermissionError):
            self.assert_denied("Project")
        self.assertFalse(self.used_reverse_query())

    def test_missing_or_wrong_index_fails_closed(self):
        correct, = self.index
        for index in ((), ((*correct[:4], 32, *correct[5:]),), ((*correct[:5], "YES", *correct[6:]),)):
            with self.subTest(index=index):
                self.index = index
                self.assert_denied("Project")
        self.assertFalse(self.used_reverse_query())

    def test_unsupported_transaction_settings_fail_before_locking(self):
        for key, value in (
            ("autocommit", "ON"), ("in_transaction", "0"), ("innodb_snapshot_isolation", "ON"),
            ("tx_isolation", "READ-COMMITTED"),
        ):
            with self.subTest(key=key), patch.dict(self.session_settings, {key: value}):
                self.assert_denied("Project")
        del self.session_settings["innodb_snapshot_isolation"]
        self.assert_denied("Project")
        self.db.db_type = "postgres"
        self.db.sql.reset_mock()
        self.assert_denied("Project")
        self.db.sql.assert_not_called()
        self.db.get_value.assert_not_called()

    def test_exact_row_and_range_contention_are_converted_to_reference_denial(self):
        for target in ("Customer", "HD Customer", "reverse"):
            for error in (frappe.QueryTimeoutError, frappe.QueryDeadlockError):
                with self.subTest(target=target, error=error):
                    def get_value(doctype, *args, **kwargs):
                        if doctype == target:
                            raise error()
                        return self.get_value(doctype, *args, **kwargs)

                    def sql(query, params=None):
                        if target == "reverse" and "FORCE INDEX" in query:
                            raise error()
                        return self.sql(query, params)

                    self.db.get_value.side_effect = get_value
                    self.db.sql.side_effect = sql
                    self.assert_denied("Project")

    def test_unrelated_sql_error_propagates(self):
        failure = RuntimeError("unrelated SQL failure")
        self.db.sql.side_effect = [
            tuple(self.session_settings.items()), self.index, failure,
        ]
        with self.assertRaises(RuntimeError) as caught:
            self.validate("Project")
        self.assertIs(caught.exception, failure)
