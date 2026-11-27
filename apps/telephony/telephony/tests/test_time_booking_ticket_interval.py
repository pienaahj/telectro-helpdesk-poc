"""No-site proof of authorized Helpdesk interval and attribution policy."""

from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import Mock

from telephony.time_booking_ticket_interval import (
    ORIGIN_FIELD,
    TicketIntervalError,
    ticket_interval_changed,
    validate_ticket_interval,
)
from telephony.tests.test_time_booking_post import Reference


CREATION = datetime(2026, 11, 25, 9, 0, 0, 123456)
NOW = CREATION + timedelta(days=3)
MINUTE = timedelta(minutes=1)
TICK = timedelta(microseconds=1)


class TestTicketInterval(unittest.TestCase):
    def setUp(self):
        self.ticket = Reference(
            "HD Ticket", 987,
            creation=CREATION, status="In Progress", status_category="Open",
            resolution_date=None, **{ORIGIN_FIELD: 1},
        )
        self.categories = {
            "In Progress": "Open", "Awaiting Reply": "Paused",
            "Operational completion": "Resolved", "Closed": "Resolved", "Archived": "Resolved",
        }
        self.versions = []
        self.db = Mock()
        self.db.sql.side_effect = self.sql

    def sql(self, query, params):
        self.assertIn("LOCK IN SHARE MODE NOWAIT", query)
        if "tabHD Ticket Status" in query:
            category = self.categories.get(params[0])
            if params[0] == "closed":  # Case-insensitive MariaDB collation.
                return (("Closed", "Resolved"),)
            return ((params[0], category),) if category else ()
        self.assertIn("tabVersion", query)
        self.assertEqual(params, ("987",))
        return tuple((data,) for data in self.versions)

    def validate(self, start, end):
        return validate_ticket_interval(self.ticket, start, end, now=NOW, db=self.db)

    def resolved(self, status="Operational completion", resolution=CREATION + 2 * MINUTE):
        self.ticket.update(status=status, status_category="Resolved", resolution_date=resolution)

    def test_manual_pre_creation_cases_are_exact(self):
        for start, end, expected in (
            (CREATION - 2 * MINUTE, CREATION - MINUTE, MINUTE),
            (CREATION - 2 * MINUTE, CREATION, 2 * MINUTE),
            (CREATION - TICK, CREATION + MINUTE, TICK),
            (CREATION, CREATION + MINUTE, timedelta()),
            (CREATION + TICK, CREATION + MINUTE, timedelta()),
        ):
            with self.subTest(start=start, end=end):
                result = self.validate(start, end)
                self.assertEqual(result, expected)
                self.assertLessEqual(result, end - start)

    def test_unverified_origins_cannot_start_before_precise_creation(self):
        for origin in (0, None, "1", True, 2):
            self.ticket[ORIGIN_FIELD] = origin
            self.ticket["custom_request_source"] = "Telectro"
            for end in (CREATION - TICK, CREATION + MINUTE):
                with self.subTest(origin=origin, end=end), self.assertRaises(TicketIntervalError):
                    self.validate(CREATION - MINUTE, end)
            self.assertEqual(self.validate(CREATION, CREATION + MINUTE), timedelta())

    def test_active_or_paused_uses_now_inclusively(self):
        for status, category in (("In Progress", "Open"), ("Awaiting Reply", "Paused")):
            self.ticket.update(status=status, status_category=category)
            self.assertEqual(self.validate(CREATION, NOW), timedelta())
            with self.assertRaises(TicketIntervalError):
                self.validate(CREATION, NOW + TICK)

    def test_completed_interval_uses_exact_resolution(self):
        self.resolved(resolution=CREATION + 2 * MINUTE)
        resolution = self.ticket["resolution_date"]
        self.assertEqual(self.validate(CREATION, resolution), timedelta())
        with self.assertRaises(TicketIntervalError):
            self.validate(CREATION, resolution + TICK)

    def test_configured_category_wins_over_stale_materialized_category(self):
        self.resolved()
        self.ticket["status_category"] = "Open"
        self.assertEqual(self.validate(CREATION, self.ticket["resolution_date"]), timedelta())
        self.ticket.update(status="In Progress", status_category="Resolved", resolution_date=None)
        self.assertEqual(self.validate(CREATION, NOW), timedelta())

    def test_closed_uses_preserved_operational_resolution(self):
        self.resolved(status="Closed")
        self.versions = [
            json.dumps({"changed": [["description", "", "Later edit"]]}),
            json.dumps({"changed": [["status", "Operational completion", "Closed"]]}),
        ]
        resolution = self.ticket["resolution_date"]
        self.assertEqual(self.validate(CREATION, resolution), timedelta())
        with self.assertRaises(TicketIntervalError):
            self.validate(CREATION, resolution + TICK)

    def test_administrative_timestamp_is_not_operational_proof(self):
        for status, trail in (
            ("Closed", []),
            ("closed", []),
            ("Closed", ['{"changed":[["status","In Progress","Closed"]]}']),
            ("Closed", ['{"changed":[["status","Operational completion","Closed"],["resolution_date","before","after"]]}']),
            ("Closed", ['{"changed":[["status","Operational completion","Closed"],["status_category","Open","Resolved"]]}']),
            ("Closed", ["malformed history"]),
            ("Archived", ['{"changed":[["status","Operational completion","Archived"]]}']),
        ):
            self.resolved(status=status)
            self.versions = trail
            with self.subTest(status=status, trail=trail), self.assertRaises(TicketIntervalError):
                self.validate(CREATION, CREATION + MINUTE)

    def test_reopened_has_one_continuous_interval(self):
        self.versions = [
            '{"changed":[["status","Operational completion","In Progress"],["resolution_date","before",null]]}',
        ]
        self.assertEqual(self.validate(CREATION, NOW), timedelta())
        self.assertFalse(any("tabVersion" in args.args[0] for args in self.db.sql.call_args_list))

    def test_missing_malformed_and_contradictory_evidence_fails_closed(self):
        original = dict(self.ticket)
        for overrides in (
            {"creation": None}, {"creation": "today"}, {"creation": NOW + TICK},
            {"creation": CREATION.replace(tzinfo=timezone.utc)}, {"status": "Unknown"},
            {"resolution_date": CREATION + MINUTE},
            {"status": "Operational completion", "status_category": "Resolved"},
        ):
            self.ticket.update(original | overrides)
            with self.subTest(overrides=overrides), self.assertRaises(TicketIntervalError):
                self.validate(CREATION, CREATION + MINUTE)
        for timestamp in ("bad", CREATION - TICK, NOW + TICK):
            self.resolved(resolution=timestamp)
            with self.subTest(timestamp=timestamp), self.assertRaises(TicketIntervalError):
                self.validate(CREATION, CREATION + MINUTE)

    def test_exact_comparison_skips_only_unchanged_helpdesk_interval_and_reference(self):
        row = {"custom_work_context": "Helpdesk", "custom_hd_ticket": "987"}
        end = CREATION + MINUTE
        previous = {**row, "from_time": CREATION.isoformat(), "to_time": end}
        self.assertFalse(ticket_interval_changed(previous, row, CREATION, end))
        self.assertFalse(ticket_interval_changed({**previous, "custom_hd_ticket": 987}, row, CREATION, end))
        self.assertTrue(ticket_interval_changed(previous, row, CREATION - TICK, end))
        self.assertTrue(ticket_interval_changed(previous, row, CREATION, end + TICK))
        self.assertTrue(ticket_interval_changed(previous, {**row, "custom_hd_ticket": "988"}, CREATION, end))
        self.assertTrue(ticket_interval_changed({**previous, "custom_work_context": "Project"}, row, CREATION, end))
