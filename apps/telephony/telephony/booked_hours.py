"""Read-only interval calculations shared by Phase 2 booked-hours reports."""

from datetime import date, datetime, time, timedelta


def date_window(from_date, to_date):
    """Convert inclusive site-local dates to a half-open wall-clock range."""
    if not isinstance(from_date, str) or not isinstance(to_date, str):
        raise ValueError
    start, end = date.fromisoformat(from_date), date.fromisoformat(to_date)
    if start.isoformat() != from_date or end.isoformat() != to_date or end < start:
        raise ValueError
    return datetime.combine(start, time.min), datetime.combine(end + timedelta(days=1), time.min)


def day_slices(start, end, window_start, window_end):
    """Yield each clipped start and end within a single site-local day."""
    cursor = max(start, window_start)
    stop = min(end, window_end)
    while cursor < stop:
        midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min)
        next_cursor = min(midnight, stop)
        yield cursor, next_cursor
        cursor = next_cursor


def hours_rows(bookings, window_start, window_end, *, detail=False, group_by=(), by_day=True):
    """Build disjoint detail or grouped rows using exact clipped microseconds."""
    rows = []
    totals = {}
    fields = (*group_by, "day") if by_day else group_by
    for booking in bookings:
        status = booking["docstatus"]
        for start, end in day_slices(
            booking["from_time"], booking["to_time"], window_start, window_end
        ):
            day = start.date()
            duration = (end - start) // timedelta(microseconds=1)
            amounts = (
                duration,
                duration if status == 0 else 0,
                duration if status == 1 else 0,
                duration if booking["emergency"] == 1 else 0,
            )
            if detail:
                row = _hours_row(amounts, booking)
                row.update(day=day, from_time=start, to_time=end)
                rows.append(row)
            else:
                key = tuple(booking[field] for field in group_by)
                if by_day:
                    key += (day,)
                bucket = totals.setdefault(key, [0, 0, 0, 0])
                for index, value in enumerate(amounts):
                    bucket[index] += value
    if detail:
        return sorted(rows, key=lambda row: (row["day"], row["from_time"], row["booking"]))
    return [
        _hours_row(totals[key], dict(zip(fields, key)))
        for key in sorted(totals, key=lambda values: tuple("" if v is None else str(v) for v in values))
    ]


def _hours_row(amounts, booking):
    booked, draft, submitted, emergency = amounts
    return dict(
        booking,
        booked_hours=booked / 3_600_000_000,
        draft_hours=draft / 3_600_000_000,
        submitted_hours=submitted / 3_600_000_000,
        emergency_hours=emergency / 3_600_000_000,
    )
