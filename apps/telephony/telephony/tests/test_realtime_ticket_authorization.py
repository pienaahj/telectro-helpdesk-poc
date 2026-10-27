import unittest

from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe

from telephony import realtime_ticket_authorization as authority


class TestRealtimeTicketAuthorization(unittest.TestCase):

    def setUp(self):
        self.fake_frappe = SimpleNamespace(
            PermissionError=frappe.PermissionError,
            session=SimpleNamespace(
                user="ops.test@local.test",
            ),
        )

        self.access = Mock(
            return_value={
                "actor_kind": "internal",
                "ticket_read_allowed": True,
            }
        )

        patches = [
            # The whitelist typing-validation wrapper accesses the
            # real Frappe local context before our function executes.
            # Standalone unittest does not initialise local.flags.
            patch.object(
                frappe.local,
                "flags",
                SimpleNamespace(in_test=False),
                create=True,
            ),
            patch.object(
                authority,
                "frappe",
                self.fake_frappe,
            ),
            patch.object(
                authority,
                "get_current_actor_access",
                self.access,
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def set_actor(
        self,
        kind,
        *,
        read=True,
        user="test@example.com",
        is_ticket_customer=False,
    ):
        self.fake_frappe.session.user = user
        self.access.return_value = {
            "actor_kind": kind,
            "ticket_read_allowed": read,
            "is_ticket_customer": is_ticket_customer,
        }

    def verify(self, channel, ticket="902"):
        return authority.require_ticket_realtime_access(
            ticket_name=ticket,
            channel=channel,
        )

    def assert_denied(self, channel, ticket="902"):
        with self.assertRaises(frappe.PermissionError):
            self.verify(channel, ticket)

    def test_internal_native_document_allowed(self):
        self.assertTrue(self.verify("native_doc"))

        self.access.assert_called_once_with("902")

    def test_customer_native_document_denied(self):
        self.set_actor("customer")
        self.assert_denied("native_doc")

    def test_partner_native_document_denied(self):
        self.set_actor("partner")
        self.assert_denied("native_doc")

    def test_unknown_native_document_denied(self):
        self.set_actor("unknown")
        self.assert_denied("native_doc")

    def test_internal_helpdesk_ticket_allowed(self):
        self.assertTrue(self.verify("helpdesk_ticket"))

    def test_customer_own_helpdesk_ticket_allowed(self):
        self.set_actor(
            "customer",
            read=True,
            is_ticket_customer=True,
        )

        self.assertTrue(self.verify("helpdesk_ticket"))

    def test_other_customer_denied_despite_ticket_read(self):
        self.set_actor(
            "customer",
            read=True,
            is_ticket_customer=False,
        )

        self.assert_denied("helpdesk_ticket")

    def test_authorised_partner_helpdesk_ticket_allowed(self):
        self.set_actor("partner", read=True)

        self.assertTrue(self.verify("helpdesk_ticket"))

    def test_customer_without_ticket_read_denied(self):
        self.set_actor("customer", read=False)

        self.assert_denied("helpdesk_ticket")

    def test_partner_without_ticket_read_denied(self):
        self.set_actor("partner", read=False)

        self.assert_denied("helpdesk_ticket")

    def test_unknown_helpdesk_actor_denied(self):
        self.set_actor("unknown", read=True)

        self.assert_denied("helpdesk_ticket")

    def test_guest_denied(self):
        self.fake_frappe.session.user = "Guest"

        self.assert_denied("helpdesk_ticket")
        self.access.assert_not_called()

    def test_unknown_channel_denied(self):
        self.assert_denied("other_channel")
        self.access.assert_not_called()

    def test_empty_ticket_denied(self):
        self.assert_denied("native_doc", ticket="")
        self.access.assert_not_called()
