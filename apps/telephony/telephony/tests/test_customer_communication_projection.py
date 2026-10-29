import unittest

from telephony.customer_communication_projection import (
    project_customer_activities,
)


class TestCustomerCommunicationProjection(unittest.TestCase):

    def setUp(self):
        self.activities = {
            "communications": [
                {
                    "name": "CUSTOMER-001",
                    "content": "<p>Original request</p>",
                    "creation": "2026-10-23 08:00:00",
                    "sender": "customer@example.com",
                    "subject": "Connection issue",
                    "cc": "internal@example.com",
                    "bcc": "private@example.com",
                    "recipients": "staff@example.com",
                    "user": {
                        "name": "Customer User",
                        "email": "customer@example.com",
                        "roles": ["Customer"],
                    },
                    "attachments": [
                        {
                            "file_url": "/private/files/customer.pdf",
                        }
                    ],
                },
                {
                    "name": "INTERNAL-001",
                    "content": "<p>Private technician analysis</p>",
                    "sender": "technician@example.com",
                    "attachments": [
                        {
                            "file_url": "/private/files/internal.pdf",
                        }
                    ],
                },
            ],
            "comments": [
                {
                    "content": "Internal note",
                    "attachments": [],
                }
            ],
            "history": [{"action": "Assigned"}],
            "views": [{"viewed_by": "technician@example.com"}],
            "calls": [{"recording_url": "/recording/private"}],
        }

    def test_only_authorised_communications_returned(self):
        result = project_customer_activities(
            self.activities,
            {"CUSTOMER-001"},
        )

        self.assertEqual(
            [c["name"] for c in result["communications"]],
            ["CUSTOMER-001"],
        )

    def test_unclassified_communications_hidden(self):
        result = project_customer_activities(
            self.activities,
            set(),
        )

        self.assertEqual(result["communications"], [])

    def test_sensitive_communication_metadata_removed(self):
        result = project_customer_activities(
            self.activities,
            {"CUSTOMER-001"},
        )

        communication = result["communications"][0]

        for field in ("cc", "bcc", "recipients"):
            self.assertNotIn(field, communication)

        self.assertEqual(
            communication["user"],
            {"name": "Customer User"},
        )

    def test_attachment_urls_not_exposed_yet(self):
        result = project_customer_activities(
            self.activities,
            {"CUSTOMER-001"},
        )

        self.assertEqual(
            result["communications"][0]["attachments"],
            [],
        )

    def test_authorised_attachment_exposes_only_safe_metadata(self):
        self.activities["communications"][0]["attachments"] = [
            {
                "name": "FILE-001",
                "file_name": "customer.pdf",
                "file_url": "/private/files/customer.pdf",
                "is_private": 1,
            }
        ]

        result = project_customer_activities(
            self.activities,
            {"CUSTOMER-001"},
        )

        attachments = result["communications"][0]["attachments"]

        self.assertEqual(
            attachments,
            [
                {
                    "file_id": "FILE-001",
                    "file_name": "customer.pdf",
                }
            ],
        )

        self.assertNotIn("file_url", attachments[0])
        self.assertNotIn("is_private", attachments[0])

    def test_internal_activity_sections_removed(self):
        result = project_customer_activities(
            self.activities,
            {"CUSTOMER-001"},
        )

        for section in (
            "comments",
            "history",
            "views",
            "calls",
        ):
            self.assertEqual(result[section], [])

    def test_source_data_not_modified(self):
        original_count = len(
            self.activities["communications"]
        )

        project_customer_activities(
            self.activities,
            {"CUSTOMER-001"},
        )

        self.assertEqual(
            len(self.activities["communications"]),
            original_count,
        )

        self.assertIn(
            "bcc",
            self.activities["communications"][0],
        )

    def test_client_supplied_audience_not_trusted(self):
        self.activities["communications"][1][
            "custom_audience"
        ] = "Customer"

        result = project_customer_activities(
            self.activities,
            {"CUSTOMER-001"},
        )

        self.assertEqual(
            len(result["communications"]),
            1,
        )

    def test_empty_input(self):
        result = project_customer_activities(
            {},
            set(),
        )

        self.assertEqual(
            result,
            {
                "communications": [],
                "comments": [],
                "history": [],
                "views": [],
                "calls": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
