import unittest
from unittest import mock

import frappe

from telephony import telectro_site_guard


class TestTelectroSiteGuardFaultLocation(unittest.TestCase):
    def _fault_doc(self, **overrides):
        values = {
            "ticket_type": "Faults",
            "email_account": None,
            "custom_fault_category": "Buildings",
            "custom_fault_asset": None,
            "custom_site": None,
        }
        values.update(overrides)
        return frappe._dict(values)

    def test_links_and_areas_accept_fault_asset_without_fault_point(self):
        for category in ("Links", "Areas"):
            with self.subTest(category=category):
                doc = self._fault_doc(
                    custom_fault_category=category,
                    custom_fault_asset="Selected Fault Asset",
                    custom_site=None,
                )

                telectro_site_guard._require_fault_location_for_faults(
                    doc
                )

    def test_links_and_areas_require_fault_asset(self):
        for category in ("Links", "Areas"):
            with self.subTest(category=category):
                doc = self._fault_doc(
                    custom_fault_category=category,
                    custom_fault_asset=None,
                    custom_site=None,
                )

                with self.assertRaisesRegex(
                    frappe.ValidationError,
                    r"Please select Fault Asset\.",
                ):
                    telectro_site_guard._require_fault_location_for_faults(
                        doc
                    )

    def test_point_category_requires_fault_point(self):
        doc = self._fault_doc(
            custom_fault_category="Buildings",
            custom_site=None,
        )

        with self.assertRaisesRegex(
            frappe.ValidationError,
            r"Please select Fault Point\.",
        ):
            telectro_site_guard._require_fault_location_for_faults(
                doc
            )

    def test_point_category_accepts_fault_point(self):
        doc = self._fault_doc(
            custom_fault_category="Buildings",
            custom_site="Selected Fault Point",
        )

        telectro_site_guard._require_fault_location_for_faults(
            doc
        )

    def test_email_intake_remains_triage_first(self):
        doc = self._fault_doc(
            email_account="Helpdesk",
            custom_fault_category="Links",
            custom_fault_asset=None,
            custom_site=None,
        )

        telectro_site_guard._require_fault_location_for_faults(
            doc
        )


class TestCustomerPortalCampusOwnership(unittest.TestCase):
    def _doc(self, **overrides):
        values = {
            "email_account": None,
            "custom_site_group": "Boschendal",
            "customer": "Client Supplied HD Customer",
        }
        values.update(overrides)
        return frappe._dict(values)

    def test_owned_campus_is_accepted_from_authenticated_user(
        self,
    ):
        doc = self._doc(
            customer="Spoofed HD Customer",
        )

        with (
            mock.patch.object(
                telectro_site_guard,
                "get_customer",
                return_value=["Boschendal"],
                create=True,
            ) as get_customer,
            mock.patch.object(
                telectro_site_guard.frappe,
                "session",
            ) as session,
            mock.patch.object(
                telectro_site_guard.frappe.db,
                "get_value",
                side_effect=[
                    "Website User",
                    "Customer B",
                    "Customer B",
                ],
            ) as get_value,
        ):
            session.user = "test@boschendal.co.za"

            telectro_site_guard._require_customer_portal_campus_ownership(
                doc
            )

        get_customer.assert_called_once_with(
            "test@boschendal.co.za"
        )

        self.assertEqual(
            get_value.call_args_list,
            [
                mock.call(
                    "User",
                    "test@boschendal.co.za",
                    "user_type",
                ),
                mock.call(
                    "HD Customer",
                    "Boschendal",
                    "custom_erp_customer",
                ),
                mock.call(
                    "Location",
                    "Boschendal",
                    "custom_customer",
                ),
            ],
        )

    def test_foreign_campus_is_rejected_even_if_doc_customer_is_spoofed(
        self,
    ):
        doc = self._doc(
            custom_site_group="A - Head Office (Goodwood)",
            customer="Customer A",
        )

        with (
            mock.patch.object(
                telectro_site_guard,
                "get_customer",
                return_value=["Boschendal"],
                create=True,
            ),
            mock.patch.object(
                telectro_site_guard.frappe,
                "session",
            ) as session,
            mock.patch.object(
                telectro_site_guard.frappe.db,
                "get_value",
                side_effect=[
                    "Website User",
                    "Customer B",
                    "Customer A",
                ],
            ),
        ):
            session.user = "test@boschendal.co.za"

            with self.assertRaisesRegex(
                frappe.ValidationError,
                r"Campus does not belong to your Customer",
            ):
                telectro_site_guard._require_customer_portal_campus_ownership(
                    doc
                )

    def test_missing_erp_customer_bridge_is_rejected(
        self,
    ):
        doc = self._doc()

        with (
            mock.patch.object(
                telectro_site_guard,
                "get_customer",
                return_value=["Boschendal"],
                create=True,
            ),
            mock.patch.object(
                telectro_site_guard.frappe,
                "session",
            ) as session,
            mock.patch.object(
                telectro_site_guard.frappe.db,
                "get_value",
                side_effect=[
                    "Website User",
                    None,
                ],
            ),
        ):
            session.user = "test@boschendal.co.za"

            with self.assertRaisesRegex(
                frappe.ValidationError,
                r"Customer account is not linked to an ERP Customer",
            ):
                telectro_site_guard._require_customer_portal_campus_ownership(
                    doc
                )

    def test_internal_system_user_is_not_customer_portal_scoped(
        self,
    ):
        doc = self._doc()

        with (
            mock.patch.object(
                telectro_site_guard,
                "get_customer",
                create=True,
            ) as get_customer,
            mock.patch.object(
                telectro_site_guard.frappe,
                "session",
            ) as session,
            mock.patch.object(
                telectro_site_guard.frappe.db,
                "get_value",
                return_value="System User",
            ),
        ):
            session.user = "internal@example.com"

            telectro_site_guard._require_customer_portal_campus_ownership(
                doc
            )

        get_customer.assert_not_called()

if __name__ == "__main__":
    unittest.main()
