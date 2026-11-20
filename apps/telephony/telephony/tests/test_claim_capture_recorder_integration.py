"""Claim-only integration with real recorder/writers and an isolated SQL store.

Tests simulate conditional-update contention, not live MariaDB concurrency.
"""
import ast
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from telephony import time_booking_assignment_capture as capture
from telephony import time_booking_assignment_history as history
from telephony.tests.test_assignment_capture_recorder import MemoryDB
from telephony.tests import test_assignment_capture_recorder as recorder_fixture


class ClaimDB(MemoryDB):
    def __init__(self):
        super().__init__()
        self.assignments = dict(ticket=dict(name="T", status="Open", agent_group="Team",
            custom_fulfilment_party="Telectro", _assign=""), todos=[], comments=[], outbox=[])
        self.rowcount = 0
        self.contested = False
        self.member = True
        self.locked = False
        self.events = []
        self.notification_schema = True
        self.expect_capture = True
        self.finish_transaction()

    def table_exists(self, doctype, **kwargs):
        if doctype == "TELECTRO Task Notification Intent":
            return self.notification_schema
        return super().table_exists(doctype, **kwargs)

    def get_value(self, doctype, name, fields, **kwargs):
        if doctype == "HD Ticket":
            assert self.locked, "authoritative ticket read before lock"
            row = self.assignments["ticket"]
            return {f: row.get(f) for f in fields} if type(fields) is list else row.get(fields)
        return super().get_value(doctype, name, fields, **kwargs)

    def exists(self, doctype, filters):
        if doctype == "ToDo":
            return any(t["status"] == "Open" for t in self.assignments["todos"])
        if doctype == "HD Team":
            return filters == "Team"
        if doctype == "HD Team Member":
            return self.member
        raise AssertionError(doctype)

    def sql(self, query, value=None, **kwargs):
        self.events.append(query)
        ticket = self.assignments["ticket"]
        if query.lstrip().startswith("UPDATE `tabHD Ticket`"):
            if len(value) == 5:
                assign, name, group, privileged, user = value
                self.rowcount = int(not self.contested and ticket["_assign"] in ("", "[]")
                    and ticket["status"] == "Open" and ticket["agent_group"] == group
                    and ticket["custom_fulfilment_party"] == "Telectro"
                    and not self.exists("ToDo", {}) and (privileged or self.member))
                if self.rowcount:
                    ticket["_assign"] = assign
            else:
                ticket["_assign"] = value[0]
            return []
        if "ROW_COUNT()" in query:
            return [[self.rowcount]]
        if "SELECT name, allocated_to FROM `tabToDo`" in query:
            assert self.locked and "FOR UPDATE" in query
            return [copy.deepcopy(t) for t in self.assignments["todos"] if t["status"] == "Open"]
        if "SELECT name, _assign FROM `tabHD Ticket`" in query:
            assert self.locked and "FOR UPDATE" in query
            return [copy.deepcopy(ticket)]
        if "SELECT name FROM `tabHD Ticket`" in query:
            self.locked = True
        return super().sql(query, value, **kwargs)

    def set_value(self, doctype, name, field, value, **kwargs):
        assert doctype == "ToDo"
        next(t for t in self.assignments["todos"] if t["name"] == name)[field] = value

    def commit(self):
        if self.expect_capture:
            assert len(self.history) == len(self.receipts) == 1
            assert len(self.assignments["comments"]) == len(self.assignments["outbox"]) == 1
            assert capture._operation.get() is None
        self.commits += 1
        self.events.append("COMMIT")
        self.finish_transaction()


class TestClaimCaptureRecorderIntegration(unittest.TestCase):
    def setUp(self):
        # Fixture reuse only: the accepted recorder component tests are not rerun.
        self.fixture = recorder_fixture.TestAssignmentCaptureRecorder()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.db = ClaimDB()
        self.fixture.db = self.db
        self.f = self.fixture.f
        self.f.db = self.f.local.db = self.db
        self.f.conf = {"telectro_assignment_history_capture": 1}
        self.f.session.user = "tech-a"
        self.f.get_roles = lambda user: ["TELECTRO-POC Role - Tech"]
        self.f.has_permission = lambda *args, **kwargs: True
        self.f.get_all = lambda doctype, **kwargs: [copy.deepcopy(t)
            for t in self.db.assignments["todos"] if t["status"] == "Open"]
        original_get_doc = self.fixture.get_doc
        test = self
        class AssignmentDoc(dict):
            def insert(self, **kwargs):
                if self["doctype"] == test.fixture.fail_doctype:
                    raise RuntimeError("simulated insert failure")
                key = "todos" if self["doctype"] == "ToDo" else "comments"
                self["name"] = kwargs.get("set_name") or key + str(len(test.db.assignments[key]) + 1)
                if any(d["name"] == self["name"] for d in test.db.assignments[key]):
                    raise test.f.UniqueValidationError("duplicate Comment")
                test.db.assignments[key].append(copy.deepcopy(dict(self)))
                return self
            @property
            def name(self):
                return self.get("name")
        def get_doc(*args):
            if type(args[0]) is dict and args[0]["doctype"] in ("ToDo", "Comment"):
                return AssignmentDoc(args[0])
            return original_get_doc(*args)
        self.f.get_doc = get_doc
        def outbox(**values):
            self.db.assignments["outbox"].append(values)
        wanted = {"_assignment_history_capture_enabled", "_require_claim_authorization",
            "_normalize_assignment", "_atomic_claim", "_claim_with_assignment_capture",
            "telectro_claim_ticket", "_ClaimCaptureRejected"}
        path = Path(__file__).resolve().parents[1] / "telectro_claim.py"
        nodes = []
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted:
                node.decorator_list = []
                nodes.append(node)
        self.ns = dict(frappe=self.f, json=json, now_datetime=lambda: self.fixture.at,
                       capture_verified_task_ownership_transition=outbox)
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(path), "exec"), self.ns)
        self.claim = self.ns["telectro_claim_ticket"]

    def assert_no_effects(self, allow_history=False):
        self.assertEqual(self.db.assignments["ticket"]["_assign"], "")
        for key in ("todos", "comments", "outbox"):
            self.assertEqual(self.db.assignments[key], [])
        self.assertEqual(self.db.receipts, [])
        if not allow_history:
            self.assertEqual(self.db.history, [])
        self.assertEqual(self.db.commits, 0)

    def test_success_from_true_pool(self):
        self.assertEqual(self.claim("T"), {"ok": 1, "ticket": "T", "assigned_to": "tech-a"})
        state = self.db.assignments
        self.assertEqual(state["ticket"]["_assign"], '["tech-a"]')
        self.assertEqual(len(state["todos"]), 1)
        self.assertEqual(state["todos"][0]["allocated_to"], "tech-a")
        self.assertEqual(state["todos"][0]["status"], "Open")
        self.assertEqual((len(self.db.history), len(self.db.receipts)), (1, 1))
        self.assertEqual(self.db.history[0]["effective_start"], self.fixture.at)
        self.assertIsNone(json.loads(self.db.receipts[0]["previous_owner"]))
        self.assertEqual(self.db.commits, 1)

    def test_random_identity_shared_with_comment_history_and_outbox(self):
        self.claim("T")
        event = self.db.receipts[0]["event_id"]
        self.assertEqual(len(event), 32)
        int(event, 16)
        self.assertEqual(event, self.db.history[0]["start_event_id"])
        self.assertEqual(event, self.db.assignments["comments"][0]["name"])
        self.assertEqual(event, self.db.assignments["outbox"][0]["event_id"])
        self.assertEqual(self.db.assignments["comments"][0]["content"], "Claim | Assigned via TELECTRO pilot action")

    def test_repeated_http_claim_does_not_duplicate(self):
        self.claim("T")
        before = copy.deepcopy((self.db.history, self.db.receipts, self.db.assignments))
        self.assertEqual(self.claim("T"), {"ok": 0, "reason": "not_authorized"})
        self.assertEqual((self.db.history, self.db.receipts, self.db.assignments), before)
        self.assertEqual(self.db.commits, 1)

    def test_exact_internal_retry_skips_claim_mutation(self):
        self.claim("T")
        receipt = self.db.receipts[0]
        before = copy.deepcopy((self.db.history, self.db.receipts, self.db.assignments))
        with capture._assignment_capture_operation(ticket="T", authorize=lambda t, a: True) as operation:
            result = capture._record_assignment_history(operation, event_id=receipt["event_id"],
                source="Claim", reason="Claim", at=receipt["event_at"],
                request_payload=json.loads(receipt["request_payload"])["request"],
                resolve_transition=Mock(side_effect=AssertionError("must not mutate")))
        self.assertEqual(result["receipt"], receipt["name"])
        self.assertEqual((self.db.history, self.db.receipts, self.db.assignments), before)

    def test_internal_event_changed_request_is_rejected(self):
        self.claim("T")
        receipt = self.db.receipts[0]
        before = copy.deepcopy((self.db.history, self.db.receipts, self.db.assignments))
        with self.assertRaises(history.AssignmentHistoryError):
            with capture._assignment_capture_operation(ticket="T", authorize=lambda t, a: True) as operation:
                capture._record_assignment_history(operation, event_id=receipt["event_id"],
                    source="Claim", reason="Claim", at=receipt["event_at"],
                    request_payload={"action": "claim", "ticket": "T", "recipient": "tech-b"},
                    resolve_transition=Mock(side_effect=AssertionError("must not mutate")))
        self.assertEqual((self.db.history, self.db.receipts, self.db.assignments), before)

    def test_contested_atomic_update_creates_no_authority(self):
        self.db.contested = True
        self.assertEqual(self.claim("T")["reason"], "already_claimed")
        self.assert_no_effects()

    def test_second_claimant_is_denied(self):
        self.claim("T")
        self.f.session.user = "tech-b"
        self.assertEqual(self.claim("T")["ok"], 0)
        self.assertEqual(self.db.assignments["ticket"]["_assign"], '["tech-a"]')
        self.assertEqual((len(self.db.history), len(self.db.receipts)), (1, 1))

    def test_open_todo_blocks_despite_empty_mirror(self):
        self.db.assignments["todos"] = [dict(name="OTHER", allocated_to="tech-b", status="Open")]
        self.db.finish_transaction()
        self.assertEqual(self.claim("T")["reason"], "not_authorized")
        self.assertEqual(self.db.history, [])

    def test_mirror_only_or_malformed_state_is_not_baselined(self):
        for mirror in ('["tech-b"]', "bad-json"):
            self.db.assignments["ticket"]["_assign"] = mirror
            self.db.finish_transaction()
            self.assertEqual(self.claim("T")["reason"], "already_claimed")
            self.assertEqual(self.db.history, [])
            self.assertEqual(self.db.receipts, [])

    def test_conflicting_active_history_rolls_back(self):
        self.db.history.append(dict(name="OLD", ticket="T", technician_user="tech-b", employee="EMP-B",
            company="Company", state="Active", active_key=history._active_key("T", "tech-b"),
            effective_start=self.fixture.at, recorded_start=self.fixture.at, start_event_id="old"))
        self.db.finish_transaction()
        with self.assertRaises(history.AssignmentHistoryError):
            self.claim("T")
        self.assert_no_effects(allow_history=True)
        self.assertEqual(len(self.db.history), 1)

    def test_receipt_history_comment_failures_roll_back(self):
        for doctype in (capture.RECEIPT, history.DOCTYPE, "Comment"):
            with self.subTest(doctype=doctype):
                self.fixture.fail_doctype = doctype
                with self.assertRaises(RuntimeError):
                    self.claim("T")
                self.assert_no_effects()

    def test_outbox_exception_rolls_back(self):
        self.ns["capture_verified_task_ownership_transition"] = Mock(side_effect=RuntimeError("outbox"))
        with self.assertRaises(RuntimeError):
            self.claim("T")
        self.assert_no_effects()

    def test_safe_outbox_failure_result_preserves_behavior(self):
        self.ns["capture_verified_task_ownership_transition"] = Mock(return_value={"ok": False, "error": "safe"})
        self.db.expect_capture = False
        self.assertEqual(self.claim("T")["ok"], 1)
        self.assertEqual(len(self.db.receipts), 1)

    def test_missing_receipt_schema_denied_before_mutation(self):
        original = self.db.table_exists
        self.db.table_exists = lambda doctype, **kw: doctype != capture.RECEIPT and original(doctype, **kw)
        with self.assertRaises(history.AssignmentHistoryError):
            self.claim("T")
        self.assert_no_effects()

    def test_missing_notification_schema_preserves_response(self):
        self.db.notification_schema = False
        self.assertEqual(self.claim("T"), {"ok": 0, "ticket": "T", "reason": "notification_schema_unavailable"})
        self.assert_no_effects()

    def test_authorization_rechecked_under_lock(self):
        self.db.member = False
        self.assertEqual(self.claim("T"), {"ok": 0, "reason": "not_authorized"})
        self.assertTrue(self.db.locked)
        self.assert_no_effects()
        self.db.member = True
        self.f.has_permission = lambda *a, **kw: False
        self.assertEqual(self.claim("T")["reason"], "not_authorized")
        self.assert_no_effects()

    def test_lock_first_and_only_one_final_commit(self):
        self.claim("T")
        self.assertIn("SELECT name FROM `tabHD Ticket`", self.db.events[0])
        self.assertEqual(self.db.events[-1], "COMMIT")
        self.assertEqual(self.db.events.count("COMMIT"), 1)

    def test_capture_disabled_compatibility(self):
        self.f.conf.clear()
        self.db.expect_capture = False
        self.db.locked = True  # The legacy branch uses the SQL predicate, no explicit lock.
        self.assertEqual(self.claim("T")["ok"], 1)
        self.assertEqual(self.db.history, [])
        self.assertEqual(self.db.receipts, [])
        self.assertFalse(any("Capture Receipt" in q for q in self.db.events))
        self.assertEqual(len(self.db.assignments["comments"]), 1)
        self.assertEqual(self.db.commits, 1)

    def test_bad_canonical_post_state_rolls_back(self):
        normalize = self.ns["_normalize_assignment"]
        def corrupt(*args, **kwargs):
            result = normalize(*args, **kwargs)
            self.db.assignments["todos"].append(dict(name="EXTRA", allocated_to="tech-b", status="Open"))
            return result
        self.ns["_normalize_assignment"] = corrupt
        with self.assertRaises(history.AssignmentHistoryError):
            self.claim("T")
        self.assert_no_effects()


if __name__ == "__main__":
    unittest.main()
