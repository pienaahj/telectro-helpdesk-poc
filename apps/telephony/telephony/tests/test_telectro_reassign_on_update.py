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
