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


def hours_rows(bookings, window_start, window_end, *, detail=False):
    """Build daily totals or their constituent detail rows from authorized bookings."""
    rows = []
    daily = {}
    for booking in bookings:
        status = booking["docstatus"]
        for start, end in day_slices(
            booking["from_time"], booking["to_time"], window_start, window_end
        ):
            day = start.date()
            seconds = (end - start).total_seconds()
            amounts = (
                seconds,
                seconds if status == 0 else 0,
                seconds if status == 1 else 0,
                seconds if booking["emergency"] == 1 else 0,
            )
            if detail:
                row = _hours_row(day, amounts, booking)
                row.update(from_time=start, to_time=end)
                rows.append(row)
            else:
                totals = daily.setdefault(day, [0, 0, 0, 0])
                for index, value in enumerate(amounts):
                    totals[index] += value
    if detail:
        return sorted(rows, key=lambda row: (row["day"], row["from_time"], row["booking"]))
    return [_hours_row(day, totals) for day, totals in sorted(daily.items())]


def _hours_row(day, amounts, booking=None):
    booked, draft, submitted, emergency = amounts
    row = dict(booking or ())
    row.update(
        day=day,
        booked_hours=booked / 3600,
        draft_hours=draft / 3600,
        submitted_hours=submitted / 3600,
        emergency_hours=emergency / 3600,
    )
    return row
