import unittest
from unittest.mock import patch

import frappe

from telephony import customer_ticket_resolution as resolution
from telephony import customer_communication_privacy as privacy


class TestCustomerCompletionDownloadSecurity(unittest.TestCase):

    def test_sent_unclassified_communication_attachment_is_denied(self):
        file_doc = frappe._dict({
            "name": "FILE-001",
            "file_name": "private-report.xls",
            "attached_to_doctype": "Communication",
            "attached_to_name": "COMM-INTERNAL",
        })

        communication = frappe._dict({
            "name": "COMM-INTERNAL",
            "reference_doctype": "HD Ticket",
            "reference_name": "54",
            "sent_or_received": "Sent",
            "custom_telectro_audience": "",
        })

        def get_doc(doctype, name):
            if (doctype, name) == ("File", "FILE-001"):
                return file_doc

            if (doctype, name) == (
                "Communication",
                "COMM-INTERNAL",
            ):
                return communication

            raise AssertionError(
                f"Unexpected document lookup: {doctype} {name}"
            )

        with (
            patch.object(
                resolution.frappe.db,
                "get_value",
                return_value="FILE-001",
            ),
            patch.object(
                resolution.frappe,
                "get_doc",
                side_effect=get_doc,
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                resolution._get_customer_completion_evidence_file(
                    ticket_name="54",
                    file_id="FILE-001",
                )

    def test_same_customer_organisation_member_has_ticket_access(self):
        ticket = frappe._dict({
            "name": "54",
            "customer": "Emerald Life",
            "raised_by": "reinhardt.botes@emeraldlife.co.za",
        })

        authorised_access = {
            "actor_kind": "customer",
            "ticket_read_allowed": True,
            "is_ticket_customer": True,
        }

        with (
            patch.object(
                resolution.frappe,
                "session",
                frappe._dict(
                    user="bendre.leroux@emeraldlife.co.za",
                ),
            ),
            patch.object(
                resolution.frappe,
                "get_roles",
                return_value=["All", "Customer"],
            ),
            patch.object(
                privacy,
                "get_current_actor_access",
                return_value=authorised_access,
            ) as access_lookup,
            patch.object(
                resolution.frappe,
                "throw",
            ) as deny,
        ):
            resolution._require_customer_ticket_access(ticket)

        deny.assert_not_called()
        access_lookup.assert_called_once_with("54")

    def test_other_customer_organisation_is_denied(self):
        ticket = frappe._dict({
            "name": "54",
            "customer": "Emerald Life",
        })

        denied_access = {
            "actor_kind": "customer",
            "ticket_read_allowed": True,
            "is_ticket_customer": False,
        }

        with (
            patch.object(
                privacy,
                "get_current_actor_access",
                return_value=denied_access,
            ) as access_lookup,
            patch.object(
                resolution.frappe,
                "throw",
                side_effect=frappe.PermissionError,
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                resolution._require_customer_ticket_access(
                    ticket,
                )

        access_lookup.assert_called_once_with("54")

    def test_unauthorised_actor_contexts_are_denied(self):
        ticket = frappe._dict({
            "name": "54",
            "customer": "Emerald Life",
        })

        cases = [
            (
                "internal_without_ticket_read",
                {
                    "actor_kind": "internal",
                    "ticket_read_allowed": False,
                    "is_ticket_customer": False,
                },
            ),
            (
                "customer_without_ticket_read",
                {
                    "actor_kind": "customer",
                    "ticket_read_allowed": False,
                    "is_ticket_customer": True,
                },
            ),
            (
                "partner_with_ticket_read",
                {
                    "actor_kind": "partner",
                    "ticket_read_allowed": True,
                    "is_ticket_customer": False,
                },
            ),
            (
                "unknown_with_ticket_read",
                {
                    "actor_kind": "unknown",
                    "ticket_read_allowed": True,
                    "is_ticket_customer": False,
                },
            ),
        ]

        for label, access in cases:
            with self.subTest(actor=label):
                with (
                    patch.object(
                        privacy,
                        "get_current_actor_access",
                        return_value=access,
                    ) as access_lookup,
                    patch.object(
                        resolution.frappe,
                        "throw",
                        side_effect=frappe.PermissionError,
                    ) as deny,
                ):
                    with self.assertRaises(frappe.PermissionError):
                        resolution._require_customer_ticket_access(
                            ticket,
                        )

                access_lookup.assert_called_once_with("54")
                deny.assert_called_once()

    def test_file_from_different_ticket_is_denied(self):
        file_doc = frappe._dict({
            "name": "FILE-CROSS",
            "file_name": "other-customer-report.xls",
            "attached_to_doctype": "Communication",
            "attached_to_name": "COMM-OTHER",
        })

        communication = frappe._dict({
            "name": "COMM-OTHER",
            "reference_doctype": "HD Ticket",
            "reference_name": "999",
            "sent_or_received": "Sent",
            "custom_telectro_audience": "Customer",
        })

        def get_doc(doctype, name):
            if (doctype, name) == ("File", "FILE-CROSS"):
                return file_doc

            if (doctype, name) == (
                "Communication",
                "COMM-OTHER",
            ):
                return communication

            raise AssertionError(
                f"Unexpected document lookup: {doctype} {name}"
            )

        with (
            patch.object(
                resolution.frappe.db,
                "get_value",
                return_value="FILE-CROSS",
            ),
            patch.object(
                resolution.frappe,
                "get_doc",
                side_effect=get_doc,
            ),
            patch.object(
                resolution.frappe,
                "throw",
                side_effect=frappe.PermissionError,
            ) as deny,
        ):
            with self.assertRaises(frappe.PermissionError):
                resolution._get_customer_completion_evidence_file(
                    ticket_name="54",
                    file_id="FILE-CROSS",
                )

        deny.assert_called_once()

    def test_file_url_only_lookup_is_denied(self):
        file_doc = frappe._dict({
            "name": "FILE-URL",
            "file_name": "report.xls",
            "file_url": "/private/files/report.xls",
            "attached_to_doctype": "Communication",
            "attached_to_name": "COMM-CUSTOMER",
        })

        communication = frappe._dict({
            "name": "COMM-CUSTOMER",
            "reference_doctype": "HD Ticket",
            "reference_name": "54",
            "sent_or_received": "Sent",
            "custom_telectro_audience": "Customer",
        })

        with (
            patch.object(
                resolution.frappe.db,
                "get_value",
                return_value="FILE-URL",
            ),
            patch.object(
                resolution.frappe,
                "get_doc",
                side_effect=[file_doc, communication],
            ),
            patch.object(
                resolution.frappe,
                "throw",
                side_effect=frappe.PermissionError,
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                resolution._get_customer_completion_evidence_file(
                    ticket_name="54",
                    file_url="/private/files/report.xls",
                )

    def test_download_endpoint_rejects_url_only_before_document_access(self):
        with (
            patch.object(
                resolution.frappe,
                "throw",
                side_effect=frappe.PermissionError,
            ) as deny,
            patch.object(
                resolution.frappe,
                "get_doc",
            ) as get_doc,
            patch.object(
                resolution,
                "_is_customer_ticket",
                return_value=True,
            ),
            patch.object(
                resolution,
                "_require_customer_ticket_access",
            ),
            patch.object(
                resolution,
                "_get_customer_completion_evidence_file",
                side_effect=frappe.PermissionError,
            ) as file_lookup,
        ):
            with self.assertRaises(frappe.PermissionError):
                resolution.download_customer_completion_evidence(
                    ticket_name="54",
                    file_url="/private/files/report.xls",
                )

        deny.assert_called_once()
        get_doc.assert_not_called()
        file_lookup.assert_not_called()

    def test_authorised_download_returns_file_content(self):
        from unittest.mock import Mock

        ticket = frappe._dict({
            "name": "54",
            "customer": "Emerald Life",
            "raised_by": "customer@example.com",
        })

        expected_content = b"controlled-test-file-content"

        file_doc = frappe._dict({
            "name": "FILE-001",
            "file_name": "report.xls",
            "get_content": Mock(return_value=expected_content),
        })

        response = frappe._dict()

        with (
            patch.object(
                resolution.frappe,
                "get_doc",
                return_value=ticket,
            ) as get_doc,
            patch.object(
                resolution,
                "_is_customer_ticket",
                return_value=True,
            ),
            patch.object(
                resolution,
                "_require_customer_ticket_access",
            ) as access_check,
            patch.object(
                resolution,
                "_get_customer_completion_evidence_file",
                return_value=file_doc,
            ) as file_lookup,
            patch.object(
                resolution.frappe.local,
                "response",
                response,
                create=True,
            ),
        ):
            resolution.download_customer_completion_evidence(
                ticket_name="54",
                file_id="FILE-001",
            )

        get_doc.assert_called_once_with("HD Ticket", "54")
        access_check.assert_called_once_with(ticket)
        file_lookup.assert_called_once_with(
            ticket_name="54",
            file_url="",
            file_id="FILE-001",
        )

        file_doc.get_content.assert_called_once_with()

        self.assertEqual(response.type, "download")
        self.assertEqual(response.filename, "report.xls")
        self.assertEqual(response.filecontent, expected_content)
