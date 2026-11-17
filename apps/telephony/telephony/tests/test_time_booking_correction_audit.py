"""No-site proof of private correction audit evidence and immutability."""

from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from telephony.time_booking_correction_audit import (
    ACTIONS, BookingCorrectionAuditError, DOCTYPE, record_correction_event,
)


ROOT = Path(__file__).resolve().parents[1]


def snapshot(status=0):
    return {
        "doctype": "Timesheet", "name": "TS-1", "docstatus": status,
        "custom_telectro_booking_origin": "Phase 2", "employee": "EMP-1",
        "company": "Company A", "user": "tech@example.com",
        "owner": "tech@example.com", "creation": datetime(2026, 11, 17, 12),
        "time_logs": [{"doctype": "Timesheet Detail", "name": "ROW-1",
            "parent": "TS-1", "parenttype": "Timesheet", "parentfield": "time_logs",
            "custom_work_context": "Helpdesk", "custom_hd_ticket": "HD-1",
            "custom_hd_customer": None, "project": None, "task": None,
            "from_time": datetime(2026, 11, 16, 9),
            "to_time": datetime(2026, 11, 16, 10), "hours": 1.0,
            "description": "Repair", "activity_type": "Service"}],
    }


class StoredDoc(dict):
    def __init__(self, values, store):
        super().__init__(values)
        self.store = store
        self.name = None
    def insert(self, **kwargs):
        self.name = "AUDIT-" + str(len(self.store) + 1)
        self["name"] = self.name
        self.store.append(self)


class TestAuditWriter(unittest.TestCase):
    def setUp(self):
        self.rows = []
        self.sql_calls = []
        self.f = types.ModuleType("frappe")
        self.f.session = types.SimpleNamespace(user="tech@example.com")
        self.f.UniqueValidationError = type("UniqueValidationError", (Exception,), {})
        self.f.db = types.SimpleNamespace(sql=self.sql, commit=Mock(), rollback=Mock(),
                                          delete=Mock(), set_value=Mock())
        self.f.get_doc = lambda values: StoredDoc(values, self.rows)
        utils = types.ModuleType("frappe.utils")
        utils.now_datetime = lambda: datetime(2026, 11, 17, 13)
        patcher = patch.dict(sys.modules, {"frappe": self.f, "frappe.utils": utils})
        patcher.start(); self.addCleanup(patcher.stop)

    def sql(self, query, event_id, **kwargs):
        self.assertIn("WHERE event_id=%s FOR UPDATE", query)
        self.sql_calls.append(event_id)
        return [dict(row) for row in self.rows if row.get("event_id") == event_id]

    def call(self, **updates):
        values = dict(event_id="correction-1", action="Draft Correction",
                      reason="Wrong duration", before=snapshot(), after=snapshot())
        values["after"]["time_logs"][0]["hours"] = 1.5
        values.update(updates)
        return record_correction_event(**values)

    def test_complete_before_after_snapshot_and_server_identity(self):
        self.assertEqual(self.call(), "AUDIT-1")
        row = self.rows[0]
        before, after = json.loads(row["before_snapshot"]), json.loads(row["after_snapshot"])
        self.assertEqual(before["time_logs"][0]["custom_hd_ticket"], "HD-1")
        self.assertEqual(before["time_logs"][0]["from_time"], "2026-11-16T09:00:00")
        self.assertEqual(before["employee"], "EMP-1")
        self.assertEqual(before["company"], "Company A")
        self.assertEqual(before["owner"], "tech@example.com")
        self.assertEqual(before["creation"], "2026-11-17T12:00:00")
        self.assertEqual(after["time_logs"][0]["hours"], 1.5)
        self.assertEqual(row["original_timesheet"], "TS-1")
        self.assertEqual(row["original_time_log"], "ROW-1")
        self.assertEqual(row["actor"], "tech@example.com")
        self.assertEqual(row["recorded_at"], datetime(2026, 11, 17, 13))
        self.assertEqual(DOCTYPE, "TELECTRO Booking Correction Audit")

    def test_same_event_is_idempotent(self):
        self.call()
        self.assertEqual(self.call(), "AUDIT-1")
        self.assertEqual(len(self.rows), 1)

    def test_conflicting_event_reuse_fails_closed(self):
        self.call()
        for updates in ({"reason": "Other"}, {"action": "Draft Withdrawal", "after": None},
                        {"replacement_timesheet": "TS-2"}):
            with self.subTest(updates=updates):
                with self.assertRaises(BookingCorrectionAuditError):
                    self.call(**updates)
        self.assertEqual(len(self.rows), 1)

    def test_different_actor_cannot_reuse_event(self):
        self.call()
        self.f.session.user = "another@example.com"
        with self.assertRaises(BookingCorrectionAuditError): self.call()

    def test_required_reason_actor_and_event_id(self):
        for updates in ({"reason": ""}, {"reason": " "}, {"event_id": ""},
                        {"event_id": "x"*141}):
            with self.subTest(updates=updates):
                with self.assertRaises(BookingCorrectionAuditError): self.call(**updates)
        for actor in (None, "", "Guest", "Administrator"):
            self.f.session.user = actor
            with self.subTest(actor=actor):
                with self.assertRaises(BookingCorrectionAuditError): self.call()
        self.assertEqual(self.rows, [])

    def test_draft_withdrawal_needs_no_replacement(self):
        self.assertEqual(self.call(action="Draft Withdrawal", after=None), "AUDIT-1")
        self.assertIsNone(self.rows[0]["after_snapshot"])

    def test_submitted_cancellation_and_replacement(self):
        before = snapshot(1)
        self.assertEqual(self.call(action="Submitted Cancellation", before=before, after=None), "AUDIT-1")
        self.assertEqual(self.call(event_id="correction-2", action="Submitted Replacement",
                                   before=before, after=None, replacement_timesheet="TS-2"), "AUDIT-2")
        self.assertEqual(len(self.rows), 2)

    def test_action_status_and_snapshot_inconsistency_rejected(self):
        for updates in ({"action": "Unknown"}, {"action": "Submitted Cancellation", "after": None},
                        {"action": "Draft Correction", "after": None},
                        {"action": "Draft Withdrawal", "after": None, "replacement_timesheet": "TS-2"}):
            with self.subTest(updates=updates):
                with self.assertRaises(BookingCorrectionAuditError): self.call(**updates)
        bad = snapshot(); bad["time_logs"] = []
        with self.assertRaises(BookingCorrectionAuditError): self.call(before=bad)
        bad = snapshot(); bad["owner"] = None
        with self.assertRaises(BookingCorrectionAuditError): self.call(before=bad)
        self.assertEqual(self.rows, [])

    def test_original_identity_uses_plain_data_not_link(self):
        path = ROOT / "ftelephony/doctype/telectro_booking_correction_audit/telectro_booking_correction_audit.json"
        schema = json.loads(path.read_text())
        fields = {field["fieldname"]: field for field in schema["fields"]}
        self.assertEqual(schema["permissions"], [])
        self.assertEqual(schema["engine"], "InnoDB")
        self.assertEqual(fields["event_id"]["unique"], 1)
        self.assertEqual(fields["original_timesheet"]["fieldtype"], "Data")
        self.assertEqual(fields["original_time_log"]["fieldtype"], "Data")
        self.assertEqual(set(ACTIONS), set(fields["action"]["options"].split("\n")))

    def test_insert_failure_propagates_and_does_not_commit(self):
        error = RuntimeError("database unavailable")
        with patch.object(StoredDoc, "insert", side_effect=error):
            with self.assertRaises(RuntimeError) as caught: self.call()
        self.assertIs(caught.exception, error)
        self.assertEqual(self.rows, [])
        self.f.db.commit.assert_not_called()
        self.f.db.rollback.assert_not_called()

    def test_unique_collision_fails_closed(self):
        with patch.object(StoredDoc, "insert", side_effect=self.f.UniqueValidationError()):
            with self.assertRaises(BookingCorrectionAuditError): self.call()
        self.assertEqual(self.rows, [])

    def test_no_transaction_or_timesheet_mutations(self):
        self.call()
        for method in ("commit", "rollback", "delete", "set_value"):
            getattr(self.f.db, method).assert_not_called()


class TestAuditDocType(unittest.TestCase):
    def test_existing_record_cannot_be_saved_or_deleted(self):
        from frappe.model.document import Document
        path = ROOT / "ftelephony/doctype/telectro_booking_correction_audit/telectro_booking_correction_audit.py"
        spec = importlib.util.spec_from_file_location("audit_doctype_test", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        doc = module.TELECTROBookingCorrectionAudit.__new__(module.TELECTROBookingCorrectionAudit)
        with self.assertRaises(BookingCorrectionAuditError): doc.on_trash()
        with patch.object(Document, "get_doc_before_save", return_value=object()):
            with self.assertRaises(BookingCorrectionAuditError):
                doc.validate()
