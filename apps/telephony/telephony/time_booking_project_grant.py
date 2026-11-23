"""Private Project booking grant periods and interval authorization."""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import uuid4

from telephony.time_booking_coverage import TemporalCoverageError, covers_booking_interval
from telephony.time_booking_identity import (
    TechnicianBookingIdentity,
    TechnicianIdentityError,
    _resolve_technician_identity,
)


DOCTYPE = "TELECTRO Project Booking Grant"
_transition = ContextVar("project_booking_grant_transition", default=None)


class ProjectBookingGrantError(PermissionError):
    """A grant or Project booking reference is unavailable."""

    def __init__(self):
        super().__init__("Project booking grant is unavailable.")


def _identifier(value):
    return type(value) is str and bool(value.strip()) and value == value.strip()


def _local_time(value):
    if type(value) is not datetime or value.tzinfo is not None:
        raise ProjectBookingGrantError()
    return value


def _stored_time(value):
    if type(value) is str:
        try:
            if len(value) < 19 or value[10] not in (" ", "T"):
                raise ValueError()
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ProjectBookingGrantError() from exc
    return _local_time(value)


@dataclass(frozen=True)
class ProjectBookingGrantPeriod:
    identity: TechnicianBookingIdentity
    project: str
    project_created_at: datetime
    permitted_tasks: frozenset[tuple[str, datetime]]
    effective_start: datetime
    effective_end: datetime | None = None

    def __post_init__(self):
        _scope(self.identity, self.project)
        _local_time(self.project_created_at)
        if type(self.permitted_tasks) is not frozenset:
            raise ProjectBookingGrantError()
        names = set()
        for entry in self.permitted_tasks:
            if type(entry) is not tuple or len(entry) != 2:
                raise ProjectBookingGrantError()
            task, created_at = entry
            if not _identifier(task) or task in names:
                raise ProjectBookingGrantError()
            names.add(task)
            _local_time(created_at)
        _local_time(self.effective_start)
        if self.effective_end is not None and _local_time(self.effective_end) <= self.effective_start:
            raise ProjectBookingGrantError()


def _scope(identity, project):
    if type(identity) is not TechnicianBookingIdentity or not all(
        _identifier(value) for value in (identity.user, identity.employee, identity.company, project)
    ) or identity.user in ("Guest", "Administrator"):
        raise ProjectBookingGrantError()
    return {
        "technician_user": identity.user,
        "employee": identity.employee,
        "company": identity.company,
        "project": project,
    }


def _active_key(identity, project):
    scope = _scope(identity, project)
    return sha256(json.dumps(list(scope.values())).encode()).hexdigest()


def covers_project_booking(
    *, identity, project, project_company, project_created_at, start, end, periods,
    evaluated_at, task=None, task_project=None, task_created_at=None,
):
    """Check trusted grant periods and current Project/Task metadata without I/O."""
    _scope(identity, project)
    _local_time(evaluated_at)
    _local_time(project_created_at)
    if project_company != identity.company:
        raise ProjectBookingGrantError()
    if task is not None:
        if not _identifier(task) or task_project != project:
            raise ProjectBookingGrantError()
        _local_time(task_created_at)
    elif task_project is not None or task_created_at is not None:
        raise ProjectBookingGrantError()
    if type(periods) not in (tuple, list):
        raise ProjectBookingGrantError()

    validated = []
    for period in periods:
        if (
            type(period) is not ProjectBookingGrantPeriod
            or period.identity != identity
            or period.project != project
            or period.project_created_at != project_created_at
            or period.effective_start > evaluated_at
            or (period.effective_end is not None and period.effective_end > evaluated_at)
        ):
            raise ProjectBookingGrantError()
        validated.append(period)

    authority = []
    previous_end = None
    saw_open_period = False
    for period in sorted(validated, key=lambda item: item.effective_start):
        if saw_open_period or (previous_end is not None and period.effective_start < previous_end):
            raise ProjectBookingGrantError()
        saw_open_period = period.effective_end is None
        stop = period.effective_end or evaluated_at
        previous_end = stop
        task_allowed = task is None or (task, task_created_at) in period.permitted_tasks
        if period.effective_start < stop and task_allowed:
            authority.append((period.effective_start, stop))
    try:
        return covers_booking_interval(start, end, authority, evaluated_at=evaluated_at)
    except TemporalCoverageError as exc:
        raise ProjectBookingGrantError() from exc


def _task_json(tasks):
    return json.dumps(
        {name: created_at.isoformat() for name, created_at in sorted(tasks)},
        separators=(",", ":"),
    )


def project_booking_grant_period(record):
    """Decode a persisted grant, rejecting inconsistent state and audit data."""
    try:
        raw = record.get("permitted_tasks")
        stored_tasks = json.loads(raw)
        if type(stored_tasks) is not dict or not all(_identifier(task) for task in stored_tasks):
            raise ValueError()
        tasks = frozenset((task, _stored_time(created)) for task, created in stored_tasks.items())
        if raw != _task_json(tasks):
            raise ValueError()
    except (TypeError, ValueError) as exc:
        raise ProjectBookingGrantError() from exc

    identity = TechnicianBookingIdentity(
        record.get("technician_user"), record.get("employee"), record.get("company")
    )
    end = record.get("effective_end")
    period = ProjectBookingGrantPeriod(
        identity, record.get("project"), _stored_time(record.get("project_created_at")), tasks,
        _stored_time(record.get("effective_start")),
        _stored_time(end) if end is not None else None,
    )
    if record.get("granted_by") != "Administrator" or not _identifier(record.get("grant_reason")):
        raise ProjectBookingGrantError()
    if end is None:
        if (
            record.get("active_key") != _active_key(identity, period.project)
            or record.get("ended_by") or record.get("end_reason")
        ):
            raise ProjectBookingGrantError()
    elif (
        record.get("active_key")
        or record.get("ended_by") != "Administrator"
        or not _identifier(record.get("end_reason"))
    ):
        raise ProjectBookingGrantError()
    return period


def _administrator():
    import frappe

    if getattr(frappe.session, "user", None) != "Administrator":
        raise ProjectBookingGrantError()
    return frappe.session.user


def _lock_project(project):
    import frappe

    row = frappe.db.get_value(
        "Project", project, ["name", "company", "creation"], as_dict=True, for_update=True
    )
    if row and row.name != project:
        raise ProjectBookingGrantError()
    return row


def _resolve_tasks(project, tasks):
    if not tasks:
        return frozenset()
    import frappe

    rows = frappe.db.get_values(
        "Task", {"name": ["in", sorted(tasks)]}, ["name", "project", "creation"],
        for_update=True, order_by="name asc",
    )
    if {name for name, parent, _ in rows if parent == project} != tasks:
        raise ProjectBookingGrantError()
    return frozenset((name, _stored_time(created)) for name, _, created in rows)


@contextmanager
def _grant_savepoint():
    import frappe

    name = "project_grant_" + uuid4().hex
    frappe.db.savepoint(name)
    try:
        yield
    except BaseException:
        # Frappe's savepoint context manager suppresses caught exceptions.
        # A failed grant transition must also fail for its caller.
        frappe.db.rollback(save_point=name)
        frappe.db.release_savepoint(name)
        raise
    else:
        frappe.db.release_savepoint(name)


def _save_transition(doc, *, insert=False):
    token = _transition.set((doc, insert))
    try:
        if insert:
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)
    finally:
        _transition.reset(token)


def validate_project_booking_grant(doc, previous):
    """Accept only writer-owned inserts or a single close of an existing period."""
    transition = _transition.get()
    if transition is None or transition[0] is not doc or transition[1] != (previous is None):
        raise ProjectBookingGrantError()
    period = project_booking_grant_period(doc)
    if previous is None:
        if period.effective_end is not None:
            raise ProjectBookingGrantError()
        return
    prior = project_booking_grant_period(previous)
    if (
        prior.effective_end is not None
        or period.effective_end is None
        or period.identity != prior.identity
        or period.project != prior.project
        or period.project_created_at != prior.project_created_at
        or period.effective_start != prior.effective_start
        or period.permitted_tasks != prior.permitted_tasks
        or doc.get("granted_by") != previous.get("granted_by")
        or doc.get("grant_reason") != previous.get("grant_reason")
    ):
        raise ProjectBookingGrantError()


def _close(doc, *, now, actor, reason):
    period = project_booking_grant_period(doc)
    if period.effective_end is not None or now <= period.effective_start:
        raise ProjectBookingGrantError()
    doc.update(dict(effective_end=now, ended_by=actor, end_reason=reason, active_key=None))
    _save_transition(doc)


def set_project_booking_grant(*, technician_user, project, permitted_tasks, reason, expected_grant=None):
    """Open a grant or replace its Task set. The caller owns the transaction."""
    import frappe
    from frappe.utils import now_datetime

    actor = _administrator()
    if (
        not all(_identifier(value) for value in (technician_user, project, reason))
        or (expected_grant is not None and not _identifier(expected_grant))
        or type(permitted_tasks) not in (tuple, list)
        or not all(_identifier(task) for task in permitted_tasks)
    ):
        raise ProjectBookingGrantError()
    tasks = frozenset(permitted_tasks)

    with _grant_savepoint():
        project_row = _lock_project(project)
        try:
            identity = _resolve_technician_identity(technician_user)
        except TechnicianIdentityError as exc:
            raise ProjectBookingGrantError() from exc
        if not project_row or project_row.company != identity.company:
            raise ProjectBookingGrantError()
        project_created_at = _stored_time(project_row.creation)
        task_references = _resolve_tasks(project, tasks)
        scope = _scope(identity, project)
        key = _active_key(identity, project)
        active = frappe.db.get_value(DOCTYPE, {"active_key": key}, "name", for_update=True)
        if active != expected_grant:
            raise ProjectBookingGrantError()
        now = _local_time(now_datetime())
        if active:
            current = frappe.get_doc(DOCTYPE, active, for_update=True)
            period = project_booking_grant_period(current)
            if (
                period.identity != identity
                or period.project != project
                or period.project_created_at != project_created_at
                or period.effective_end is not None
            ):
                raise ProjectBookingGrantError()
            if period.permitted_tasks == task_references:
                return active
            _close(current, now=now, actor=actor, reason=reason)
        else:
            last_end = frappe.db.get_value(
                DOCTYPE, {**scope, "effective_end": ["is", "set"]}, "effective_end",
                order_by="effective_end desc", for_update=True,
            )
            if last_end is not None and now < _stored_time(last_end):
                raise ProjectBookingGrantError()

        doc = frappe.get_doc({
            "doctype": DOCTYPE, **scope, "project_created_at": project_created_at,
            "effective_start": now, "active_key": key,
            "permitted_tasks": _task_json(task_references), "granted_by": actor, "grant_reason": reason,
        })
        _save_transition(doc, insert=True)
        return doc.name


def revoke_project_booking_grant(*, grant_name, reason):
    """Close that exact active period, even if the recipient is now ineligible."""
    import frappe
    from frappe.utils import now_datetime

    actor = _administrator()
    if not _identifier(grant_name) or not _identifier(reason):
        raise ProjectBookingGrantError()
    with _grant_savepoint():
        scope = frappe.db.get_value(DOCTYPE, grant_name, ["name", "project"], as_dict=True)
        if not scope or scope.name != grant_name:
            raise ProjectBookingGrantError()
        _lock_project(scope.project)
        doc = frappe.get_doc(DOCTYPE, grant_name, for_update=True)
        _close(doc, now=_local_time(now_datetime()), actor=actor, reason=reason)
