
import unittest
from types import SimpleNamespace
from unittest import mock

import frappe

from telephony import data_request_intake as intake
from telephony import customer_portal_ticket_type as portal_guard


CUSTOMER_USER = "emerald.portal.test@example.com"
TECHNICIAN_USER = "tech.bravo@local.test"
HD_CUSTOMER = "Emerald Life"


class Ticket(dict):
    """In-memory HD Ticket with new-document lifecycle state."""

    def __init__(self, *, new=True, previous=None, **values):
        super().__init__(values)
        object.__setattr__(
            self,
            "flags",
            SimpleNamespace(data_request_intake_prepared=False),
        )
        object.__setattr__(self, "_new", new)
        object.__setattr__(self, "_previous", previous)

    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        self[name] = value

    def is_new(self):
        return self._new

    def get_doc_before_save(self):
        return self._previous


class TestDataRequestIntake(unittest.TestCase):

    def setUp(self):
        self.session = SimpleNamespace(user=CUSTOMER_USER)
        self.db = mock.Mock()

        self.db.get_value.return_value = SimpleNamespace(
            enabled=1,
            user_type="Website User",
        )

        patcher = mock.patch.dict(
            intake.frappe.__dict__,
            {
                "session": self.session,
                "db": self.db,
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch.object(
            intake,
            "get_customer",
            return_value=[HD_CUSTOMER],
        )
        self.get_customer = patcher.start()
        self.addCleanup(patcher.stop)

    def ticket(self, *, new=True, previous=None, **overrides):
        values = {
            "custom_service_area": "Data Request",
            "customer": HD_CUSTOMER,
            "raised_by": CUSTOMER_USER,
            "ticket_type": "Faults",
            "priority": "Medium",
        }
        values.update(overrides)

        return Ticket(
            new=new,
            previous=previous,
            **values,
        )

    def test_customer_creation_sets_type_and_priority(self):
        doc = self.ticket()

        intake.prepare_data_request_insert(doc)
        intake.validate_data_request_intake(doc)

        self.assertEqual(doc.ticket_type, "Service Request")
        self.assertEqual(doc.priority, "High")
        self.assertTrue(doc.flags.data_request_intake_prepared)

    def test_customer_cannot_choose_urgent_on_creation(self):
        doc = self.ticket(priority="Urgent")

        intake.prepare_data_request_insert(doc)

        self.assertEqual(doc.priority, "High")

    def test_internal_technician_cannot_create(self):
        self.session.user = TECHNICIAN_USER
        self.db.get_value.return_value = SimpleNamespace(
            enabled=1,
            user_type="System User",
        )

        with self.assertRaises(frappe.PermissionError):
            intake.prepare_data_request_insert(self.ticket())

    def test_administrator_and_guest_cannot_create(self):
        for actor in ("Administrator", "Guest", ""):
            with self.subTest(actor=actor):
                self.session.user = actor

                with self.assertRaises(frappe.PermissionError):
                    intake.prepare_data_request_insert(self.ticket())

    def test_disabled_customer_cannot_create(self):
        self.db.get_value.return_value = SimpleNamespace(
            enabled=0,
            user_type="Website User",
        )

        with self.assertRaises(frappe.PermissionError):
            intake.prepare_data_request_insert(self.ticket())

    def test_unlinked_website_user_cannot_create(self):
        self.get_customer.return_value = []

        with self.assertRaises(frappe.PermissionError):
            intake.prepare_data_request_insert(self.ticket())

    def test_foreign_hd_customer_rejected(self):
        doc = self.ticket(customer="Another Customer")

        with self.assertRaises(frappe.PermissionError):
            intake.prepare_data_request_insert(doc)

    def test_forged_requester_rejected(self):
        doc = self.ticket(raised_by="another@example.com")

        with self.assertRaises(frappe.PermissionError):
            intake.prepare_data_request_insert(doc)

    def test_missing_hd_customer_rejected_at_validation(self):
        doc = self.ticket(customer=None)

        intake.prepare_data_request_insert(doc)

        with self.assertRaises(frappe.PermissionError):
            intake.validate_data_request_intake(doc)

    def test_customer_identity_can_arrive_after_preparation(self):
        doc = self.ticket(customer=None)

        intake.prepare_data_request_insert(doc)

        # Simulate native Helpdesk Customer population.
        doc.customer = HD_CUSTOMER

        intake.validate_data_request_intake(doc)

        self.assertEqual(doc.priority, "High")

    def test_late_classification_rejected(self):
        doc = self.ticket(priority="High")

        with self.assertRaises(frappe.PermissionError):
            intake.validate_data_request_intake(doc)

    def test_priority_manipulation_after_preparation_rejected(self):
        doc = self.ticket()

        intake.prepare_data_request_insert(doc)
        doc.priority = "Medium"

        with self.assertRaises(frappe.PermissionError):
            intake.validate_data_request_intake(doc)

    def test_existing_ticket_conversion_rejected(self):
        previous = self.ticket(
            new=False,
            custom_service_area="PABX",
        )
        doc = self.ticket(new=False, previous=previous)

        with self.assertRaises(frappe.PermissionError):
            intake.validate_data_request_intake(doc)

    def test_existing_data_request_update_allowed(self):
        previous = self.ticket(new=False)
        doc = self.ticket(new=False, previous=previous)

        # Existing tickets may be updated by authorized
        # internal users; this guard must not obstruct them.
        self.session.user = TECHNICIAN_USER

        intake.validate_data_request_intake(doc)

    def test_other_service_areas_unchanged(self):
        doc = self.ticket(
            custom_service_area="PABX",
            ticket_type="Faults",
            priority="Medium",
        )

        intake.prepare_data_request_insert(doc)
        intake.validate_data_request_intake(doc)

        self.assertEqual(doc.ticket_type, "Faults")
        self.assertEqual(doc.priority, "Medium")
        self.assertFalse(doc.flags.data_request_intake_prepared)

    def test_portal_fault_data_request_rejected(self):
        doc = self.ticket(
            via_customer_portal=1,
            ticket_type="Faults",
            custom_request_type="Other",
        )

        with self.assertRaisesRegex(
            frappe.ValidationError,
            "Data Requests must be Service Requests",
        ):
            intake.prepare_data_request_insert(doc)

        # Failed validation must not silently normalize the ticket.
        self.assertEqual(doc.ticket_type, "Faults")
        self.assertEqual(doc.priority, "Medium")
        self.assertFalse(doc.flags.data_request_intake_prepared)

    def test_portal_data_request_combined_classification(self):
        """Verify both classification hooks accept a valid Data Request."""

        def user_lookup(doctype, name, fieldname, **kwargs):
            self.assertEqual(doctype, "User")
            self.assertEqual(name, CUSTOMER_USER)

            if fieldname == "user_type":
                return "Website User"

            if fieldname == ["enabled", "user_type"]:
                return SimpleNamespace(
                    enabled=1,
                    user_type="Website User",
                )

            self.fail(f"Unexpected User lookup: {fieldname!r}")

        self.db.get_value.side_effect = user_lookup

        doc = self.ticket(
            via_customer_portal=1,
            ticket_type="Service Request",
            custom_request_type="Other",
            priority="Medium",
        )

        # First: existing before_insert preparation.
        intake.prepare_data_request_insert(doc)

        self.assertEqual(doc.ticket_type, "Service Request")
        self.assertEqual(doc.priority, "High")
        self.assertTrue(doc.flags.data_request_intake_prepared)

        # Second: existing Data Request validation.
        intake.validate_data_request_intake(doc)

        # Third: new Customer Portal classification validation.
        portal_guard.validate_customer_portal_ticket_type(doc)

        self.assertEqual(doc.ticket_type, "Service Request")
        self.assertEqual(doc.custom_request_type, "Other")
        self.assertEqual(doc.priority, "High")

if __name__ == "__main__":
    unittest.main()
