"""No-site endpoint tests exercising the real private revocation foundation."""

import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from telephony.time_booking_cooption import BookingCooptionError, _active_key


class Grant:
    def __init__(self, row, saves):
        self.__dict__.update(copy.deepcopy(row))
        self._row = row
        self._saves = saves

    def save(self, **kwargs):
        self._saves.append((self.name, kwargs))
        self._row.update({k: v for k, v in vars(self).items() if not k.startswith("_")})


class TestTicketWorkerGrantRevocation(unittest.TestCase):
    def setUp(self):
        self.ticket = {"name": "HD-1", "_assign": '["assignee"]', "status": "Open"}
        self.rows = [self.episode("G-1", "worker")]
        self.saves = []
        self.queries = []
        self.on_lock = None
        self.roles = []
        self.f = types.ModuleType("frappe")
        self.f.whitelist = lambda **kwargs: lambda fn: fn
        self.f.session = types.SimpleNamespace(user="issuer")
        self.f.local = types.SimpleNamespace(request=types.SimpleNamespace(method="POST"))
        self.f.get_roles = lambda actor: self.roles
        self.f.get_doc = self.get_doc
        self.f.db = types.SimpleNamespace(sql=self.sql, commit=Mock(), rollback=Mock(),
                                         set_value=Mock(), delete=Mock())
        utils = types.ModuleType("frappe.utils")
        utils.now_datetime = lambda: "2026-11-17 14:00:00"
        utils.cint = int
        utils.pretty_date = lambda x: x
        utils.strip_html = lambda x: x
        self.f.utils = utils
        self.f._ = lambda x: x
        modules = patch.dict(sys.modules, {"frappe": self.f, "frappe.utils": utils})
        modules.start()
        self.addCleanup(modules.stop)
        path = Path(__file__).resolve().parents[1] / "api/workspace.py"
        spec = importlib.util.spec_from_file_location("_workspace_revocation_test", path)
        self.workspace = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.workspace)
        self.before = copy.deepcopy(self.rows)
        self.before_ticket = copy.deepcopy(self.ticket)

    def episode(self, name, user):
        return {"name": name, "ticket": "HD-1", "technician_user": user,
                "granted_by": "issuer", "reason": "help", "employee": "EMP-1",
                "company": "Company", "state": "Active", "revoked_at": None,
                "active_key": _active_key("HD-1", user)}

    def sql(self, query, value, **kwargs):
        self.assertIn("FOR UPDATE", query)
        self.assertTrue(kwargs["as_dict"])
        self.queries.append((query, value))
        if "tabHD Ticket" in query:
            if self.on_lock:
                callback, self.on_lock = self.on_lock, None
                callback()
            return [dict(self.ticket)] if self.ticket and self.ticket["name"] == value else []
        self.assertIn("tabTELECTRO Ticket Worker Grant", query)
        field = "active_key" if "WHERE active_key" in query else "name"
        return [dict(r) for r in self.rows if r.get(field) == value]

    def get_doc(self, doctype, name):
        self.assertEqual(doctype, "TELECTRO Ticket Worker Grant")
        return Grant(next(r for r in self.rows if r["name"] == name), self.saves)

    def call(self, ticket="HD-1", grant="G-1", reason="  finished  "):
        return self.workspace.revoke_ticket_worker_grant(ticket, grant, reason)

    def assert_denied(self, **kwargs):
        before = copy.deepcopy(self.rows)
        with self.assertRaises(BookingCooptionError) as caught:
            self.call(**kwargs)
        self.assertEqual(str(caught.exception), "Ticket worker grant is unavailable.")
        self.assertEqual(self.rows, before)
        self.assertEqual(self.saves, [])

    def test_issuer_revokes_exact_episode_and_retains_history(self):
        self.assertEqual(self.call(), {"ok": 1})
        row = self.rows[0]
        self.assertEqual(row["state"], "Revoked")
        self.assertIsNone(row["active_key"])
        self.assertEqual(row["revoked_by"], "issuer")
        self.assertEqual(row["revocation_reason"], "finished")
        self.assertEqual(row["revoked_at"], "2026-11-17 14:00:00")
        for key in ("name", "ticket", "technician_user", "granted_by", "reason", "employee", "company"):
            self.assertEqual(row[key], self.before[0][key])
        self.assertEqual(self.saves, [("G-1", {"ignore_permissions": True})])

    def test_current_assignee_can_revoke(self):
        self.f.session.user = "assignee"
        self.assertEqual(self.call(), {"ok": 1})

    def test_each_existing_governance_role_can_revoke(self):
        for role in self.workspace.SHARE_CONTEXT_ROLES:
            with self.subTest(role=role):
                self.rows = copy.deepcopy(self.before)
                self.f.session.user = "governance"
                self.roles = [role]
                self.assertEqual(self.call(), {"ok": 1})

    def test_unrelated_user_cannot_revoke(self):
        self.f.session.user = "other"
        self.assert_denied()

    def test_worker_is_not_authorized_by_receiving_grant(self):
        self.f.session.user = "worker"
        self.assert_denied()

    def test_missing_ticket_and_episode_and_wrong_ticket_are_generic(self):
        for args in ({"ticket": "secret"}, {"grant": "secret"}):
            with self.subTest(args=args):
                self.assert_denied(**args)
        self.rows[0]["ticket"] = "other"
        self.assert_denied()

    def test_authentication_required_before_database_access(self):
        for actor in ("Guest", "", " ", None, 1, []):
            with self.subTest(actor=actor):
                self.f.session.user = actor
                self.assert_denied()
                self.assertEqual(self.queries, [])

    def test_post_required_even_for_direct_python_callers(self):
        for method in ("GET", "PUT", "DELETE", None):
            with self.subTest(method=method):
                self.f.local.request.method = method
                self.assert_denied()
                self.assertEqual(self.queries, [])
        self.f.local.request = None
        self.assert_denied()

    def test_strict_identifiers_and_required_reason(self):
        for field in ("ticket", "grant", "reason"):
            for value in (None, "", " ", 1, True, [], {}):
                with self.subTest(field=field, value=value):
                    self.assert_denied(**{field: value})
                    self.assertEqual(self.queries, [])

    def test_resolved_closed_archived_tickets_can_be_revoked(self):
        for status in ("Resolved", "Closed", "Archived"):
            with self.subTest(status=status):
                self.rows = copy.deepcopy(self.before)
                self.ticket["status"] = status
                self.assertEqual(self.call(), {"ok": 1})

    def test_duplicate_revocation_fails_closed_without_rewriting_audit(self):
        self.call()
        revoked = copy.deepcopy(self.rows)
        self.saves.clear()
        self.assert_denied()
        self.assertEqual(self.rows, revoked)

    def test_stale_request_never_revokes_later_regrant(self):
        self.call()
        self.rows.append(self.episode("G-2", "worker"))
        self.saves.clear()
        self.assert_denied()
        self.assertEqual(self.rows[1]["state"], "Active")

    def test_concurrent_revocation_observed_after_ticket_lock(self):
        def committed_revoke():
            self.rows[0].update(state="Revoked", active_key=None, revoked_at="earlier")
        self.on_lock = committed_revoke
        with self.assertRaises(BookingCooptionError):
            self.call()
        self.assertEqual(self.saves, [])
        self.assertEqual(self.rows[0]["revoked_at"], "earlier")

    def test_concurrent_regrant_observed_after_ticket_lock(self):
        def committed_regrant():
            self.rows[0].update(state="Revoked", active_key=None, revoked_at="earlier")
            self.rows.append(self.episode("G-2", "worker"))
        self.on_lock = committed_regrant
        with self.assertRaises(BookingCooptionError):
            self.call()
        self.assertEqual(self.saves, [])
        self.assertEqual(self.rows[1]["state"], "Active")

    def test_current_assignment_used_after_ticket_lock(self):
        self.f.session.user = "assignee"
        self.on_lock = lambda: self.ticket.update(_assign='["new-assignee"]')
        self.assert_denied()

    def test_current_issuer_used_from_exact_persisted_episode(self):
        self.rows[0]["granted_by"] = "other"
        self.assert_denied()

    def test_inconsistent_or_colliding_active_rows_fail_closed(self):
        for field, value in (("state", "Revoked"), ("revoked_at", "earlier")):
            with self.subTest(field=field):
                self.rows = copy.deepcopy(self.before)
                self.rows[0][field] = value
                self.assert_denied()
        self.rows = copy.deepcopy(self.before) + [self.episode("G-2", "worker")]
        self.assert_denied()

    def test_other_grants_assignment_and_transaction_ownership_preserved(self):
        self.rows.append(self.episode("OTHER", "other-worker"))
        other = copy.deepcopy(self.rows[1])
        self.call()
        self.assertEqual(self.rows[1], other)
        self.assertEqual(self.ticket, self.before_ticket)
        for name in ("commit", "rollback", "set_value", "delete"):
            getattr(self.f.db, name).assert_not_called()
        self.assertIn("tabHD Ticket", self.queries[0][0])
        self.assertTrue(all("FOR UPDATE" in q for q, _ in self.queries))

    def test_save_failure_propagates_without_transaction_control(self):
        error = RuntimeError("save failed")
        with patch.object(Grant, "save", side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                self.call()
        self.assertIs(caught.exception, error)
        self.assertEqual(self.rows, self.before)
        self.f.db.rollback.assert_not_called()
        self.f.db.commit.assert_not_called()

    def test_database_failure_propagates(self):
        error = RuntimeError("database failed")
        self.f.db.sql = Mock(side_effect=error)
        with self.assertRaises(RuntimeError) as caught:
            self.call()
        self.assertIs(caught.exception, error)
        self.f.db.rollback.assert_not_called()
        self.f.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
