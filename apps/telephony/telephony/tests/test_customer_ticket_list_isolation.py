import unittest
from types import SimpleNamespace
from unittest.mock import patch

from telephony import permissions


class TestCustomerTicketListIsolation(unittest.TestCase):

    def conditions(
        self,
        linked=(),
        *,
        legacy_linked=None,
        user="portal@example.com",
        roles=("Customer",),
    ):
        fake_frappe = SimpleNamespace(
            get_roles=lambda _user: list(roles),
            db=SimpleNamespace(
                escape=lambda value: "'" + value.replace("'", "''") + "'"
            ),
        )

        if legacy_linked is None:
            legacy_linked = linked

        with (
            patch.object(permissions, "frappe", fake_frappe),
            patch.object(
                permissions,
                "get_customer_names_for_user",
                return_value=list(legacy_linked),
            ),
            patch(
                "helpdesk.utils.get_customer",
                return_value=list(linked),
            ),
        ):
            return permissions.hd_ticket_query_conditions(user)

    def test_single_customer_is_organisation_scoped(self):
        condition = self.conditions(["Emerald Life"])

        self.assertEqual(
            condition,
            "`tabHD Ticket`.`customer` = 'Emerald Life'",
        )
        self.assertNotIn("owner", condition)
        self.assertNotIn("raised_by", condition)

    def test_reassigned_customer_uses_current_relationship(self):
        condition = self.conditions(
            ["Emerald Life"],
            legacy_linked=["Boschendal"],
        )

        self.assertEqual(
            condition,
            "`tabHD Ticket`.`customer` = 'Emerald Life'",
        )

    def test_unlinked_customer_denied(self):
        self.assertEqual(self.conditions([]), "1=0")

    def test_multiple_customer_links_denied(self):
        self.assertEqual(
            self.conditions(["Boschendal", "Emerald Life"]),
            "1=0",
        )

    def test_duplicate_customer_links_denied(self):
        self.assertEqual(
            self.conditions(["Emerald Life", "Emerald Life"]),
            "1=0",
        )

    def test_two_users_share_customer_scope(self):
        a = self.conditions(
            ["Emerald Life"],
            user="customer.one@example.com",
        )
        b = self.conditions(
            ["Emerald Life"],
            user="customer.two@example.com",
        )

        self.assertEqual(a, b)
        self.assertEqual(
            a,
            "`tabHD Ticket`.`customer` = 'Emerald Life'",
        )

    def test_internal_coordinator_unchanged(self):
        self.assertEqual(
            self.conditions(
                roles=("TELECTRO-POC Role - Coordinator Ops",)
            ),
            "",
        )

    def test_partner_ownership_rule_unchanged(self):
        condition = self.conditions(
            roles=("TELECTRO-POC Role - Partner",)
        )

        self.assertEqual(
            condition,
            "`tabHD Ticket`.`owner` = 'portal@example.com'",
        )


if __name__ == "__main__":
    unittest.main()
