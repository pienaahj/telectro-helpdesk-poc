import unittest

import frappe

from telephony import telectro_intake
from telephony import telectro_site_guard


class _TicketStub:
    def __init__(self, **values):
        for key, value in values.items():
            setattr(self, key, value)

    def get(self, fieldname, default=None):
        return getattr(self, fieldname, default)

    def set(self, fieldname, value):
        setattr(self, fieldname, value)

    def is_new(self):
        return True


class TestEmailIntakeClassification(unittest.TestCase):
    def test_portal_customer_email_identity_is_not_email_intake(self):
        doc = frappe._dict(
            {
                "custom_request_source": "Customer",
                "via_customer_portal": 1,
                "email_account": None,
                "raised_by": "customer@example.com",
                "contact_email": None,
            }
        )

        self.assertFalse(
            telectro_site_guard._is_email_intake(doc)
        )

    def test_email_account_identifies_email_intake(self):
        doc = frappe._dict(
            {
                "custom_request_source": "Customer",
                "via_customer_portal": 0,
                "email_account": "Helpdesk",
                "raised_by": "sender@example.com",
                "contact_email": None,
            }
        )

        self.assertTrue(
            telectro_site_guard._is_email_intake(doc)
        )

    def test_request_source_does_not_define_email_channel(self):
        doc = frappe._dict(
            {
                "custom_request_source": "Email",
                "via_customer_portal": 0,
                "email_account": None,
                "raised_by": None,
                "contact_email": None,
            }
        )

        self.assertFalse(
            telectro_site_guard._is_email_intake(doc)
        )

    def test_populate_from_email_does_not_write_request_source(self):
        doc = _TicketStub(
            custom_request_source=None,
            custom_customer="Existing Customer",
            custom_site_group="Existing Campus",
            custom_site="Existing Site",
            custom_equipment_ref="Existing Asset",
            subject="",
            description="",
            raised_by=None,
            contact_email=None,
            sender=None,
            email_from=None,
        )

        telectro_intake.populate_from_email(doc)

        self.assertIsNone(
            doc.custom_request_source
        )


if __name__ == "__main__":
    unittest.main()
