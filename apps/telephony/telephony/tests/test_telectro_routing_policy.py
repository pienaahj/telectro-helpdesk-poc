import unittest
from unittest import mock

from telephony import telectro_routing_policy as routing


class _TicketDoc(dict):
    __getattr__ = dict.get


class TestTelectroRoutingPolicy(unittest.TestCase):
    def test_boschendal_does_not_direct_assign_owner(self):
        doc = _TicketDoc(
            owner="Administrator",
            custom_take_ownership_on_create=0,
            custom_fulfilment_party="Telectro",
            custom_request_source="Telectro",
            custom_site_group="Boschendal",
            custom_service_area="PABX",
            agent_group="PABX",
        )

        policy = routing.resolve_ticket_routing_policy(doc)

        self.assertIsNone(policy)

    def test_explicit_creator_take_ownership_still_wins(self):
        user = "tech.test@local.test"

        doc = _TicketDoc(
            owner=user,
            custom_take_ownership_on_create=1,
            custom_fulfilment_party="Telectro",
            custom_request_source="Telectro",
            custom_site_group="Boschendal",
            custom_service_area="PABX",
            agent_group="PABX",
        )

        with (
            mock.patch.object(
                routing,
                "_user_exists",
                return_value=True,
            ) as user_exists,
            mock.patch.object(
                routing,
                "_is_internal_technician_user",
                return_value=True,
            ) as is_internal_technician,
        ):
            policy = routing.resolve_ticket_routing_policy(doc)

        self.assertEqual(
            policy,
            {
                "target_user": user,
                "reason": (
                    "Ticket creator chose to take ownership: "
                    f"{user}"
                ),
                "policy_key": "creator_take_ownership",
            },
        )

        user_exists.assert_called_once_with(user)
        is_internal_technician.assert_called_once_with(user)


if __name__ == "__main__":
    unittest.main()
