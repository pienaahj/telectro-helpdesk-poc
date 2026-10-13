import unittest
from unittest import mock

from telephony import telectro_reassign_on_update as reassign


class TestPartnerFulfilmentRoutingFields(unittest.TestCase):
    def test_fulfilment_partner_is_routing_relevant(self):
        self.assertIn(
            "custom_fulfilment_partner",
            reassign.ROUTING_FIELDS,
        )


class TestNativeTeamUsersSafety(unittest.TestCase):
    def test_disabled_native_rule_returns_no_team_users(self):
        rule_name = "TEST-CCTV-ASSIGNMENT-RULE"

        with mock.patch.object(
            reassign,
            "frappe",
        ) as frappe_mock:
            frappe_mock.db.get_value.side_effect = [
                rule_name,
                1,
            ]
            frappe_mock.db.exists.return_value = True

            users = reassign._native_team_users("CCTV")

        self.assertEqual(users, [])

        self.assertEqual(
            frappe_mock.db.get_value.call_args_list,
            [
                mock.call(
                    "HD Team",
                    "CCTV",
                    "assignment_rule",
                ),
                mock.call(
                    "Assignment Rule",
                    rule_name,
                    "disabled",
                ),
            ],
        )

        frappe_mock.db.exists.assert_called_once_with(
            "Assignment Rule",
            rule_name,
        )

        frappe_mock.get_all.assert_not_called()


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
    def test_partner_fulfilment_clears_contextual_hold_and_resolves_dispatch_user(self):
        doc = _TicketDoc(
            name="TEST-PARTNER-REASSIGN",
            subject="Partner reassignment proof",
            custom_fulfilment_party="Partner",
            custom_fulfilment_partner="CN Services",
            custom_contextual_assignment_hold=1,
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
            mock.patch.object(
                reassign,
                "frappe",
            ) as frappe_mock,
        ):
            reassign.reassign_if_routing_changed(doc)

        seed_ticket_routing.assert_called_once_with(
            doc,
            method=None,
        )

        resolve_dispatch_user.assert_called_once_with(
            "CN Services"
        )

        frappe_mock.db.set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-PARTNER-REASSIGN",
            "custom_contextual_assignment_hold",
            0,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            0,
        )

        normalize_assignment.assert_called_once_with(
            "TEST-PARTNER-REASSIGN",
            "partner.test@local.test",
            note=(
                "Routing change: reassigned to Partner fulfilment | "
                "Partner reassignment proof"
            ),
        )


class TestDirectOwnerReassignment(unittest.TestCase):
    def test_direct_owner_clears_contextual_hold_when_owner_is_already_correct(self):
        target_user = "tech.owner@local.test"

        doc = _TicketDoc(
            name="TEST-DIRECT-OWNER-REASSIGN",
            subject="Direct-owner reassignment proof",
            custom_fulfilment_party="Telectro",
            custom_fulfilment_partner="",
            custom_contextual_assignment_hold=1,
            agent_group="Helpdesk Team",
        )

        with (
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ) as seed_ticket_routing,
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value={
                    "target_user": target_user,
                    "reason": "Explicit direct-owner test",
                },
            ) as resolve_policy,
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value=target_user,
            ),
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "frappe",
            ) as frappe_mock,
        ):
            reassign.reassign_if_routing_changed(doc)

        seed_ticket_routing.assert_called_once_with(
            doc,
            method=None,
        )

        resolve_policy.assert_called_once_with(doc)

        frappe_mock.db.set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-DIRECT-OWNER-REASSIGN",
            "custom_contextual_assignment_hold",
            0,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            0,
        )

        normalize_assignment.assert_not_called()


class TestNativeTeamReassignment(unittest.TestCase):
    def test_boschendal_routing_change_falls_through_to_native_team(self):
        doc = _TicketDoc(
            name="TEST-BOSCHENDAL-PABX-REASSIGN",
            subject="Boschendal PABX reassignment proof",
            custom_fulfilment_party="Telectro",
            custom_fulfilment_partner="",
            custom_site_group="Boschendal",
            custom_service_area="PABX",
            agent_group="PABX",
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ) as seed_ticket_routing,
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value=None,
            ) as resolve_policy,
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value="hendrik@local.test",
            ),
            mock.patch.object(
                reassign,
                "_native_team_users",
                return_value=["tech.charlie@local.test"],
            ) as native_team_users,
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_release_for_native_team_assignment",
            ) as release_for_native_team,
            mock.patch.object(
                reassign,
                "_native_team_assignment_state",
                return_value={
                    "rule": "PABX - Support Rotation",
                    "users": [
                        "tech.charlie@local.test",
                    ],
                    "last_user": "",
                },
            ),
            mock.patch.object(
                reassign,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": False,
                    "coverage_rows": [],
                    "eligible_users": [],
                    "selected_user": "",
                },
            ),
            mock.patch.object(
                reassign.frappe.db,
                "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

        seed_ticket_routing.assert_called_once_with(
            doc,
            method=None,
        )

        resolve_policy.assert_called_once_with(doc)

        native_team_users.assert_called_once_with("PABX")

        normalize_assignment.assert_not_called()

        release_for_native_team.assert_called_once()

        args, kwargs = release_for_native_team.call_args

        self.assertIs(args[0], doc)
        self.assertEqual(
            args[1],
            "TEST-BOSCHENDAL-PABX-REASSIGN",
        )

        self.assertIn(
            "group=PABX",
            kwargs["note"],
        )
        set_value.assert_called_once_with(
            "HD Ticket",
            "TEST-BOSCHENDAL-PABX-REASSIGN",
            "custom_contextual_assignment_hold",
            0,
            update_modified=False,
        )

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            0,
        )


class TestContextualCoverageReassignment(unittest.TestCase):
    def test_matching_coverage_without_capable_team_member_sets_hold_and_releases_owner(
        self,
    ):
        ticket = "TEST-CONTEXTUAL-EMPTY-REASSIGN"

        doc = _TicketDoc(
            name=ticket,
            subject="Contextual empty-intersection reassignment proof",
            custom_fulfilment_party="Telectro",
            custom_fulfilment_partner="",
            custom_request_source="Customer",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="PABX",
            agent_group="PABX",
            custom_contextual_assignment_hold=0,
        )

        current_user = "tech.charlie@local.test"

        with (
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ),
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value=current_user,
            ),
            # Preserve the current legacy behaviour during the RED run:
            # the present implementation sees the owner as a valid
            # native-team member and therefore keeps the assignment.
            mock.patch.object(
                reassign,
                "_native_team_users",
                return_value=[current_user],
            ),
            # These are the intended contextual integration seams.
            # create=True lets the test establish the contract before
            # the production module imports them.
            mock.patch.object(
                reassign,
                "_native_team_assignment_state",
                create=True,
                return_value={
                    "rule": "PABX - Support Rotation",
                    "users": [current_user],
                    "last_user": current_user,
                },
            ),
            mock.patch.object(
                reassign,
                "resolve_contextual_team_assignment",
                create=True,
                return_value={
                    "coverage_applies": True,
                    "coverage_rows": [
                        {
                            "user": (
                                "outside.team@telectro.co.za"
                            )
                        }
                    ],
                    "eligible_users": [],
                    "selected_user": "",
                },
            ),
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_release_for_native_team_assignment",
            ) as release_for_native_team,
            mock.patch.object(
                reassign.frappe.db,
                "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

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

        normalize_assignment.assert_not_called()

        release_for_native_team.assert_called_once()

        args, kwargs = release_for_native_team.call_args

        self.assertIs(args[0], doc)
        self.assertEqual(args[1], ticket)

        self.assertIn(
            "contextual",
            kwargs["note"].lower(),
        )

    def test_contextual_coverage_replaces_native_owner_outside_eligible_population(
        self,
    ):
        ticket = "TEST-CONTEXTUAL-SELECTED-REASSIGN"

        current_user = "tech.charlie@local.test"
        selected_user = "armandt@telectro.co.za"
        rule_name = "PABX - Support Rotation"

        doc = _TicketDoc(
            name=ticket,
            subject="Contextual selected-user reassignment proof",
            custom_fulfilment_party="Telectro",
            custom_fulfilment_partner="",
            custom_request_source="Customer",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="PABX",
            agent_group="PABX",
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ),
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value=current_user,
            ),
            mock.patch.object(
                reassign,
                "_native_team_assignment_state",
                return_value={
                    "rule": rule_name,
                    "users": [
                        current_user,
                        selected_user,
                    ],
                    "last_user": current_user,
                },
            ),
            mock.patch.object(
                reassign,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": True,
                    "coverage_rows": [
                        {"user": selected_user},
                    ],
                    "eligible_users": [
                        selected_user,
                    ],
                    "selected_user": selected_user,
                },
            ),
            mock.patch.object(
                reassign,
                "_native_team_users",
                return_value=[
                    current_user,
                    selected_user,
                ],
            ),
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_release_for_native_team_assignment",
            ) as release_for_native_team,
            mock.patch.object(
                reassign,
                "_advance_native_team_cursor",
                create=True,
            ) as advance_cursor,
            mock.patch.object(
                reassign.frappe.db,
                "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

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

        normalize_assignment.assert_called_once_with(
            ticket,
            selected_user,
            note=(
                "Routing change: reassigned via contextual "
                "Service Coverage | "
                "Contextual selected-user reassignment proof"
            ),
        )

        release_for_native_team.assert_not_called()

        advance_cursor.assert_called_once_with(
            rule_name,
            selected_user,
        )

    def test_no_contextual_coverage_clears_stale_hold_and_preserves_valid_native_owner(
        self,
    ):
        ticket = "TEST-NO-CONTEXTUAL-COVERAGE-REASSIGN"
        current_user = "tech.charlie@local.test"

        doc = _TicketDoc(
            name=ticket,
            subject="No contextual coverage reassignment proof",
            custom_fulfilment_party="Telectro",
            custom_fulfilment_partner="",
            custom_request_source="Customer",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="CCTV",
            agent_group="CCTV",
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ),
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "get_ticket_assignment_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value=current_user,
            ),
            mock.patch.object(
                reassign,
                "_native_team_assignment_state",
                return_value={
                    "rule": "CCTV - Support Rotation",
                    "users": [current_user],
                    "last_user": current_user,
                },
            ),
            mock.patch.object(
                reassign,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": False,
                    "coverage_rows": [],
                    "eligible_users": [],
                    "selected_user": "",
                },
            ),
            mock.patch.object(
                reassign,
                "_native_team_users",
                return_value=[current_user],
            ),
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_release_for_native_team_assignment",
            ) as release_for_native_team,
            mock.patch.object(
                reassign.frappe.db,
                "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

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

        normalize_assignment.assert_not_called()
        release_for_native_team.assert_not_called()

    def test_contextual_coverage_preserves_current_owner_when_still_eligible(
        self,
    ):
        ticket = "TEST-CONTEXTUAL-ELIGIBLE-OWNER-REASSIGN"

        current_user = "sean@telectro.co.za"
        selected_user = "armandt@telectro.co.za"
        rule_name = "PABX - Support Rotation"

        doc = _TicketDoc(
            name=ticket,
            subject="Contextual eligible-owner preservation proof",
            custom_fulfilment_party="Telectro",
            custom_fulfilment_partner="",
            custom_request_source="Customer",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="PABX",
            agent_group="PABX",
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ),
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value=current_user,
            ),
            mock.patch.object(
                reassign,
                "_native_team_assignment_state",
                return_value={
                    "rule": rule_name,
                    "users": [
                        current_user,
                        selected_user,
                    ],
                    "last_user": current_user,
                },
            ),
            mock.patch.object(
                reassign,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": True,
                    "coverage_rows": [
                        {"user": current_user},
                        {"user": selected_user},
                    ],
                    "eligible_users": [
                        current_user,
                        selected_user,
                    ],
                    "selected_user": selected_user,
                },
            ),
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_release_for_native_team_assignment",
            ) as release_for_native_team,
            mock.patch.object(
                reassign,
                "_advance_native_team_cursor",
            ) as advance_cursor,
            mock.patch.object(
                reassign.frappe.db,
                "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

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

        normalize_assignment.assert_not_called()
        release_for_native_team.assert_not_called()
        advance_cursor.assert_not_called()


class TestAssignmentPolicyRoutingTransitions(unittest.TestCase):
    def test_entering_true_pool_releases_previous_owner(self):
        ticket = "TEST-ENTER-TRUE-POOL"

        old_doc = _TicketDoc(
            name=ticket,
            custom_fulfilment_party="Telectro",
            custom_customer="Emerald Life",
            custom_service_area="Routing",
            agent_group="Routing",
        )

        doc = _TicketDoc(
            name=ticket,
            subject="Emerald Life CCTV policy transition",
            custom_fulfilment_party="Telectro",
            custom_customer="Emerald Life",
            custom_service_area="CCTV",
            agent_group="CCTV",
            custom_contextual_assignment_hold=0,
        )

        with (
            mock.patch.object(
                reassign,
                "_get_old_doc",
                return_value=old_doc,
            ),
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ),
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value="tech.previous@local.test",
            ),
            mock.patch.object(
                reassign,
                "get_ticket_assignment_policy",
                side_effect=[
                    {
                        "name": "TAP-EMERALD-CCTV",
                        "assignment_mode": "True Pool",
                    },
                    None,
                ],
            ) as resolve_policy,
            mock.patch.object(
                reassign,
                "_release_for_native_team_assignment",
            ) as release_assignment,
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_native_team_assignment_state",
            ) as native_state,
            mock.patch.object(
                reassign.frappe.db,
                "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

        self.assertEqual(
            resolve_policy.call_args_list,
            [
                mock.call(doc),
                mock.call(old_doc),
            ],
        )

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

        release_assignment.assert_called_once()

        args, kwargs = release_assignment.call_args

        self.assertIs(args[0], doc)
        self.assertEqual(args[1], ticket)
        self.assertIn("True Pool", kwargs["note"])

        normalize_assignment.assert_not_called()
        native_state.assert_not_called()

    def test_same_true_pool_preserves_manually_claimed_owner(self):
        ticket = "TEST-TRUE-POOL-MANUAL-OWNER"
        current_user = "tech.claimed@local.test"

        old_doc = _TicketDoc(
            name=ticket,
            custom_fulfilment_party="Telectro",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="CCTV",
            custom_request_type="Fault",
            agent_group="CCTV",
            custom_contextual_assignment_hold=1,
        )

        doc = _TicketDoc(
            name=ticket,
            subject="Preserve manually claimed CCTV ticket",
            custom_fulfilment_party="Telectro",
            custom_customer="Emerald Life",
            custom_site_group="Emerald Life - Head Office",
            custom_service_area="CCTV",
            custom_request_type="Assistance",
            agent_group="CCTV",
            custom_contextual_assignment_hold=1,
        )

        policy = {
            "name": "TAP-EMERALD-CCTV",
            "assignment_mode": "True Pool",
        }

        with (
            mock.patch.object(
                reassign,
                "_get_old_doc",
                return_value=old_doc,
            ),
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ),
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value=current_user,
            ),
            mock.patch.object(
                reassign,
                "get_ticket_assignment_policy",
                return_value=policy,
            ) as resolve_policy,
            mock.patch.object(
                reassign,
                "_release_for_native_team_assignment",
            ) as release_assignment,
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_native_team_assignment_state",
            ) as native_state,
            mock.patch.object(
                reassign.frappe.db,
                "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

        self.assertEqual(
            resolve_policy.call_args_list,
            [
                mock.call(doc),
                mock.call(old_doc),
            ],
        )

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

        release_assignment.assert_not_called()
        normalize_assignment.assert_not_called()
        native_state.assert_not_called()

    def test_leaving_true_pool_enters_contextual_round_robin(self):
        ticket = "TEST-TRUE-POOL-TO-ROUND-ROBIN"

        old_doc = _TicketDoc(
            name=ticket,
            custom_fulfilment_party="Telectro",
            custom_customer="Emerald Life",
            custom_service_area="CCTV",
            agent_group="CCTV",
            custom_contextual_assignment_hold=1,
        )

        doc = _TicketDoc(
            name=ticket,
            subject="CCTV round-robin transition proof",
            custom_fulfilment_party="Telectro",
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
        rule_name = "CCTV - Support Rotation"

        with (
            mock.patch.object(
                reassign,
                "_get_old_doc",
                return_value=old_doc,
            ),
            mock.patch.object(
                reassign,
                "seed_ticket_routing",
            ),
            mock.patch.object(
                reassign,
                "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "_current_assignee",
                return_value=None,
            ),
            mock.patch.object(
                reassign,
                "get_ticket_assignment_policy",
                return_value={
                    "name": "TAP-BOSCHENDAL-CCTV",
                    "assignment_mode": "Round Robin",
                },
            ) as resolve_policy,
            mock.patch.object(
                reassign,
                "_native_team_assignment_state",
                return_value={
                    "rule": rule_name,
                    "users": team_users,
                    "last_user": "sean@telectro.co.za",
                },
            ) as native_state,
            mock.patch.object(
                reassign,
                "resolve_contextual_team_assignment",
                return_value={
                    "coverage_applies": True,
                    "eligible_users": team_users,
                    "selected_user": selected_user,
                },
            ) as resolve_coverage,
            mock.patch.object(
                reassign,
                "_normalize_assignment",
            ) as normalize_assignment,
            mock.patch.object(
                reassign,
                "_release_for_native_team_assignment",
            ) as release_assignment,
            mock.patch.object(
                reassign,
                "_advance_native_team_cursor",
            ) as advance_cursor,
            mock.patch.object(
                reassign.frappe.db,
                "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

        resolve_policy.assert_called_once_with(doc)

        native_state.assert_called_once_with("CCTV")

        resolve_coverage.assert_called_once_with(
            doc,
            team_users,
            last_user="sean@telectro.co.za",
        )

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

        normalize_assignment.assert_called_once_with(
            ticket,
            selected_user,
            note=(
                "Routing change: reassigned via contextual "
                "Service Coverage | "
                "CCTV round-robin transition proof"
            ),
        )

        advance_cursor.assert_called_once_with(
            rule_name,
            selected_user,
        )

        release_assignment.assert_not_called()


class TestCCTVIncompleteContextRoutingChange(unittest.TestCase):
    """Protect ownership when CCTV Customer/Campus context is incomplete."""

    def test_entering_incomplete_context_releases_previous_owner(self):
        scenarios = [
            ("NO_CUSTOMER", "", "Boschendal"),
            ("NO_CAMPUS", "Boschendal", ""),
            ("NEITHER", "", ""),
        ]

        for label, customer, campus in scenarios:
            with self.subTest(context=label):
                ticket = f"TEST-CCTV-ROUTING-{label}"

                old_doc = _TicketDoc(
                    name=ticket,
                    custom_fulfilment_party="Telectro",
                    custom_customer="Boschendal",
                    custom_site_group="Boschendal",
                    custom_service_area="CCTV",
                    agent_group="CCTV",
                )

                doc = _TicketDoc(
                    name=ticket,
                    subject="Incomplete CCTV routing proof",
                    custom_fulfilment_party="Telectro",
                    custom_customer=customer,
                    custom_site_group=campus,
                    custom_service_area="CCTV",
                    agent_group="CCTV",
                    custom_contextual_assignment_hold=0,
                )

                with (
                    mock.patch.object(
                        reassign, "_get_old_doc",
                        return_value=old_doc,
                    ),
                    mock.patch.object(
                        reassign, "seed_ticket_routing",
                    ),
                    mock.patch.object(
                        reassign, "resolve_ticket_routing_policy",
                        return_value=None,
                    ),
                    mock.patch.object(
                        reassign, "get_ticket_assignment_policy",
                        return_value=None,
                    ),
                    mock.patch.object(
                        reassign, "_current_assignee",
                        return_value="kyle@telectro.co.za",
                    ),
                    mock.patch.object(
                        reassign, "_native_team_assignment_state",
                    ) as native_state,
                    mock.patch.object(
                        reassign, "resolve_contextual_team_assignment",
                    ) as resolve_coverage,
                    mock.patch.object(
                        reassign, "_native_team_users",
                        return_value=["kyle@telectro.co.za"],
                    ),
                    mock.patch.object(
                        reassign, "_release_for_native_team_assignment",
                    ) as release_owner,
                    mock.patch.object(
                        reassign, "_normalize_assignment",
                    ) as normalize,
                    mock.patch.object(
                        reassign.frappe.db, "set_value",
                    ) as set_value,
                ):
                    reassign.reassign_if_routing_changed(doc)

                self.assertEqual(
                    doc.get("custom_contextual_assignment_hold"),
                    1,
                )

                set_value.assert_called_once_with(
                    "HD Ticket",
                    ticket,
                    "custom_contextual_assignment_hold",
                    1,
                    update_modified=False,
                )

                release_owner.assert_called_once()
                native_state.assert_not_called()
                resolve_coverage.assert_not_called()
                normalize.assert_not_called()

    def test_unchanged_incomplete_context_preserves_manual_owner(self):
        ticket = "TEST-CCTV-INCOMPLETE-MANUAL-OWNER"

        old_doc = _TicketDoc(
            name=ticket,
            custom_fulfilment_party="Telectro",
            custom_customer="Boschendal",
            custom_site_group="",
            custom_service_area="CCTV",
            custom_request_type="Fault",
            agent_group="CCTV",
            custom_contextual_assignment_hold=1,
        )

        doc = _TicketDoc(
            name=ticket,
            subject="Preserve manually claimed CCTV ticket",
            custom_fulfilment_party="Telectro",
            custom_customer="Boschendal",
            custom_site_group="",
            custom_service_area="CCTV",
            custom_request_type="Assistance",
            agent_group="CCTV",
            custom_contextual_assignment_hold=1,
        )

        with (
            mock.patch.object(
                reassign, "_get_old_doc",
                return_value=old_doc,
            ),
            mock.patch.object(
                reassign, "seed_ticket_routing",
            ),
            mock.patch.object(
                reassign, "resolve_ticket_routing_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign, "get_ticket_assignment_policy",
                return_value=None,
            ),
            mock.patch.object(
                reassign, "_current_assignee",
                return_value="pierre@telectro.co.za",
            ),
            mock.patch.object(
                reassign, "_native_team_assignment_state",
            ) as native_state,
            mock.patch.object(
                reassign, "resolve_contextual_team_assignment",
            ) as resolve_coverage,
            mock.patch.object(
                reassign, "_release_for_native_team_assignment",
            ) as release_owner,
            mock.patch.object(
                reassign, "_normalize_assignment",
            ) as normalize,
            mock.patch.object(
                reassign.frappe.db, "set_value",
            ) as set_value,
        ):
            reassign.reassign_if_routing_changed(doc)

        self.assertEqual(
            doc.get("custom_contextual_assignment_hold"),
            1,
        )

        set_value.assert_called_once_with(
            "HD Ticket",
            ticket,
            "custom_contextual_assignment_hold",
            1,
            update_modified=False,
        )

        release_owner.assert_not_called()
        native_state.assert_not_called()
        resolve_coverage.assert_not_called()
        normalize.assert_not_called()
