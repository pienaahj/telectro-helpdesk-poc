"""Security regressions for Customer recipient lookup."""

import inspect
import unittest
from types import SimpleNamespace
from unittest import mock

import frappe
from helpdesk import utils as helpdesk_utils
from telephony import customer_communication_privacy as privacy
from telephony import customer_ticket_resolution as resolution
from telephony import telectro_ticket_edit_guard as edit_guard


ACTOR = "hendrik@local.test"
TICKET = "948"


def raise_frappe_error(message, exc=frappe.ValidationError):
    raise exc(message)


class TestCustomerRecipientLookup(unittest.TestCase):

    def setUp(self):
        self.ticket = {
            "customer": "Emerald Life",
            "raised_by": ACTOR,
            "via_customer_portal": 0,
            "custom_request_source": "Telectro",
        }

        self.actor_roles = ["System Manager"]

        self.access = {
            "actor_kind": "internal",
            "ticket_read_allowed": True,
            "is_ticket_customer": False,
        }

        self.users = {
            "emerald.portal.test@example.com": {
                "enabled": 1,
                "customers": ["Emerald Life"],
                "roles": ["Customer"],
            },
            "customer2@boschendal.co.za": {
                "enabled": 1,
                "customers": ["Boschendal"],
                "roles": ["Customer"],
            },
            "test@boschendal.co.za": {
                "enabled": 1,
                "customers": ["Boschendal"],
                "roles": ["Customer"],
            },
            "disabled@example.test": {
                "enabled": 0,
                "customers": ["Emerald Life"],
                "roles": ["Customer"],
            },
            "mixed@example.test": {
                "enabled": 1,
                "customers": ["Emerald Life"],
                "roles": [
                    "Customer",
                    "TELECTRO-POC Role - Partner",
                ],
            },
            "ambiguous@example.test": {
                "enabled": 1,
                "customers": ["Emerald Life", "Boschendal"],
                "roles": ["Customer"],
            },
            "unlinked@example.test": {
                "enabled": 1,
                "customers": [],
                "roles": ["Customer"],
            },
        }

        def db_get_value(doctype, name, field):
            self.assertEqual(doctype, "User")
            self.assertEqual(field, "enabled")
            return self.users[name]["enabled"]

        def get_roles(user):
            if user == ACTOR:
                return self.actor_roles
            return self.users[user]["roles"]

        self.fake_frappe = SimpleNamespace(
            PermissionError=frappe.PermissionError,
            ValidationError=frappe.ValidationError,
            session=SimpleNamespace(user=ACTOR),
            throw=mock.Mock(side_effect=raise_frappe_error),
            get_roles=mock.Mock(side_effect=get_roles),
            get_doc=mock.Mock(return_value=self.ticket),
            get_all=mock.Mock(return_value=list(self.users)),
            has_permission=mock.Mock(return_value=True),
            db=SimpleNamespace(
                get_value=mock.Mock(side_effect=db_get_value),
            ),
        )

        patchers = [
            mock.patch.object(
                resolution, "frappe", self.fake_frappe
            ),
            mock.patch.object(
                resolution, "_",
                side_effect=lambda message: message,
            ),
            mock.patch.object(
                privacy,
                "get_current_actor_access",
                return_value=self.access,
            ),
            mock.patch.object(
                helpdesk_utils,
                "get_customer",
                side_effect=lambda user: self.users[user]["customers"],
            ),
            mock.patch.object(
                edit_guard,
                "validate_ticket_edit_rights",
            ),
        ]

        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.edit_guard = edit_guard.validate_ticket_edit_rights

    def lookup(self):
        # Exercise the implementation without Frappe's
        # request-context-dependent whitelist wrapper.
        lookup_function = inspect.unwrap(
            resolution.get_customer_recipient_options
        )
        return lookup_function(TICKET)

    def test_emerald_returns_only_eligible_user(self):
        self.assertEqual(
            self.lookup(),
            ["emerald.portal.test@example.com"],
        )
        self.fake_frappe.get_all.assert_called_once_with(
            "Has Role",
            filters={
                "parenttype": "User",
                "role": "Customer",
            },
            pluck="parent",
            limit_page_length=0,
        )

    def test_boschendal_returns_two_eligible_users(self):
        self.ticket["customer"] = "Boschendal"

        self.assertEqual(
            self.lookup(),
            [
                "customer2@boschendal.co.za",
                "test@boschendal.co.za",
            ],
        )

    def test_unrelated_disabled_and_ambiguous_users_excluded(self):
        self.assertEqual(
            self.lookup(),
            ["emerald.portal.test@example.com"],
        )

        self.assertNotIn(
            "disabled@example.test",
            self.lookup(),
        )
        self.assertNotIn(
            "mixed@example.test",
            self.lookup(),
        )
        self.assertNotIn(
            "ambiguous@example.test",
            self.lookup(),
        )
        self.assertNotIn(
            "unlinked@example.test",
            self.lookup(),
        )

    def test_customer_without_eligible_users_returns_empty(self):
        self.ticket["customer"] = "Empty Organisation"
        self.assertEqual(self.lookup(), [])

    def test_portal_and_customer_source_do_not_enumerate(self):
        cases = [
            (1, "Telectro"),
            (0, "Customer"),
        ]

        for portal_flag, source in cases:
            with self.subTest(portal=portal_flag, source=source):
                self.ticket["via_customer_portal"] = portal_flag
                self.ticket["custom_request_source"] = source

                self.assertEqual(self.lookup(), [])

        self.fake_frappe.get_all.assert_not_called()

    def test_noninternal_actor_denied(self):
        self.access["actor_kind"] = "customer"

        with self.assertRaises(frappe.PermissionError):
            self.lookup()

        self.fake_frappe.get_all.assert_not_called()

    def test_missing_ticket_read_denied(self):
        self.access["ticket_read_allowed"] = False

        with self.assertRaises(frappe.PermissionError):
            self.lookup()

        self.fake_frappe.get_all.assert_not_called()

    def test_missing_ticket_write_denied(self):
        self.fake_frappe.has_permission.return_value = False

        with self.assertRaises(frappe.PermissionError):
            self.lookup()

        self.fake_frappe.get_all.assert_not_called()

    def test_assignment_edit_guard_denied(self):
        self.edit_guard.side_effect = frappe.PermissionError(
            "Ticket assignment required"
        )

        with self.assertRaises(frappe.PermissionError):
            self.lookup()

        self.fake_frappe.get_all.assert_not_called()

    def test_actor_without_internal_role_denied(self):
        self.actor_roles = ["Customer"]

        with self.assertRaises(frappe.ValidationError):
            self.lookup()

        self.fake_frappe.get_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
