"""Regression tests for Data Request notification delivery."""

import unittest
from unittest.mock import patch

import frappe

from telephony import data_request_notification_delivery as delivery


USER = "coordinator.test@local.test"


class TestRecipientAuthorization(unittest.TestCase):

    def intent(self, event="arrival", user=USER):
        return {
            "event": event,
            "recipient": user,
        }

    def ticket(
        self,
        *,
        area="Data Request",
        team="Data Provisioning",
    ):
        return {
            "custom_service_area": area,
            "agent_group": team,
        }

    def authorize_arrival(
        self,
        *,
        eligible=True,
        members=None,
        readable=True,
        team="Data Provisioning",
    ):
        if members is None:
            members = [USER]

        ticket = self.ticket(team=team)

        hd_team = {
            "users": [
                {"user": user}
                for user in members
            ]
        }

        with (
            patch.object(
                delivery,
                "_eligible_user",
                return_value=eligible,
            ),
            patch.object(
                delivery.frappe,
                "get_doc",
                return_value=hd_team,
            ),
            patch.object(
                delivery.frappe,
                "has_permission",
                return_value=readable,
            ),
        ):
            return delivery._require_authorized_recipient(
                self.intent(),
                ticket,
            )

    def test_rejects_invalid_users(self):
        for user in ("", "Administrator", "Guest"):
            with self.subTest(user=user):
                with self.assertRaises(frappe.PermissionError):
                    delivery._require_authorized_recipient(
                        self.intent(user=user),
                        self.ticket(),
                    )

    def test_rejects_other_service_area(self):
        with self.assertRaises(ValueError):
            delivery._require_authorized_recipient(
                self.intent(),
                self.ticket(area="Routing"),
            )

    def test_rejects_unsupported_event(self):
        with self.assertRaises(ValueError):
            delivery._require_authorized_recipient(
                self.intent(event="unknown"),
                self.ticket(),
            )

    def test_arrival_authorized(self):
        self.assertIsNone(self.authorize_arrival())

    def test_arrival_rejects_ineligible_account(self):
        with self.assertRaises(frappe.PermissionError):
            self.authorize_arrival(eligible=False)

    def test_arrival_rejects_removed_team_member(self):
        with self.assertRaises(frappe.PermissionError):
            self.authorize_arrival(members=["other@local.test"])

    def test_arrival_rejects_changed_team(self):
        with self.assertRaises(frappe.PermissionError):
            self.authorize_arrival(team="Routing")

    def test_arrival_rejects_revoked_ticket_read(self):
        with self.assertRaises(frappe.PermissionError):
            self.authorize_arrival(readable=False)

    def test_escalation_authorized(self):
        ticket = self.ticket()

        with patch.object(
            delivery,
            "resolve_coordinator_recipients",
            return_value=[USER],
        ) as resolver:
            self.assertIsNone(
                delivery._require_authorized_recipient(
                    self.intent(event="escalation"),
                    ticket,
                )
            )

            resolver.assert_called_once_with(ticket)

    def test_escalation_rejects_revoked_authority(self):
        with patch.object(
            delivery,
            "resolve_coordinator_recipients",
            return_value=[],
        ):
            with self.assertRaises(frappe.PermissionError):
                delivery._require_authorized_recipient(
                    self.intent(event="escalation"),
                    self.ticket(),
                )


if __name__ == "__main__":
    unittest.main()
