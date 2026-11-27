"""Validate work against a locked, already-authorized Helpdesk Ticket."""

from datetime import datetime, timedelta
import json
import re

from telephony.setup.ticket_status_durability import ARCHIVED_STATUS_NAME


ORIGIN_FIELD = "custom_telectro_manual_origin"
ACTIVE_CATEGORIES = frozenset(("Open", "Paused"))
COMPLETED_CATEGORY = "Resolved"
CLOSED_STATUS = "Closed"  # Native HD Ticket Status identity.


class TicketIntervalError(ValueError):
    """The requested work interval or its lifecycle evidence is invalid."""


def _timestamp(value):
    if type(value) is str and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?", value,
    ):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    return value if type(value) is datetime and value.tzinfo is None else None


def ticket_interval_changed(previous, row, start, end):
    """Compare precise native and serialized intervals without rounding."""
    if previous is None:
        return True
    previous_ticket = previous.get("custom_hd_ticket")
    if type(previous_ticket) is int:
        previous_ticket = str(previous_ticket)
    return (
        previous.get("custom_work_context") != "Helpdesk"
        or previous_ticket != row["custom_hd_ticket"]
        or _timestamp(previous.get("from_time")) != _timestamp(start)
        or _timestamp(previous.get("to_time")) != _timestamp(end)
    )


def _configured_category(db, status):
    if type(status) is not str or not status:
        raise TicketIntervalError("Ticket lifecycle evidence is unavailable.")
    rows = db.sql("""
        SELECT name, category FROM `tabHD Ticket Status`
        WHERE name = %s LOCK IN SHARE MODE NOWAIT
    """, (status,))
    if (
        len(rows) != 1 or rows[0][0] != status
        or rows[0][1] not in ACTIVE_CATEGORIES | {COMPLETED_CATEGORY}
    ):
        raise TicketIntervalError("Ticket lifecycle evidence is unavailable.")
    return rows[0][1]


def _closed_preserves_resolution(db, ticket_name):
    # The native SLA preserves the exact database resolution_date only when
    # Closed follows an already resolved state. Track Changes can establish
    # that transition, but its formatted datetime values lose precision.
    rows = db.sql("""
        SELECT data FROM `tabVersion`
        WHERE ref_doctype = 'HD Ticket' AND docname = %s
        ORDER BY creation DESC, name DESC LOCK IN SHARE MODE NOWAIT
    """, (str(ticket_name),))
    for (data,) in rows:
        try:
            changes = json.loads(data)["changed"]
            if not isinstance(changes, list):
                return False
            relevant = {}
            for field, old, new in changes:
                if field in ("status", "status_category", "resolution_date"):
                    if field in relevant:
                        return False
                    relevant[field] = old, new
        except (KeyError, TypeError, ValueError):
            return False

        if not relevant:
            continue
        # A change to the resolution date/category, even during closure,
        # cannot prove the current precise timestamp was preserved.
        if set(relevant) != {"status"}:
            return False
        previous, current = relevant["status"]
        return (
            current == CLOSED_STATUS
            and previous not in (CLOSED_STATUS, ARCHIVED_STATUS_NAME)
            and _configured_category(db, previous) == COMPLETED_CATEGORY
        )
    return False


def validate_ticket_interval(ticket, start, end, *, now, db):
    """Return the exact pre-creation timedelta without changing the booking.

    Call only after reference authorization and with the persisted Ticket
    locked through the booking write. All timestamps are naive site-local.
    """
    creation = _timestamp(ticket.get("creation"))
    now = _timestamp(now)
    start, end = _timestamp(start), _timestamp(end)
    if (
        creation is None or now is None or creation > now
        or start is None or end is None or end <= start
    ):
        raise TicketIntervalError("Ticket lifecycle evidence or work interval is invalid.")

    status = ticket.get("status")
    # The configured category is authoritative. Native Ticket saves can
    # retain a previously materialized category when only status is changed.
    category = _configured_category(db, status)
    raw_resolution = ticket.get("resolution_date")
    upper = now
    if category == COMPLETED_CATEGORY:
        upper = _timestamp(raw_resolution)
        if upper is None or not creation <= upper <= now:
            raise TicketIntervalError("Ticket resolution evidence is unavailable or invalid.")
        if status == ARCHIVED_STATUS_NAME or (
            status == CLOSED_STATUS
            and (
                ticket.get("status_category") != COMPLETED_CATEGORY
                or not _closed_preserves_resolution(db, ticket.name)
            )
        ):
            raise TicketIntervalError("Operational Ticket resolution could not be verified.")
    elif raw_resolution not in (None, ""):
        # Native reopening clears the prior resolution. There is no gap to
        # reconstruct once the persisted Ticket is active again.
        raise TicketIntervalError("Ticket lifecycle evidence is contradictory.")

    # A missing or noncanonical marker conveys no positive origin evidence.
    origin = ticket.get(ORIGIN_FIELD)
    verified = type(origin) is int and origin == 1
    if end > upper or (not verified and start < creation):
        raise TicketIntervalError("Work is outside the permitted Ticket interval.")
    return max(timedelta(), min(end, creation) - start)
