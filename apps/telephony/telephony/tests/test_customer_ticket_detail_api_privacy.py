import unittest
from unittest.mock import patch

import frappe

from telephony import customer_ticket_api_guard as guard


class TestCustomerTicketDetailApiPrivacy(unittest.TestCase):

    def setUp(self):
        self._original_flags = getattr(
            frappe.local, "flags", None
        )
        frappe.local.flags = frappe._dict(in_test=False)

        self.customer_access = {
            "actor_kind": "customer",
            "ticket_read_allowed": True,
            "is_ticket_customer": True,
        }

        self.detail = {
            "name": 902,
            "subject": "Internet fault",
            "status": "Open",
            "priority": "High",
            "customer": "Boschendal",
            "raised_by": "test@boschendal.co.za",
            "owner": "internal@example.com",
            "_assign": '["tech.bravo@local.test"]',
            "custom_service_area": "Internet Connection",
            "template": {
                "fields": [
                    {
                        "fieldname": "custom_service_area",
                        "fieldtype": "Select",
                        "label": "Service Area",
                        "hide_from_customer": 0,
                    }
                ]
            },
            "communications": [
                {
                    "name": "internal-secret",
                    "content": "Private investigation",
                }
            ],
            "comments": [{"content": "Internal comment"}],
            "history": [{"action": "Assignment changed"}],
            "views": [{"viewed_by": "internal@example.com"}],
            "calls": [{"recording_url": "/private/recording"}],
        }

    def tearDown(self):
        if self._original_flags is None:
            del frappe.local.flags
        else:
            frappe.local.flags = self._original_flags

    def test_customer_receives_projected_detail(self):
        activities = {
            "communications": [
                {
                    "name": "customer-visible",
                    "content": "Approved update",
                    "sender": "test@boschendal.co.za",
                    "attachments": [],
                }
            ],
            "comments": [],
            "history": [],
            "views": [],
            "calls": [],
        }

        with (
            patch.object(guard, "_require_ticket_read"),
            patch(
                "telephony.customer_communication_privacy."
                "get_current_actor_access",
                return_value=self.customer_access,
            ),
            patch.object(
                guard.helpdesk_api,
                "get_one",
                return_value=self.detail,
            ) as native,
            patch.object(
                guard,
                "get_ticket_activities",
                return_value=activities,
            ) as activity_guard,
            patch.object(
                guard.frappe,
                "session",
                frappe._dict(user="test@boschendal.co.za"),
            ),
        ):
            result = guard.get_one(
                "902",
                is_customer_portal=False,
            )

        native.assert_called_once_with(
            "902",
            is_customer_portal=True,
        )
        activity_guard.assert_called_once_with("902")

        self.assertEqual(result["name"], 902)
        self.assertEqual(result["subject"], "Internet fault")
        self.assertEqual(
            result["custom_service_area"],
            "Internet Connection",
        )

        self.assertEqual(
            result["communications"],
            activities["communications"],
        )

        for field in ("owner", "_assign", "_customActions"):
            self.assertNotIn(field, result)

        self.assertEqual(
            result["contact"],
            {
                "name": "test@boschendal.co.za",
                "email_id": "test@boschendal.co.za",
                "image": None,
            },
        )

        for section in ("comments", "history", "views", "calls"):
            self.assertEqual(result[section], [])

        self.assertEqual(result["_form_script"], "")

    def test_internal_user_retains_native_response(self):
        access = {
            "actor_kind": "internal",
            "ticket_read_allowed": True,
            "is_ticket_customer": False,
        }

        with (
            patch.object(guard, "_require_ticket_read"),
            patch(
                "telephony.customer_communication_privacy."
                "get_current_actor_access",
                return_value=access,
            ),
            patch.object(
                guard.helpdesk_api,
                "get_one",
                return_value=self.detail,
            ) as native,
            patch.object(
                guard,
                "get_ticket_activities",
            ) as activities,
        ):
            result = guard.get_one(
                "902",
                is_customer_portal=True,
            )

        self.assertIs(result, self.detail)

        native.assert_called_once_with(
            "902",
            is_customer_portal=False,
        )

        activities.assert_not_called()

    def test_external_unauthorised_actors_denied(self):
        cases = (
            ("partner", False),
            ("unknown", False),
            ("customer", False),
        )

        for actor_kind, ownership in cases:
            with self.subTest(actor_kind=actor_kind):
                access = {
                    "actor_kind": actor_kind,
                    "ticket_read_allowed": True,
                    "is_ticket_customer": ownership,
                }

                with (
                    patch.object(
                        guard,
                        "_require_ticket_read",
                    ),
                    patch(
                        "telephony.customer_communication_privacy."
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
                        "get_one",
                    ) as native,
                ):
                    with self.assertRaises(frappe.PermissionError):
                        guard.get_one("902")

                native.assert_not_called()

    def test_ticket_read_denial_blocks_native_lookup(self):
        with (
            patch.object(
                guard,
                "_require_ticket_read",
                side_effect=frappe.PermissionError,
            ),
            patch.object(
                guard.helpdesk_api,
                "get_one",
            ) as native,
        ):
            with self.assertRaises(frappe.PermissionError):
                guard.get_one("941")

        native.assert_not_called()


if __name__ == "__main__":
    unittest.main()
