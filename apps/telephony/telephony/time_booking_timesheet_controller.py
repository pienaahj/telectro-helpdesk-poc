"""Unregistered native Timesheet insert wrapper; no lifecycle activation.

Trusted callers must supply creation intent and authenticated identity. This
does not prove final-name absence, transaction commit, update provenance or
authorization of references. Direct writes and native RPC containment remain
separate integration requirements.
"""

from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from uuid import uuid4

from erpnext.projects.doctype.timesheet.timesheet import Timesheet

from telephony.time_booking_provenance import BookingProvenanceError
from telephony.time_booking_provenance_adapter import (
    _complete_insertion,
    _insertion_attempt,
    _require_final_name_absence,
)


_retained_links = ContextVar("telectro_retained_booking_links", default=None)


@contextmanager
def retain_missing_booking_links(doc, previous):
    """Retain only missing Link values on the authorized, unchanged work row."""
    import frappe

    row, = doc.time_logs
    missing = {}
    for field, doctype in (
        ("custom_hd_ticket", "HD Ticket"), ("custom_hd_customer", "HD Customer"),
        ("project", "Project"), ("task", "Task"),
    ):
        value = previous.get(field)
        if value and str(row.get(field)) == str(value) and not frappe.db.exists(doctype, value):
            missing[field] = row.get(field)
    token = _retained_links.set((doc, row, missing))
    try:
        yield
    finally:
        _retained_links.reset(token)


class TelectroBookingTimesheet(Timesheet):
    """Preserve native behavior while bounding one trusted insertion attempt."""

    @contextmanager
    def _omit_missing_booking_links(self, fields):
        scope = _retained_links.get()
        if not scope or scope[0] is not self or len(self.time_logs) != 1 or self.time_logs[0] is not scope[1]:
            yield
            return
        _, row, missing = scope
        values = {
            field: value for field, value in missing.items()
            if field in fields and str(row.get(field)) == str(value)
        }
        try:
            for field in values:
                row.set(field, None)
            yield
        finally:
            row.update(values)

    def _validate_links(self):
        with self._omit_missing_booking_links(("custom_hd_ticket", "custom_hd_customer", "project", "task")):
            return super()._validate_links()

    def update_task_and_project(self):
        with self._omit_missing_booking_links(("project", "task")):
            return super().update_task_and_project()

    def insert(
        self,
        ignore_permissions=None,
        ignore_links=None,
        ignore_if_duplicate=False,
        ignore_mandatory=None,
        set_name=None,
        set_child_names=True,
    ):
        with _insertion_attempt(self) as frame:
            managed = frame.identity is not None
            if managed:
                # Registration is inert until a reviewed site explicitly enables
                # booking and the exact live activation contract passes.
                import frappe
                from telephony.time_booking_activation_adapter import (
                    _require_activation_configuration,
                )
                from telephony.time_booking_activation_policy import ACTIVE_RUNTIME

                if frappe.conf.get("telectro_time_booking_enabled") not in (1, True, "1"):
                    raise BookingProvenanceError()
                _require_activation_configuration(mode=ACTIVE_RUNTIME)
                # Native Document.insert checks this Document-local flag first.
                # Print rendering sets doc.flags.in_print, not frappe.flags.
                if self.flags.in_print or ignore_if_duplicate is not False:
                    raise BookingProvenanceError()
            scope = _managed_insert_savepoint() if managed else nullcontext()
            with scope:
                result = super().insert(
                    ignore_permissions=ignore_permissions,
                    ignore_links=ignore_links,
                    ignore_if_duplicate=ignore_if_duplicate,
                    ignore_mandatory=ignore_mandatory,
                    set_name=set_name,
                    set_child_names=set_child_names,
                )
                if managed:
                    if result is not self:
                        raise BookingProvenanceError()
                    _require_final_name_absence(frame, self)
                    _complete_insertion(frame, self, frame.identity)
            return result


class _ManagedSavepointCleanupError(RuntimeError):
    """Cleanup failed: callers must abort the enclosing transaction/unit."""

    def __init__(self, stage):
        super().__init__(
            f"Managed Timesheet savepoint {stage} failed; transaction state is uncertain."
        )


@contextmanager
def _managed_insert_savepoint():
    """Contain transactional DB writes only; never commit or retry.

    Savepoint rollback does not unwind callback queues, realtime, jobs, files
    or external effects. It cannot protect against intervening commits, implicit
    transaction boundaries, lost connections or nontransactional tables. Other
    writes inside this scope are also rolled back. Future trusted booking-service
    transaction ownership remains mandatory; success is not a committed booking.
    """
    import frappe

    # Retain the actual Database object rather than a dynamically rebound proxy.
    db = frappe.local.db
    name = "p2_ts_" + uuid4().hex
    db.savepoint(name)
    try:
        yield
    except BaseException:
        try:
            db.rollback(save_point=name)
        except BaseException as cleanup_error:
            raise _ManagedSavepointCleanupError("rollback") from cleanup_error
        try:
            db.release_savepoint(name)
        except BaseException as cleanup_error:
            raise _ManagedSavepointCleanupError("release") from cleanup_error
        raise
    else:
        try:
            db.release_savepoint(name)
        except BaseException:
            # Release failed after body success. Attempt rollback, but do not
            # retry release. Abort the enclosing unit even if rollback succeeds.
            try:
                db.rollback(save_point=name)
            except BaseException as cleanup_error:
                raise _ManagedSavepointCleanupError("rollback after release") from cleanup_error
            raise
