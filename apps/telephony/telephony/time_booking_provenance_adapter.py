"""Private live Mapping bridge; no lifecycle or database integration."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from frappe.model.docstatus import DocStatus

from telephony.time_booking_provenance import BookingProvenanceError


_FIELDS = (
    "doctype", "name", "custom_telectro_booking_origin",
    "employee", "company", "user", "docstatus",
)


def _normalize_docstatus(value: object) -> int:
    """Accept only built-in int or the exact installed Frappe DocStatus type."""
    if type(value) is int:
        status = value
    elif type(value) is DocStatus:
        status = int(value)
    else:
        raise BookingProvenanceError()
    if status not in (0, 1, 2):
        raise BookingProvenanceError()
    return status


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class _TimesheetDocumentView(Mapping[str, object]):
    """Read-only live projection with a fixed underlying object reference.

    The underlying Document remains mutable. Retain this exact view instance
    throughout any pure-policy creation grant; constructing another view does
    not transfer authorization. This view does not establish snapshot trust.
    """

    _document: object

    def __post_init__(self) -> None:
        if not callable(getattr(self._document, "get", None)):
            raise BookingProvenanceError()

    def __getitem__(self, key: str) -> object:
        if type(key) is not str or key not in _FIELDS:
            raise KeyError(key)
        value = self._document.get(key)
        if key == "docstatus":
            return _normalize_docstatus(value)
        return value

    def __iter__(self) -> Iterator[str]:
        return iter(_FIELDS)

    def __len__(self) -> int:
        return len(_FIELDS)

# Integration obligations before activation:
# - Only a trusted insert wrapper may open an insertion attempt.
# - Existing updates require a fresh persisted row; absence is not creation.
# - Check final-name absence before insertion; never adopt a name collision.
# - Managed creation must reject ignore_if_duplicate in that future wrapper.
# - Complete only after native insert returns successfully, never on a hook or
#   row-presence signal. Completion does not commit the database transaction.

from contextlib import contextmanager
from contextvars import ContextVar
from types import MappingProxyType

from telephony.time_booking_identity import TechnicianBookingIdentity
from telephony.time_booking_provenance import (
    _complete_creation,
    _creation_authorization,
    _creation_identity,
    _execution_owner,
)


@dataclass
class _CapabilityState:
    active: bool = True
    consumed: bool = False
    completed: bool = False


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class _CreationIntent:
    document: object
    view: _TimesheetDocumentView
    identity: TechnicianBookingIdentity
    owner: tuple
    state: _CapabilityState


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class _FinalNameAbsence:
    frame: object
    document: object
    name: str


@dataclass
class _AbsenceState:
    attempted: bool = False
    evidence: _FinalNameAbsence | None = None


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class _InsertionFrame:
    document: object
    view: _TimesheetDocumentView
    identity: TechnicianBookingIdentity | None
    owner: tuple
    state: _CapabilityState
    absence: _AbsenceState = field(default_factory=_AbsenceState)


_intent: ContextVar[_CreationIntent | None] = ContextVar(
    "telectro_booking_adapter_intent", default=None
)
_frames: ContextVar[tuple[_InsertionFrame, ...]] = ContextVar(
    "telectro_booking_adapter_frames", default=()
)


def _check_capability(capability) -> None:
    thread, task = _execution_owner()
    if (
        not capability.state.active
        or capability.owner[0] != thread
        or capability.owner[1] is not task
    ):
        raise BookingProvenanceError()


def _checked_frames() -> tuple[_InsertionFrame, ...]:
    frames = _frames.get()
    for frame in frames:
        _check_capability(frame)
    intent = _intent.get()
    if intent is not None:
        _check_capability(intent)
    return frames


@contextmanager
def _phase2_creation_intent(
    document: object, identity: TechnicianBookingIdentity
) -> Iterator[None]:
    """Private one-use intent; identity authenticity is the trusted caller's duty.

    Never accept this capability from a client. This scope performs no insert,
    permissions change, site initialization or database operation.
    """
    frames = _checked_frames()
    if _intent.get() is not None or any(f.identity is not None for f in frames):
        raise BookingProvenanceError()
    if type(identity) is not TechnicianBookingIdentity or not all(
        type(value) is str and bool(value.strip())
        for value in (identity.user, identity.employee, identity.company)
    ):
        raise BookingProvenanceError()
    view = _TimesheetDocumentView(document)
    _creation_identity(view, identity)
    intent = _CreationIntent(document, view, identity, _execution_owner(), _CapabilityState())
    token = _intent.set(intent)
    try:
        yield
    finally:
        intent.state.active = False
        _intent.reset(token)


@contextmanager
def _insertion_attempt(document: object) -> Iterator[_InsertionFrame]:
    """Evidence for one future wrapper call, never evidence of DB row absence.

    Native attempts receive no managed creation grant. Context exit always
    revokes evidence; it does not imply successful native insertion.
    """
    frames = _checked_frames()
    if any(f.document is document for f in frames):
        raise BookingProvenanceError()
    intent = _intent.get()
    managed = False
    if intent is not None:
        if not intent.state.consumed:
            if intent.document is not document:
                raise BookingProvenanceError()
            intent.state.consumed = True
            managed = True
        elif intent.document is document:
            raise BookingProvenanceError()
    if managed:
        if any(f.identity is not None for f in frames):
            raise BookingProvenanceError()
        view, identity = intent.view, intent.identity
    else:
        view, identity = _TimesheetDocumentView(document), None
    frame = _InsertionFrame(document, view, identity, _execution_owner(), _CapabilityState())
    token = _frames.set(frames + (frame,))
    try:
        if managed:
            with _creation_authorization(view, identity):
                yield frame
        else:
            yield frame
    finally:
        frame.absence.evidence = None
        frame.state.active = False
        _frames.reset(token)


def _current_insertion(document: object) -> _InsertionFrame | None:
    """Return only the innermost exact-Document frame in this execution owner."""
    frames = _checked_frames()
    if frames and frames[-1].document is document:
        return frames[-1]
    return None


def _complete_insertion(
    frame: _InsertionFrame,
    document: object,
    identity: TechnicianBookingIdentity | None = None,
) -> None:
    """Private success signal, called only after the future native insert returns.

    This cannot prove success itself. The trusted wrapper must supply that fact.
    No transaction is committed, and the frame lives until its context exits.
    """
    if (
        type(frame) is not _InsertionFrame
        or _current_insertion(document) is not frame
        or frame.document is not document
        or frame.identity is not identity
        or frame.state.completed
    ):
        raise BookingProvenanceError()
    if identity is not None:
        _complete_creation(frame.view, identity)
    frame.state.completed = True


_PERSISTED_FIELDS = (
    "name", "custom_telectro_booking_origin", "employee", "company", "user", "docstatus",
    "creation",
)


def _load_persisted_provenance(name: str) -> Mapping[str, object] | None:
    """Bounded locking read, unused until separately authorized integration.

    No row is not proof of creation. Locks and transaction lifetime belong to
    the caller. Infrastructure errors propagate; no permissions are granted.
    """
    if type(name) is not str or not name.strip():
        raise BookingProvenanceError()
    import frappe

    row = frappe.db.get_value(
        "Timesheet",
        name,
        list(_PERSISTED_FIELDS),
        as_dict=True,
        order_by=None,
        cache=False,
        for_update=True,
        skip_locked=False,
        wait=True,
    )
    if row is None:
        return None
    if not isinstance(row, Mapping) or any(key not in row for key in _PERSISTED_FIELDS):
        raise BookingProvenanceError()
    snapshot = {key: row[key] for key in _PERSISTED_FIELDS}
    if type(snapshot["name"]) is not str or snapshot["name"] != name:
        raise BookingProvenanceError()
    for key in ("custom_telectro_booking_origin", "employee", "company", "user"):
        value = snapshot[key]
        if value is not None and type(value) is not str:
            raise BookingProvenanceError()
    if snapshot["custom_telectro_booking_origin"] not in (None, "", "Phase 2"):
        raise BookingProvenanceError()
    snapshot["docstatus"] = _normalize_docstatus(snapshot["docstatus"])
    return MappingProxyType(snapshot)


def _absence_frame_name(frame: _InsertionFrame, document: object) -> str:
    if (
        type(frame) is not _InsertionFrame
        or _current_insertion(document) is not frame
        or frame.document is not document
        or frame.identity is None
        or frame.state.completed
    ):
        raise BookingProvenanceError()
    name = frame.view["name"]
    if type(name) is not str or not name.strip():
        if frame.absence.attempted:
            frame.absence.evidence = None
        raise BookingProvenanceError()
    return name


def _require_final_name_absence(frame: _InsertionFrame, document: object) -> None:
    """Require live attempt/name evidence, never grant creation authorization.

    Future controller integration must call this before managed completion.
    The current controller deliberately remains unchanged and does not do so.
    """
    name = _absence_frame_name(frame, document)
    evidence = frame.absence.evidence
    if (
        not frame.absence.attempted
        or type(evidence) is not _FinalNameAbsence
        or evidence.frame is not frame
        or evidence.document is not document
        or evidence.name != name
    ):
        if frame.absence.attempted:
            frame.absence.evidence = None
        raise BookingProvenanceError()


def _verify_final_name_absence(frame: _InsertionFrame, document: object) -> None:
    """One locking read at the managed pre-write checkpoint; no retry or commit."""
    name = _absence_frame_name(frame, document)
    if frame.absence.attempted:
        _require_final_name_absence(frame, document)
        return
    frame.absence.attempted = True
    if _load_persisted_provenance(name) is not None:
        raise BookingProvenanceError()
    # A reader exception leaves attempted=True and no evidence. Recheck live
    # binding/name after the read before recording any successful absence.
    if _absence_frame_name(frame, document) != name:
        raise BookingProvenanceError()
    frame.absence.evidence = _FinalNameAbsence(frame, document, name)
