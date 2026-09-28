import unittest
import frappe
from unittest import mock

from telephony import customer_location_lookup


class TestCustomerAllowedCampuses(unittest.TestCase):
    def test_single_customer_returns_owned_top_level_campuses(
        self,
    ):
        campuses = [
            {
                "name": "Emerald Life - Cape Town",
                "location_name":
                    "Emerald Life - Cape Town",
            },
            {
                "name": "Emerald Life - Johannesburg",
                "location_name":
                    "Emerald Life - Johannesburg",
            },
        ]

        with (
            mock.patch.object(
                customer_location_lookup,
                "get_customer",
                return_value=["Emerald Life Helpdesk"],
            ),
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "get_value",
                return_value="Emerald Life",
            ) as get_value,
            mock.patch.object(
                customer_location_lookup.frappe,
                "get_all",
                return_value=campuses,
            ) as get_all,
        ):
            result = (
                customer_location_lookup
                ._get_customer_allowed_campuses_for_user(
                    "emerald@example.com"
                )
            )

        self.assertEqual(
            result,
            campuses,
        )

        get_value.assert_called_once_with(
            "HD Customer",
            "Emerald Life Helpdesk",
            "custom_erp_customer",
        )

        get_all.assert_called_once_with(
            "Location",
            filters={
                "parent_location": "Pilot Sites",
                "is_group": 1,
                "custom_customer": "Emerald Life",
            },
            fields=[
                "name",
                "location_name",
            ],
            order_by="location_name asc, name asc",
        )
    def test_single_hd_customer_without_erp_bridge_returns_no_campuses(
        self,
    ):
        with (
            mock.patch.object(
                customer_location_lookup,
                "get_customer",
                return_value=["Boschendal"],
            ),
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "get_value",
                return_value=None,
            ) as get_value,
            mock.patch.object(
                customer_location_lookup.frappe,
                "get_all",
            ) as get_all,
        ):
            result = (
                customer_location_lookup
                ._get_customer_allowed_campuses_for_user(
                    "test@boschendal.co.za"
                )
            )

        self.assertEqual(result, [])

        get_value.assert_called_once_with(
            "HD Customer",
            "Boschendal",
            "custom_erp_customer",
        )

        get_all.assert_not_called()
    def test_multiple_customers_returns_no_campuses(
        self,
    ):
        with (
            mock.patch.object(
                customer_location_lookup,
                "get_customer",
                return_value=[
                    "Customer A",
                    "Customer B",
                ],
            ),
            mock.patch.object(
                customer_location_lookup.frappe,
                "get_all",
            ) as get_all,
        ):
            result = (
                customer_location_lookup
                ._get_customer_allowed_campuses_for_user(
                    "shared@example.com"
                )
            )

        self.assertEqual(result, [])
        get_all.assert_not_called()

    def test_public_allowed_campuses_uses_session_user(
        self,
    ):
        expected = [
            {
                "name": "Emerald Life - Cape Town",
                "location_name":
                    "Emerald Life - Cape Town",
            }
        ]

        with (
            mock.patch.object(
                customer_location_lookup,
                "_get_customer_allowed_campuses_for_user",
                return_value=expected,
            ) as get_allowed,
            mock.patch.object(
                customer_location_lookup.frappe,
                "session",
            ) as session,
        ):
            session.user = "emerald@example.com"

            result = (
                customer_location_lookup
                .get_customer_allowed_campuses()
            )

        self.assertEqual(result, expected)

        get_allowed.assert_called_once_with(
            "emerald@example.com"
        )

    def test_fault_point_search_rejects_unowned_campus(
        self,
    ):
        allowed_campuses = [
            {
                "name": "Emerald Life - Cape Town",
                "location_name":
                    "Emerald Life - Cape Town",
            },
            {
                "name": "Emerald Life - Johannesburg",
                "location_name":
                    "Emerald Life - Johannesburg",
            },
        ]

        with (
            mock.patch.object(
                customer_location_lookup,
                "_get_customer_allowed_campuses_for_user",
                return_value=allowed_campuses,
            ),
            mock.patch.object(
                customer_location_lookup.frappe,
                "session",
            ) as session,
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "get_value",
            ) as get_value,
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "sql",
            ) as sql,
        ):
            session.user = "emerald@example.com"

            result = (
                customer_location_lookup
                .search_customer_fault_points(
                    campus="Boschendal",
                    category="Buildings",
                )
            )

        self.assertEqual(result, [])
        get_value.assert_not_called()
        sql.assert_not_called()

    def test_fault_point_search_uses_owned_campus(
        self,
    ):
        allowed_campuses = [
            {
                "name": "Emerald Life - Cape Town",
                "location_name":
                    "Emerald Life - Cape Town",
            }
        ]

        root = frappe._dict(
            {
                "name":
                    "Emerald Life - Cape Town - Buildings",
                "lft": 10,
                "rgt": 20,
                "is_group": 1,
                "parent_location":
                    "Emerald Life - Cape Town",
            }
        )

        expected_rows = [
            {
                "name": "EL-CPT-001",
                "location_name": "Reception",
                "parent_location":
                    "Emerald Life - Cape Town - Buildings",
                "custom_kmz_geometry_type": "Point",
                "latitude": None,
                "longitude": None,
            }
        ]

        with (
            mock.patch.object(
                customer_location_lookup,
                "_get_customer_allowed_campuses_for_user",
                return_value=allowed_campuses,
            ),
            mock.patch.object(
                customer_location_lookup.frappe,
                "session",
            ) as session,
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "get_value",
                return_value=root,
            ) as get_value,
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "sql",
                return_value=expected_rows,
            ) as sql,
        ):
            session.user = "emerald@example.com"

            result = (
                customer_location_lookup
                .search_customer_fault_points(
                    campus="Emerald Life - Cape Town",
                    category="Buildings",
                )
            )

        self.assertEqual(result, expected_rows)

        get_value.assert_called_once_with(
            "Location",
            "Emerald Life - Cape Town - Buildings",
            [
                "name",
                "lft",
                "rgt",
                "is_group",
                "parent_location",
            ],
            as_dict=True,
        )

        sql.assert_called_once()
    def test_equipment_search_accepts_location_in_second_owned_campus(
        self,
    ):
        allowed_campuses = [
            {
                "name": "Emerald Life - Cape Town",
                "location_name": "Emerald Life - Cape Town",
            },
            {
                "name": "Emerald Life - Johannesburg",
                "location_name": "Emerald Life - Johannesburg",
            },
        ]

        campus_rows = [
            frappe._dict(
                {
                    "name": "Emerald Life - Cape Town",
                    "lft": 10,
                    "rgt": 20,
                    "is_group": 1,
                }
            ),
            frappe._dict(
                {
                    "name": "Emerald Life - Johannesburg",
                    "lft": 30,
                    "rgt": 40,
                    "is_group": 1,
                }
            ),
        ]

        location_row = frappe._dict(
            {
                "name": "EL-JHB-001",
                "location_name": "Reception",
                "parent_location":
                    "Emerald Life - Johannesburg - Buildings",
                "lft": 34,
                "rgt": 35,
                "is_group": 0,
                "latitude": None,
                "longitude": None,
                "custom_kmz_geometry_type": "Point",
            }
        )

        equipment_rows = [
            {
                "name": "EQ-001",
                "equipment_name": "Reception Router",
                "equipment_type": "Router",
                "manufacturer": "Example",
                "model": "R1",
            }
        ]

        def get_value(doctype, name, fields, as_dict=False):
            if doctype != "Location":
                return None

            if name == "Emerald Life - Cape Town":
                return campus_rows[0]

            if name == "Emerald Life - Johannesburg":
                return campus_rows[1]

            if name == "EL-JHB-001":
                return location_row

            return None

        with (
            mock.patch.object(
                customer_location_lookup,
                "_get_customer_allowed_campuses_for_user",
                return_value=allowed_campuses,
            ) as get_allowed_campuses,
            mock.patch.object(
                customer_location_lookup,
                "_get_customer_allowed_campus_for_user",
                return_value="Emerald Life - Cape Town",
            ) as get_legacy_campus,
            mock.patch.object(
                customer_location_lookup.frappe,
                "get_all",
                return_value=campus_rows,
            ),
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "get_value",
                side_effect=get_value,
            ),
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "sql",
                return_value=equipment_rows,
            ) as sql,
            mock.patch.object(
                customer_location_lookup.frappe,
                "session",
            ) as session,
        ):
            session.user = "emerald@example.com"

            result = (
                customer_location_lookup
                .search_customer_equipment(
                    location="EL-JHB-001",
                )
            )

        self.assertEqual(result, equipment_rows)

        get_allowed_campuses.assert_called_once_with(
            "emerald@example.com"
        )

        get_legacy_campus.assert_not_called()
        sql.assert_called_once()

    def test_map_context_accepts_location_in_second_owned_campus(
        self,
    ):
        allowed_campuses = [
            {
                "name": "Emerald Life - Cape Town",
                "location_name": "Emerald Life - Cape Town",
            },
            {
                "name": "Emerald Life - Johannesburg",
                "location_name": "Emerald Life - Johannesburg",
            },
        ]

        campus_rows = [
            frappe._dict(
                {
                    "name": "Emerald Life - Cape Town",
                    "lft": 10,
                    "rgt": 20,
                    "is_group": 1,
                }
            ),
            frappe._dict(
                {
                    "name": "Emerald Life - Johannesburg",
                    "lft": 30,
                    "rgt": 40,
                    "is_group": 1,
                }
            ),
        ]

        location_row = frappe._dict(
            {
                "name": "EL-JHB-001",
                "location_name": "Reception",
                "parent_location":
                    "Emerald Life - Johannesburg - Buildings",
                "lft": 34,
                "rgt": 35,
                "is_group": 0,
                "latitude": -26.2041,
                "longitude": 28.0473,
                "custom_kmz_geometry_type": "Point",
            }
        )

        def get_value(doctype, name, fields, as_dict=False):
            if doctype != "Location":
                return None

            if name == "Emerald Life - Cape Town":
                return campus_rows[0]

            if name == "Emerald Life - Johannesburg":
                return campus_rows[1]

            if name == "EL-JHB-001":
                return location_row

            return None

        with (
            mock.patch.object(
                customer_location_lookup,
                "_get_customer_allowed_campuses_for_user",
                return_value=allowed_campuses,
            ) as get_allowed_campuses,
            mock.patch.object(
                customer_location_lookup,
                "_get_customer_allowed_campus_for_user",
                return_value="Emerald Life - Cape Town",
            ) as get_legacy_campus,
            mock.patch.object(
                customer_location_lookup.frappe,
                "get_all",
                return_value=campus_rows,
            ),
            mock.patch.object(
                customer_location_lookup.frappe.db,
                "get_value",
                side_effect=get_value,
            ),
            mock.patch.object(
                customer_location_lookup.frappe,
                "session",
            ) as session,
        ):
            session.user = "emerald@example.com"

            result = (
                customer_location_lookup
                .get_customer_location_map_context(
                    location="EL-JHB-001",
                )
            )

        self.assertEqual(
            result,
            {
                "location": "EL-JHB-001",
                "location_name": "Reception",
                "campus": "Emerald Life - Johannesburg",
                "parent_location":
                    "Emerald Life - Johannesburg - Buildings",
                "latitude": -26.2041,
                "longitude": 28.0473,
                "geometry_type": "Point",
            },
        )

        get_allowed_campuses.assert_called_once_with(
            "emerald@example.com"
        )

        get_legacy_campus.assert_not_called()

if __name__ == "__main__":
    unittest.main()
