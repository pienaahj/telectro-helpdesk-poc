import unittest
from unittest.mock import patch

import frappe

from telephony import customer_ticket_api_guard as guard
from telephony import customer_communication_privacy as privacy


class TestCustomerTicketActivityPrivacy(unittest.TestCase):

    def setUp(self):
        self._original_flags = getattr(
            frappe.local,
            "flags",
            None,
        )

        frappe.local.flags = frappe._dict(in_test=False)
        self.activities = {
            "communications": [
                {
                    "name": "customer-visible",
                    "content": "Approved Customer update",
                    "sender": "test@boschendal.co.za",
                    "recipients": "internal@example.com",
                    "bcc": "private@example.com",
                    "attachments": [
                        {"file_url": "/private/files/secret.pdf"}
                    ],
                },
                {
                    "name": "customer-cross",
                    "content": "Not authorised for this user",
                },
                {
                    "name": "internal-secret",
                    "content": "Internal investigation details",
                },
            ],
            "comments": [{"content": "Internal note"}],
            "history": [{"action": "Internal assignment"}],
            "views": [{"viewed_by": "internal@example.com"}],
            "calls": [{"recording_url": "/private/recording"}],
        }

    def tearDown(self):
        if self._original_flags is None:
            del frappe.local.flags
        else:
            frappe.local.flags = self._original_flags

    def test_customer_receives_only_authorised_projection(self):
        access = {
            "actor_kind": "customer",
            "ticket_read_allowed": True,
            "is_ticket_customer": True,
        }

        with (
            patch.object(guard, "_require_ticket_read"),
            patch.object(
                privacy,
                "get_current_actor_access",
                return_value=access,
            ),
            patch.object(
                guard.helpdesk_api,
                "get_ticket_activities",
                return_value=self.activities,
            ),
            patch.object(
                guard.frappe,
                "get_all",
                return_value=[
                    "customer-visible",
                    "customer-cross",
                ],
            ) as lookup,
            patch.object(
                guard.frappe,
                "has_permission",
                side_effect=lambda doctype, ptype, doc=None: (
                    doctype == "Communication"
                    and ptype == "read"
                    and doc == "customer-visible"
                ),
            ),
        ):
            result = guard.get_ticket_activities("902")

        lookup.assert_called_once_with(
            "Communication",
            filters={
                "reference_doctype": "HD Ticket",
                "reference_name": "902",
                "custom_telectro_audience": "Customer",
            },
            pluck="name",
            limit_page_length=0,
        )

        self.assertEqual(
            [item["name"] for item in result["communications"]],
            ["customer-visible"],
        )

        visible = result["communications"][0]

        self.assertEqual(
            visible["content"],
            "Approved Customer update",
        )

        self.assertEqual(visible["attachments"], [])
        self.assertNotIn("recipients", visible)
        self.assertNotIn("bcc", visible)

        for section in ("comments", "history", "views", "calls"):
            self.assertEqual(result[section], [])

    def test_internal_user_retains_native_response(self):
        access = {
            "actor_kind": "internal",
            "ticket_read_allowed": True,
            "is_ticket_customer": False,
        }

        with (
            patch.object(guard, "_require_ticket_read"),
            patch.object(
                privacy,
                "get_current_actor_access",
                return_value=access,
            ),
            patch.object(
                guard.helpdesk_api,
                "get_ticket_activities",
                return_value=self.activities,
            ),
            patch.object(guard.frappe, "get_all") as lookup,
        ):
            result = guard.get_ticket_activities("902")

        self.assertIs(result, self.activities)
        lookup.assert_not_called()

    def test_other_customer_is_denied(self):
        access = {
            "actor_kind": "customer",
            "ticket_read_allowed": True,
            "is_ticket_customer": False,
        }

        with (
            patch.object(guard, "_require_ticket_read"),
            patch.object(
                privacy,
                "get_current_actor_access",
                return_value=access,
            ),
            patch.object(
                guard.frappe,
                "throw",
                side_effect=frappe.PermissionError,
            ),
            patch.object(
                guard.helpdesk_api,
                "get_ticket_activities",
            ) as native,
        ):
            with self.assertRaises(frappe.PermissionError):
                guard.get_ticket_activities("902")

        native.assert_not_called()

    def test_unknown_actor_is_denied(self):
        access = {
            "actor_kind": "unknown",
            "ticket_read_allowed": True,
            "is_ticket_customer": False,
        }

        with (
            patch.object(guard, "_require_ticket_read"),
            patch.object(
                privacy,
                "get_current_actor_access",
                return_value=access,
            ),
            patch.object(
                guard.frappe,
                "throw",
                side_effect=frappe.PermissionError,
            ),
            patch.object(
                guard.helpdesk_api,
                "get_ticket_activities",
            ) as native,
        ):
            with self.assertRaises(frappe.PermissionError):
                guard.get_ticket_activities("902")

        native.assert_not_called()


if __name__ == "__main__":
    unittest.main()
