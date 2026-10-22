import unittest
from unittest import mock

from telephony import telectro_ticket_edit_guard as guard


TECH_ROLE = "TELECTRO-POC Role - Tech"

ELEVATED_ROLES = [
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
    "System Manager",
    "Pilot Admin",
]


class GuardDenied(Exception):
    pass


def raise_permission_error(message, exception_class):
    raise exception_class(message)


class TestTechnicianTicketEditGuard(unittest.TestCase):

    def invoke_guard(
        self,
        user,
        roles,
        persisted_assignment,
        *,
        is_new=False,
        incoming_assignment=None,
    ):
        doc = mock.Mock()
        doc.name = "TEST-TICKET-001"
        doc.is_new.return_value = is_new

        # Deliberately separate the incoming form value from
        # the assignment already persisted in the database.
        doc._assign = incoming_assignment

        frappe_mock = mock.MagicMock()

        frappe_mock.session.user = user
        frappe_mock.get_roles.return_value = list(roles)
        frappe_mock.db.get_value.return_value = (
            persisted_assignment
        )

        frappe_mock.PermissionError = GuardDenied
        frappe_mock.throw.side_effect = raise_permission_error

        with (
            mock.patch.object(
                guard,
                "frappe",
                frappe_mock,
            ),
            mock.patch.object(
                guard,
                "_",
                side_effect=lambda message: message,
            ),
        ):
            guard.validate_ticket_edit_rights(doc)

    def test_technician_can_edit_own_assignment(self):
        self.invoke_guard(
            user="tech.bravo@local.test",
            roles=[TECH_ROLE],
            persisted_assignment='["tech.bravo@local.test"]',
        )

    def test_technician_cannot_edit_other_assignment(self):
        cases = [
            (
                "tech.bravo@local.test",
                '["tech.charlie@local.test"]',
            ),
            (
                "tech.charlie@local.test",
                '["tech.bravo@local.test"]',
            ),
        ]

        for user, assignment in cases:
            with self.subTest(user=user):
                with self.assertRaises(GuardDenied):
                    self.invoke_guard(
                        user=user,
                        roles=[TECH_ROLE],
                        persisted_assignment=assignment,
                    )

    def test_technician_can_edit_unassigned_pool_ticket(self):
        self.invoke_guard(
            user="tech.bravo@local.test",
            roles=[TECH_ROLE],
            persisted_assignment="",
        )

    def test_new_ticket_is_not_blocked(self):
        self.invoke_guard(
            user="tech.bravo@local.test",
            roles=[TECH_ROLE],
            persisted_assignment='["tech.charlie@local.test"]',
            is_new=True,
        )

    def test_incoming_assignment_cannot_bypass_guard(self):
        with self.assertRaises(GuardDenied):
            self.invoke_guard(
                user="tech.bravo@local.test",
                roles=[TECH_ROLE],
                persisted_assignment='["tech.charlie@local.test"]',
                incoming_assignment='["tech.bravo@local.test"]',
            )

    def test_elevated_users_can_intervene(self):
        for elevated_role in ELEVATED_ROLES:
            with self.subTest(role=elevated_role):
                self.invoke_guard(
                    user="internal.user@local.test",
                    roles=[
                        TECH_ROLE,
                        elevated_role,
                    ],
                    persisted_assignment='["tech.charlie@local.test"]',
                )

    def test_administrator_retains_bypass(self):
        self.invoke_guard(
            user="Administrator",
            roles=[TECH_ROLE],
            persisted_assignment='["tech.charlie@local.test"]',
        )

    def test_non_technician_remains_outside_tech_guard(self):
        # Other permission layers remain responsible for
        # non-Technician access.
        self.invoke_guard(
            user="other.user@local.test",
            roles=["Customer"],
            persisted_assignment='["tech.charlie@local.test"]',
        )


if __name__ == "__main__":
    unittest.main()
