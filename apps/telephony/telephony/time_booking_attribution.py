"""Managed Timesheet Detail pre-creation attribution and write boundaries."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import copy
from datetime import timedelta

import frappe

from telephony.time_booking_provenance import BookingProvenanceError, _execution_owner
from telephony.time_booking_ticket_interval import _timestamp, ticket_interval_changed


FIELD = "custom_telectro_pre_creation_us"
UNSET = -1
MAX_US = 86_400_000_000
DETAIL = "Timesheet Detail"
CHILD_HANDLER = "telephony.time_booking_attribution.protect_child"
CHILD_EVENTS = (
    "before_insert", "before_validate", "before_save", "before_submit",
    "before_cancel", "before_update_after_submit", "before_change", "on_trash",
)
_ORIGIN = "custom_telectro_booking_origin"
_BOUND = ("custom_work_context", "custom_hd_ticket", "from_time", "to_time", FIELD, "custom_hd_customer")
_CHILD_FIELDS = ("name", "parent", "parenttype", "parentfield", *_BOUND)
_write = ContextVar("telectro_attribution_write", default=None)


class AttributionUnavailable(ValueError):
    def __init__(self):
        super().__init__("Pre-creation attribution is unavailable.")


def schema_ready():
    return frappe.get_meta(DETAIL).has_field(FIELD) and frappe.db.has_column(DETAIL, FIELD)


def _native_schema_ready(rows):
    if frappe.db.has_column(DETAIL, FIELD):
        return True
    meta = frappe.get_meta(DETAIL)
    if not meta.has_field(FIELD):
        return False

    # Frappe derives SQL columns from metadata. In a partial installation,
    # omit only the missing column on these documents, never on cached meta.
    local_meta = copy(meta)
    local_meta._valid_columns = [name for name in meta.get_valid_columns() if name != FIELD]
    for row in rows:
        row.meta = local_meta
    return False


def _microseconds(delta):
    return delta // timedelta(microseconds=1)


def _valid_value(row, value):
    if type(value) is not int or not UNSET <= value <= MAX_US:
        return False
    if value == UNSET:
        return True
    start, end = _timestamp(row.get("from_time")), _timestamp(row.get("to_time"))
    return (
        row.get("custom_work_context") == "Helpdesk"
        and start is not None and end is not None and start < end
        and value <= _microseconds(end - start)
    )


def _require_child_protection():
    child_hooks = frappe.get_doc_hooks().get(DETAIL, {})
    if any(tuple(child_hooks.get(event, ())) != (CHILD_HANDLER,) for event in CHILD_EVENTS):
        raise AttributionUnavailable()


def prepare_attribution(row, start, end, *, portion, previous=None):
    """Return fields for a trusted write after the shared interval check."""
    helpdesk = row["custom_work_context"] == "Helpdesk"
    changed = helpdesk and ticket_interval_changed(previous, row, start, end)
    if not schema_ready():
        if changed:
            raise AttributionUnavailable()
        return {}
    _require_child_protection()
    if not helpdesk:
        return {FIELD: UNSET}
    if changed:
        if type(portion) is not timedelta or portion < timedelta():
            raise AttributionUnavailable()
        value = _microseconds(portion)
    else:
        value = previous.get(FIELD, UNSET)
    if not _valid_value({**row, "from_time": start, "to_time": end}, value):
        raise AttributionUnavailable()
    return {FIELD: value}


def booking_snapshot(doc):
    """Preserve the native detail scalar before Int projection can coerce None."""
    data = doc.as_dict()
    for row, detail in zip(data.get("time_logs", ()), getattr(doc, "time_logs", ())):
        value = detail.get(FIELD)
        if value is None:
            row.pop(FIELD, None)
        else:
            row[FIELD] = value
    return data


def attribution_response(row):
    """Expose a confirmed scalar or explicit unknown for authorized Helpdesk work."""
    if row.get("custom_work_context") != "Helpdesk":
        return {}
    value = row.get(FIELD)
    return {"pre_creation_us": value if _valid_value(row, value) and value != UNSET else None}


def _bound_values(row):
    ticket = row.get("custom_hd_ticket")
    # Frappe's Link validation loads the integer HD Ticket name before before_insert.
    if type(ticket) is int and ticket > 0:
        ticket = str(ticket)
    return (
        row.get("custom_work_context"), ticket,
        _timestamp(row.get("from_time")), _timestamp(row.get("to_time")), row.get(FIELD),
        row.get("custom_hd_customer") or None,
    )


@contextmanager
def authorized_attribution(doc, values):
    """Bind server-written fields to the existing exact-document write scope."""
    if FIELD not in values:
        yield
        return
    if _write.get() is not None or len(doc.time_logs) != 1:
        raise BookingProvenanceError()
    row = doc.time_logs[0]
    if row.get(FIELD) != values[FIELD] or not _valid_value(row, row.get(FIELD)):
        raise BookingProvenanceError()
    grant = [doc, row, _bound_values(row), _execution_owner()]
    token = _write.set(grant)
    try:
        yield
        persisted = _stored_row(row.get("name"))
        if not persisted or not _is_owned_row(persisted, doc.get("name")) or _bound_values(persisted) != grant[2]:
            raise BookingProvenanceError()
    finally:
        grant.clear()
        _write.reset(token)


def _authorized(doc, row):
    grant = _write.get()
    return bool(
        grant and grant[0] is doc and grant[1] is row
        and grant[2] == _bound_values(row) and grant[3] == _execution_owner()
    )


def _name(row):
    return row.get("name")


def _stored_row(name):
    if not name:
        return None
    return frappe.db.get_value(
        DETAIL, name, _CHILD_FIELDS, as_dict=True, order_by=None, for_update=True, wait=False,
    )


def _is_managed_parent(name):
    return bool(name) and frappe.db.get_value(
        "Timesheet", name, _ORIGIN, order_by=None, for_update=True, wait=False,
    ) == "Phase 2"


def _is_owned_row(row, parent):
    return (
        row.get("parent") == parent and row.get("parenttype") == "Timesheet"
        and row.get("parentfield") == "time_logs"
    )


def _protect_unmanaged(row):
    value = row.get(FIELD)
    if value is None:
        row.set(FIELD, UNSET)
    elif type(value) is not int or value != UNSET:
        raise BookingProvenanceError()


def protect_parent(doc, *, inserting, managed, method):
    """Guard parent saves, which persist their children without child save hooks."""
    if method == "before_change":
        return
    details = doc.get("time_logs") or []
    if not details and not managed:
        return
    if not _native_schema_ready(details):
        return
    parent = doc.get("name")
    if managed and not inserting:
        stored = frappe.db.get_values(
            DETAIL, {"parent": parent, "parenttype": "Timesheet", "parentfield": "time_logs"},
            _CHILD_FIELDS, as_dict=True, for_update=True, wait=False,
        )
        if len(details) != 1 or len(stored) != 1 or _name(details[0]) != _name(stored[0]):
            raise BookingProvenanceError()
        row = details[0]
        if _bound_values(row) != _bound_values(stored[0]) and not _authorized(doc, row):
            raise BookingProvenanceError()
        return

    for row in details:
        stored = _stored_row(_name(row))
        if stored and (managed or not _is_owned_row(stored, parent)):
            if managed or _is_managed_parent(stored.get("parent")):
                raise BookingProvenanceError()
        if managed:
            if not _authorized(doc, row):
                raise BookingProvenanceError()
        else:
            _protect_unmanaged(row)


def protect_child(doc, method=None):
    """Guard direct child persistence before any later parent callback."""
    if not _native_schema_ready((doc,)):
        return
    stored = _stored_row(_name(doc))
    parents = {row.get("parent") for row in (stored, doc) if row and row.get("parent")}
    if any(_is_managed_parent(parent) for parent in sorted(parents)):
        raise BookingProvenanceError()
    if method != "on_trash":
        _protect_unmanaged(doc)
