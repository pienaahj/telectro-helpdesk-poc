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

class TestNativeTeamAfterInsert(unittest.TestCase):
    def test_normal_internal_ticket_falls_through_to_native_team_assignment(self):
        doc = _TicketDoc(
            name="TEST-NATIVE-PABX-INSERT",
            subject="Boschendal PABX native routing proof",
            custom_fulfilment_party="Telectro",
            custom_request_source="Telectro",
            custom_site_group="Boschendal",
            custom_service_area="PABX",
            agent_group="PABX",
        )

        with (
            mock.patch.object(
                round_robin,
                "resolve_ticket_routing_policy",
                return_value=None,
            ) as resolve_policy,
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_open_todo,
            mock.patch.object(
                round_robin,
                "_mirror_assign_from_todo",
            ) as mirror_assign,
            mock.patch.object(
                round_robin.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = round_robin.assign_after_insert(doc)

        self.assertIsNone(result)

        resolve_policy.assert_called_once_with(doc)
        ensure_open_todo.assert_not_called()
        mirror_assign.assert_not_called()
        set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-NATIVE-PABX-INSERT",
            "custom_contextual_assignment_hold",
            0,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            0,
        )


class TestContextualCoverageAfterInsert(unittest.TestCase):
    def test_matching_contextual_coverage_assigns_selected_team_member(self):
        doc = _TicketDoc(
            name="TEST-CONTEXTUAL-PABX-INSERT",
            subject="Emerald Life PABX contextual routing proof",
            custom_fulfilment_party="Telectro",
            custom_request_source="Customer",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="PABX",
            agent_group="PABX",
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                round_robin,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                round_robin,
                "_native_team_assignment_state",
                return_value={
                    "rule": "PABX - Support Rotation",
                    "users": [
                        "pierre@telectro.co.za",
                        "sean@telectro.co.za",
                        "armandt@telectro.co.za",
                        "kyle@telectro.co.za",
                    ],
                    "last_user": "sean@telectro.co.za",
                },
            ) as native_team_state,
            mock.patch.object(
                round_robin,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": True,
                    "coverage_rows": [
                        {"user": "armandt@telectro.co.za"},
                    ],
                    "eligible_users": [
                        "armandt@telectro.co.za",
                        "kyle@telectro.co.za",
                    ],
                    "selected_user": "armandt@telectro.co.za",
                },
            ) as resolve_contextual,
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
            mock.patch.object(
                round_robin,
                "_advance_native_team_cursor",
            ) as advance_cursor,
            mock.patch.object(
                round_robin.frappe.db,
                "set_value",
            ) as set_value,
        ):
            round_robin.assign_after_insert(doc)

        native_team_state.assert_called_once_with("PABX")

        resolve_contextual.assert_called_once_with(
            doc,
            [
                "pierre@telectro.co.za",
                "sean@telectro.co.za",
                "armandt@telectro.co.za",
                "kyle@telectro.co.za",
            ],
            last_user="sean@telectro.co.za",
        )

        ensure_open_todo.assert_called_once_with(
            "TEST-CONTEXTUAL-PABX-INSERT",
            "armandt@telectro.co.za",
            desc="Emerald Life PABX contextual routing proof",
        )

        mirror_assign.assert_called_once_with(doc)

        advance_cursor.assert_called_once_with(
            "PABX - Support Rotation",
            "armandt@telectro.co.za",
        )

        set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-CONTEXTUAL-PABX-INSERT",
            "custom_contextual_assignment_hold",
            0,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            0,
        )

    def test_no_contextual_coverage_still_falls_through_to_native_assignment(self):
        doc = _TicketDoc(
            name="TEST-NATIVE-POOL-INSERT",
            subject="Native pool fallback proof",
            custom_fulfilment_party="Telectro",
            custom_request_source="Customer",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="CCTV",
            agent_group="CCTV",
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                round_robin,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                round_robin,
                "_native_team_assignment_state",
                return_value={
                    "rule": "CCTV - Support Rotation",
                    "users": [
                        "tech.bravo@local.test",
                    ],
                    "last_user": "",
                },
            ),
            mock.patch.object(
                round_robin,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": False,
                    "coverage_rows": [],
                    "eligible_users": [],
                    "selected_user": "",
                },
            ),
            mock.patch.object(
                round_robin.frappe.db,
                "set_value",
            ) as set_value,
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_open_todo,
            mock.patch.object(
                round_robin,
                "_mirror_assign_from_todo",
            ) as mirror_assign,
            mock.patch.object(
                round_robin,
                "_advance_native_team_cursor",
            ) as advance_cursor,
        ):
            result = round_robin.assign_after_insert(doc)

        self.assertIsNone(result)
        ensure_open_todo.assert_not_called()
        mirror_assign.assert_not_called()
        advance_cursor.assert_not_called()
        set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-NATIVE-POOL-INSERT",
            "custom_contextual_assignment_hold",
            0,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            0,
        )

    def test_matching_coverage_with_no_capable_team_member_stays_true_pool(self):
        doc = _TicketDoc(
            name="TEST-CONTEXTUAL-EMPTY-INSERT",
            subject="Contextual configuration fault proof",
            custom_fulfilment_party="Telectro",
            custom_request_source="Customer",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="PABX",
            agent_group="PABX",
        )

        with (
            mock.patch.object(
                round_robin,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                round_robin,
                "_native_team_assignment_state",
                return_value={
                    "rule": "PABX - Support Rotation",
                    "users": [
                        "pierre@telectro.co.za",
                        "sean@telectro.co.za",
                    ],
                    "last_user": "pierre@telectro.co.za",
                },
            ),
            mock.patch.object(
                round_robin,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": True,
                    "coverage_rows": [
                        {"user": "outside.team@telectro.co.za"},
                    ],
                    "eligible_users": [],
                    "selected_user": "",
                },
            ),
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_open_todo,
            mock.patch.object(
                round_robin,
                "_mirror_assign_from_todo",
            ) as mirror_assign,
            mock.patch.object(
                round_robin,
                "_advance_native_team_cursor",
            ) as advance_cursor,
                        mock.patch.object(
                round_robin.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = round_robin.assign_after_insert(doc)

        self.assertIsNone(result)
        ensure_open_todo.assert_not_called()
        mirror_assign.assert_not_called()
        advance_cursor.assert_not_called()
        set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-CONTEXTUAL-EMPTY-INSERT",
            "custom_contextual_assignment_hold",
            1,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )
