import unittest

from telephony.customer_communication_projection import (
    project_customer_ticket_detail,
)


class TestCustomerTicketDetailProjection(unittest.TestCase):

    def setUp(self):
        self.detail = {
            "name": "902",
            "subject": "Internet connection unavailable",
            "description": "Customer-reported connectivity issue",
            "status": "Open",
            "priority": "High",
            "customer": "Boschendal",
            "raised_by": "test@boschendal.co.za",
            "response_by": "2026-10-23 12:00:00",
            "owner": "internal@example.com",
            "modified_by": "coordinator@example.com",
            "_assign": '["tech.bravo@local.test"]',
            "agent_group": "Internet Connection",
            "custom_partner_brief": "Private supplier instructions",
            "custom_site": "Boschendal",
            "custom_internal_notes": "Internal diagnosis",
            "custom_password_file": "/private/files/passwords.pdf",
            "contact": {
                "email_id": "private@example.com",
                "phone": "000000000",
            },
            "tags": ["internal-review"],
            "_form_script": "private_script()",
            "_customActions": [{"label": "Internal action"}],
            "template": {
                "name": "Customer Request",
                "fields": [
                    {
                        "fieldname": "custom_site",
                        "fieldtype": "Link",
                        "label": "Site",
                        "options": "Location",
                        "hide_from_customer": 0,
                    },
                    {
                        "fieldname": "custom_internal_notes",
                        "fieldtype": "Small Text",
                        "label": "Internal Notes",
                        "hide_from_customer": 1,
                    },
                    {
                        "fieldname": "custom_partner_brief",
                        "fieldtype": "Small Text",
                        "label": "Partner Brief",
                        "hide_from_customer": 0,
                    },
                    {
                        "fieldname": "custom_password_file",
                        "fieldtype": "Attach",
                        "label": "Password File",
                        "hide_from_customer": 0,
                    },
                ],
            },
            "fields": [
                {
                    "fieldname": "custom_site",
                    "fieldtype": "Link",
                    "label": "Site",
                    "options": "Location",
                },
                {
                    "fieldname": "custom_internal_notes",
                    "fieldtype": "Small Text",
                    "label": "Internal Notes",
                    "hide_from_customer": 1,
                },
            ],
            "communications": [
                {
                    "name": "public-comm",
                    "content": "Approved Customer update",
                    "sender": "test@boschendal.co.za",
                    "creation": "2026-10-23 09:00:00",
                    "bcc": "hidden@example.com",
                    "attachments": [
                        {"file_url": "/private/files/internal.pdf"}
                    ],
                },
                {
                    "name": "internal-comm",
                    "content": "Internal diagnostic note",
                },
            ],
            "comments": [{"content": "Internal note"}],
            "history": [{"action": "Assigned to technician"}],
            "views": [{"viewed_by": "internal@example.com"}],
            "calls": [{"recording_url": "/private/recording"}],
        }

    def project(self):
        return project_customer_ticket_detail(
            self.detail,
            {"public-comm"},
        )

    def test_standard_customer_fields_preserved(self):
        result = self.project()

        for field in (
            "name",
            "subject",
            "description",
            "status",
            "priority",
            "raised_by",
            "response_by",
        ):
            self.assertEqual(
                result[field],
                self.detail[field],
            )

    def test_operational_fields_removed(self):
        result = self.project()

        for field in (
            "owner",
            "modified_by",
            "_assign",
            "agent_group",
            "contact",
            "_customActions",
            "custom_partner_brief",
            "custom_internal_notes",
            "custom_password_file",
        ):
            self.assertNotIn(field, result)

        self.assertEqual(result["_form_script"], "")
        self.assertEqual(result["tags"], [])

    def test_approved_dynamic_field_preserved(self):
        result = self.project()

        self.assertEqual(result["custom_site"], "Boschendal")

        names = [
            field["fieldname"]
            for field in result["template"]["fields"]
        ]

        self.assertEqual(names, ["custom_site"])

    def test_dynamic_metadata_filtered(self):
        result = self.project()

        self.assertEqual(
            [field["fieldname"] for field in result["fields"]],
            ["custom_site"],
        )

        self.assertEqual(
            result["template"]["fields"][0]["options"],
            "Location",
        )

        self.assertNotIn(
            "custom_internal_notes",
            result["template"]["fields"][0],
        )

    def test_customer_communication_projection_reused(self):
        result = self.project()

        self.assertEqual(
            [item["name"] for item in result["communications"]],
            ["public-comm"],
        )

        public = result["communications"][0]

        self.assertEqual(
            public["content"],
            "Approved Customer update",
        )

        self.assertNotIn("bcc", public)
        self.assertEqual(public["attachments"], [])

        for key in ("comments", "history", "views", "calls"):
            self.assertEqual(result[key], [])

    def test_source_response_not_modified(self):
        self.project()

        self.assertEqual(
            len(self.detail["communications"]),
            2,
        )

        self.assertEqual(
            self.detail["custom_internal_notes"],
            "Internal diagnosis",
        )

        self.assertEqual(
            self.detail["_form_script"],
            "private_script()",
        )

    def test_missing_template_uses_safe_defaults(self):
        result = project_customer_ticket_detail(
            {
                "name": "941",
                "subject": "PABX fault",
                "status": "Open",
                "secret_field": "Private",
            },
            [],
        )

        self.assertEqual(result["template"], {"fields": []})
        self.assertEqual(result["communications"], [])
        self.assertNotIn("secret_field", result)

    def test_verified_viewer_contact_is_minimal(self):
        result = project_customer_ticket_detail(
            self.detail,
            {"public-comm"},
            viewer_email="test@boschendal.co.za",
        )

        self.assertEqual(
            result["contact"],
            {
                "name": "test@boschendal.co.za",
                "email_id": "test@boschendal.co.za",
                "image": None,
            },
        )

        self.assertNotEqual(
            result["contact"]["email_id"],
            self.detail["contact"]["email_id"],
        )

if __name__ == "__main__":
    unittest.main()
