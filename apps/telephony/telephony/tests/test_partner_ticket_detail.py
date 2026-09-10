import unittest
from unittest import mock

from telephony import partner_create


class TestPartnerTicketDetail(unittest.TestCase):
    def test_detail_preserves_raw_location_ids_and_adds_display_names(self):
        ticket = {
            field: None
            for field in partner_create.PARTNER_DETAIL_FIELDS
        }

        ticket.update(
            {
                "name": "41",
                "custom_site_group": "Boschendal",
                "custom_fault_asset": "location-asset-id",
                "custom_site": "location-point-id",
            }
        )

        location_names = {
            "Boschendal": "Boschendal",
            "location-asset-id": "Buildings: Baker House",
            "location-point-id": "Buildings: Baker House",
        }

        with (
            mock.patch.object(
                partner_create,
                "_assert_partner_ticket_access",
            ),
            mock.patch.object(
                partner_create,
                "get_partner_note_summary",
                return_value={},
            ),
            mock.patch.object(
                partner_create,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.session.user = "partner@example.com"
            frappe_mock.get_doc.return_value = ticket
            frappe_mock.db.exists.return_value = True
            frappe_mock.db.get_value.side_effect = (
                lambda doctype, name, fieldname:
                location_names.get(name)
            )

            result = partner_create.get_partner_ticket_detail("41")

        self.assertEqual(
            result["custom_site_group"],
            "Boschendal",
        )
        self.assertEqual(
            result["custom_fault_asset"],
            "location-asset-id",
        )
        self.assertEqual(
            result["custom_site"],
            "location-point-id",
        )

        self.assertEqual(
            result["custom_site_group_display"],
            "Boschendal",
        )
        self.assertEqual(
            result["custom_fault_asset_display"],
            "Buildings: Baker House",
        )
        self.assertEqual(
            result["custom_site_display"],
            "Buildings: Baker House",
        )

    def test_location_display_falls_back_to_raw_value(self):
        with mock.patch.object(
            partner_create,
            "frappe",
        ) as frappe_mock:
            frappe_mock.db.exists.return_value = False

            result = partner_create._get_location_display_name(
                "missing-location-id"
            )

        self.assertEqual(
            result,
            "missing-location-id",
        )

    def test_blank_location_display_remains_blank(self):
        with mock.patch.object(
            partner_create,
            "frappe",
        ) as frappe_mock:
            result = partner_create._get_location_display_name("")

        self.assertEqual(result, "")
        frappe_mock.db.exists.assert_not_called()


if __name__ == "__main__":
    unittest.main()
