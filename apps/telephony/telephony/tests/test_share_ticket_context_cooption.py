"""Isolated tests of the trusted Share Ticket Context co-option boundary."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from telephony.time_booking_cooption import BookingCooptionError


class Doc(dict):
    def __getattr__(self, key):
        return self.get(key)


class TestShareContextCooption(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.effects = []
        self.user = "issuer@example.com"
        self.roles = ["TELECTRO-POC Role - Tech"]
        self.ticket = Doc(name="HD-001", status="Open", _assign='["issuer@example.com"]')
        self.ticket.check_permission = self.check_permission
        self.collaborator = Doc(name="worker@example.com", full_name="Worker")
        self.current = self.ticket
        self.db = types.SimpleNamespace(
            exists=lambda *args: True,
            get_value=lambda *args: self.ticket["_assign"],
            rollback=self.rollback,
        )
        self.frappe = types.ModuleType("frappe")
        self.frappe.db = self.db
        self.frappe.session = types.SimpleNamespace(user=self.user)
        self.frappe.local = types.SimpleNamespace(request=types.SimpleNamespace(method="POST"))
        self.frappe.get_roles = lambda user: self.roles
        self.frappe.whitelist = lambda **kwargs: lambda fn: fn
        self.frappe.get_doc = self.get_doc
        self.frappe.throw = self.throw
        self.frappe.ValidationError = ValueError
        self.frappe.PermissionError = PermissionError
        self.frappe._ = lambda value: value
        utils = types.ModuleType("frappe.utils")
        utils.cint = lambda v: int(v or 0)
        utils.pretty_date = lambda v: v
        utils.strip_html = lambda v: v
        utils.escape_html = lambda v: v
        self.frappe.utils = utils
        privacy = types.ModuleType("telephony.customer_communication_privacy")
        privacy.classify_actor_roles = lambda roles: (
            "unknown" if "TELECTRO-POC Role - Partner" in roles else "internal"
        )
        modules = patch.dict(sys.modules, {
            "frappe": self.frappe, "frappe.utils": utils,
            "telephony.customer_communication_privacy": privacy,
        })
        modules.start()
        self.addCleanup(modules.stop)
        path = Path(__file__).resolve().parents[1] / "api/workspace.py"
        spec = importlib.util.spec_from_file_location("_workspace_cooption_test", path)
        self.workspace = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.workspace)
        for name, callback in {
            "_get_context_share_collaborator": lambda user: self.collaborator,
            "_build_ticket_context_share_comment": lambda **kwargs: "Shared context",
            "_share_ticket_read_access": lambda **kwargs: self.effect("DocShare"),
            "_create_ticket_context_share_notification": lambda **kwargs: self.effect("Notification"),
        }.items():
            patcher = patch.object(self.workspace, name, side_effect=callback)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.grant = patch("telephony.time_booking_cooption._grant_after_authorization", side_effect=self.grant_worker)
        self.grant_mock = self.grant.start()
        self.addCleanup(self.grant.stop)

    def throw(self, message, error=ValueError):
        raise error(message)

    def check_permission(self, permission):
        self.events.append(("permission", permission))

    def effect(self, kind):
        self.effects.append(kind)
        return kind + "-001"

    def rollback(self):
        self.events.append("rollback")
        self.effects.clear()

    def grant_worker(self, **kwargs):
        self.events.append(("grant", kwargs))
        return self.effect("Grant")

    def get_doc(self, *args, **kwargs):
        if args[0] == "HD Ticket":
            self.events.append(("ticket", kwargs.get("for_update")))
            # A locking read must refresh stale assignment/status before policy.
            if kwargs.get("for_update"):
                self.ticket = self.current
            return self.ticket
        values = args[0]
        self.assertEqual(values["doctype"], "Comment")
        self.comment = values
        return types.SimpleNamespace(insert=lambda **kw: self.effect("Comment"))

    def call(self, **kwargs):
        return self.workspace.share_ticket_context("HD-001", "worker@example.com", "Help on site", **kwargs)

    def test_omitted_and_false_preserve_legacy_share_response_and_effects(self):
        for kwargs in ({}, {"coopt_as_worker": False}, {"coopt_as_worker": "false"}):
            with self.subTest(kwargs=kwargs):
                self.effects.clear()
                self.frappe.local.request.method = "GET"
                result = self.call(**kwargs)
                self.assertEqual(self.effects, ["Comment", "DocShare", "Notification"])
                self.assertNotIn("worker_grant", result)
                self.assertNotIn("co-opted", self.comment["content"])
                self.grant_mock.assert_not_called()
                self.assertEqual(self.events[-1], ("ticket", False))

    def test_strict_boolean_rejects_malformed_values_without_effects(self):
        for value in (None, 0, 1, 2, "0", "1", "", "yes", "TRUE", " true ", [], {}, 1.0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.call(coopt_as_worker=value)
                self.assertEqual(self.effects, [])
        self.grant_mock.assert_not_called()

    def test_checked_requires_authenticated_post(self):
        for user, method in (("Guest", "POST"), ("", "POST"), (None, "POST"), (self.user, "GET"), (self.user, "PUT")):
            with self.subTest(user=user, method=method):
                self.frappe.session.user = user
                self.frappe.local.request.method = method
                with self.assertRaises(PermissionError):
                    self.call(coopt_as_worker=True)
                self.assertEqual(self.effects, [])
        self.grant_mock.assert_not_called()

    def test_checked_assignee_grants_and_shares_without_assignment_change(self):
        before = self.ticket["_assign"]
        result = self.call(coopt_as_worker="true")
        self.assertEqual(result["worker_grant"], "Grant-001")
        self.assertEqual(self.effects, ["Grant", "Comment", "DocShare", "Notification"])
        self.assertEqual(self.ticket["_assign"], before)
        self.assertEqual(self.events[:2], [("ticket", True), ("permission", "read")])
        self.grant_mock.assert_called_once_with(ticket="HD-001", user="worker@example.com", issuer=self.user, reason="Help on site")
        self.assertIn("explicitly co-opted", self.comment["content"])

    def test_governance_can_coopt_unassigned_ticket(self):
        self.roles = ["TELECTRO-POC Role - Supervisor Governance"]
        self.ticket["_assign"] = "[]"
        self.call(coopt_as_worker=True)
        self.grant_mock.assert_called_once()

    def test_unassigned_ordinary_internal_user_is_denied(self):
        self.ticket["_assign"] = "[]"
        with self.assertRaises(PermissionError):
            self.call(coopt_as_worker=True)
        self.assertEqual(self.effects, [])
        self.grant_mock.assert_not_called()

    def test_current_locked_assignment_overrules_stale_assignee(self):
        self.current = Doc(self.ticket)
        self.current.check_permission = self.check_permission
        self.current["_assign"] = '["other@example.com"]'
        with self.assertRaises(PermissionError):
            self.call(coopt_as_worker=True)
        self.grant_mock.assert_not_called()

    def test_terminal_status_is_rejected_from_current_locked_ticket(self):
        for status in ("Resolved", "Closed", "Archived"):
            with self.subTest(status=status):
                self.current = Doc(self.ticket)
                self.current.check_permission = self.check_permission
                self.current["status"] = status
                with self.assertRaises(ValueError):
                    self.call(coopt_as_worker=True)
                self.assertEqual(self.effects, [])
        self.grant_mock.assert_not_called()

    def test_partner_issuer_is_denied_even_when_assigned(self):
        self.roles.append("TELECTRO-POC Role - Partner")
        with self.assertRaises(PermissionError):
            self.call(coopt_as_worker=True)
        self.grant_mock.assert_not_called()

    def test_read_permission_is_separate_from_issuer_authority(self):
        self.ticket.check_permission = lambda permission: self.throw("No read", PermissionError)
        with self.assertRaises(PermissionError):
            self.call(coopt_as_worker=True)
        self.assertEqual(self.effects, [])
        self.grant_mock.assert_not_called()

    def test_ineligible_recipient_or_missing_schema_fails_closed(self):
        for error in (BookingCooptionError(), RuntimeError("DocType not installed")):
            with self.subTest(error=error):
                self.grant_mock.side_effect = error
                with self.assertRaises(type(error)):
                    self.call(coopt_as_worker=True)
                self.assertEqual(self.effects, [])
                self.assertEqual(self.events[-1], "rollback")

    def test_downstream_failure_rolls_back_grant_and_share_effects(self):
        with patch.object(self.workspace, "_create_ticket_context_share_notification", side_effect=RuntimeError("failure")):
            with self.assertRaises(RuntimeError):
                self.call(coopt_as_worker=True)
        self.assertEqual(self.effects, [])
        self.assertEqual(self.events[-1], "rollback")

    def test_assignment_guard_failure_rolls_back_grant_and_comment(self):
        self.db.get_value = lambda *args: '["unexpected@example.com"]'
        with self.assertRaises(ValueError):
            self.call(coopt_as_worker=True)
        self.assertEqual(self.effects, [])
        self.assertEqual(self.events[-1], "rollback")

    def test_blank_note_never_grants(self):
        with self.assertRaises(ValueError):
            self.workspace.share_ticket_context("HD-001", "worker@example.com", "  ", coopt_as_worker=True)
        self.grant_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
