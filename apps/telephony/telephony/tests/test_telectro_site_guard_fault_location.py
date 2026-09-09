import unittest

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


if __name__ == "__main__":
    unittest.main()
