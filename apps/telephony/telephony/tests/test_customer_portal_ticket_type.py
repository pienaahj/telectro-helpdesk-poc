import unittest
from types import SimpleNamespace
from unittest import mock

import frappe

from telephony import customer_portal_ticket_type as guard


CUSTOMER_USER = "portal.customer@example.test"
TECHNICIAN_USER = "technician@example.test"


class Ticket(dict):
    """In-memory HD Ticket with new-document lifecycle state."""

    def __init__(self, *, new=True, **values):
        super().__init__(values)
        self._new = new

    def is_new(self):
        return self._new


class TestCustomerPortalTicketType(unittest.TestCase):

    @staticmethod
    def _raise_validation(message, exc=frappe.ValidationError):
        raise exc(message)

    def setUp(self):
        self.session = SimpleNamespace(user=CUSTOMER_USER)
        self.db = mock.Mock()
        self.db.get_value.return_value = "Website User"

        patcher = mock.patch.dict(
            guard.frappe.__dict__,
            {
                "session": self.session,
                "db": self.db,
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch.object(
            guard.frappe,
            "throw",
            side_effect=self._raise_validation,
        )
        self.throw = patcher.start()
        self.addCleanup(patcher.stop)

    def ticket(self, *, new=True, **overrides):
        values = {
            "via_customer_portal": 1,
            "ticket_type": "Faults",
            "custom_service_area": "Internet Connection",
            "custom_request_type": "General Assistance",
        }
        values.update(overrides)

        return Ticket(new=new, **values)

    def validate(self, doc):
        guard.validate_customer_portal_ticket_type(doc)

    def test_valid_fault_accepted(self):
        doc = self.ticket()

        self.validate(doc)

        self.assertEqual(doc["ticket_type"], "Faults")
        self.throw.assert_not_called()

    def test_valid_service_request_accepted(self):
        doc = self.ticket(
            ticket_type="Service Request",
            custom_request_type="Other",
        )

        self.validate(doc)

        self.assertEqual(doc["ticket_type"], "Service Request")
        self.throw.assert_not_called()

    def test_service_request_independent_of_service_area(self):
        doc = self.ticket(
            ticket_type="Service Request",
            custom_service_area="Internet Connection",
            custom_request_type="Other",
        )

        self.validate(doc)

        self.throw.assert_not_called()

    def test_valid_data_request_accepted(self):
        doc = self.ticket(
            ticket_type="Service Request",
            custom_service_area="Data Request",
            custom_request_type="Other",
        )

        self.validate(doc)

        self.throw.assert_not_called()

    def test_missing_ticket_type_rejected(self):
        doc = self.ticket(ticket_type="")

        with self.assertRaisesRegex(
            frappe.ValidationError,
            "Choose Report a Fault or Request a Service",
        ):
            self.validate(doc)

    def test_unsupported_ticket_type_rejected(self):
        doc = self.ticket(ticket_type="Incident")

        with self.assertRaises(frappe.ValidationError):
            self.validate(doc)

    def test_data_request_cannot_be_fault(self):
        doc = self.ticket(
            ticket_type="Faults",
            custom_service_area="Data Request",
        )

        with self.assertRaisesRegex(
            frappe.ValidationError,
            "Data Requests must be Service Requests",
        ):
            self.validate(doc)

    def test_service_request_wrong_request_type_rejected(self):
        doc = self.ticket(
            ticket_type="Service Request",
            custom_request_type="General Assistance",
        )

        with self.assertRaisesRegex(
            frappe.ValidationError,
            "Request Type Other",
        ):
            self.validate(doc)

    def test_email_account_does_not_bypass_validation(self):
        doc = self.ticket(
            ticket_type="Incident",
            email_account="forged@example.test",
        )

        with self.assertRaises(frappe.ValidationError):
            self.validate(doc)

    def test_internal_agent_workflow_unchanged(self):
        self.session.user = TECHNICIAN_USER
        self.db.get_value.return_value = "System User"

        doc = self.ticket(ticket_type="Incident")

        self.validate(doc)

        self.throw.assert_not_called()

    def test_existing_ticket_workflow_unchanged(self):
        doc = self.ticket(
            new=False,
            ticket_type="Incident",
        )

        self.validate(doc)

        self.throw.assert_not_called()

    def test_non_portal_workflow_unchanged(self):
        doc = self.ticket(
            via_customer_portal=0,
            ticket_type="Incident",
        )

        self.validate(doc)

        self.throw.assert_not_called()


if __name__ == "__main__":
    unittest.main()
