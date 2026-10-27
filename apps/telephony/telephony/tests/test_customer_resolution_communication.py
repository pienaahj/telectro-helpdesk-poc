"""Standalone regressions for Customer-visible resolution Communications."""

import unittest
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

import frappe

from telephony import customer_ticket_resolution as resolution


TICKET = "948"
ACTOR = "hendrik@local.test"
RECIPIENT = "emerald.portal.test@example.com"


class Ticket(dict):
    name = TICKET

    def __init__(self):
        super().__init__(subject="Controlled Emerald Life DEV acceptance")


def raise_validation(message, exception_class=frappe.PermissionError):
    raise exception_class(message)


class TestCustomerResolutionCommunication(unittest.TestCase):

    def setUp(self):
        self.events = []
        self.comm = SimpleNamespace(name="TEST-COMM-948")
        self.comm.insert = mock.Mock(side_effect=self.record_insert)

        self.fake_frappe = SimpleNamespace(
            PermissionError=frappe.PermissionError,
            session=SimpleNamespace(user=ACTOR),
            get_doc=mock.Mock(return_value=self.comm),
            throw=mock.Mock(side_effect=raise_validation),
        )

        @contextmanager
        def recording_scope(ticket_name, recipient):
            self.events.append(("scope_enter", ticket_name, recipient))
            try:
                yield
            finally:
                self.events.append(("scope_exit", ticket_name, recipient))

        self.scope = mock.Mock(side_effect=recording_scope)

        patchers = [
            mock.patch.object(resolution, "frappe", self.fake_frappe),
            mock.patch.object(
                resolution,
                "customer_outbound_communication_scope",
                self.scope,
            ),
            mock.patch.object(
                resolution,
                "now_datetime",
                return_value=datetime(2026, 10, 27, 20, 0),
            ),
            mock.patch.object(resolution, "_", side_effect=lambda s: s),
        ]

        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def record_insert(self, **kwargs):
        self.events.append(("insert", kwargs))

    def test_resolution_creates_customer_visible_communication(self):
        note = 'Controlled resolution <verified> & "complete"'

        result = (
            resolution._create_customer_visible_resolution_communication(
                Ticket(),
                note,
                RECIPIENT,
            )
        )

        self.assertIs(result, self.comm)

        self.fake_frappe.get_doc.assert_called_once()
        payload = self.fake_frappe.get_doc.call_args.args[0]

        self.assertEqual(payload["doctype"], "Communication")
        self.assertEqual(payload["sender"], ACTOR)
        self.assertEqual(payload["recipients"], RECIPIENT)
        self.assertEqual(payload["reference_doctype"], "HD Ticket")
        self.assertEqual(payload["reference_name"], TICKET)
        self.assertEqual(payload["sent_or_received"], "Sent")
        self.assertEqual(payload["communication_medium"], "Email")

        expected_content = (
            '<div class="ql-editor read-mode">'
            f"<p>{resolution.escape_html(note)}</p>"
            "</div>"
        )
        self.assertEqual(payload["content"], expected_content)
        self.assertNotIn("<verified>", payload["content"])

        self.scope.assert_called_once_with(TICKET, RECIPIENT)
        self.comm.insert.assert_called_once_with(
            ignore_permissions=True
        )

        self.assertEqual(
            self.events,
            [
                ("scope_enter", TICKET, RECIPIENT),
                ("insert", {"ignore_permissions": True}),
                ("scope_exit", TICKET, RECIPIENT),
            ],
        )

    def test_resolution_rejects_missing_customer_recipient(self):
        with self.assertRaises(frappe.PermissionError):
            resolution._create_customer_visible_resolution_communication(
                Ticket(),
                "Controlled resolution",
                "  ",
            )

        self.fake_frappe.get_doc.assert_not_called()
        self.scope.assert_not_called()
        self.comm.insert.assert_not_called()


    def test_portal_recipient_locked_to_requester(self):
        doc = {
            "raised_by": RECIPIENT,
            "via_customer_portal": 1,
            "custom_request_source": "Customer",
        }

        helper = resolution._resolve_customer_message_recipient

        self.assertEqual(helper(doc), RECIPIENT)
        self.assertEqual(helper(doc, RECIPIENT), RECIPIENT)

        with self.assertRaises(frappe.PermissionError):
            helper(doc, "other@example.test")

    def test_customer_source_also_locks_recipient(self):
        doc = {
            "raised_by": RECIPIENT,
            "via_customer_portal": 0,
            "custom_request_source": "Customer",
        }

        with self.assertRaises(frappe.PermissionError):
            resolution._resolve_customer_message_recipient(
                doc,
                "other@example.test",
            )

    def test_internal_ticket_requires_explicit_recipient(self):
        doc = {
            "raised_by": ACTOR,
            "via_customer_portal": 0,
            "custom_request_source": "Telectro",
        }

        for supplied in (None, "", "   "):
            with self.subTest(supplied=supplied):
                with self.assertRaises(frappe.PermissionError):
                    resolution._resolve_customer_message_recipient(
                        doc,
                        supplied,
                    )

    def test_internal_ticket_preserves_explicit_recipient(self):
        doc = {
            "raised_by": ACTOR,
            "via_customer_portal": 0,
            "custom_request_source": "Telectro",
        }

        recipient = resolution._resolve_customer_message_recipient(
            doc,
            RECIPIENT,
        )

        self.assertEqual(recipient, RECIPIENT)
        self.assertEqual(doc["raised_by"], ACTOR)


if __name__ == "__main__":
    unittest.main()
