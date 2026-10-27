import unittest
from unittest import mock

import frappe

from telephony import customer_ticket_api_guard as guarded


ENDPOINTS = (
    "get_ticket_activities",
    "get_ticket_assignees",
    "get_ticket_contact",
    "get_recent_similar_tickets",
)


def raise_permission_error(message, exception_class):
    raise exception_class(message)


class TestCustomerTicketApiGuard(unittest.TestCase):

    def setUp(self):
        # Plain unittest runs outside Frappe's request/test context.
        # Initialise flags so whitelisted decorators can execute.
        self._original_flags = getattr(
            frappe.local,
            "flags",
            None,
        )

        frappe.local.flags = frappe._dict(in_test=False)

    def tearDown(self):
        # Restore the original Frappe context after every test.
        if self._original_flags is None:
            del frappe.local.flags
        else:
            frappe.local.flags = self._original_flags

    def test_unreadable_ticket_denied_by_all_endpoints(self):
        with (
            mock.patch.object(
                guarded.frappe,
                "has_permission",
                return_value=False,
            ),
            mock.patch.object(
                guarded.frappe,
                "throw",
                side_effect=raise_permission_error,
            ),
            mock.patch.object(
                guarded,
                "_",
                side_effect=lambda message: message,
            ),
            mock.patch.object(
                guarded,
                "helpdesk_api",
            ) as upstream,
        ):
            for endpoint in ENDPOINTS:
                with self.subTest(endpoint=endpoint):
                    with self.assertRaises(frappe.PermissionError):
                        getattr(guarded, endpoint)("941")

                    getattr(
                        upstream,
                        endpoint,
                    ).assert_not_called()

    def test_authorised_activity_retains_response(self):
        expected = {
            "comments": [],
            "communications": [{"name": "COMM-001"}],
            "history": [],
            "views": [],
            "calls": [],
        }

        internal_access = {
            "actor_kind": "internal",
            "ticket_read_allowed": True,
            "is_ticket_customer": False,
        }

        with (
            mock.patch.object(
                guarded.frappe,
                "has_permission",
                return_value=True,
            ),
            mock.patch(
                "telephony.customer_communication_privacy."
                "get_current_actor_access",
                return_value=internal_access,
            ),
            mock.patch.object(
                guarded,
                "helpdesk_api",
            ) as upstream,
        ):
            upstream.get_ticket_activities.return_value = expected

            result = guarded.get_ticket_activities("902")

            self.assertEqual(result, expected)
            upstream.get_ticket_activities.assert_called_once_with(
                "902"
            )

    def test_authorised_assignees_remain_json_string(self):
        expected = '["tech.bravo@local.test"]'

        with (
            mock.patch.object(
                guarded.frappe,
                "has_permission",
                return_value=True,
            ),
            mock.patch.object(
                guarded,
                "helpdesk_api",
            ) as upstream,
            mock.patch(
                "telephony.customer_communication_privacy."
                "get_current_actor_access",
                return_value={
                    "actor_kind": "internal",
                    "ticket_read_allowed": True,
                    "is_ticket_customer": False,
                },
            ),

        ):
            upstream.get_ticket_assignees.return_value = expected

            result = guarded.get_ticket_assignees("902")

            self.assertEqual(result, expected)
            upstream.get_ticket_assignees.assert_called_once_with(
                "902"
            )

    def test_authorised_contact_retains_response(self):
        expected = {
            "name": "CONTACT-001",
            "email_id": "customer@example.com",
        }

        with (
            mock.patch.object(
                guarded.frappe,
                "has_permission",
                return_value=True,
            ),
            mock.patch.object(
                guarded,
                "helpdesk_api",
            ) as upstream,
            mock.patch(
                "telephony.customer_communication_privacy."
                "get_current_actor_access",
                return_value={
                    "actor_kind": "internal",
                    "ticket_read_allowed": True,
                    "is_ticket_customer": False,
                },
            ),

        ):
            upstream.get_ticket_contact.return_value = expected

            result = guarded.get_ticket_contact("902")

            self.assertEqual(result, expected)
            upstream.get_ticket_contact.assert_called_once_with(
                "902"
            )

    def test_customer_assignees_are_hidden(self):
        access = {
            "actor_kind": "customer",
            "ticket_read_allowed": True,
            "is_ticket_customer": True,
        }

        with (
            mock.patch.object(
                guarded.frappe,
                "has_permission",
                return_value=True,
            ),
            mock.patch(
                "telephony.customer_communication_privacy."
                "get_current_actor_access",
                return_value=access,
            ),
            mock.patch.object(
                guarded,
                "helpdesk_api",
            ) as upstream,
        ):
            result = guarded.get_ticket_assignees("902")

            self.assertEqual(result, "[]")
            upstream.get_ticket_assignees.assert_not_called()

    def test_customer_contact_is_viewer_only(self):
        viewer = "test@boschendal.co.za"

        access = {
            "actor_kind": "customer",
            "ticket_read_allowed": True,
            "is_ticket_customer": True,
        }

        with (
            mock.patch.object(
                guarded.frappe,
                "has_permission",
                return_value=True,
            ),
            mock.patch(
                "telephony.customer_communication_privacy."
                "get_current_actor_access",
                return_value=access,
            ),
            mock.patch.object(
                guarded.frappe,
                "session",
                frappe._dict(user=viewer),
            ),
            mock.patch.object(
                guarded,
                "helpdesk_api",
            ) as upstream,
        ):
            result = guarded.get_ticket_contact("902")

            self.assertEqual(
                result,
                {
                    "name": viewer,
                    "email_id": viewer,
                    "image": None,
                },
            )

            upstream.get_ticket_contact.assert_not_called()

    def test_assignee_and_contact_access_denied_for_other_actors(self):
        denied_access = (
            ("partner", True, False),
            ("unknown", True, False),
            ("customer", True, False),
            ("internal", False, False),
        )

        with (
            mock.patch.object(
                guarded.frappe,
                "has_permission",
                return_value=True,
            ),
            mock.patch(
                "telephony.customer_communication_privacy."
                "get_current_actor_access",
            ) as get_access,
            mock.patch.object(
                guarded.frappe,
                "throw",
                side_effect=raise_permission_error,
            ),
            mock.patch.object(
                guarded,
                "helpdesk_api",
            ) as upstream,
        ):
            for actor_kind, readable, is_customer in denied_access:
                get_access.return_value = {
                    "actor_kind": actor_kind,
                    "ticket_read_allowed": readable,
                    "is_ticket_customer": is_customer,
                }

                for endpoint in (
                    guarded.get_ticket_assignees,
                    guarded.get_ticket_contact,
                ):
                    with self.subTest(
                        actor_kind=actor_kind,
                        endpoint=endpoint.__name__,
                    ):
                        with self.assertRaises(frappe.PermissionError):
                            endpoint("902")

            upstream.get_ticket_assignees.assert_not_called()
            upstream.get_ticket_contact.assert_not_called()

    def test_similar_tickets_filtered_by_individual_access(self):
        def can_read(doctype, permission, doc=None, **kwargs):
            return (
                doctype == "HD Ticket"
                and permission == "read"
                and str(doc) in {"902", "914"}
            )

        upstream_result = {
            "recent_tickets": [
                {"name": "914"},
                {"name": "941"},
            ],
            "similar_tickets": [
                {"name": "941"},
                {"name": "914"},
                {"name": ""},
            ],
        }

        with (
            mock.patch.object(
                guarded.frappe,
                "has_permission",
                side_effect=can_read,
            ),
            mock.patch.object(
                guarded,
                "helpdesk_api",
            ) as upstream,
        ):
            upstream.get_recent_similar_tickets.return_value = (
                upstream_result
            )

            result = guarded.get_recent_similar_tickets("902")

            self.assertEqual(
                result,
                {
                    "recent_tickets": [{"name": "914"}],
                    "similar_tickets": [{"name": "914"}],
                },
            )

            upstream.get_recent_similar_tickets.assert_called_once_with(
                "902"
            )


if __name__ == "__main__":
    unittest.main()
