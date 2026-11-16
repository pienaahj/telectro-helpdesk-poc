"""Unregistered Timesheet provenance checks for supported pre-write events.

LIMITATIONS: ignore_validate can skip before_cancel and
before_update_after_submit. before_change protects db_set, not all writes.
db_update_all, db_update, database setters and SQL bypass these events. Late
trusted handlers may change state after checks. This is not complete lifecycle
or ownership enforcement and grants no native Timesheet permissions.

Before activation, install the marker separately, register the reviewed wrapper
and events together, and require matching final-name evidence in controller
integration before managed completion. No registration or activation occurs here.
"""

from collections.abc import Mapping

from telephony import time_booking_provenance_adapter as _adapter
from telephony.time_booking_provenance import (
    BookingProvenanceError,
    validate_provenance_transition,
)


_EVENTS = (
    "before_insert", "before_validate", "before_save", "before_submit",
    "before_cancel", "before_update_after_submit", "before_change",
)
_INSERT_EVENTS = ("before_insert", "before_validate", "before_save", "before_submit")


def _validate_timesheet_provenance(doc, method=None) -> None:
    """Future event entry point. Event names and insertion evidence are trusted
    only as internal integration inputs; this callable is not whitelisted.
    """
    if type(method) is not str or method not in _EVENTS:
        raise BookingProvenanceError()
    if method == "before_change":
        _validate_existing_provenance(doc)
        return
    frame = _adapter._current_insertion(doc)
    if frame is not None:
        _validate_insertion_provenance(doc, method, frame)
    elif method == "before_insert":
        raise BookingProvenanceError()
    else:
        _validate_existing_provenance(doc)


def _validate_existing_provenance(doc) -> None:
    """Require a fresh six-field persisted snapshot, never a client previous row."""
    view = _adapter._TimesheetDocumentView(doc)
    if type(view["doctype"]) is not str or view["doctype"] != "Timesheet":
        raise BookingProvenanceError()
    name = view["name"]
    if type(name) is not str or not name.strip():
        raise BookingProvenanceError()
    persisted = _adapter._load_persisted_provenance(name)
    # Reassert the reader contract at this boundary; no malformed/missing
    # evidence may be interpreted as new. All accepted values are scalars.
    if (
        not isinstance(persisted, Mapping)
        or set(persisted) != set(_adapter._PERSISTED_FIELDS)
        or type(persisted["name"]) is not str
        or persisted["name"] != name
        or type(persisted["docstatus"]) is not int
        or persisted["docstatus"] not in (0, 1, 2)
    ):
        raise BookingProvenanceError()
    for key in ("custom_telectro_booking_origin", "employee", "company", "user"):
        value = persisted[key]
        if value is not None and type(value) is not str:
            raise BookingProvenanceError()
    validate_provenance_transition(view, persisted=persisted)


def _validate_insertion_provenance(doc, method, frame) -> None:
    """Reuse the exact view/grant; final-name absence is a before_save duty."""
    if (
        type(frame) is not _adapter._InsertionFrame
        or type(method) is not str or method not in _INSERT_EVENTS
        or _adapter._current_insertion(doc) is not frame
        or frame.document is not doc
    ):
        raise BookingProvenanceError()
    view = frame.view
    if type(view["doctype"]) is not str or view["doctype"] != "Timesheet":
        raise BookingProvenanceError()
    if frame.identity is not None:
        flags = getattr(doc, "flags", None)
        if not isinstance(flags, Mapping) or flags.get("ignore_validate"):
            raise BookingProvenanceError()
    validate_provenance_transition(view, persisted=None, identity=frame.identity)
    if frame.identity is not None:
        if method == "before_save":
            _adapter._verify_final_name_absence(frame, doc)
        elif frame.absence.attempted:
            _adapter._require_final_name_absence(frame, doc)
