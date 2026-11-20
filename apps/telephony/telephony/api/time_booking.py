"""Dedicated, gated Technician Timesheet creation endpoint."""

from contextlib import contextmanager
from datetime import datetime, timedelta
import re

import frappe

from telephony.time_booking_activation_adapter import _require_activation_configuration
from telephony.time_booking_activation_policy import ACTIVE_RUNTIME, ActivationConfigurationError
from telephony.time_booking_identity import (
    TechnicianBookingIdentity,
    resolve_current_technician_identity,
)
from telephony.time_booking_policy import validate_work_context
from telephony.time_booking_provenance_adapter import _phase2_creation_intent
from telephony.time_booking_timesheet_controller import TelectroBookingTimesheet
from telephony.time_booking_transaction import (
    _active_booking,
    _top_level_booking_transaction,
)


COMMAND = "telephony.api.time_booking.book_technician_time"


class BookingReferenceDenied(PermissionError):
    def __init__(self):
        super().__init__("Booking reference is unavailable.")


class BookingInputError(ValueError):
    def __init__(self):
        super().__init__("Booking input is invalid.")


def _identifier(value):
    return type(value) is str and bool(value.strip()) and value == value.strip()


def _visible(doctype, name):
    if not _identifier(name):
        raise BookingReferenceDenied()
    try:
        doc = frappe.get_doc(doctype, name)
        doc.check_permission("read")
    except (frappe.DoesNotExistError, frappe.PermissionError) as exc:
        raise BookingReferenceDenied() from exc
    if doc.doctype != doctype or doc.name != name:
        raise BookingReferenceDenied()
    return doc


def _authorize_references(row, company):
    context = row["custom_work_context"]
    if context == "Helpdesk":
        _visible("HD Ticket", row["custom_hd_ticket"])

        # An optional Customer reference requires independent authorization.
        if row.get("custom_hd_customer"):
            _visible("HD Customer", row["custom_hd_customer"])
    elif context == "Project":
        project = _visible("Project", row["project"])

        if project.get("company") != company:
            raise BookingReferenceDenied()

        if row.get("task"):
            task = _visible("Task", row["task"])

            if task.get("project") != project.name:
                raise BookingReferenceDenied()
        # Optional HD Customer requires independent read authorization.
        if row.get("custom_hd_customer"):
            _visible("HD Customer", row["custom_hd_customer"])
    elif context == "Customer Support":
        _visible("HD Customer", row["custom_hd_customer"])
    elif context != "Internal":
        raise BookingReferenceDenied()


def _period(from_time, duration_minutes):
    if (not _identifier(from_time)
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}", from_time) is None):
        raise BookingInputError()
    if type(duration_minutes) is str:
        if (not duration_minutes.isascii() or not duration_minutes.isdecimal()
                or str(int(duration_minutes)) != duration_minutes):
            raise BookingInputError()
        duration_minutes = int(duration_minutes)
    if type(duration_minutes) is not int or not 0 < duration_minutes <= 1440:
        raise BookingInputError()
    try:
        start = datetime.fromisoformat(from_time)
        if start.tzinfo is not None:
            raise ValueError()
        end = start + timedelta(minutes=duration_minutes)
    except (ValueError, OverflowError) as exc:
        raise BookingInputError() from exc
    if end <= start or start > frappe.utils.now_datetime():
        raise BookingInputError()
    return start, end, duration_minutes

@contextmanager
def _authorized_native_creation(timesheet, identity):
    """Temporarily allow native insertion of one authorized Phase 2 Timesheet."""
    if (
        not _active_booking.get()
        or type(timesheet) is not TelectroBookingTimesheet
        or type(identity) is not TechnicianBookingIdentity
        or timesheet.get("doctype") != "Timesheet"
        or timesheet.get("custom_telectro_booking_origin") != "Phase 2"
        or timesheet.get("employee") != identity.employee
        or timesheet.get("company") != identity.company
        or timesheet.get("user") != identity.user
        or timesheet.get("docstatus") != 0
        or len(timesheet.time_logs) != 1
    ):
        raise ActivationConfigurationError()

    flags = getattr(timesheet, "flags", None)

    if flags is None:
        raise ActivationConfigurationError()

    previous = getattr(flags, "ignore_permissions", None)

    if previous:
        raise ActivationConfigurationError()

    try:
        flags.ignore_permissions = True
        yield
    finally:
        flags.ignore_permissions = previous

@frappe.whitelist(methods=["POST"])
def book_technician_time(*, work_context, from_time, duration_minutes,
                         description, activity_type, ticket_name=None,
                         project_name=None, task_name=None, customer_name=None):
    with _top_level_booking_transaction(expected_command=COMMAND):
        # Source registration is not authorization. Require both the explicit
        # site enable switch and the complete live controller/hook invariant.
        if frappe.conf.get("telectro_time_booking_enabled") not in (1, True, "1"):
            raise ActivationConfigurationError()
        _require_activation_configuration(mode=ACTIVE_RUNTIME)
        identity = resolve_current_technician_identity()
        if (not _identifier(description) or len(description) > 2000
                or not _identifier(activity_type)):
            raise BookingInputError()
        start, end, minutes = _period(from_time, duration_minutes)
        row = {
            "custom_work_context": work_context,
            "custom_hd_ticket": ticket_name,
            "custom_hd_customer": customer_name,
            "project": project_name,
            "task": task_name,
        }
        validate_work_context(row)
        _authorize_references(row, identity.company)
        _visible("Activity Type", activity_type)
        timesheet = frappe.get_doc({
            "doctype": "Timesheet",
            "naming_series": "TS-.YYYY.-",
            "custom_telectro_booking_origin": "Phase 2",
            "employee": identity.employee,
            "company": identity.company,
            "user": identity.user,
            "docstatus": 0,
            "time_logs": [{
                "doctype": "Timesheet Detail", "activity_type": activity_type,
                "from_time": start, "to_time": end,
                "hours": minutes / 60,
                "description": description,
                **row,
            }],
        })
        if type(timesheet) is not TelectroBookingTimesheet or len(timesheet.time_logs) != 1:
            raise ActivationConfigurationError()
        with _phase2_creation_intent(timesheet, identity):
            with _authorized_native_creation(timesheet, identity):
                inserted = timesheet.insert()
        if (inserted is not timesheet or not _identifier(timesheet.name)
                or len(timesheet.time_logs) != 1
                or timesheet.get("employee") != identity.employee
                or timesheet.get("company") != identity.company
                or timesheet.get("user") != identity.user
                or timesheet.get("owner") != identity.user):
            raise ActivationConfigurationError()
        return {"timesheet": timesheet.name}
