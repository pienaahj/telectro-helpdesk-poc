"""Isolated transaction-store tests; real writers/controllers, no site database."""

import copy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from telephony import time_booking_assignment_capture as capture
from telephony import time_booking_assignment_history as history
from telephony.time_booking_identity import TechnicianBookingIdentity


class MemoryDB:
    def __init__(self):
        self.history = []
        self.receipts = []
        self.assignments = {}
        self.queries = []
        self.rollbacks = 0
        self.commits = 0
        self.missing_schema = False
        self.finish_transaction()

    def finish_transaction(self):
        # Simulate a successful outer transaction, retaining durable rows.
        self.baseline = copy.deepcopy((self.history, self.receipts, self.assignments))

    def rollback(self):
        self.rollbacks += 1
        self.history, self.receipts, self.assignments = copy.deepcopy(self.baseline)

    def commit(self):
        self.commits += 1
        raise AssertionError("Recorder must never commit")

    def get_value(self, doctype, name, fields, **kwargs):
        return dict(enabled=1, user_type="System User")

    def table_exists(self, doctype, **kwargs):
        return not self.missing_schema

    def sql(self, query, value, **kwargs):
        self.queries.append((query, value))
        if "FOR UPDATE" not in query:
            raise AssertionError("Expected current locking read")
        if "tabHD Ticket" in query:
            return [dict(name=value)]
        if "tabTELECTRO Assignment Capture Receipt" in query:
            return copy.deepcopy([r for r in self.receipts if r["event_id"] == value])
        if "WHERE active_key" in query:
            rows = [r for r in self.history if r.get("active_key") == value]
        elif "WHERE start_event_id" in query:
            rows = [r for r in self.history if r.get("start_event_id") == value]
        elif "WHERE end_event_id" in query:
            rows = [r for r in self.history if r.get("end_event_id") == value]
        elif "WHERE ticket=" in query:
            rows = [r for r in self.history if r["ticket"] == value
                    and (r["state"] == "Active" or r.get("active_key") is not None)]
        else:
            raise AssertionError(query)
        return copy.deepcopy(rows)


class TestAssignmentCaptureRecorder(unittest.TestCase):
    def setUp(self):
        self.db = MemoryDB()
        self.a = TechnicianBookingIdentity("tech-a", "EMP-A", "Company")
        self.b = TechnicianBookingIdentity("tech-b", "EMP-B", "Company")
        self.c = TechnicianBookingIdentity("tech-c", "EMP-C", "Company")
        self.identities = {i.user: i for i in (self.a, self.b, self.c)}
        self.at = datetime(2026, 11, 19, 10, 0, 0, 123456)
        self.now = self.at + timedelta(seconds=1)
        self.fail_doctype = None
        self.insert_log = []
        f = types.ModuleType("frappe")
        self.f = f
        f.db = self.db
        f.local = types.SimpleNamespace(db=self.db)
        f.session = types.SimpleNamespace(user="supervisor")
        f.UniqueValidationError = type("UniqueValidationError", (Exception,), {})
        f.get_doc = self.get_doc
        utils = types.ModuleType("frappe.utils")
        utils.now_datetime = lambda: self.now
        test = self

        class Document(dict):
            def __init__(self, values):
                super().__init__(values)
                self._previous = None
            def __getattr__(self, key):
                return self.get(key)
            def __setattr__(self, key, value):
                if key.startswith("_"):
                    object.__setattr__(self, key, value)
                else:
                    self[key] = value
            def get_doc_before_save(self):
                return self._previous
            def insert(self, **kwargs):
                if self["doctype"] == test.fail_doctype:
                    raise RuntimeError("simulated insert failure")
                self.validate()
                rows = test.db.receipts if self["doctype"] == capture.RECEIPT else test.db.history
                self.name = ("R-" if rows is test.db.receipts else "EP-") + str(len(rows) + 1)
                rows.append(copy.deepcopy(dict(self)))
                test.insert_log.append(self["doctype"])
                return self
            def save(self, **kwargs):
                rows = test.db.receipts if self["doctype"] == capture.RECEIPT else test.db.history
                index = next(i for i, row in enumerate(rows) if row["name"] == self.name)
                self._previous = Document(copy.deepcopy(rows[index]))
                self.validate()
                rows[index] = copy.deepcopy(dict(self))
                return self
        model = types.ModuleType("frappe.model")
        document = types.ModuleType("frappe.model.document")
        document.Document = Document
        modules = patch.dict(sys.modules, {"frappe": f, "frappe.utils": utils,
                    "frappe.model": model, "frappe.model.document": document})
        modules.start()
        self.addCleanup(modules.stop)
        root = Path(__file__).resolve().parents[1] / "ftelephony/doctype"
        def controller(directory, name):
            path = root / directory / (directory + ".py")
            spec = importlib.util.spec_from_file_location("isolated_" + directory, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, name)
        self.Receipt = controller("telectro_assignment_capture_receipt", "TELECTROAssignmentCaptureReceipt")
        self.History = controller("telectro_ticket_assignment_history", "TELECTROTicketAssignmentHistory")
        for target in ("telephony.time_booking_assignment_history._require_recipient_identity",
                       "telephony.time_booking_cooption._require_recipient_identity"):
            identity = patch(target, side_effect=lambda user: self.identities[user])
            identity.start()
            self.addCleanup(identity.stop)

    def get_doc(self, *args):
        if type(args[0]) is dict:
            values = args[0]
        else:
            rows = self.db.receipts if args[0] == capture.RECEIPT else self.db.history
            values = copy.deepcopy(next(r for r in rows if r["name"] == args[1]))
        cls = self.Receipt if values["doctype"] == capture.RECEIPT else self.History
        return cls(values)

    def record(self, previous=None, new=None, **updates):
        args = dict(event_id="event", source="Controlled Handoff", reason="Work",
                    at=self.at, request_payload={"target": new.user if new else None},
                    resolve_transition=lambda: (previous, new, True))
        args.update(updates)
        with capture._assignment_capture_operation(ticket="T", authorize=lambda t, a: True) as operation:
            return capture._record_assignment_history(operation, **args)

    def seed(self):
        at = self.at - timedelta(hours=1)
        self.now = at + timedelta(seconds=1)
        result = self.record(new=self.a, event_id="seed", at=at)
        self.db.finish_transaction()
        self.now = self.at + timedelta(seconds=1)
        return result

    def test_initial_assignment_persists_receipt_and_history(self):
        result = self.record(new=self.a)
        self.assertEqual((len(self.db.history), len(self.db.receipts)), (1, 1))
        self.assertEqual(result, dict(receipt="R-1", end_episode=None, start_episode="EP-1", no_op=False))
        receipt = self.db.receipts[0]
        self.assertEqual(json.loads(receipt["previous_owner"]), None)
        self.assertEqual(json.loads(receipt["new_owner"])["employee"], "EMP-A")
        self.assertEqual(receipt["actor"], "supervisor")

    def test_handoff_preserves_exact_shared_timestamp(self):
        self.seed()
        result = self.record(self.a, self.b)
        self.assertEqual(result["end_episode"], "EP-1")
        self.assertEqual(result["start_episode"], "EP-2")
        self.assertEqual(self.db.history[0]["effective_end"], self.at)
        self.assertEqual(self.db.history[1]["effective_start"], self.at)
        self.assertEqual(self.db.history[1]["effective_start"].microsecond, 123456)

    def test_release_closes_episode(self):
        self.seed()
        self.record(self.a, None)
        self.assertEqual(self.db.history[0]["state"], "Closed")
        self.assertIsNone(self.db.history[0]["active_key"])
        self.assertEqual(len(self.db.history), 1)

    def test_same_owner_noop_is_durable(self):
        self.seed()
        before = copy.deepcopy(self.db.history)
        result = self.record(self.a, self.a)
        self.assertTrue(result["no_op"])
        self.assertEqual(self.db.history, before)
        self.assertEqual(len(self.db.receipts), 2)

    def test_noop_retry_across_transactions_does_not_resolve_current_state(self):
        self.seed()
        first = self.record(self.a, self.a)
        self.db.finish_transaction()
        resolver = Mock(side_effect=AssertionError("must not resolve current state"))
        self.assertEqual(first, self.record(self.a, self.a, resolve_transition=resolver))
        resolver.assert_not_called()
        self.assertEqual(len(self.db.receipts), 2)

    def test_transition_retry_across_transactions(self):
        self.seed()
        first = self.record(self.a, self.b)
        self.db.finish_transaction()
        before = copy.deepcopy((self.db.history, self.db.receipts))
        self.assertEqual(first, self.record(self.a, self.b,
            resolve_transition=Mock(side_effect=AssertionError("retry"))))
        self.assertEqual((self.db.history, self.db.receipts), before)

    def test_retry_after_independent_transition(self):
        self.seed()
        first = self.record(self.a, self.b)
        self.db.finish_transaction()
        later = self.at + timedelta(minutes=10)
        self.now = later + timedelta(seconds=1)
        self.record(self.b, self.c, event_id="later", at=later)
        self.db.finish_transaction()
        before = copy.deepcopy((self.db.history, self.db.receipts))
        self.assertEqual(first, self.record(self.a, self.b,
            resolve_transition=Mock(side_effect=AssertionError("retry"))))
        self.assertEqual((self.db.history, self.db.receipts), before)

    def test_changed_event_payload_rejected(self):
        self.record(new=self.a)
        self.db.finish_transaction()
        for changes in (dict(source="Other"), dict(reason="Other"),
                        dict(at=self.at + timedelta(microseconds=1)),
                        dict(request_payload={"target": "tech-b"})):
            with self.subTest(changes=changes), self.assertRaises(history.AssignmentHistoryError):
                self.record(new=self.a, **changes)
        self.assertEqual(len(self.db.receipts), 1)

    def test_changed_noop_payload_rejected(self):
        self.record()
        self.db.finish_transaction()
        with self.assertRaises(history.AssignmentHistoryError):
            self.record(request_payload={"different": True})

    def test_other_actor_cannot_retrieve_receipt(self):
        self.record(new=self.a)
        self.db.finish_transaction()
        self.f.session.user = "other"
        with self.assertRaises(history.AssignmentHistoryError):
            self.record(new=self.a)

    def test_missing_active_episode_rejected(self):
        with self.assertRaises(history.AssignmentHistoryError):
            self.record(self.a, None)
        self.assertEqual(self.db.receipts, [])

    def test_conflicting_episodes_rejected(self):
        self.seed()
        conflict = copy.deepcopy(self.db.history[0])
        conflict.update(name="conflict", technician_user="tech-b", employee="EMP-B",
                        active_key=history._active_key("T", "tech-b"))
        self.db.history.append(conflict)
        self.db.finish_transaction()
        with self.assertRaises(history.AssignmentHistoryError):
            self.record(self.a, self.b)

    def test_inconsistent_active_key_rejected(self):
        self.seed()
        self.db.history[0]["active_key"] = None
        self.db.finish_transaction()
        with self.assertRaises(history.AssignmentHistoryError):
            self.record(self.a, self.b)

    def test_handoff_insert_failure_rolls_back_history_and_assignment(self):
        self.seed()
        before = copy.deepcopy((self.db.history, self.db.receipts, self.db.assignments))
        self.fail_doctype = history.DOCTYPE
        with self.assertRaisesRegex(RuntimeError, "simulated"):
            with capture._assignment_capture_operation(ticket="T", authorize=lambda t, a: True) as operation:
                def transition():
                    self.db.assignments["T"] = "tech-b"
                    return self.a, self.b, True
                capture._record_assignment_history(operation, event_id="event", source="Handoff",
                    reason="Work", at=self.at, request_payload={"target": "tech-b"},
                    resolve_transition=transition)
        self.assertEqual((self.db.history, self.db.receipts, self.db.assignments), before)
        self.assertGreater(self.db.rollbacks, 0)

    def test_receipt_insert_failure_rolls_back_history(self):
        self.seed()
        before = copy.deepcopy(self.db.history)
        self.fail_doctype = capture.RECEIPT
        with self.assertRaises(RuntimeError):
            self.record(self.a, self.b)
        self.assertEqual(self.db.history, before)
        self.assertEqual(len(self.db.receipts), 1)

    def test_no_internal_commit(self):
        self.seed()
        self.record(self.a, self.b)
        self.assertEqual(self.db.commits, 0)

    def test_unknown_owner_denied(self):
        with self.assertRaises(history.AssignmentHistoryError):
            self.record(history._UNKNOWN_AUTHORITY, self.a)

    def test_untrusted_or_expired_capability_denied(self):
        with self.assertRaises(history.AssignmentHistoryError):
            capture._record_assignment_history(None, event_id="e", source="s", reason="r",
                at=self.at, request_payload={}, resolve_transition=lambda: (None, None, True))
        with capture._assignment_capture_operation(ticket="T", authorize=lambda t, a: True) as operation:
            pass
        with self.assertRaises(history.AssignmentHistoryError):
            capture._record_assignment_history(operation, event_id="e", source="s", reason="r",
                at=self.at, request_payload={}, resolve_transition=lambda: (None, None, True))

    def test_unauthorized_context_denied_before_receipt_read(self):
        with self.assertRaises(history.AssignmentHistoryError):
            with capture._assignment_capture_operation(ticket="T", authorize=lambda t, a: False):
                self.fail("must not enter")
        self.assertFalse(any("Capture Receipt" in q for q, v in self.db.queries))

    def test_lock_precedes_authorization_and_resolver(self):
        def authorize(ticket, actor):
            self.assertIn("tabHD Ticket", self.db.queries[0][0])
            return True
        with capture._assignment_capture_operation(ticket="T", authorize=authorize) as operation:
            def resolve():
                self.assertIn("tabHD Ticket", self.db.queries[0][0])
                return None, None, True
            capture._record_assignment_history(operation, event_id="event", source="Sync", reason="Work",
                at=self.at, request_payload={}, resolve_transition=resolve)

    def test_guest_and_disabled_user_denied(self):
        self.f.session.user = "Guest"
        with self.assertRaises(history.AssignmentHistoryError):
            self.record()
        self.f.session.user = "supervisor"
        with patch.object(self.db, "get_value", return_value=dict(enabled=0, user_type="System User")):
            with self.assertRaises(history.AssignmentHistoryError):
                self.record()

    def test_missing_schema_denied(self):
        self.db.missing_schema = True
        with self.assertRaises(history.AssignmentHistoryError):
            self.record()
        self.assertEqual(self.db.receipts, [])

    def test_receipt_immutable_and_not_deletable(self):
        self.record(new=self.a)
        self.db.finish_transaction()
        doc = self.get_doc(capture.RECEIPT, "R-1")
        doc.actor = "other"
        with self.assertRaises(history.AssignmentHistoryError):
            doc.save()
        with self.assertRaises(history.AssignmentHistoryError):
            doc.on_trash()
        self.assertEqual(self.db.receipts[0]["actor"], "supervisor")

    def test_receipt_rejects_noncanonical_or_contradictory_result(self):
        self.record(new=self.a)
        row = self.db.receipts[0]
        for field, value in (("request_payload", "{}"), ("previous_owner", "{}"),
                             ("result", capture._json(dict(end_episode=None, start_episode=None, no_op=True)))):
            doc = self.Receipt(dict(row, **{field: value}))
            with self.subTest(field=field), self.assertRaises(history.AssignmentHistoryError):
                doc.validate()

    def test_identity_mapping_mismatch_denied(self):
        self.identities[self.a.user] = TechnicianBookingIdentity("tech-a", "OTHER", "Company")
        with self.assertRaises(history.AssignmentHistoryError):
            self.record(new=self.a)
        self.assertEqual(self.db.history, [])

    def test_invalid_future_or_aware_timestamp_denied(self):
        for at in (self.at.replace(tzinfo=timezone.utc), self.now + timedelta(seconds=1)):
            with self.subTest(at=at), self.assertRaises(history.AssignmentHistoryError):
                self.record(at=at)

    def test_existing_unreceipted_event_not_adopted(self):
        self.seed()
        self.db.receipts = []
        self.db.finish_transaction()
        with self.assertRaises(history.AssignmentHistoryError):
            self.record(self.a, self.a, event_id="seed")

    def test_noop_retry_after_later_assignment(self):
        self.seed()
        first = self.record(self.a, self.a)
        self.db.finish_transaction()
        later = self.at + timedelta(minutes=5)
        self.now = later + timedelta(seconds=1)
        self.record(self.a, self.b, event_id="later", at=later)
        self.db.finish_transaction()
        before = copy.deepcopy((self.db.history, self.db.receipts))
        self.assertEqual(first, self.record(self.a, self.a,
            resolve_transition=Mock(side_effect=AssertionError("retry must not mutate"))))
        self.assertEqual((self.db.history, self.db.receipts), before)

    def test_caught_recorder_failure_still_rolls_back_scope(self):
        self.seed()
        before = copy.deepcopy(self.db.history)
        self.fail_doctype = capture.RECEIPT
        with self.assertRaises(history.AssignmentHistoryError):
            with capture._assignment_capture_operation(ticket="T", authorize=lambda t, a: True) as operation:
                try:
                    capture._record_assignment_history(operation, event_id="event", source="Handoff",
                        reason="Work", at=self.at, request_payload={"target": "tech-b"},
                        resolve_transition=lambda: (self.a, self.b, True))
                except RuntimeError:
                    pass
        self.assertEqual(self.db.history, before)
        self.assertEqual(len(self.db.receipts), 1)

    def test_replaced_database_or_changed_actor_denied(self):
        for field in ("db", "actor"):
            with self.subTest(field=field):
                with self.assertRaises(history.AssignmentHistoryError):
                    with capture._assignment_capture_operation(ticket="T", authorize=lambda t, a: True) as operation:
                        if field == "db":
                            self.f.local.db = MemoryDB()
                        else:
                            self.f.session.user = "other"
                        capture._record_assignment_history(operation, event_id="event", source="Sync",
                            reason="Work", at=self.at, request_payload={},
                            resolve_transition=lambda: (None, None, True))
                self.f.local.db = self.db
                self.f.session.user = "supervisor"

    def test_canonical_request_order_retry(self):
        first = self.record(request_payload={"one": 1, "two": [True, None]})
        self.db.finish_transaction()
        self.assertEqual(first, self.record(request_payload={"two": [True, None], "one": 1}))

    def test_receipt_duplicate_failure_rolls_back_handoff(self):
        self.seed()
        before = copy.deepcopy(self.db.history)
        def collision(doc, **kwargs):
            raise self.f.UniqueValidationError("simulated competing event")
        with patch.object(self.Receipt, "insert", collision):
            with self.assertRaises(self.f.UniqueValidationError):
                self.record(self.a, self.b)
        self.assertEqual(self.db.history, before)
        self.assertEqual(len(self.db.receipts), 1)

    def test_schema_private_unique_and_no_hooks(self):
        path = Path(__file__).resolve().parents[1] / "ftelephony/doctype/telectro_assignment_capture_receipt/telectro_assignment_capture_receipt.json"
        schema = json.loads(path.read_text())
        fields = {f["fieldname"]: f for f in schema["fields"]}
        self.assertEqual(schema["permissions"], [])
        self.assertEqual(fields["event_id"]["unique"], 1)
        self.assertEqual(schema["engine"], "InnoDB")
        self.assertEqual(schema["allow_rename"], 0)


if __name__ == "__main__":
    unittest.main()
