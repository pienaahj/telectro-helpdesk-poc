"""Isolated claim/release/handoff capture and rollback tests."""

import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class TestClaimHistoryIntegration(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / "telectro_claim.py"
        tree = ast.parse(source.read_text())
        wanted = {"_assignment_history_capture_enabled", "telectro_claim_ticket",
                  "telectro_release_ticket", "telectro_handoff_ticket"}
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in wanted:
                node.decorator_list = []
                functions.append(node)
        module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
        self.ns = {"json": __import__("json")}
        exec(compile(module, str(source), "exec"), self.ns)
        self.f = types.ModuleType("frappe")
        self.f.conf = {"telectro_assignment_history_capture": 1}
        self.f.session = types.SimpleNamespace(user="tech")
        self.f.db = types.SimpleNamespace(
            table_exists=Mock(return_value=True), sql=Mock(side_effect=self.sql),
            get_value=Mock(side_effect=self.get_value), exists=Mock(return_value=True),
            commit=Mock(), rollback=Mock(),
        )
        self.f.get_doc = Mock(return_value=types.SimpleNamespace(status="Open", get=lambda k: "Telectro" if k == "custom_fulfilment_party" else "subject"))
        self.f.utils = types.SimpleNamespace(now_datetime=lambda: "2026-11-17 12:00:00")
        p = patch.dict(sys.modules, {"frappe": self.f, "frappe.utils": self.f.utils})
        p.start(); self.addCleanup(p.stop)
        self.ns["frappe"] = self.f
        self.ns.update(
            _require_claim_authorization=Mock(return_value={"agent_group": "team", "privileged": False}),
            _normalize_assignment=Mock(return_value="COMMENT-1"),
            _normalize_to_pool=Mock(return_value="COMMENT-2"),
            _first_assignee=lambda raw: "tech" if raw == '["tech"]' else None,
            _history_active_episode=Mock(return_value="EP-1"),
            _record_assignment_start=Mock(), _record_assignment_end=Mock(),
            capture_verified_task_ownership_transition=Mock(),
            _is_operational_intervention_user=Mock(return_value=True),
            _insert_handoff_audit_log=Mock(), _notify_controlled_handoff_receiver=Mock(),
        )
        history = types.ModuleType("telephony.time_booking_assignment_history")
        history._lock_ticket = Mock()
        p2 = patch.dict(sys.modules, {"telephony.time_booking_assignment_history": history})
        p2.start(); self.addCleanup(p2.stop)
        self.lock = history._lock_ticket
        self.assign = '["tech"]'
        self.claimed = True

    def sql(self, query, *args, **kwargs):
        if "ROW_COUNT" in query:
            return [[1 if self.claimed else 0]]
        return []

    def get_value(self, doctype, name, field, **kwargs):
        if doctype == "User":
            return types.SimpleNamespace(name=name, enabled=1)
        return self.assign

    def test_gate_is_off_by_default_and_requires_schema_when_enabled(self):
        self.f.conf.clear()
        self.assertFalse(self.ns["_assignment_history_capture_enabled"]())
        self.f.db.table_exists.assert_not_called()
        self.f.conf["telectro_assignment_history_capture"] = 1
        self.f.db.table_exists.return_value = False
        with self.assertRaises(RuntimeError): self.ns["_assignment_history_capture_enabled"]()

    def test_claim_starts_episode_after_confirmed_claim(self):
        self.assertEqual(self.ns["telectro_claim_ticket"]("T")["ok"], 1)
        self.lock.assert_called_once_with("T")
        self.ns["_record_assignment_start"].assert_called_once_with(
            "T", "tech", "tech", "Claim", "Claim", "COMMENT-1", "2026-11-17 12:00:00")
        self.f.db.commit.assert_called_once()

    def test_unclaimed_request_does_not_write_history(self):
        self.claimed = False
        self.ns["telectro_claim_ticket"]("T")
        self.ns["_record_assignment_start"].assert_not_called()

    def test_claim_capture_failure_rolls_back_without_commit(self):
        self.ns["_record_assignment_start"].side_effect = RuntimeError("history")
        with self.assertRaises(RuntimeError): self.ns["telectro_claim_ticket"]("T")
        self.f.db.rollback.assert_called_once(); self.f.db.commit.assert_not_called()

    def test_release_ends_exact_episode(self):
        self.ns["telectro_release_ticket"]("T", "done")
        self.lock.assert_called_once_with("T")
        self.ns["_record_assignment_end"].assert_called_once_with(
            "T", "tech", "EP-1", "tech", "Release", "done", "COMMENT-2", "2026-11-17 12:00:00")
        self.f.db.commit.assert_called_once()

    def test_release_capture_failure_rolls_back(self):
        self.ns["_record_assignment_end"].side_effect = RuntimeError("history")
        with self.assertRaises(RuntimeError): self.ns["telectro_release_ticket"]("T", "done")
        self.f.db.rollback.assert_called_once(); self.f.db.commit.assert_not_called()

    def test_handoff_ends_and_starts_at_same_timestamp(self):
        self.ns["telectro_handoff_ticket"]("T", "other", "transfer")
        self.lock.assert_called_once_with("T")
        self.ns["_record_assignment_end"].assert_called_once_with(
            "T", "tech", "EP-1", "tech", "Controlled Handoff", "transfer", "COMMENT-1", "2026-11-17 12:00:00")
        self.ns["_record_assignment_start"].assert_called_once_with(
            "T", "other", "tech", "Controlled Handoff", "transfer", "COMMENT-1", "2026-11-17 12:00:00")
        self.f.db.commit.assert_called_once()

    def test_handoff_start_or_notification_failure_rolls_back(self):
        for name in ("_record_assignment_start", "_notify_controlled_handoff_receiver"):
            with self.subTest(name=name):
                self.ns[name].side_effect = RuntimeError("failure")
                with self.assertRaises(RuntimeError): self.ns["telectro_handoff_ticket"]("T", "other", "transfer")
                self.f.db.rollback.assert_called()
                self.f.db.commit.assert_not_called()
                self.ns[name].side_effect = None
                self.f.db.rollback.reset_mock()

    def test_disabled_capture_keeps_existing_transition_commit(self):
        self.f.conf.clear()
        self.ns["telectro_claim_ticket"]("T")
        self.ns["telectro_release_ticket"]("T", "done")
        self.ns["telectro_handoff_ticket"]("T", "other", "transfer")
        self.lock.assert_not_called()
        self.ns["_record_assignment_start"].assert_not_called()
        self.ns["_record_assignment_end"].assert_not_called()
        self.assertEqual(self.f.db.commit.call_count, 3)


if __name__ == "__main__": unittest.main()
