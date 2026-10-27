import unittest
from unittest.mock import patch

import frappe

from telephony import (
    customer_communication_permission as permission,
)


class TestCustomerCommunicationPermission(unittest.TestCase):

    def check_permission(
        self,
        *,
        roles,
        audience="Customer",
        linked_customers=(),
        ticket_customer="Boschendal",
        user="test@example.com",
        ptype="read",
        reference_doctype="HD Ticket",
        reference_name="902",
    ):
        doc = frappe._dict(
            reference_doctype=reference_doctype,
            reference_name=reference_name,
            custom_telectro_audience=audience,
        )

        with (
            patch.object(
                permission.frappe,
                "get_roles",
                return_value=list(roles),
            ),
            patch.object(
                permission,
                "get_customer",
                return_value=list(linked_customers),
            ),
            patch.object(
                permission,
                "_get_ticket_hd_customer",
                return_value=ticket_customer,
            ),
        ):
            return permission.communication_has_permission(
                doc,
                ptype,
                user=user,
            )

    def test_verified_customer_defers_to_native(self):
        result = self.check_permission(
            roles={"Customer"},
            linked_customers={"Boschendal"},
        )

        self.assertIsNone(result)

    def test_cross_customer_access_denied(self):
        result = self.check_permission(
            roles={"Customer"},
            linked_customers={"Emerald Life"},
            ticket_customer="Boschendal",
        )

        self.assertIs(result, False)

    def test_unclassified_communication_denied(self):
        result = self.check_permission(
            roles={"Customer"},
            linked_customers={"Boschendal"},
            audience=None,
        )

        self.assertIs(result, False)

    def test_internal_communication_denied_to_customer(self):
        result = self.check_permission(
            roles={"Customer"},
            linked_customers={"Boschendal"},
            audience="Internal",
        )

        self.assertIs(result, False)

    def test_partner_communication_denied_to_customer(self):
        result = self.check_permission(
            roles={"Customer"},
            linked_customers={"Boschendal"},
            audience="Partner",
        )

        self.assertIs(result, False)

    def test_internal_technician_defers_to_native(self):
        result = self.check_permission(
            roles={
                "Agent",
                "TELECTRO-POC Role - Tech",
            },
            audience=None,
        )

        self.assertIsNone(result)

    def test_partner_denied(self):
        result = self.check_permission(
            roles={
                "TELECTRO-POC Role - Partner",
                "TELECTRO-POC Role - Partner Creator",
            },
        )

        self.assertIs(result, False)

    def test_mixed_internal_partner_roles_denied(self):
        result = self.check_permission(
            roles={
                "TELECTRO-POC Role - Tech",
                "TELECTRO-POC Role - Partner",
            },
        )

        self.assertIs(result, False)

    def test_generic_agent_not_treated_as_internal(self):
        result = self.check_permission(
            roles={"Agent"},
        )

        self.assertIs(result, False)

    def test_missing_customer_relationship_denied(self):
        result = self.check_permission(
            roles={"Customer"},
            linked_customers=(),
        )

        self.assertIs(result, False)

    def test_missing_ticket_reference_denied(self):
        result = self.check_permission(
            roles={"Customer"},
            linked_customers={"Boschendal"},
            reference_name=None,
        )

        self.assertIs(result, False)

    def test_non_ticket_communications_unchanged(self):
        result = self.check_permission(
            roles={"Customer"},
            reference_doctype="Issue",
        )

        self.assertIsNone(result)

    def test_customer_write_and_delete_denied_for_all_audiences(self):
        for ptype in ("write", "delete"):
            for audience in ("Customer", "Internal", "Partner", None):
                for linked_customers in (
                    {"Boschendal"},
                    {"Emerald Life"},
                    set(),
                ):
                    with self.subTest(
                        ptype=ptype,
                        audience=audience,
                        linked_customers=linked_customers,
                    ):
                        result = self.check_permission(
                            roles={"Customer"},
                            linked_customers=linked_customers,
                            audience=audience,
                            ptype=ptype,
                        )
                        self.assertIs(result, False)

    def test_partner_unknown_and_mixed_write_delete_denied(self):
        role_sets = (
            {"TELECTRO-POC Role - Partner"},
            {"TELECTRO-POC Role - Partner Creator"},
            {"Agent"},
            {
                "TELECTRO-POC Role - Tech",
                "TELECTRO-POC Role - Partner",
            },
            set(),
        )

        for roles in role_sets:
            for ptype in ("write", "delete"):
                with self.subTest(roles=roles, ptype=ptype):
                    result = self.check_permission(
                        roles=roles,
                        ptype=ptype,
                        audience=None,
                    )
                    self.assertIs(result, False)

    def test_internal_write_and_delete_defer_to_native(self):
        for ptype in ("write", "delete"):
            with self.subTest(ptype=ptype):
                result = self.check_permission(
                    roles={"TELECTRO-POC Role - Tech"},
                    ptype=ptype,
                    audience=None,
                )
                self.assertIsNone(result)

    def test_unrelated_communication_and_other_permissions_unchanged(self):
        for ptype in ("read", "write", "delete"):
            with self.subTest(
                reference_doctype="Issue",
                ptype=ptype,
            ):
                result = self.check_permission(
                    roles={"Customer"},
                    reference_doctype="Issue",
                    ptype=ptype,
                )
                self.assertIsNone(result)

        for ptype in ("create", "submit", "cancel"):
            with self.subTest(
                reference_doctype="HD Ticket",
                ptype=ptype,
            ):
                result = self.check_permission(
                    roles={"Customer"},
                    ptype=ptype,
                )
                self.assertIsNone(result)

    def test_administrator_write_and_delete_defer_to_native(self):
        for ptype in ("write", "delete"):
            with self.subTest(ptype=ptype):
                result = self.check_permission(
                    roles={"System Manager"},
                    user="Administrator",
                    ptype=ptype,
                    audience=None,
                )
                self.assertIsNone(result)

    def test_administrator_defers_to_native(self):
        result = self.check_permission(
            roles={"System Manager"},
            user="Administrator",
            audience=None,
        )

        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
