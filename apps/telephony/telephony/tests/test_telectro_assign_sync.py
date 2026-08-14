import unittest
from unittest.mock import call, patch

from telephony import telectro_assign_sync as assign_sync


class _TicketDoc(dict):
    __getattr__ = dict.get


class TestTerminalAssignmentCleanup(unittest.TestCase):
    def test_terminal_statuses_cancel_open_todos_and_clear_assign(self):
        for status in ("Resolved", "Closed", "Archived"):
            with self.subTest(status=status):
                doc = _TicketDoc(
                    name="TEST-TERMINAL",
                    status=status,
                    custom_fulfilment_party="Partner",
                    _assign='["owner@example.com"]',
                )
                todos = [
                    {
                        "name": "TODO-1",
                        "allocated_to": "owner@example.com",
                    },
                    {
                        "name": "TODO-2",
                        "allocated_to": "other@example.com",
                    },
                ]

                with (
                    patch.object(
                        assign_sync,
                        "_open_todos",
                        return_value=todos,
                    ) as open_todos,
                    patch.object(assign_sync, "_close_todo") as close_todo,
                    patch.object(assign_sync, "_mirror_assign") as mirror_assign,
                    patch.object(
                        assign_sync,
                        "_is_partner_fulfilment",
                    ) as is_partner_fulfilment,
                    patch.object(
                        assign_sync,
                        "_enforce_partner_assignment",
                    ) as enforce_partner_assignment,
                    patch.object(
                        assign_sync,
                        "_parse_assign_users",
                    ) as parse_assign_users,
                    patch.object(
                        assign_sync,
                        "_ensure_open_todo",
                    ) as ensure_open_todo,
                ):
                    assign_sync.sync_ticket_assignments(doc)

                open_todos.assert_called_once_with("TEST-TERMINAL")
                self.assertEqual(
                    close_todo.call_args_list,
                    [
                        call("TODO-1"),
                        call("TODO-2"),
                    ],
                )
                mirror_assign.assert_called_once_with("TEST-TERMINAL", [])

                is_partner_fulfilment.assert_not_called()
                enforce_partner_assignment.assert_not_called()
                parse_assign_users.assert_not_called()
                ensure_open_todo.assert_not_called()

    def test_open_owned_ticket_keeps_canonical_owner(self):
        doc = _TicketDoc(
            name="TEST-ACTIVE",
            status="Open",
            _assign='["stale@example.com"]',
        )
        todos = [
            {
                "name": "TODO-1",
                "allocated_to": "owner@example.com",
            }
        ]

        with (
            patch.object(
                assign_sync,
                "_open_todos",
                return_value=todos,
            ) as open_todos,
            patch.object(assign_sync, "_close_todo") as close_todo,
            patch.object(assign_sync, "_mirror_assign") as mirror_assign,
            patch.object(
                assign_sync,
                "_is_partner_fulfilment",
                return_value=False,
            ) as is_partner_fulfilment,
            patch.object(
                assign_sync,
                "_enforce_partner_assignment",
            ) as enforce_partner_assignment,
            patch.object(
                assign_sync,
                "_parse_assign_users",
            ) as parse_assign_users,
            patch.object(
                assign_sync,
                "_ensure_open_todo",
            ) as ensure_open_todo,
        ):
            assign_sync.sync_ticket_assignments(doc)

        open_todos.assert_called_once_with("TEST-ACTIVE")
        is_partner_fulfilment.assert_called_once_with(doc)

        close_todo.assert_not_called()
        enforce_partner_assignment.assert_not_called()
        parse_assign_users.assert_not_called()
        ensure_open_todo.assert_not_called()

        mirror_assign.assert_called_once_with(
            "TEST-ACTIVE",
            ["owner@example.com"],
        )
