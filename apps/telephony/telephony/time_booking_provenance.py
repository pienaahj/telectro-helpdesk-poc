"""Pure provenance policy; trusted integration supplies persisted state.

No Frappe, database, hooks or endpoints. None as persisted means new only when
independently established by trusted integration, never a client is_new flag.
"""

import asyncio
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from telephony.time_booking_identity import TechnicianBookingIdentity


_MARKER = "custom_telectro_booking_origin"


class BookingProvenanceError(PermissionError):
    def __init__(self):
        super().__init__("Booking provenance is not permitted.")


@dataclass
class _CreationGrant:
    document: Mapping[str, object]
    identity: TechnicianBookingIdentity
    thread: int
    task: object
    active: bool = True
    completed: bool = False


_creation_grant: ContextVar[_CreationGrant | None] = ContextVar(
    "telectro_booking_creation_grant", default=None
)


def _execution_owner():
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    return threading.get_ident(), task


def _marker(document):
    if not isinstance(document, Mapping):
        raise BookingProvenanceError()
    value = document.get(_MARKER)
    if value is None:
        return ""
    if type(value) is not str:
        raise BookingProvenanceError()
    if value == "":
        return ""
    if value == "Phase 2":
        return value
    raise BookingProvenanceError()


def _creation_identity(document, identity):
    if (
        not isinstance(document, Mapping)
        or not isinstance(identity, TechnicianBookingIdentity)
        or not all(isinstance(v, str) and bool(v.strip()) for v in (
            identity.user, identity.employee, identity.company
        ))
        or identity.user in ("Guest", "Administrator")
        or document.get("doctype") != "Timesheet"
        or _marker(document) != "Phase 2"
        or document.get("employee") != identity.employee
        or document.get("company") != identity.company
        or document.get("user") != identity.user
        or type(document.get("docstatus")) is not int
        or document.get("docstatus") != 0
    ):
        raise BookingProvenanceError()


def _require_grant(document, identity):
    grant = _creation_grant.get()
    thread, task = _execution_owner()
    if (
        grant is None or not grant.active or grant.completed
        or grant.document is not document or grant.identity != identity
        or grant.thread != thread or grant.task is not task
    ):
        raise BookingProvenanceError()
    _creation_identity(document, identity)
    return grant


@contextmanager
def _creation_authorization(
    document: Mapping[str, object], identity: TechnicianBookingIdentity
) -> Iterator[None]:
    """Private capability for one trusted insertion attempt.

    The caller resolves the session identity, constructs the document and enters
    this scope exactly around one insert. Hooks may check repeatedly. On success
    the caller invokes _complete_creation before leaving; on failure it leaves
    immediately. Do not wrap retries or multiple inserts in one scope.
    """
    if _creation_grant.get() is not None:
        raise BookingProvenanceError()
    _creation_identity(document, identity)
    thread, task = _execution_owner()
    grant = _CreationGrant(document, identity, thread, task)
    token = _creation_grant.set(grant)
    try:
        yield
    finally:
        # Also revoke copied contexts retaining this grant object.
        grant.active = False
        _creation_grant.reset(token)


def _complete_creation(
    document: Mapping[str, object], identity: TechnicianBookingIdentity
) -> None:
    """Trusted caller signals insert success; subsequent checks must fail."""
    _require_grant(document, identity).completed = True


def validate_provenance_transition(
    document: Mapping[str, object],
    *,
    persisted: Mapping[str, object] | None,
    identity: TechnicianBookingIdentity | None = None,
) -> None:
    """Validate markers and managed identities, without mutation.

    Neither persisted state nor identity authenticity is established here.
    Existing unmarked native records retain their native identity workflows.
    This does not enforce lifecycle, ownership or business-field permissions.
    """
    proposed_marker = _marker(document)
    if persisted is None:
        if proposed_marker:
            _require_grant(document, identity)
        return

    previous_marker = _marker(persisted)
    if previous_marker != proposed_marker:
        raise BookingProvenanceError()
    if previous_marker == "Phase 2":
        for field in ("employee", "company", "user"):
            previous = persisted.get(field)
            if (
                not isinstance(previous, str) or not previous.strip()
                or document.get(field) != previous
            ):
                raise BookingProvenanceError()
