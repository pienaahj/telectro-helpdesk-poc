import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from telephony.time_booking_cooption import BookingCooptionError


class Ticket(dict):
    def check_permission(self, permission):
        if not self.get("visible", True):
            raise PermissionError()


class TestListing(unittest.TestCase):
    def setUp(self):
        self.ticket = Ticket(name="T", _assign='["assignee"]')
        self.rows = [
            dict(name="G1", technician_user="worker1", employee="E1", granted_by="issuer"),
            dict(name="G2", technician_user="worker2", employee="E2", granted_by="other"),
        ]
        self.f = types.ModuleType("frappe")
        self.f.whitelist = lambda: lambda fn: fn
        self.f.session = types.SimpleNamespace(user="issuer")
        self.f.PermissionError = PermissionError
        self.f.get_roles = lambda user: []
        self.f.get_doc = Mock(return_value=self.ticket)
        self.f.db = types.SimpleNamespace(sql=Mock(return_value=self.rows))
        utils = types.ModuleType("frappe.utils")
        utils.cint = int
        utils.pretty_date = lambda x: x
        utils.strip_html = lambda x: x
        self.f.utils = utils
        self.f._ = lambda x: x
        modules = patch.dict(sys.modules, {"frappe": self.f, "frappe.utils": utils})
        modules.start(); self.addCleanup(modules.stop)
        spec = importlib.util.spec_from_file_location("workspace_listing_test", Path(__file__).resolve().parents[1] / "api/workspace.py")
        self.m = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.m)
        lock = patch("telephony.time_booking_cooption._lock_ticket")
        self.lock = lock.start(); self.addCleanup(lock.stop)

    def test_issuer_sees_only_own_active_grant(self):
        self.assertEqual(self.m.list_revocable_ticket_worker_grants("T"), [
            dict(grant_name="G1", technician_user="worker1", employee="E1")])
        self.f.get_doc.assert_called_once_with("HD Ticket", "T", for_update=True)
        query = self.f.db.sql.call_args.args[0]
        self.assertIn("state = 'Active'", query)
        self.assertIn("FOR UPDATE", query)

    def test_assignee_sees_both(self):
        self.f.session.user = "assignee"
        self.assertEqual(len(self.m.list_revocable_ticket_worker_grants("T")), 2)

    def test_governance_sees_both(self):
        self.f.session.user = "governor"
        self.f.get_roles = lambda user: ["System Manager"]
        self.assertEqual(len(self.m.list_revocable_ticket_worker_grants("T")), 2)

    def test_unrelated_actor_sees_nothing(self):
        self.f.session.user = "other-actor"
        self.assertEqual(self.m.list_revocable_ticket_worker_grants("T"), [])

    def test_visibility_denial_is_generic(self):
        self.ticket["visible"] = False
        with self.assertRaises(BookingCooptionError):
            self.m.list_revocable_ticket_worker_grants("T")
        self.f.db.sql.assert_not_called()

    def test_guest_and_malformed_ticket_fail_before_read(self):
        for user, ticket in (("Guest", "T"), ("issuer", ""), ("issuer", 1)):
            self.f.session.user = user
            with self.assertRaises(BookingCooptionError):
                self.m.list_revocable_ticket_worker_grants(ticket)
        self.f.get_doc.assert_not_called()
