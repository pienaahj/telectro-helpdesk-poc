"""Private grants governing Supervisor access to Phase 2 booked hours."""

from collections.abc import Mapping
from contextvars import ContextVar
from datetime import datetime
from hashlib import sha256
import json

import frappe
from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions
from frappe.utils import now_datetime

from telephony.customer_communication_privacy import classify_actor_roles
from telephony.time_booking_identity import (
    TechnicianBookingIdentity,
    TechnicianIdentityError,
    _resolve_technician_identity,
)
from telephony.time_booking_project_grant import _grant_savepoint

DOCTYPE = "TELECTRO Supervisor Reporting Grant"
SUPERVISOR_ROLE = "TELECTRO-POC Role - Supervisor Governance"
_SCOPE_FIELDS = ("supervisor_user", "employee", "technician_user", "company")
_GRANT_FIELDS = ("granted_by", "granted_at", "grant_reason")
_REVOCATION_FIELDS = ("revoked_by", "revoked_at", "revocation_reason")
_PERMISSION_CONTEXTS = {
    "Company": ("Company", "Employee", "Timesheet", "Timesheet Detail"),
    "Employee": ("Employee", "Timesheet", "Timesheet Detail"),
}
_transition = ContextVar("supervisor_reporting_grant_transition", default=None)


class SupervisorReportingGrantError(frappe.PermissionError):
    """The grant or reporting scope is unavailable."""

    def __init__(self):
        super().__init__("Supervisor reporting authority is unavailable.")


def _text(value, limit=140):
    return type(value) is str and 0 < len(value) <= limit and bool(value.strip()) and value.strip() == value


def _timestamp(value):
    if type(value) is str and len(value) >= 19 and value[10] in (" ", "T"):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise SupervisorReportingGrantError() from exc
    if type(value) is not datetime or value.tzinfo is not None:
        raise SupervisorReportingGrantError()
    return value


def _administrator():
    actor = getattr(frappe.session, "user", None)
    if actor != "Administrator":
        raise SupervisorReportingGrantError()
    return actor


def _require_supervisor(user):
    if not _text(user) or user in ("Administrator", "Guest"):
        raise SupervisorReportingGrantError()
    account = frappe.db.get_value("User", user, ["name", "enabled", "user_type"], as_dict=True)
    if not account or (account.name, account.enabled, account.user_type) != (user, 1, "System User"):
        raise SupervisorReportingGrantError()
    role = frappe.db.get_value("Role", SUPERVISOR_ROLE, ["name", "disabled"], as_dict=True)
    if not role or (role.name, role.disabled) != (SUPERVISOR_ROLE, 0):
        raise SupervisorReportingGrantError()
    roles = set(frappe.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User", "parentfield": "roles"},
        pluck="role",
        limit_page_length=0,
    ))
    if SUPERVISOR_ROLE not in roles or classify_actor_roles(roles) != "internal":
        raise SupervisorReportingGrantError()


def _active_key(grant):
    scope = (grant.get("supervisor_user"), grant.get("employee"), grant.get("company"))
    return sha256(json.dumps(scope).encode()).hexdigest()


def _validate_record(grant):
    if not all(_text(grant.get(field)) for field in _SCOPE_FIELDS):
        raise SupervisorReportingGrantError()
    if grant.get("granted_by") != "Administrator" or not _text(grant.get("grant_reason"), 2000):
        raise SupervisorReportingGrantError()
    granted_at = _timestamp(grant.get("granted_at"))
    revoked_at = grant.get("revoked_at")
    if revoked_at is None:
        if (
            grant.get("active_key") != _active_key(grant)
            or grant.get("revoked_by") not in (None, "")
            or grant.get("revocation_reason") not in (None, "")
        ):
            raise SupervisorReportingGrantError()
    elif (
        grant.get("active_key") is not None
        or grant.get("revoked_by") != "Administrator"
        or not _text(grant.get("revocation_reason"), 2000)
        or _timestamp(revoked_at) < granted_at
    ):
        raise SupervisorReportingGrantError()
    return granted_at


def validate_supervisor_reporting_grant(doc, previous):
    """Accept only a writer-owned insert or a one-way revocation."""
    transition = _transition.get()
    if transition is None or transition[0] is not doc or transition[1] != (previous is None):
        raise SupervisorReportingGrantError()
    granted_at = _validate_record(doc)
    if previous is None:
        if doc.get("revoked_at") is not None:
            raise SupervisorReportingGrantError()
        return
    if (
        previous.get("revoked_at") is not None
        or doc.get("revoked_at") is None
        or any(doc.get(field) != previous.get(field) for field in (*_SCOPE_FIELDS, "granted_by", "grant_reason"))
        or granted_at != _validate_record(previous)
    ):
        raise SupervisorReportingGrantError()


def _save_transition(doc, *, insert=False):
    token = _transition.set((doc, insert))
    try:
        if insert:
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)
    finally:
        _transition.reset(token)


def create_supervisor_reporting_grant(*, supervisor_user, employee, reason):
    """Grant the exact current Employee mapping. The caller owns the transaction."""
    actor = _administrator()
    if not _text(supervisor_user) or not _text(employee) or not _text(reason, 2000):
        raise SupervisorReportingGrantError()
    with _grant_savepoint():
        # Lock the subject row before opening a snapshot for current identity checks.
        subject = frappe.db.get_value(
            "Employee", employee, ["name", "user_id", "company"], as_dict=True, for_update=True,
        )
        if not subject or subject.name != employee:
            raise SupervisorReportingGrantError()
        _require_supervisor(supervisor_user)
        try:
            identity = _resolve_technician_identity(subject.user_id)
        except TechnicianIdentityError as exc:
            raise SupervisorReportingGrantError() from exc
        if identity != TechnicianBookingIdentity(subject.user_id, employee, subject.company):
            raise SupervisorReportingGrantError()
        grant = frappe.get_doc({
            "doctype": DOCTYPE,
            "supervisor_user": supervisor_user,
            "employee": employee,
            "technician_user": identity.user,
            "company": identity.company,
            "granted_by": actor,
            "granted_at": now_datetime(),
            "grant_reason": reason,
        })
        grant.active_key = _active_key(grant)
        try:
            _save_transition(grant, insert=True)
        except frappe.UniqueValidationError as exc:
            raise SupervisorReportingGrantError() from exc
        return grant.name


def revoke_supervisor_reporting_grant(*, grant_name, reason):
    """Revoke that exact grant even after role loss or an Employee remap."""
    actor = _administrator()
    if not _text(grant_name) or not _text(reason, 2000):
        raise SupervisorReportingGrantError()
    with _grant_savepoint():
        try:
            grant = frappe.get_doc(DOCTYPE, grant_name, for_update=True)
        except frappe.DoesNotExistError as exc:
            raise SupervisorReportingGrantError() from exc
        if grant.name != grant_name or grant.revoked_at is not None:
            raise SupervisorReportingGrantError()
        grant.update({
            "revoked_by": actor,
            "revoked_at": now_datetime(),
            "revocation_reason": reason,
            "active_key": None,
        })
        _save_transition(grant)


def _allowed_identity(identity, user_permissions):
    for doctype, value in (("Company", identity.company), ("Employee", identity.employee)):
        for context in _PERMISSION_CONTEXTS[doctype]:
            allowed = get_allowed_docs_for_doctype(user_permissions.get(doctype, ()), context)
            if allowed and value not in allowed:
                return False
    return True


def resolve_supervisor_reporting_scope() -> frozenset[TechnicianBookingIdentity]:
    """Return exact current roster tuples for the session user, without grant details.

    A consumer matches each booking's stored tuple and independently authorizes
    its Customer and linked records before disclosing data or aggregating hours.
    """
    supervisor = getattr(frappe.session, "user", None)
    _require_supervisor(supervisor)
    grants = frappe.get_all(
        DOCTYPE,
        filters={"supervisor_user": supervisor, "revoked_at": ["is", "not set"]},
        fields=[*_SCOPE_FIELDS, *_GRANT_FIELDS, *_REVOCATION_FIELDS, "active_key"],
        limit_page_length=0,
    )
    if not grants:
        return frozenset()
    restrictions = get_user_permissions(supervisor)
    # An unavailable policy must not be interpreted as an unrestricted result.
    if not isinstance(restrictions, Mapping):
        raise SupervisorReportingGrantError()
    evaluated_at = _timestamp(now_datetime())
    scope = set()
    for grant in grants:
        if grant.supervisor_user != supervisor or grant.revoked_at is not None:
            raise SupervisorReportingGrantError()
        if _validate_record(grant) > evaluated_at:
            raise SupervisorReportingGrantError()
        recorded = TechnicianBookingIdentity(grant.technician_user, grant.employee, grant.company)
        try:
            current = _resolve_technician_identity(recorded.user)
        except TechnicianIdentityError:
            continue
        if current == recorded and _allowed_identity(recorded, restrictions):
            scope.add(recorded)
    return frozenset(scope)
