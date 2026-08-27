import unittest
from unittest import mock

from telephony import customer_portal_landing


class TestCustomerPortalLanding(unittest.TestCase):
    def test_customer_website_user_gets_customer_portal_home(self):
        with mock.patch.object(
            customer_portal_landing,
            "frappe",
        ) as frappe_mock:
            frappe_mock.db.get_value.return_value = "Website User"
            frappe_mock.get_roles.return_value = [
                "Customer",
                "All",
                "Guest",
            ]

            result = (
                customer_portal_landing
                .get_website_user_home_page(
                    "customer@example.com"
                )
            )

        self.assertEqual(
            result,
            "helpdesk/my-tickets",
        )

        frappe_mock.db.get_value.assert_called_once_with(
            "User",
            "customer@example.com",
            "user_type",
        )

        frappe_mock.get_roles.assert_called_once_with(
            "customer@example.com"
        )

    def test_non_customer_website_user_uses_native_home_resolution(self):
        with mock.patch.object(
            customer_portal_landing,
            "frappe",
        ) as frappe_mock:
            frappe_mock.db.get_value.return_value = "Website User"
            frappe_mock.get_roles.return_value = [
                "All",
                "Guest",
            ]

            result = (
                customer_portal_landing
                .get_website_user_home_page(
                    "portal@example.com"
                )
            )

        self.assertIsNone(result)

    def test_system_user_with_customer_role_is_not_redirected(self):
        with mock.patch.object(
            customer_portal_landing,
            "frappe",
        ) as frappe_mock:
            frappe_mock.db.get_value.return_value = "System User"

            result = (
                customer_portal_landing
                .get_website_user_home_page(
                    "system@example.com"
                )
            )

        self.assertIsNone(result)

        frappe_mock.get_roles.assert_not_called()

    def test_guest_uses_native_home_resolution(self):
        with mock.patch.object(
            customer_portal_landing,
            "frappe",
        ) as frappe_mock:
            result = (
                customer_portal_landing
                .get_website_user_home_page(
                    "Guest"
                )
            )

        self.assertIsNone(result)

        frappe_mock.db.get_value.assert_not_called()
        frappe_mock.get_roles.assert_not_called()

    def test_blank_user_uses_native_home_resolution(self):
        with mock.patch.object(
            customer_portal_landing,
            "frappe",
        ) as frappe_mock:
            result = (
                customer_portal_landing
                .get_website_user_home_page("")
            )

        self.assertIsNone(result)

        frappe_mock.db.get_value.assert_not_called()
        frappe_mock.get_roles.assert_not_called()


if __name__ == "__main__":
    unittest.main()
