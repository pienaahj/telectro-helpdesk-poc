"""Private transactional capture; no hooks, activation, or assignment mutation.

Only trusted Python callers may supply authorization/state resolver functions.
Never forward request-controlled callbacks or treat normalized payload as authority.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
import json

from telephony.time_booking_assignment_history import (
    AssignmentHistoryError, _ActiveAssignmentEpisode, _active_key, _lock_ticket,
    _normalized_owner, _normalized_timestamp, _plan_assignment_transition,
    _recorded_now, _time, start_assignment, end_assignment,
)
from telephony.time_booking_identity import TechnicianBookingIdentity

RECEIPT = "TELECTRO Assignment Capture Receipt"
_operation = ContextVar("_assignment_capture_operation", default=None)
_failed = ContextVar("_assignment_capture_failed", default=False)


def _text(value, limit=140):
    if (type(value) is not str or not value.strip() or value != value.strip()
            or len(value) > limit):
        raise AssignmentHistoryError()


def _json(value):
    # Restrict to plain JSON data; no coercion of identities or arbitrary objects.
    def check(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise AssignmentHistoryError()
    check(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded) > 16000:
        raise AssignmentHistoryError()
    return encoded


def _owner_snapshot(owner):
    _normalized_owner(owner)
    if owner is None:
        return None
    return dict(user=owner.user, employee=owner.employee, company=owner.company)


def _owner_from_snapshot(value):
    if value is None:
        return None
    if type(value) is not dict or set(value) != {"user", "employee", "company"}:
        raise AssignmentHistoryError()
    owner = TechnicianBookingIdentity(**value)
    _normalized_owner(owner)
    return owner


def _validate_capture_receipt(doc):
    """Structural and semantic validation shared by controller and retry reader."""
    try:
        for field in ("event_id", "ticket", "operation_source", "actor"):
            _text(doc.get(field))
        event_at, recorded_at = _time(doc.get("event_at")), _time(doc.get("recorded_at"))
        _normalized_timestamp(event_at)
        _normalized_timestamp(recorded_at)
        if event_at > recorded_at:
            raise AssignmentHistoryError()
        parsed = {}
        for field in ("request_payload", "previous_owner", "new_owner", "result"):
            value = doc.get(field)
            if type(value) is not str:
                raise AssignmentHistoryError()
            parsed[field] = json.loads(value)
            if _json(parsed[field]) != value:
                raise AssignmentHistoryError()
        request = parsed["request_payload"]
        if type(request) is not dict or set(request) != {"reason", "request"}:
            raise AssignmentHistoryError()
        _text(request["reason"], 2000)
        if type(request["request"]) is not dict:
            raise AssignmentHistoryError()
        previous = _owner_from_snapshot(parsed["previous_owner"])
        new = _owner_from_snapshot(parsed["new_owner"])
        if previous and new and previous.user == new.user and previous != new:
            raise AssignmentHistoryError()
        result = parsed["result"]
        if (type(result) is not dict
                or set(result) != {"end_episode", "start_episode", "no_op"}
                or type(result["no_op"]) is not bool
                or result["no_op"] != (previous == new)):
            raise AssignmentHistoryError()
        for field, required in (
            ("end_episode", previous != new and previous is not None),
            ("start_episode", previous != new and new is not None),
        ):
            if required:
                _text(result[field])
            elif result[field] is not None:
                raise AssignmentHistoryError()
        if result["end_episode"] is not None and result["end_episode"] == result["start_episode"]:
            raise AssignmentHistoryError()
        return result
    except (ValueError, TypeError, OverflowError, KeyError) as exc:
        raise AssignmentHistoryError() from exc


@dataclass(frozen=True)
class _CaptureOperation:
    ticket: str
    actor: str
    db: object


@contextmanager
def _assignment_capture_operation(*, ticket, authorize):
    """Lock first, then authorize; yield a live operation capability.

    authorize(ticket, actor) must be trusted server code returning exactly True
    after checking permission for this operation (including receipt retrieval).
    This scope must begin BEFORE authoritative assignment inspection or mutation.
    The caller owns success commit, request validation, operation intent and all
    assignment writes. No intervening commits/rollbacks, DDL, external effects or
    swallowed capture failures are permitted. Failure rolls back the whole current
    transaction, including caller assignment writes, and propagates to the caller.
    """
    import frappe
    if _operation.get() is not None or not callable(authorize):
        raise AssignmentHistoryError()
    _text(ticket)
    actor = frappe.session.user
    _text(actor)
    if actor == "Guest":
        raise AssignmentHistoryError()
    db = frappe.local.db
    token = failed_token = None
    try:
        account = db.get_value("User", actor, ["enabled", "user_type"], as_dict=True)
        if not account or account.get("enabled") != 1 or account.get("user_type") != "System User":
            raise AssignmentHistoryError()
        _lock_ticket(ticket)
        if authorize(ticket, actor) is not True:
            raise AssignmentHistoryError()
        # No receipt/history queries occur on an unmigrated schema.
        for doctype in (RECEIPT, "TELECTRO Ticket Assignment History"):
            if not db.table_exists(doctype, cached=False):
                raise AssignmentHistoryError()
        operation = _CaptureOperation(ticket, actor, db)
        token = _operation.set(operation)
        failed_token = _failed.set(False)
        yield operation
        if _failed.get():
            raise AssignmentHistoryError()
    except BaseException:
        db.rollback()
        raise
    finally:
        if failed_token is not None:
            _failed.reset(failed_token)
        if token is not None:
            _operation.reset(token)


def _active_episodes(ticket):
    import frappe
    rows = frappe.db.sql(
        "SELECT name, ticket, technician_user, employee, company, state, active_key, "
        "effective_start, recorded_start, start_event_id, effective_end, recorded_end, "
        "ended_by, end_source, end_reason, end_event_id FROM "
        "`tabTELECTRO Ticket Assignment History` WHERE ticket=%s "
        "AND (state='Active' OR active_key IS NOT NULL) FOR UPDATE", ticket, as_dict=True)
    episodes = []
    for row in rows:
        _text(row.get("name"))
        _text(row.get("start_event_id"))
        identity = TechnicianBookingIdentity(row.get("technician_user"), row.get("employee"), row.get("company"))
        _normalized_owner(identity)
        if (row.get("ticket") != ticket or row.get("state") != "Active"
                or row.get("active_key") != _active_key(ticket, identity.user)
                or any(row.get(field) for field in (
                    "effective_end", "recorded_end", "ended_by", "end_source", "end_reason", "end_event_id"))):
            raise AssignmentHistoryError()
        episodes.append(_ActiveAssignmentEpisode(
            row["name"], identity, _time(row.get("effective_start")), _time(row.get("recorded_start"))))
    return episodes


def _capture_failure(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except BaseException:
            if _operation.get() is not None:
                _failed.set(True)
            raise
    return guarded


@_capture_failure
def _record_assignment_history(operation, *, event_id, source, reason, at,
                               request_payload, resolve_transition):
    """Persist one planner result and immutable receipt in the current transaction.

    request_payload is the complete normalized business request, including target
    and expected revision if applicable. It is compared on retry, never trusted as
    owner evidence. at is the original server event time, not the retry clock.
    resolve_transition() is trusted server code, called only for a NEW event under
    the ticket lock; it returns (previous_owner, new_owner, supported_transition).
    All assignment inspection and mutation must occur INSIDE resolve_transition:
    inspect previous ownership, execute the authorized assignment operation, then
    independently verify new ownership. Never mutate assignments before calling this
    recorder. On retry the callback is not called, so assignments remain untouched
    and original snapshots remain authoritative.

    A capability from the currently live authorized scope is mandatory. There are
    no internal commits or savepoints. Failures propagate and poison the scope:
    even a caught recorder error causes outer rollback when the scope exits.
    """
    import frappe
    if (type(operation) is not _CaptureOperation or _operation.get() is not operation
            or frappe.local.db is not operation.db or frappe.session.user != operation.actor):
        raise AssignmentHistoryError()
    _text(event_id)
    _text(source)
    _text(reason, 2000)
    _normalized_timestamp(at)
    if type(request_payload) is not dict or not callable(resolve_transition):
        raise AssignmentHistoryError()
    payload = _json(dict(reason=reason, request=request_payload))
    rows = frappe.db.sql(
        "SELECT name, event_id, ticket, operation_source, actor, event_at, recorded_at, "
        "request_payload, previous_owner, new_owner, result FROM "
        "`tabTELECTRO Assignment Capture Receipt` WHERE event_id=%s FOR UPDATE",
        event_id, as_dict=True)
    if len(rows) > 1:
        raise AssignmentHistoryError()
    if rows:
        row = rows[0]
        result = _validate_capture_receipt(row)
        if (row.get("event_id") != event_id or row.get("ticket") != operation.ticket
                or row.get("actor") != operation.actor or row.get("operation_source") != source
                or _time(row.get("event_at")) != at or row.get("request_payload") != payload):
            raise AssignmentHistoryError()
        _text(row.get("name"))
        return dict(receipt=row["name"], **result)
    previous, new, supported = resolve_transition()
    plan = _plan_assignment_transition(
        previous_owner=previous, new_owner=new, active_episodes=_active_episodes(operation.ticket),
        at=at, supported_transition=supported)
    recorded = _recorded_now()
    _normalized_timestamp(recorded)
    if at > recorded:
        raise AssignmentHistoryError()
    if new is not None and not plan.is_noop:
        # The existing writer independently resolves identity; require exact agreement.
        from telephony.time_booking_cooption import _require_recipient_identity
        if _require_recipient_identity(new.user) != new:
            raise AssignmentHistoryError()
    # Avoid adopting events written outside this recorder or partial prior writes.
    from telephony.time_booking_assignment_history import _event
    if _event("START", event_id) or _event("END", event_id):
        raise AssignmentHistoryError()
    common = dict(ticket=operation.ticket, actor=operation.actor, source=source,
                  reason=reason, event_id=event_id)
    ended = started = None
    if plan.end_episode is not None:
        ended = end_assignment(**common, user=previous.user, episode=plan.end_episode, effective_end=at)
    if plan.start_owner is not None:
        started = start_assignment(**common, user=new.user, effective_start=at)
        # Verify the writer persisted exactly the trusted identity, not a changed mapping.
        active = _active_episodes(operation.ticket)
        if len(active) != 1 or active[0].name != started or active[0].identity != new:
            raise AssignmentHistoryError()
    result = dict(end_episode=ended, start_episode=started, no_op=plan.is_noop)
    receipt = frappe.get_doc(dict(
        doctype=RECEIPT, event_id=event_id, ticket=operation.ticket, operation_source=source,
        actor=operation.actor, event_at=at, recorded_at=_recorded_now(), request_payload=payload,
        previous_owner=_json(_owner_snapshot(previous)), new_owner=_json(_owner_snapshot(new)),
        result=_json(result)))
    _validate_capture_receipt(receipt)
    receipt.insert(ignore_permissions=True)
    return dict(receipt=receipt.name, **result)
