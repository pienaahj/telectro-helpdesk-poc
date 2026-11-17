"""Private assignment episodes; callers establish assignment transition authority."""

from datetime import datetime
from hashlib import sha256

from telephony.time_booking_cooption import _require_recipient_identity

DOCTYPE = "TELECTRO Ticket Assignment History"


class AssignmentHistoryError(PermissionError):
    def __init__(self):
        super().__init__("Ticket assignment history is unavailable.")


def _text(value):
    return type(value) is str and bool(value.strip())


def _active_key(ticket, user):
    if not _text(ticket) or not _text(user):
        raise AssignmentHistoryError()
    return sha256(f"{len(ticket)}:{ticket}{len(user)}:{user}".encode()).hexdigest()


def _time(value):
    if isinstance(value, datetime):
        return value
    if _text(value):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    raise AssignmentHistoryError()


def _lock_ticket(ticket):
    import frappe
    if not _text(ticket):
        raise AssignmentHistoryError()
    rows = frappe.db.sql("SELECT name FROM `tabHD Ticket` WHERE name=%s FOR UPDATE", ticket, as_dict=True)
    if len(rows) != 1 or rows[0].get("name") != ticket:
        raise AssignmentHistoryError()


def _active(ticket, user):
    import frappe
    rows = frappe.db.sql(
        "SELECT name, ticket, technician_user, employee, company, state, active_key, "
        "effective_start, recorded_start, start_event_id FROM "
        "`tabTELECTRO Ticket Assignment History` WHERE active_key=%s FOR UPDATE",
        _active_key(ticket, user), as_dict=True)
    if len(rows) > 1:
        raise AssignmentHistoryError()
    if not rows:
        return None
    row = rows[0]
    if (row.get("ticket") != ticket or row.get("technician_user") != user
            or row.get("state") != "Active" or row.get("active_key") != _active_key(ticket, user)
            or not _text(row.get("name"))):
        raise AssignmentHistoryError()
    return row


def _event(operation, event_id):
    import frappe
    if operation not in ("START", "END"):
        raise AssignmentHistoryError()
    column = "start_event_id" if operation == "START" else "end_event_id"
    rows = frappe.db.sql(
        "SELECT name, ticket, technician_user, start_event_id, end_event_id, "
        "started_by, start_source, start_reason, ended_by, end_source, end_reason, "
        "state, effective_start, effective_end, recorded_start, recorded_end FROM "
        "`tabTELECTRO Ticket Assignment History` "
        f"WHERE {column}=%s FOR UPDATE",
        event_id, as_dict=True)
    if len(rows) > 1:
        raise AssignmentHistoryError()
    return rows[0] if rows else None


def _recorded_now():
    from frappe.utils import now_datetime
    return _time(now_datetime())


def start_assignment(*, ticket, user, actor, source, reason, event_id, effective_start):
    """Call only after a trusted assignment transition; never infer old history."""
    import frappe
    if not all(_text(v) for v in (ticket, user, actor, source, reason, event_id)):
        raise AssignmentHistoryError()
    start = _time(effective_start)
    _lock_ticket(ticket)
    prior_event = _event("START", event_id)
    if prior_event:
        if (prior_event.get("ticket") == ticket and prior_event.get("technician_user") == user
                and prior_event.get("start_event_id") == event_id
                and _time(prior_event.get("effective_start")) == start
                and prior_event.get("started_by") == actor
                and prior_event.get("start_source") == source
                and prior_event.get("start_reason") == reason):
            return prior_event["name"]
        raise AssignmentHistoryError()
    identity = _require_recipient_identity(user)
    if _active(ticket, user):
        raise AssignmentHistoryError()
    recorded = _recorded_now()
    if start > recorded:
        raise AssignmentHistoryError()
    doc = frappe.get_doc(dict(
        doctype=DOCTYPE, ticket=ticket, technician_user=user,
        employee=identity.employee, company=identity.company,
        effective_start=start, recorded_start=recorded, started_by=actor,
        start_source=source, start_reason=reason, start_event_id=event_id,
        state="Active", active_key=_active_key(ticket, user),
    ))
    try:
        doc.insert(ignore_permissions=True)
    except frappe.UniqueValidationError as exc:
        raise AssignmentHistoryError() from exc
    return doc.name


def end_assignment(*, ticket, user, episode, actor, source, reason, event_id, effective_end):
    """Close exactly the specified active episode; retries use a stable event ID."""
    import frappe
    if not all(_text(v) for v in (ticket, user, episode, actor, source, reason, event_id)):
        raise AssignmentHistoryError()
    end = _time(effective_end)
    _lock_ticket(ticket)
    prior_event = _event("END", event_id)
    if prior_event:
        if (prior_event.get("name") == episode and prior_event.get("ticket") == ticket
                and prior_event.get("technician_user") == user
                and prior_event.get("end_event_id") == event_id
                and _time(prior_event.get("effective_end")) == end
                and prior_event.get("ended_by") == actor
                and prior_event.get("end_source") == source
                and prior_event.get("end_reason") == reason):
            return episode
        raise AssignmentHistoryError()
    active = _active(ticket, user)
    if not active or active.get("name") != episode:
        raise AssignmentHistoryError()
    start = _time(active.get("effective_start"))
    recorded_start = _time(active.get("recorded_start"))
    recorded_end = _recorded_now()
    if end < start or end > recorded_end or recorded_end < recorded_start:
        raise AssignmentHistoryError()
    doc = frappe.get_doc(DOCTYPE, episode)
    if (doc.ticket != ticket or doc.technician_user != user or doc.state != "Active"
            or doc.active_key != _active_key(ticket, user)):
        raise AssignmentHistoryError()
    doc.effective_end = end
    doc.recorded_end = recorded_end
    doc.ended_by = actor
    doc.end_source = source
    doc.end_reason = reason
    doc.end_event_id = event_id
    doc.state = "Closed"
    doc.active_key = None
    try:
        doc.save(ignore_permissions=True)
    except frappe.UniqueValidationError as exc:
        raise AssignmentHistoryError() from exc
    return episode


# Future governance regularization must use a separate, authorized service
# with mandatory evidence, actor and reason. This writer accepts only trusted
# transition calls and does not infer participation from _assign or ToDo.
