import unittest
from unittest import mock

from telephony import telectro_round_robin as round_robin


class _TicketDoc(dict):
    __getattr__ = dict.get


class TestPartnerFulfilmentAfterInsert(unittest.TestCase):
    def test_partner_fulfilment_resolves_default_dispatch_user(self):
        doc = _TicketDoc(
            name="TEST-PARTNER-INSERT",
            subject="Partner after-insert proof",
            custom_fulfilment_party="Partner",
            custom_fulfilment_partner="CN Services",
        )

        with (
            mock.patch.object(
                round_robin,
                "resolve_partner_dispatch_user",
                return_value="partner.test@local.test",
            ) as resolve_dispatch_user,
            mock.patch.object(
                round_robin,
                "frappe",
            ) as frappe_mock,
            mock.patch.object(
                round_robin,
                "_open_todos_for_ticket",
                return_value=[],
            ),
            mock.patch.object(
                round_robin,
                "_parse_assign_users",
                return_value=[],
            ),
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_open_todo,
            mock.patch.object(
                round_robin,
                "_mirror_assign_from_todo",
            ) as mirror_assign,
        ):
            frappe_mock.db.get_value.return_value = ""

            round_robin.assign_after_insert(doc)

        resolve_dispatch_user.assert_called_once_with(
            "CN Services"
        )

        ensure_open_todo.assert_called_once_with(
            "TEST-PARTNER-INSERT",
            "partner.test@local.test",
            desc="Partner after-insert proof",
        )

        mirror_assign.assert_called_once_with(doc)
