import unittest
from unittest import mock

import frappe

from telephony import customer_identity_sync


class Ticket(dict):
    """Small in-memory HD Ticket test double."""

    def set(self, fieldname, value):
        self[fieldname] = value


class TestCustomerIdentitySync(unittest.TestCase):

    @staticmethod
    def _raise_validation(message, exc=frappe.ValidationError):
        raise exc(message)

    def setUp(self):
        self.db = mock.Mock()

        db_patcher = mock.patch.dict(
            customer_identity_sync.frappe.__dict__,
            {"db": self.db},
        )
        db_patcher.start()
        self.addCleanup(db_patcher.stop)

        patcher = mock.patch.object(
            customer_identity_sync.frappe,
            "throw",
            side_effect=self._raise_validation,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def ticket(self, **overrides):
        values = {
            "customer": None,
            "custom_customer": None,
            "raised_by": "hendrik@local.test",
            "contact": "Hendrik Pienaar",
            "owner": "hendrik@local.test",
            "custom_request_source": "Telectro",
        }
        values.update(overrides)
        return Ticket(values)

    @mock.patch.object(
        customer_identity_sync.frappe, "get_all",
        return_value=["Emerald Life"],
    )
    def test_portal_ticket_populates_erp_customer(self, get_all):
        self.db.get_value.return_value = "Emerald Life"
        doc = self.ticket(
            customer="Emerald Life",
            raised_by="emerald.portal.test@example.com",
            custom_request_source="Customer",
        )

        customer_identity_sync.sync_ticket_customer_identity(doc)

        self.assertEqual(doc["customer"], "Emerald Life")
        self.assertEqual(doc["custom_customer"], "Emerald Life")
        self.assertEqual(
            doc["raised_by"], "emerald.portal.test@example.com"
        )
        self.db.get_value.assert_called_once_with(
            "HD Customer", "Emerald Life", "custom_erp_customer"
        )

    @mock.patch.object(
        customer_identity_sync.frappe, "get_all",
        return_value=["Emerald Life"],
    )
    def test_internal_ticket_populates_hd_customer(self, get_all):
        doc = self.ticket(custom_customer="Emerald Life")

        customer_identity_sync.sync_ticket_customer_identity(doc)

        self.assertEqual(doc["customer"], "Emerald Life")
        self.assertEqual(doc["custom_customer"], "Emerald Life")
        self.assertEqual(doc["raised_by"], "hendrik@local.test")
        self.assertEqual(doc["contact"], "Hendrik Pienaar")

    def test_conflicting_references_rejected(self):
        self.db.get_value.return_value = "Different Customer"
        doc = self.ticket(
            customer="Emerald Life",
            custom_customer="Emerald Life",
        )

        with self.assertRaises(frappe.ValidationError):
            customer_identity_sync.sync_ticket_customer_identity(doc)

    @mock.patch.object(
        customer_identity_sync.frappe, "get_all",
        return_value=["HD Customer A", "HD Customer B"],
    )
    def test_ambiguous_mapping_rejected(self, get_all):
        doc = self.ticket(custom_customer="Emerald Life")

        with self.assertRaises(frappe.ValidationError):
            customer_identity_sync.sync_ticket_customer_identity(doc)

    @mock.patch.object(
        customer_identity_sync.frappe, "get_all",
        return_value=[],
    )
    def test_unmapped_erp_customer_not_guessed(self, get_all):
        doc = self.ticket(custom_customer="Unmapped Customer")

        customer_identity_sync.sync_ticket_customer_identity(doc)

        self.assertIsNone(doc["customer"])
        self.assertEqual(
            doc["custom_customer"], "Unmapped Customer"
        )

    def test_ticket_without_customer_unchanged(self):
        doc = self.ticket()
        original = dict(doc)

        customer_identity_sync.sync_ticket_customer_identity(doc)

        self.assertEqual(dict(doc), original)
