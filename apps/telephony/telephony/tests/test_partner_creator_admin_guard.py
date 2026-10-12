import unittest
from unittest import mock

from telephony import partner_create


class _TicketDoc(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

    def is_new(self):
        return True


class _ExistingTicketDoc(_TicketDoc):
    def is_new(self):
        return False


class TestPartnerCreatorAdministratorGuard(unittest.TestCase):
    def test_administrator_does_not_inherit_partner_creator_defaults(self):
        doc = _TicketDoc(
            custom_request_source="Telectro",
            custom_fulfilment_party="Telectro",
            agent_group="CCTV",
            ticket_type="Service Request",
        )

        with (
            mock.patch.object(partner_create, "frappe") as frappe_mock,
            mock.patch.object(
                partner_create,
                "_is_partner_creator",
                return_value=True,
            ) as is_partner_creator,
            mock.patch.object(
                partner_create,
                "_set_if_field_exists",
            ) as set_if_field,
        ):
            frappe_mock.session.user = "Administrator"

            partner_create.enforce_partner_create_v1(doc)

        is_partner_creator.assert_not_called()
        set_if_field.assert_not_called()

        self.assertEqual(doc.custom_request_source, "Telectro")
        self.assertEqual(doc.custom_fulfilment_party, "Telectro")
        self.assertEqual(doc.agent_group, "CCTV")

    def test_actual_partner_creator_still_receives_partner_defaults(self):
        doc = _TicketDoc(
            custom_request_source="Telectro",
            custom_fulfilment_party="Telectro",
            agent_group="CCTV",
            ticket_type="Service Request",
        )

        with (
            mock.patch.object(partner_create, "frappe") as frappe_mock,
            mock.patch.object(
                partner_create,
                "_is_partner_creator",
                return_value=True,
            ) as is_partner_creator,
            mock.patch.object(
                partner_create,
                "_set_if_field_exists",
            ),
        ):
            frappe_mock.session.user = "partner.creator@local.test"

            partner_create.enforce_partner_create_v1(doc)

        is_partner_creator.assert_called_once_with(
            "partner.creator@local.test"
        )

        self.assertEqual(doc.custom_request_source, "Partner")
        self.assertEqual(doc.custom_fulfilment_party, "Telectro")
        self.assertIsNone(doc.agent_group)

    def test_existing_ticket_is_not_redefaulted_by_partner_creator(self):
        doc = _ExistingTicketDoc(
            custom_request_source="Telectro",
            custom_fulfilment_party="Partner",
            agent_group="CCTV",
            ticket_type="Faults",
            custom_partner_acceptance_state="Accepted",
        )

        with (
            mock.patch.object(partner_create, "frappe") as frappe_mock,
            mock.patch.object(
                partner_create,
                "_is_partner_creator",
                return_value=True,
            ) as is_partner_creator,
            mock.patch.object(
                partner_create,
                "_set_if_field_exists",
            ) as set_if_field,
        ):
            frappe_mock.session.user = "partner.creator@local.test"

            partner_create.enforce_partner_create_v1(doc)

        is_partner_creator.assert_called_once_with(
            "partner.creator@local.test"
        )

        set_if_field.assert_not_called()

        self.assertEqual(doc.custom_request_source, "Telectro")
        self.assertEqual(doc.custom_fulfilment_party, "Partner")
        self.assertEqual(doc.agent_group, "CCTV")
        self.assertEqual(doc.ticket_type, "Faults")
        self.assertEqual(
            doc.custom_partner_acceptance_state,
            "Accepted",
        )
