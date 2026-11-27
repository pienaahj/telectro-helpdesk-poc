"""Deterministic coverage tests; standard library only, no Frappe session."""

import copy
import unittest
from datetime import date, datetime, timedelta, timezone, tzinfo

from telephony.time_booking_coverage import (
    TemporalCoverageError,
    covers_booking_interval,
)


class TestTemporalCoverage(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 11, 19, 9)
        self.end = self.start + timedelta(hours=1)
        self.now = self.end + timedelta(hours=1)
        self.mid = self.start + timedelta(minutes=30)
        self.tick = timedelta(microseconds=1)

    def covers(self, intervals, **updates):
        values = dict(start=self.start, end=self.end,
                      authority_intervals=intervals, evaluated_at=self.now)
        values.update(updates)
        return covers_booking_interval(**values)

    def test_exact_coverage(self):
        self.assertTrue(self.covers([(self.start, self.end)]))

    def test_surrounding_coverage(self):
        self.assertTrue(self.covers([(self.start - self.tick, self.end + self.tick)]))

    def test_partial_coverage(self):
        self.assertFalse(self.covers([(self.start, self.mid)]))

    def test_missing_start(self):
        self.assertFalse(self.covers([(self.start + self.tick, self.end)]))

    def test_gap(self):
        self.assertFalse(self.covers([
            (self.start, self.mid), (self.mid + timedelta(minutes=1), self.end)]))

    def test_adjacent_intervals(self):
        self.assertTrue(self.covers([(self.start, self.mid), (self.mid, self.end)]))

    def test_overlapping_intervals(self):
        self.assertTrue(self.covers([
            (self.start, self.mid + self.tick), (self.mid, self.end)]))

    def test_unsorted_intervals(self):
        self.assertTrue(self.covers([(self.mid, self.end), (self.start, self.mid)]))

    def test_empty_evidence(self):
        self.assertFalse(self.covers([]))

    def test_invalid_booking_intervals(self):
        for end in (self.start, self.start - self.tick):
            with self.subTest(end=end), self.assertRaises(TemporalCoverageError):
                self.covers([], end=end)

    def test_invalid_authority_order(self):
        for end in (self.start, self.start - self.tick):
            with self.subTest(end=end), self.assertRaises(TemporalCoverageError):
                self.covers([(self.start, end)])

    def test_malformed_authority_pairs(self):
        for interval in (None, (), (self.start,), (self.start, self.end, self.now),
                         {"start": self.start, "end": self.end}, "interval"):
            with self.subTest(interval=interval), self.assertRaises(TemporalCoverageError):
                self.covers([interval])

    def test_invalid_endpoint_types(self):
        for value in (None, "2026-11-19 09:00:00", date(2026, 11, 19), 0, True):
            for field in ("start", "end", "evaluated_at"):
                with self.subTest(value=value, field=field), self.assertRaises(TemporalCoverageError):
                    self.covers([], **{field: value})
            for interval in ((value, self.end), (self.start, value)):
                with self.subTest(interval=interval), self.assertRaises(TemporalCoverageError):
                    self.covers([interval])

    def test_invalid_evidence_collection(self):
        for intervals in (None, "", {}, {1}, iter(())):
            with self.subTest(intervals=intervals), self.assertRaises(TemporalCoverageError):
                self.covers(intervals)

    def test_microsecond_gap(self):
        self.assertFalse(self.covers([
            (self.start, self.mid), (self.mid + self.tick, self.end)]))

    def test_microsecond_booking(self):
        self.assertTrue(self.covers([(self.start, self.start + self.tick)],
                                   end=self.start + self.tick))

    def test_exact_end_boundary(self):
        self.assertTrue(self.covers([(self.start, self.end)], evaluated_at=self.end))

    def test_booking_beyond_authority_end(self):
        self.assertFalse(self.covers([(self.start, self.end - self.tick)]))

    def test_touching_only_is_not_coverage(self):
        self.assertFalse(self.covers([
            (self.start - timedelta(hours=1), self.start),
            (self.end, self.now)]))

    def test_timezone_aware_or_mixed_rejected(self):
        for zone in (timezone.utc, timezone(timedelta(hours=2))):
            for field in ("start", "end", "evaluated_at"):
                value = getattr(self, {"evaluated_at": "now"}.get(field, field))
                with self.subTest(zone=zone, field=field), self.assertRaises(TemporalCoverageError):
                    self.covers([], **{field: value.replace(tzinfo=zone)})
            for interval in ((self.start.replace(tzinfo=zone), self.end),
                             (self.start, self.end.replace(tzinfo=zone)),
                             (self.start.replace(tzinfo=zone), self.end.replace(tzinfo=zone))):
                with self.subTest(interval=interval), self.assertRaises(TemporalCoverageError):
                    self.covers([interval])

    def test_tzinfo_without_offset_rejected(self):
        class UnspecifiedTimezone(tzinfo):
            def utcoffset(self, dt):
                return None
        with self.assertRaises(TemporalCoverageError):
            self.covers([], start=self.start.replace(tzinfo=UnspecifiedTimezone()))

    def test_future_booking_uses_explicit_evaluation_time(self):
        intervals = [(self.start, self.end)]
        with self.assertRaises(TemporalCoverageError):
            self.covers(intervals, evaluated_at=self.end - self.tick)
        self.assertTrue(self.covers(intervals, evaluated_at=self.end))

    def test_combined_evidence_sources(self):
        assignment = (self.start, self.start + timedelta(minutes=20))
        grant = (assignment[1], self.start + timedelta(minutes=40))
        attestation = (grant[1], self.end)
        self.assertTrue(self.covers([grant, attestation, assignment]))

    def test_nested_duplicate_and_irrelevant_intervals(self):
        self.assertTrue(self.covers([
            (self.start - timedelta(hours=2), self.start - timedelta(hours=1)),
            (self.start, self.end), (self.start, self.mid),
            (self.start, self.end), (self.end, self.now)]))

    def test_malformed_evidence_not_hidden_by_full_coverage(self):
        for invalid in (None, (self.end, self.start), (self.start, None)):
            with self.subTest(invalid=invalid), self.assertRaises(TemporalCoverageError):
                self.covers([(self.start, self.end), invalid])

    def test_input_collections_unchanged(self):
        intervals = [[self.mid, self.end], [self.start, self.mid]]
        before = copy.deepcopy(intervals)
        self.assertTrue(self.covers(intervals))
        self.assertEqual(intervals, before)
        self.assertTrue(self.covers(tuple(tuple(pair) for pair in intervals)))

    def test_future_authority_does_not_extend_requested_booking(self):
        self.assertTrue(self.covers([(self.start, self.now + timedelta(days=1))]))
        with self.assertRaises(TemporalCoverageError):
            self.covers([(self.start, self.now + timedelta(days=1))], end=self.now + self.tick)


if __name__ == "__main__":
    unittest.main()
