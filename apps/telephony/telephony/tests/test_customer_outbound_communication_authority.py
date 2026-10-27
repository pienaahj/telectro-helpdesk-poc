
"""Regression tests for Customer-directed Communication authority."""

import unittest
from types import SimpleNamespace
from unittest import mock

import frappe

from telephony import customer_communication_privacy as privacy


TICKET = "902"
ACTOR = "tech@telectro.test"
RECIPIENT = "customer@boschendal.test"
CUSTOMER = "Boschendal"


def raise_permission_error(message, exception_class=frappe.PermissionError):
    raise exception_class(message)


class TestCustomerOutboundCommunicationAuthority(unittest.TestCase):

    def setUp(self):
        self.ticket_record = {
            "customer": CUSTOMER,
            "raised_by": RECIPIENT,
            "via_customer_portal": 1,
            "custom_request_source": "Customer",
        }
        self.recipient_enabled = 1
        self.ticket_doc = object()

        def db_get_value(doctype, name, field, **kwargs):
            if doctype == "HD Ticket":
                self.assertEqual(name, TICKET)
                self.assertEqual(
                    field,
                    [
                        "customer",
                        "raised_by",
                        "via_customer_portal",
                        "custom_request_source",
                    ],
                )
                return self.ticket_record

            if doctype == "User":
                self.assertEqual(name, RECIPIENT)
                self.assertEqual(field, "enabled")
                return self.recipient_enabled

            raise AssertionError(f"Unexpected DocType: {doctype}")

        self.fake_frappe = SimpleNamespace(
            PermissionError=frappe.PermissionError,
            session=SimpleNamespace(user=ACTOR),
            has_permission=mock.Mock(return_value=True),
            db=SimpleNamespace(
                get_value=mock.Mock(side_effect=db_get_value),
            ),
            get_doc=mock.Mock(return_value=self.ticket_doc),
            get_roles=mock.Mock(return_value=["Customer"]),
            throw=mock.Mock(side_effect=raise_permission_error),
        )

        self.access = {
            "actor_kind": "internal",
            "ticket_read_allowed": True,
            "is_ticket_customer": False,
        }

        patchers = [
            mock.patch.object(
                privacy,
                "frappe",
                self.fake_frappe,
            ),
            mock.patch.object(
                privacy,
                "get_current_actor_access",
                return_value=self.access,
            ),
            mock.patch.object(
                privacy,
                "get_customer",
                return_value=[CUSTOMER],
            ),
            mock.patch.object(
                privacy,
                "validate_ticket_edit_rights",
            ),
        ]

        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.access_mock = privacy.get_current_actor_access
        self.customer_mock = privacy.get_customer
        self.edit_guard_mock = privacy.validate_ticket_edit_rights

        token = privacy._customer_outbound_intent.set(None)
        self.addCleanup(
            lambda: privacy._customer_outbound_intent.reset(token)
        )

    def make_communication(self, **changes):
        values = {
            "reference_doctype": "HD Ticket",
            "reference_name": TICKET,
            "sent_or_received": "Sent",
            "communication_type": "Communication",
            "communication_medium": "Email",
            "sender": ACTOR,
            "recipients": RECIPIENT,
            "cc": None,
            "bcc": None,
            "custom_telectro_audience": None,
        }
        values.update(changes)
        return frappe._dict(values)

    def test_authorised_internal_actor_and_recipient(self):
        actual = privacy.require_customer_update_authority(
            TICKET, RECIPIENT
        )

        self.assertEqual(actual, RECIPIENT)
        self.edit_guard_mock.assert_called_once_with(
            self.ticket_doc
        )

    def test_missing_ticket_or_recipient_denied(self):
        for ticket, recipient in (
            ("", RECIPIENT),
            (TICKET, ""),
            (None, RECIPIENT),
            (TICKET, None),
        ):
            with self.subTest(ticket=ticket, recipient=recipient):
                with self.assertRaises(frappe.PermissionError):
                    privacy.require_customer_update_authority(
                        ticket, recipient
                    )

    def test_noninternal_or_unreadable_ticket_denied(self):
        for actor_kind, readable in (
            ("customer", True),
            ("partner", True),
            ("unknown", True),
            ("internal", False),
        ):
            with self.subTest(
                actor_kind=actor_kind,
                readable=readable,
            ):
                self.access_mock.return_value = {
                    "actor_kind": actor_kind,
                    "ticket_read_allowed": readable,
                }

                with self.assertRaises(frappe.PermissionError):
                    privacy.require_customer_update_authority(
                        TICKET, RECIPIENT
                    )

    def test_missing_ticket_write_permission_denied(self):
        self.fake_frappe.has_permission.return_value = False

        with self.assertRaises(frappe.PermissionError):
            privacy.require_customer_update_authority(
                TICKET, RECIPIENT
            )

        self.edit_guard_mock.assert_not_called()

    def test_missing_ticket_or_customer_denied(self):
        for record in (
            None,
            {"customer": None, "raised_by": RECIPIENT},
        ):
            with self.subTest(record=record):
                self.ticket_record = record

                with self.assertRaises(frappe.PermissionError):
                    privacy.require_customer_update_authority(
                        TICKET, RECIPIENT
                    )

    def test_recipient_must_match_ticket_raiser(self):
        self.ticket_record["raised_by"] = "other@example.test"

        with self.assertRaises(frappe.PermissionError):
            privacy.require_customer_update_authority(
                TICKET, RECIPIENT
            )

    def test_internal_creator_can_use_verified_customer_recipient(self):
        self.ticket_record["raised_by"] = ACTOR
        self.ticket_record["custom_request_source"] = "Telectro"
        self.ticket_record["via_customer_portal"] = 0

        actual = privacy.require_customer_update_authority(
            TICKET, RECIPIENT
        )

        self.assertEqual(actual, RECIPIENT)
        self.edit_guard_mock.assert_called_once_with(
            self.ticket_doc
        )

    def test_disabled_recipient_denied(self):
        self.recipient_enabled = 0

        with self.assertRaises(frappe.PermissionError):
            privacy.require_customer_update_authority(
                TICKET, RECIPIENT
            )

    def test_cross_customer_recipient_denied(self):
        self.customer_mock.return_value = ["Emerald Life"]

        with self.assertRaises(frappe.PermissionError):
            privacy.require_customer_update_authority(
                TICKET, RECIPIENT
            )

    def test_ambiguous_recipient_roles_denied(self):
        self.fake_frappe.get_roles.return_value = [
            "Customer",
            "TELECTRO-POC Role - Partner",
        ]

        with self.assertRaises(frappe.PermissionError):
            privacy.require_customer_update_authority(
                TICKET, RECIPIENT
            )

    def test_existing_ticket_edit_guard_denial_preserved(self):
        self.edit_guard_mock.side_effect = frappe.PermissionError(
            "Not assigned to this technician"
        )

        with self.assertRaises(frappe.PermissionError):
            privacy.require_customer_update_authority(
                TICKET, RECIPIENT
            )

    def test_valid_outbound_scope_classifies_communication(self):
        doc = self.make_communication()

        with privacy.customer_outbound_communication_scope(
            TICKET, RECIPIENT
        ):
            privacy.classify_new_customer_communication(doc)

        self.assertEqual(
            doc.custom_telectro_audience,
            "Customer",
        )

    def test_outbound_scope_rejects_mismatched_fields(self):
        invalid_fields = {
            "reference_doctype": "Task",
            "reference_name": "941",
            "sent_or_received": "Received",
            "communication_type": "Comment",
            "communication_medium": "SMS",
            "sender": "other@telectro.test",
            "recipients": "other@boschendal.test",
            "cc": "cc@example.test",
            "bcc": "bcc@example.test",
        }

        with privacy.customer_outbound_communication_scope(
            TICKET, RECIPIENT
        ):
            for field, value in invalid_fields.items():
                with self.subTest(field=field):
                    doc = self.make_communication(
                        **{field: value}
                    )

                    with self.assertRaises(frappe.PermissionError):
                        privacy.classify_new_customer_communication(
                            doc
                        )

                    self.assertFalse(
                        doc.get("custom_telectro_audience")
                    )

    def test_actor_change_during_scope_denied(self):
        doc = self.make_communication()

        with privacy.customer_outbound_communication_scope(
            TICKET, RECIPIENT
        ):
            self.fake_frappe.session.user = "other@telectro.test"

            with self.assertRaises(frappe.PermissionError):
                privacy.classify_new_customer_communication(doc)

        self.assertFalse(doc.get("custom_telectro_audience"))

    def test_client_supplied_audience_denied_inside_scope(self):
        doc = self.make_communication(
            custom_telectro_audience="Customer"
        )

        with privacy.customer_outbound_communication_scope(
            TICKET, RECIPIENT
        ):
            with self.assertRaises(frappe.PermissionError):
                privacy.classify_new_customer_communication(doc)

    def test_scope_restored_after_normal_completion(self):
        self.assertIsNone(privacy._customer_outbound_intent.get())

        with privacy.customer_outbound_communication_scope(
            TICKET, RECIPIENT
        ):
            self.assertEqual(
                privacy._customer_outbound_intent.get(),
                (TICKET, RECIPIENT, ACTOR),
            )

        self.assertIsNone(privacy._customer_outbound_intent.get())

    def test_scope_restored_after_exception(self):
        with self.assertRaisesRegex(RuntimeError, "failure"):
            with privacy.customer_outbound_communication_scope(
                TICKET, RECIPIENT
            ):
                raise RuntimeError("insertion failure")

        self.assertIsNone(privacy._customer_outbound_intent.get())

    def test_nested_scope_restores_previous_intent(self):
        with privacy.customer_outbound_communication_scope(
            TICKET, RECIPIENT
        ):
            outer_intent = privacy._customer_outbound_intent.get()

            with privacy.customer_outbound_communication_scope(
                TICKET, RECIPIENT
            ):
                privacy._customer_outbound_intent.set(
                    ("modified-ticket", "modified-recipient", ACTOR)
                )

            self.assertEqual(
                privacy._customer_outbound_intent.get(),
                outer_intent,
            )

        self.assertIsNone(privacy._customer_outbound_intent.get())

    def test_sent_communication_without_scope_not_classified(self):
        doc = self.make_communication()

        privacy.classify_new_customer_communication(doc)

        self.assertFalse(doc.get("custom_telectro_audience"))


if __name__ == "__main__":
    unittest.main()
