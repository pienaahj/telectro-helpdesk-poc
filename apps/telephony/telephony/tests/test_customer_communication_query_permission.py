import unittest
from types import SimpleNamespace
from unittest.mock import patch

from telephony import customer_communication_permission as permission


class TestCommunicationQueryPermission(unittest.TestCase):

    def conditions(self, *, user="test@example.com", roles=()):
        fake_frappe = SimpleNamespace(
            session=SimpleNamespace(user=user),
            get_roles=lambda _user: list(roles),
        )

        with patch.object(permission, "frappe", fake_frappe):
            return permission.communication_query_conditions(user)

    def assert_ticket_list_denied(self, condition):
        self.assertIsNotNone(condition)
        self.assertIn(
            "COALESCE(`tabCommunication`.`reference_doctype`, '')",
            condition,
        )
        self.assertIn("!= 'HD Ticket'", condition)
        self.assertNotIn("custom_telectro_audience", condition)

    def test_customer_cannot_list_ticket_communications(self):
        self.assert_ticket_list_denied(
            self.conditions(roles=("Customer",))
        )

    def test_partner_cannot_list_ticket_communications(self):
        self.assert_ticket_list_denied(
            self.conditions(
                roles=("TELECTRO-POC Role - Partner",)
            )
        )

    def test_ambiguous_customer_internal_roles_denied(self):
        self.assert_ticket_list_denied(
            self.conditions(
                roles=("Customer", "TELECTRO-POC Role - Tech")
            )
        )

    def test_ambiguous_internal_partner_roles_denied(self):
        self.assert_ticket_list_denied(
            self.conditions(
                roles=(
                    "TELECTRO-POC Role - Tech",
                    "TELECTRO-POC Role - Partner",
                )
            )
        )

    def test_generic_agent_denied(self):
        self.assert_ticket_list_denied(
            self.conditions(roles=("Agent",))
        )

    def test_unknown_actor_denied(self):
        self.assert_ticket_list_denied(
            self.conditions(roles=())
        )

    def test_guest_denied(self):
        self.assert_ticket_list_denied(
            self.conditions(user="Guest")
        )

    def test_internal_technician_defers_to_native(self):
        self.assertIsNone(
            self.conditions(
                roles=("TELECTRO-POC Role - Tech",)
            )
        )

    def test_internal_coordinator_defers_to_native(self):
        self.assertIsNone(
            self.conditions(
                roles=("TELECTRO-POC Role - Coordinator Ops",)
            )
        )

    def test_administrator_defers_to_native(self):
        self.assertIsNone(
            self.conditions(
                user="Administrator",
                roles=("System Manager",),
            )
        )


if __name__ == "__main__":
    unittest.main()
