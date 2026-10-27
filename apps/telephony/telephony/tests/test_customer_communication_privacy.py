import unittest

from telephony.customer_communication_privacy import (
    can_view_communication,
    classify_actor_roles,
)

from unittest.mock import patch

import frappe

class TestCustomerCommunicationPrivacy(unittest.TestCase):

    def test_customer_requires_one_verified_relationship(self):
        self.assertEqual(
            classify_actor_roles(
                {"Customer"},
                linked_hd_customers=["Boschendal"],
            ),
            "customer",
        )

        self.assertEqual(
            classify_actor_roles(
                {"Customer"},
                linked_hd_customers=[],
            ),
            "unknown",
        )

        self.assertEqual(
            classify_actor_roles(
                {"Customer"},
                linked_hd_customers=[
                    "Boschendal",
                    "Emerald Life",
                ],
            ),
            "unknown",
        )

    def test_technician_is_internal(self):
        self.assertEqual(
            classify_actor_roles({
                "Agent",
                "TELECTRO-POC Role - Tech",
            }),
            "internal",
        )

    def test_coordinator_is_internal(self):
        self.assertEqual(
            classify_actor_roles({
                "Agent",
                "TELECTRO-POC Role - Coordinator Ops",
            }),
            "internal",
        )

    def test_partner_is_not_internal(self):
        self.assertEqual(
            classify_actor_roles({
                "Desk User",
                "TELECTRO-POC Role - Partner",
                "TELECTRO-POC Role - Partner Creator",
            }),
            "partner",
        )

    def test_ambiguous_roles_fail_closed(self):
        self.assertEqual(
            classify_actor_roles({
                "TELECTRO-POC Role - Tech",
                "TELECTRO-POC Role - Partner",
            }),
            "unknown",
        )

    def test_generic_agent_is_not_automatically_internal(self):
        self.assertEqual(
            classify_actor_roles({"Agent"}),
            "unknown",
        )

    def test_customer_sees_explicit_customer_audience_only(self):
        for audience in (
            "Internal",
            "Partner",
            None,
            "",
        ):
            with self.subTest(audience=audience):
                self.assertFalse(
                    can_view_communication(
                        ticket_read_allowed=True,
                        actor_kind="customer",
                        audience=audience,
                        is_ticket_customer=True,
                    )
                )

        self.assertTrue(
            can_view_communication(
                ticket_read_allowed=True,
                actor_kind="customer",
                audience="Customer",
                is_ticket_customer=True,
            )
        )

    def test_customer_must_own_ticket_customer_identity(self):
        self.assertFalse(
            can_view_communication(
                ticket_read_allowed=True,
                actor_kind="customer",
                audience="Customer",
                is_ticket_customer=False,
            )
        )

    def test_internal_staff_can_read_legacy_communications(self):
        for audience in (
            "Customer",
            "Internal",
            "Partner",
            None,
        ):
            with self.subTest(audience=audience):
                self.assertTrue(
                    can_view_communication(
                        ticket_read_allowed=True,
                        actor_kind="internal",
                        audience=audience,
                    )
                )

    def test_partner_access_not_yet_enabled(self):
        for audience in (
            "Customer",
            "Internal",
            "Partner",
            None,
        ):
            with self.subTest(audience=audience):
                self.assertFalse(
                    can_view_communication(
                        ticket_read_allowed=True,
                        actor_kind="partner",
                        audience=audience,
                    )
                )

    def test_ticket_permission_is_always_required(self):
        for actor_kind in (
            "internal",
            "customer",
            "partner",
            "unknown",
        ):
            with self.subTest(actor_kind=actor_kind):
                self.assertFalse(
                    can_view_communication(
                        ticket_read_allowed=False,
                        actor_kind=actor_kind,
                        audience="Customer",
                        is_ticket_customer=True,
                    )
                )

    def test_verified_customer_reply_is_classified(self):
        from telephony import customer_communication_privacy as privacy

        doc = frappe._dict(
            reference_doctype="HD Ticket",
            reference_name="902",
            sent_or_received="Received",
            sender="test@boschendal.co.za",
            custom_telectro_audience=None,
        )

        context = {
            "actor_kind": "customer",
            "ticket_read_allowed": True,
            "is_ticket_customer": True,
        }

        with (
            patch.object(
                privacy.frappe,
                "session",
                frappe._dict(
                    user="test@boschendal.co.za",
                ),
            ),
            patch.object(
                privacy,
                "get_current_actor_access",
                return_value=context,
            ),
        ):
            privacy.classify_new_customer_communication(doc)

        self.assertEqual(
            doc.custom_telectro_audience,
            "Customer",
        )

    def test_unverified_customer_reply_stays_unclassified(self):
        from telephony import customer_communication_privacy as privacy

        doc = frappe._dict(
            reference_doctype="HD Ticket",
            reference_name="941",
            sent_or_received="Received",
            sender="test@boschendal.co.za",
            custom_telectro_audience=None,
        )

        context = {
            "actor_kind": "customer",
            "ticket_read_allowed": False,
            "is_ticket_customer": False,
        }

        with (
            patch.object(
                privacy.frappe,
                "session",
                frappe._dict(
                    user="test@boschendal.co.za",
                ),
            ),
            patch.object(
                privacy,
                "get_current_actor_access",
                return_value=context,
            ),
        ):
            privacy.classify_new_customer_communication(doc)

        self.assertFalse(
            doc.get("custom_telectro_audience")
        )

    def test_mismatched_sender_stays_unclassified(self):
        from telephony import customer_communication_privacy as privacy

        doc = frappe._dict(
            reference_doctype="HD Ticket",
            reference_name="902",
            sent_or_received="Received",
            sender="another@example.com",
            custom_telectro_audience=None,
        )

        with patch.object(
            privacy.frappe,
            "session",
            frappe._dict(
                user="test@boschendal.co.za",
            ),
        ):
            privacy.classify_new_customer_communication(doc)

        self.assertFalse(
            doc.get("custom_telectro_audience")
        )

    def test_sent_communication_stays_unclassified(self):
        from telephony import customer_communication_privacy as privacy

        doc = frappe._dict(
            reference_doctype="HD Ticket",
            reference_name="902",
            sent_or_received="Sent",
            sender="test@boschendal.co.za",
            custom_telectro_audience=None,
        )

        with patch.object(
            privacy.frappe,
            "session",
            frappe._dict(
                user="test@boschendal.co.za",
            ),
        ):
            privacy.classify_new_customer_communication(doc)

        self.assertFalse(
            doc.get("custom_telectro_audience")
        )

    def test_client_supplied_audience_is_rejected(self):
        from telephony import customer_communication_privacy as privacy

        doc = frappe._dict(
            reference_doctype="HD Ticket",
            reference_name="902",
            sent_or_received="Received",
            sender="test@boschendal.co.za",
            custom_telectro_audience="Customer",
        )

        with patch.object(
            privacy.frappe,
            "throw",
            side_effect=frappe.PermissionError,
        ):
            with self.assertRaises(frappe.PermissionError):
                privacy.classify_new_customer_communication(doc)

    def check_integrity(self, *, before_audience="Customer", changes=None):
        from telephony import customer_communication_privacy as privacy

        previous = frappe._dict(
            reference_doctype="HD Ticket",
            reference_name="902",
            sender="test@boschendal.co.za",
            sent_or_received="Received",
            custom_telectro_audience=before_audience,
            delivery_status="",
            recipients="helpdesk@telectro.test",
            cc="",
            bcc="",
        )

        current = frappe._dict(dict(previous))
        current.update(changes or {})
        current.get_doc_before_save = lambda: previous

        with patch.object(
            privacy.frappe,
            "throw",
            side_effect=frappe.PermissionError,
        ):
            return privacy.validate_communication_audience_integrity(
                current
            )

    def test_customer_audience_cannot_be_removed(self):
        with self.assertRaises(frappe.PermissionError):
            self.check_integrity(
                changes={"custom_telectro_audience": None},
            )

    def test_unclassified_message_cannot_be_promoted(self):
        with self.assertRaises(frappe.PermissionError):
            self.check_integrity(
                before_audience=None,
                changes={"custom_telectro_audience": "Customer"},
            )

    def test_classified_message_cannot_change_ticket(self):
        with self.assertRaises(frappe.PermissionError):
            self.check_integrity(
                changes={"reference_name": "941"},
            )

    def test_classified_message_cannot_change_sender(self):
        with self.assertRaises(frappe.PermissionError):
            self.check_integrity(
                changes={"sender": "another@example.com"},
            )

    def test_classified_message_cannot_change_direction(self):
        with self.assertRaises(frappe.PermissionError):
            self.check_integrity(
                changes={"sent_or_received": "Sent"},
            )

    def test_classified_message_cannot_change_recipients(self):
        for audience in ("Customer", "Internal", "Partner"):
            for new_recipient in ("other@example.test", ""):
                with self.subTest(
                    audience=audience,
                    new_recipient=new_recipient,
                ):
                    with self.assertRaises(frappe.PermissionError):
                        self.check_integrity(
                            before_audience=audience,
                            changes={"recipients": new_recipient},
                        )

    def test_classified_message_cannot_change_cc(self):
        for audience in ("Customer", "Internal", "Partner"):
            with self.subTest(audience=audience):
                with self.assertRaises(frappe.PermissionError):
                    self.check_integrity(
                        before_audience=audience,
                        changes={"cc": "unexpected@example.test"},
                    )

    def test_classified_message_cannot_change_bcc(self):
        for audience in ("Customer", "Internal", "Partner"):
            with self.subTest(audience=audience):
                with self.assertRaises(frappe.PermissionError):
                    self.check_integrity(
                        before_audience=audience,
                        changes={"bcc": "unexpected@example.test"},
                    )

    def test_delivery_status_update_remains_allowed(self):
        result = self.check_integrity(
            changes={"delivery_status": "Sent"},
        )
        self.assertIsNone(result)

    def test_unchanged_classified_message_remains_allowed(self):
        result = self.check_integrity()
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
