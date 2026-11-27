import json
from pathlib import Path
from datetime import datetime
import sys
import types
import unittest
from unittest.mock import patch

from telephony.time_booking_assignment_history import (
    AssignmentHistoryError, _active_key, start_assignment, end_assignment,
)
from telephony.time_booking_identity import TechnicianBookingIdentity


class Doc(dict):
    def __init__(self, values, store):
        super().__init__(values); self.store = store
        self.name = values.get("name")
    def __getattr__(self, key):
        return self.get(key)
    def __setattr__(self, key, value):
        if key in ("store", "name"): object.__setattr__(self, key, value)
        else: self[key] = value
    def insert(self, **kwargs):
        self.name = "EP-" + str(len(self.store)+1)
        self["name"] = self.name; self.store.append(self)
    def save(self, **kwargs):
        pass


class TestAssignmentHistory(unittest.TestCase):
    def setUp(self):
        self.rows = []; self.queries = []; self.now = "2026-11-17 12:00:00"
        self.f = types.ModuleType("frappe")
        self.f.db = types.SimpleNamespace(sql=self.sql)
        self.f.get_doc = self.get_doc
        self.f.UniqueValidationError = type("UniqueValidationError", (Exception,), {})
        utils = types.ModuleType("frappe.utils")
        utils.now_datetime = lambda: self.now
        p = patch.dict(sys.modules, {"frappe": self.f, "frappe.utils": utils})
        p.start(); self.addCleanup(p.stop)
        identity = patch("telephony.time_booking_assignment_history._require_recipient_identity",
                         return_value=TechnicianBookingIdentity("tech", "EMP", "Company"))
        identity.start(); self.addCleanup(identity.stop)

    def sql(self, query, value, **kwargs):
        self.assertIn("FOR UPDATE", query); self.queries.append(query)
        if "tabHD Ticket" in query: return [{"name": value}]
        if "WHERE active_key" in query:
            return [dict(r) for r in self.rows if r.get("active_key") == value]
        field = "start_event_id" if "WHERE start_event_id" in query else "end_event_id"
        return [dict(r) for r in self.rows if r.get(field) == value]

    def get_doc(self, *args):
        if isinstance(args[0], dict): return Doc(args[0], self.rows)
        return next(r for r in self.rows if r.name == args[1])

    def start(self, **kw):
        return start_assignment(ticket="T", user="tech", actor="actor", source="claim",
                                reason="work", event_id="event-start", effective_start="2026-11-17 10:00:00", **kw)

    def end(self, **kw):
        args = dict(ticket="T", user="tech", episode="EP-1", actor="actor",
                    source="release", reason="done", event_id="event-end",
                    effective_end="2026-11-17 11:00:00")
        args.update(kw)
        return end_assignment(**args)

    def test_start_and_retry(self):
        self.assertEqual(self.start(), "EP-1")
        self.assertEqual(self.start(), "EP-1")
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(self.rows[0]["employee"], "EMP")
        self.assertEqual(self.rows[0]["company"], "Company")
        self.assertIn("tabHD Ticket", self.queries[0])

    def test_end_and_retry_preserve_episode(self):
        self.start(); self.assertEqual(self.end(), "EP-1")
        self.assertEqual(self.end(), "EP-1")
        self.assertEqual(self.rows[0]["state"], "Closed")
        self.assertIsNone(self.rows[0]["active_key"])
        self.assertEqual(self.rows[0]["effective_start"], datetime(2026, 11, 17, 10, 0))
        self.assertEqual(len(self.rows), 1)

    def test_regrant_after_close_creates_new_episode(self):
        self.start(); self.end()
        self.assertEqual(start_assignment(ticket="T", user="tech", actor="actor", source="claim",
            reason="again", event_id="event-start-2", effective_start="2026-11-17 11:30:00"), "EP-2")
        self.assertEqual(self.rows[0]["state"], "Closed")

    def test_duplicate_active_denied(self):
        self.start()
        with self.assertRaises(AssignmentHistoryError):
            start_assignment(ticket="T", user="tech", actor="actor", source="claim",
                reason="again", event_id="event-start-2", effective_start="2026-11-17 11:00:00")

    def test_stale_end_cannot_close_regrant(self):
        self.start(); self.end()
        start_assignment(ticket="T", user="tech", actor="actor", source="claim",
            reason="again", event_id="event-start-2", effective_start="2026-11-17 11:30:00")
        with self.assertRaises(AssignmentHistoryError):
            end_assignment(ticket="T", user="tech", episode="EP-1", actor="actor",
                source="release", reason="done", event_id="event-end-2", effective_end="2026-11-17 11:45:00")
        self.assertEqual(self.rows[1]["state"], "Active")

    def test_bad_time_and_event_collision_denied(self):
        with self.assertRaises(AssignmentHistoryError):
            start_assignment(ticket="T", user="tech", actor="actor", source="claim",
                reason="work", event_id="future", effective_start="2026-11-18 10:00:00")
        self.start()
        self.assertEqual(self.end(event_id="event-start"), "EP-1")
        self.assertEqual(self.rows[0]["end_event_id"], "event-start")
        with self.assertRaises(AssignmentHistoryError):
            self.end(event_id="other-end", effective_end="2026-11-17 09:00:00")

    def test_per_ticket_user_active_key(self):
        self.assertNotEqual(_active_key("T", "tech"), _active_key("T", "other"))
        self.start()
        start_assignment(ticket="T", user="other", actor="actor", source="assign",
            reason="work", event_id="other-start", effective_start="2026-11-17 10:00:00")
        self.assertEqual(len(self.rows), 2)

    def test_schema_private_and_unique(self):
        path = Path(__file__).resolve().parents[1] / "ftelephony/doctype/telectro_ticket_assignment_history/telectro_ticket_assignment_history.json"
        schema = json.loads(path.read_text()); fields = {f["fieldname"]: f for f in schema["fields"]}
        self.assertEqual(schema["permissions"], [])
        self.assertEqual(schema["engine"], "InnoDB")
        for name in ("active_key", "start_event_id", "end_event_id"):
            self.assertEqual(fields[name]["unique"], 1)


class TestOperationScopedCollisions(TestAssignmentHistory):
    def test_same_operation_start_collision_is_denied(self):
        self.start()
        for ticket, user, reason, time in (
            ("other", "tech", "work", "2026-11-17 10:00:00"),
            ("T", "other", "work", "2026-11-17 10:00:00"),
            ("T", "tech", "different", "2026-11-17 10:00:00"),
            ("T", "tech", "work", "2026-11-17 10:01:00"),
        ):
            with self.subTest(ticket=ticket, user=user, reason=reason, time=time):
                with self.assertRaises(AssignmentHistoryError):
                    start_assignment(ticket=ticket, user=user, actor="actor", source="claim",
                        reason=reason, event_id="event-start", effective_start=time)
        self.assertEqual(len(self.rows), 1)

    def test_same_operation_end_collision_is_denied(self):
        self.start(); self.end()
        for ticket, user, actor, reason, time in (
            ("other", "tech", "actor", "done", "2026-11-17 11:00:00"),
            ("T", "other", "actor", "done", "2026-11-17 11:00:00"),
            ("T", "tech", "other", "done", "2026-11-17 11:00:00"),
            ("T", "tech", "actor", "different", "2026-11-17 11:00:00"),
            ("T", "tech", "actor", "done", "2026-11-17 11:01:00"),
        ):
            with self.subTest(ticket=ticket, user=user, actor=actor, reason=reason, time=time):
                with self.assertRaises(AssignmentHistoryError):
                    end_assignment(ticket=ticket, user=user, episode="EP-1", actor=actor,
                        source="release", reason=reason, event_id="event-end", effective_end=time)

    def test_cross_operation_same_id_never_matches_retry(self):
        self.start()
        self.assertEqual(self.end(event_id="event-start"), "EP-1")
        self.assertEqual(self.start(), "EP-1")
        self.assertEqual(self.end(event_id="event-start"), "EP-1")
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(self.rows[0]["state"], "Closed")

    def test_cross_operation_different_rows_are_unambiguous(self):
        self.start(); self.end()
        start_assignment(ticket="T", user="tech", actor="actor", source="claim",
            reason="again", event_id="event-end", effective_start="2026-11-17 11:30:00")
        self.assertEqual(self.end(), "EP-1")
        self.assertEqual(self.rows[1]["state"], "Active")

    def test_queries_use_one_operation_column_and_ticket_lock_first(self):
        self.start(); self.end()
        event_queries = [q for q in self.queries if "WHERE start_event_id" in q or "WHERE end_event_id" in q]
        self.assertTrue(any("WHERE start_event_id=%s" in q for q in event_queries))
        self.assertTrue(any("WHERE end_event_id=%s" in q for q in event_queries))
        self.assertTrue(all(" OR " not in q for q in event_queries))
        self.assertIn("tabHD Ticket", self.queries[0])

    def test_schema_has_independent_operation_unique_columns(self):
        path = Path(__file__).resolve().parents[1] / "ftelephony/doctype/telectro_ticket_assignment_history/telectro_ticket_assignment_history.json"
        fields = {f["fieldname"]: f for f in json.loads(path.read_text())["fields"]}
        self.assertEqual(fields["start_event_id"]["unique"], 1)
        self.assertEqual(fields["end_event_id"]["unique"], 1)
