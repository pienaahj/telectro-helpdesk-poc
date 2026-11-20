"""Pure coverage arithmetic over finite, normalized site-local intervals.

The caller must independently establish evidence trust and ensure every interval
belongs to the same ticket, Technician, Employee and Company. This module does
not interpret records, infer assignment history, or grant reference access.
"""

from datetime import datetime


class TemporalCoverageError(ValueError):
    """Invalid temporal input, without disclosing authority evidence."""

    def __init__(self):
        super().__init__("Temporal coverage input is invalid.")


def _datetime(value):
    if type(value) is not datetime or value.tzinfo is not None:
        raise TemporalCoverageError()
    return value


def _interval(value):
    if type(value) not in (tuple, list) or len(value) != 2:
        raise TemporalCoverageError()
    start, end = (_datetime(endpoint) for endpoint in value)
    if start >= end:
        raise TemporalCoverageError()
    return start, end


def covers_booking_interval(start, end, authority_intervals, *, evaluated_at):
    """Return whether the union of authority intervals covers [start, end).

    All timestamps must be naive datetime objects in the same site timezone.
    authority_intervals must be a list/tuple of finite two-item list/tuple pairs;
    empty evidence returns False. All evidence is validated, even when another
    interval already covers the booking. Invalid input raises TemporalCoverageError.

    Require start < end <= evaluated_at; the clock is always supplied explicitly.
    Authority endpoints may exceed evaluated_at but never permit future bookings.
    Overlap and exact adjacency merge without rounding microseconds. Caller-owned
    collections are not modified. No identity, trust or timezone conversion occurs.
    """
    start, end = _interval((start, end))
    evaluated_at = _datetime(evaluated_at)
    if end > evaluated_at or type(authority_intervals) not in (tuple, list):
        raise TemporalCoverageError()
    intervals = sorted(_interval(interval) for interval in authority_intervals)

    covered_until = start
    for interval_start, interval_end in intervals:
        if interval_end <= covered_until:
            continue
        if interval_start > covered_until:
            return False
        covered_until = interval_end
        if covered_until >= end:
            return True
    return False
