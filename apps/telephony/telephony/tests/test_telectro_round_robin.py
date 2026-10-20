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

    def test_cctv_default_policy_does_not_authorize_assignment(self):
        doc = _TicketDoc(
            name="TEST-CCTV-DEFAULT-POLICY",
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
                "get_ticket_assignment_policy",
                return_value={
                    "name": "TAP-DEFAULT-CCTV",
                    "coverage_scope": "Default",
                    "service_area": "CCTV",
                    "assignment_mode": "Round Robin",
                },
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
            "TEST-CCTV-DEFAULT-POLICY",
            "custom_contextual_assignment_hold",
            1,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )

    def test_cctv_without_approved_policy_remains_held(self):
        doc = _TicketDoc(
            name="TEST-CCTV-NO-POLICY",
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
                "get_ticket_assignment_policy",
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
            "TEST-CCTV-NO-POLICY",
            "custom_contextual_assignment_hold",
            1,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )

    def test_non_cctv_without_contextual_coverage_preserves_native_fallback(self):
        ticket = "TEST-PABX-NATIVE-FALLBACK"
        native_user = "tech.charlie@local.test"

        doc = _TicketDoc(
            name=ticket,
            subject="PABX native team fallback proof",
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
                "get_ticket_assignment_policy",
                return_value=None,
            ),
            mock.patch.object(
                round_robin,
                "_native_team_assignment_state",
                return_value={
                    "rule": "PABX - Support Rotation",
                    "users": [native_user],
                    "last_user": "",
                },
            ) as native_state,
            mock.patch.object(
                round_robin,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": False,
                    "coverage_rows": [],
                    "eligible_users": [],
                    "selected_user": "",
                },
            ) as resolve_coverage,
            mock.patch.object(
                round_robin.frappe.db,
                "set_value",
            ) as set_value,
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_todo,
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

        # Ordinary non-CCTV routing must still reach native team
        # assignment evaluation.
        native_state.assert_called_once_with("PABX")

        resolve_coverage.assert_called_once_with(
            doc,
            [native_user],
            last_user="",
        )

        # No contextual assignment is created by this handler.
        # The later native Assignment Rule owns fallback selection.
        ensure_todo.assert_not_called()
        mirror_assign.assert_not_called()
        advance_cursor.assert_not_called()

        # The contextual hold must be cleared so native assignment
        # remains permitted for ordinary Service Areas.
        set_value.assert_called_once_with(
            "HD Ticket",
            ticket,
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


class TestContextualAssignmentPolicyAfterInsert(unittest.TestCase):
    def test_emerald_life_cctv_true_pool_suppresses_automatic_assignment(self):
        doc = _TicketDoc(
            name="TEST-EMERALD-CCTV-TRUE-POOL",
            subject="Emerald Life CCTV pool-only proof",
            custom_fulfilment_party="Telectro",
            custom_request_source="Customer",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="CCTV",
            agent_group="CCTV",
            custom_contextual_assignment_hold=0,
        )

        with (
            mock.patch.object(
                round_robin,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                round_robin,
                "get_ticket_assignment_policy",
                return_value={
                    "name": "TAP-EMERALD-CCTV",
                    "coverage_scope": "Customer",
                    "assignment_mode": "True Pool",
                },
            ) as resolve_policy,
            mock.patch.object(
                round_robin,
                "_native_team_assignment_state",
            ) as native_state,
            mock.patch.object(
                round_robin,
                "resolve_contextual_team_assignment",
            ) as resolve_coverage,
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_todo,
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

        resolve_policy.assert_called_once_with(doc)

        native_state.assert_not_called()
        resolve_coverage.assert_not_called()
        ensure_todo.assert_not_called()
        advance_cursor.assert_not_called()

        set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-EMERALD-CCTV-TRUE-POOL",
            "custom_contextual_assignment_hold",
            1,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )

    def test_boschendal_cctv_round_robin_assigns_covered_team_member(self):
        doc = _TicketDoc(
            name="TEST-BOSCHENDAL-CCTV-ROUND-ROBIN",
            subject="Boschendal CCTV round-robin proof",
            custom_fulfilment_party="Telectro",
            custom_request_source="Customer",
            custom_customer="Boschendal",
            custom_site_group="Boschendal",
            custom_service_area="CCTV",
            agent_group="CCTV",
            custom_contextual_assignment_hold=1,
        )

        team_users = [
            "pierre@telectro.co.za",
            "sean@telectro.co.za",
            "armandt@telectro.co.za",
            "jacques@telectro.co.za",
        ]

        selected_user = "armandt@telectro.co.za"

        with (
            mock.patch.object(
                round_robin,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                round_robin,
                "get_ticket_assignment_policy",
                return_value={
                    "name": "TAP-BOSCHENDAL-CCTV",
                    "coverage_scope": "Customer/Campus",
                    "assignment_mode": "Round Robin",
                },
            ) as resolve_policy,
            mock.patch.object(
                round_robin,
                "_native_team_assignment_state",
                return_value={
                    "rule": "CCTV - Support Rotation",
                    "users": team_users,
                    "last_user": "sean@telectro.co.za",
                },
            ) as native_state,
            mock.patch.object(
                round_robin,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": True,
                    "coverage_rows": [
                        {"user": user}
                        for user in team_users
                    ],
                    "eligible_users": team_users,
                    "selected_user": selected_user,
                },
            ) as resolve_coverage,
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
            ) as ensure_todo,
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
                "get_value",
                return_value="",
            ),
            mock.patch.object(
                round_robin.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = round_robin.assign_after_insert(doc)

        self.assertIsNone(result)

        resolve_policy.assert_called_once_with(doc)
        native_state.assert_called_once_with("CCTV")

        resolve_coverage.assert_called_once_with(
            doc,
            team_users,
            last_user="sean@telectro.co.za",
        )

        ensure_todo.assert_called_once_with(
            "TEST-BOSCHENDAL-CCTV-ROUND-ROBIN",
            selected_user,
            desc="Boschendal CCTV round-robin proof",
        )

        mirror_assign.assert_called_once_with(doc)

        advance_cursor.assert_called_once_with(
            "CCTV - Support Rotation",
            selected_user,
        )

        set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-BOSCHENDAL-CCTV-ROUND-ROBIN",
            "custom_contextual_assignment_hold",
            0,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            0,
        )

    def test_boschendal_cctv_round_robin_without_coverage_remains_held(self):
        ticket = "TEST-BOSCHENDAL-CCTV-NO-COVERAGE"

        doc = _TicketDoc(
            name=ticket,
            subject="Boschendal CCTV without Service Coverage",
            custom_fulfilment_party="Telectro",
            custom_request_source="Customer",
            custom_customer="Boschendal",
            custom_site_group="Boschendal",
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
                "get_ticket_assignment_policy",
                return_value={
                    "name": "TAP-BOSCHENDAL-CCTV",
                    "coverage_scope": "Customer/Campus",
                    "assignment_mode": "Round Robin",
                },
            ),
            mock.patch.object(
                round_robin,
                "_native_team_assignment_state",
                return_value={
                    "rule": "CCTV - Support Rotation",
                    "users": [
                        "pierre@telectro.co.za",
                        "sean@telectro.co.za",
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
            ) as resolve_coverage,
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_todo,
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

        # Coverage resolution must have been evaluated.
        resolve_coverage.assert_called_once()

        # No automatic ownership or cursor movement is permitted.
        ensure_todo.assert_not_called()
        mirror_assign.assert_not_called()
        advance_cursor.assert_not_called()

        # Without explicit Service Coverage, CCTV remains held.
        set_value.assert_called_once_with(
            "HD Ticket",
            ticket,
            "custom_contextual_assignment_hold",
            1,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )


class TestCCTVIncompleteContextAfterInsert(unittest.TestCase):
    """Incomplete CCTV context must not reach native assignment."""

    def test_incomplete_context_sets_hold_before_native_fallback(self):
        scenarios = [
            ("NO_CUSTOMER", "", "Boschendal"),
            ("NO_CAMPUS", "Boschendal", ""),
            ("NEITHER", "", ""),
        ]

        for label, customer, campus in scenarios:
            with self.subTest(context=label):
                ticket_name = f"TEST-CCTV-INCOMPLETE-{label}"

                doc = _TicketDoc(
                    name=ticket_name,
                    subject="Incomplete CCTV context proof",
                    custom_fulfilment_party="Telectro",
                    custom_request_source="Telectro",
                    custom_customer=customer,
                    customer="",
                    custom_site_group=campus,
                    custom_service_area="CCTV",
                    agent_group="CCTV",
                    custom_contextual_assignment_hold=0,
                )

                with (
                    mock.patch.object(
                        round_robin,
                        "resolve_ticket_routing_policy",
                        return_value=None,
                    ),
                    mock.patch.object(
                        round_robin,
                        "get_ticket_assignment_policy",
                        return_value=None,
                    ),
                    mock.patch.object(
                        round_robin,
                        "_native_team_assignment_state",
                        return_value={
                            "rule": "",
                            "users": [],
                            "last_user": "",
                        },
                    ) as native_state,
                    mock.patch.object(
                        round_robin,
                        "resolve_contextual_team_assignment",
                        return_value={
                            "coverage_applies": False,
                            "eligible_users": [],
                            "selected_user": "",
                        },
                    ) as resolve_coverage,
                    mock.patch.object(
                        round_robin.frappe.db,
                        "set_value",
                    ) as set_value,
                ):
                    round_robin.assign_after_insert(doc)

                self.assertEqual(
                    doc.get("custom_contextual_assignment_hold"),
                    1,
                )

                set_value.assert_called_once_with(
                    "HD Ticket",
                    ticket_name,
                    "custom_contextual_assignment_hold",
                    1,
                    update_modified=False,
                )

                native_state.assert_not_called()
                resolve_coverage.assert_not_called()


class TestCCTVPreInsertAssignmentHold(unittest.TestCase):
    """Protect CCTV from native assignment before after_insert."""

    @staticmethod
    def _ticket(area, *, is_new=True, hold=0):
        doc = round_robin.frappe._dict(
            doctype="HD Ticket",
            custom_service_area=area,
            custom_contextual_assignment_hold=hold,
        )

        doc.is_new = lambda: is_new
        return doc

    def test_new_cctv_ticket_is_held_before_insert(self):
        doc = self._ticket("CCTV", hold=0)

        with mock.patch.object(
            round_robin.frappe.db,
            "set_value",
        ) as db_set:
            round_robin.initialize_cctv_assignment_hold(doc)

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )

        # The initial insert persists the hold.
        # The validation hook must not write separately.
        db_set.assert_not_called()

    def test_new_non_cctv_ticket_preserves_native_fallback(self):
        doc = self._ticket("PABX", hold=0)

        with mock.patch.object(
            round_robin.frappe.db,
            "set_value",
        ) as db_set:
            round_robin.initialize_cctv_assignment_hold(doc)

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            0,
        )

        db_set.assert_not_called()

    def test_existing_cctv_ticket_preserves_hold_state(self):
        for initial_hold in (0, 1):
            with self.subTest(initial_hold=initial_hold):
                doc = self._ticket(
                    "CCTV",
                    is_new=False,
                    hold=initial_hold,
                )

                with mock.patch.object(
                    round_robin.frappe.db,
                    "set_value",
                ) as db_set:
                    round_robin.initialize_cctv_assignment_hold(doc)

                self.assertEqual(
                    doc.get("custom_contextual_assignment_hold"),
                    initial_hold,
                )

                db_set.assert_not_called()

    def test_pre_insert_hold_follows_routing_seed(self):
        from telephony import hooks as telephony_hooks

        handlers = telephony_hooks.doc_events[
            "HD Ticket"
        ]["validate"]

        self.assertEqual(
            handlers[:3],
            [
                "telephony.telectro_ticket_routing.seed_ticket_routing",
                "telephony.telectro_round_robin.initialize_cctv_assignment_hold",
                "telephony.telectro_site_guard.validate_site_fields",
            ],
        )


class TestCCTVExplicitOwnershipAfterInsert(unittest.TestCase):
    """Explicit ownership must not release native CCTV suppression."""

    def test_cctv_partner_dispatch_preserves_initial_hold(self):
        doc = _TicketDoc(
            name="TEST-CCTV-PARTNER-DISPATCH",
            subject="CCTV Partner dispatch proof",
            custom_service_area="CCTV",
            agent_group="CCTV",
            custom_fulfilment_party="Partner",
            custom_fulfilment_partner="CN Services",
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                round_robin,
                "resolve_partner_dispatch_user",
                return_value="partner.test@local.test",
            ) as resolve_dispatch,
            mock.patch.object(
                round_robin,
                "resolve_ticket_routing_policy",
            ) as resolve_direct_owner,
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
                round_robin.frappe.db,
                "get_value",
                return_value="",
            ),
            mock.patch.object(
                round_robin.frappe.db,
                "set_value",
            ) as db_set,
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_todo,
            mock.patch.object(
                round_robin,
                "_mirror_assign_from_todo",
            ) as mirror_assign,
        ):
            round_robin.assign_after_insert(doc)

        resolve_dispatch.assert_called_once_with("CN Services")
        resolve_direct_owner.assert_not_called()

        ensure_todo.assert_called_once_with(
            "TEST-CCTV-PARTNER-DISPATCH",
            "partner.test@local.test",
            desc="CCTV Partner dispatch proof",
        )

        mirror_assign.assert_called_once_with(doc)

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )

        db_set.assert_not_called()

    def test_cctv_explicit_creator_ownership_preserves_initial_hold(self):
        technician = "tech.bravo@local.test"

        doc = _TicketDoc(
            name="TEST-CCTV-CREATOR-OWNERSHIP",
            subject="CCTV explicit creator ownership proof",
            owner=technician,
            custom_service_area="CCTV",
            agent_group="CCTV",
            custom_fulfilment_party="Telectro",
            custom_take_ownership_on_create=1,
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                round_robin,
                "resolve_ticket_routing_policy",
                return_value={
                    "target_user": technician,
                    "reason": "Explicit creator ownership",
                    "policy_key": "creator_take_ownership",
                },
            ) as resolve_policy,
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
                round_robin.frappe.db,
                "get_value",
                return_value="",
            ),
            mock.patch.object(
                round_robin.frappe.db,
                "set_value",
            ) as db_set,
            mock.patch.object(
                round_robin,
                "_ensure_open_todo",
            ) as ensure_todo,
            mock.patch.object(
                round_robin,
                "_mirror_assign_from_todo",
            ) as mirror_assign,
        ):
            round_robin.assign_after_insert(doc)

        resolve_policy.assert_called_once_with(doc)

        ensure_todo.assert_called_once_with(
            "TEST-CCTV-CREATOR-OWNERSHIP",
            technician,
            desc="Explicit creator ownership",
        )

        mirror_assign.assert_called_once_with(doc)

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )

        db_set.assert_not_called()
