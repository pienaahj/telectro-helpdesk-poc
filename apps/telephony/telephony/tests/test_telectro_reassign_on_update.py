import unittest
from unittest import mock

from telephony import telectro_reassign_on_update as reassign


class TestPartnerFulfilmentRoutingFields(unittest.TestCase):
    def test_fulfilment_partner_is_routing_relevant(self):
        self.assertIn(
            "custom_fulfilment_partner",
            reassign.ROUTING_FIELDS,
        )

class _TicketDoc(dict):
    __getattr__ = dict.get

    def is_new(self):
        return False

    def get_doc_before_save(self):
        return _TicketDoc(
            name=self.name,
            custom_fulfilment_party="Partner",
            custom_fulfilment_partner="Previous Partner",
        )

class TestPartnerFulfilmentReassignment(unittest.TestCase):
    def test_partner_fulfilment_resolves_default_dispatch_user(self):
        doc = _TicketDoc(
            name="TEST-PARTNER-REASSIGN",
            subject="Partner reassignment proof",
            custom_fulfilment_party="Partner",
            custom_fulfilment_partner="CN Services",
            agent_group="Helpdesk Team",
        )

        with (
            mock.patch.object(
                reassign,
                "resolve_partner_dispatch_user",
                return_value="partner.test@local.test",
            ) as resolve_dispatch_user,
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ) as seed_ticket_routing,
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value="hendrik@local.test",
            ),
        ):
            reassign.reassign_if_routing_changed(doc)

        seed_ticket_routing.assert_called_once_with(
            doc,
            method=None,
        )

        resolve_dispatch_user.assert_called_once_with(
            "CN Services"
        )

        normalize_assignment.assert_called_once_with(
            "TEST-PARTNER-REASSIGN",
            "partner.test@local.test",
            note=(
                "Routing change: reassigned to Partner fulfilment | "
                "Partner reassignment proof"
            ),
        )
