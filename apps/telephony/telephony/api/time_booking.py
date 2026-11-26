"""Dedicated, gated Technician Timesheet creation endpoint."""

from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta
from functools import wraps
import json
import re

import frappe
from erpnext.projects.doctype.timesheet.timesheet import OverlapError
from frappe.exceptions import (
    CancelledLinkError,
    LinkExistsError,
    LinkValidationError,
    PermissionError as FrappePermissionError,
    TimestampMismatchError,
)
from werkzeug.wrappers import Request, Response

from telephony.time_booking_activation_adapter import _require_activation_configuration
from telephony.time_booking_activation_policy import ACTIVE_RUNTIME, ActivationConfigurationError
from telephony.time_booking_activity_types import BOOKING_ACTIVITY_TYPES
from telephony.time_booking_attribution import (
    attribution_response,
    authorized_attribution,
    prepare_attribution,
)
from telephony.time_booking_identity import (
    TechnicianBookingIdentity,
    TechnicianIdentityError,
    resolve_current_technician_identity,
)
from telephony.time_booking_ownership import (
    BookingOwnershipError,
    authorize_child,
)
from telephony.time_booking_policy import WorkContextValidationError, validate_work_context
from telephony.time_booking_ticket_interval import (
    TicketIntervalError,
    ticket_interval_changed,
    validate_ticket_interval,
)
from telephony.time_booking_project_grant import (
    ProjectBookingGrantError,
    require_project_booking_grant,
)
from telephony.time_booking_project_lookup import MAX_PAGE, project_options, task_options
from telephony.time_booking_provenance_adapter import _phase2_creation_intent
from telephony.time_booking_timesheet_controller import TelectroBookingTimesheet
from telephony.time_booking_transaction import (
    BookingTransactionDenied,
    _active_booking,
    _top_level_booking_transaction,
)
from telephony.time_booking_metadata_policy import (
    BookingMetadataValidationError,
    WORK_LOCATIONS,
    WORK_ORIGINS,
    normalize_booking_metadata,
)


COMMAND = "telephony.api.time_booking.book_technician_time"


class BookingReferenceDenied(PermissionError):
    def __init__(self, message="Booking reference is unavailable."):
        super().__init__(message)


class BookingCustomerConfigurationError(BookingReferenceDenied):
    def __init__(self):
        super().__init__("The Project's ERPNext Customer has no HD Customer mapping.")


class BookingInputError(ValueError):
    def __init__(self):
        super().__init__("Booking input is invalid.")


class OriginalBookingCreationExceeded(BookingReferenceDenied):
    pass


class SavedTicketIntervalDenied(BookingReferenceDenied):
    pass


_INPUT_ERROR = (
    422, "invalid_booking", "Check the booking details, work dates, and duration, then try again.",
)
_ACCESS_ERROR = (
    403, "booking_access_denied", "Booking access is unavailable. Reload My Time Bookings and check your access.",
)
_REFERENCE_ERROR = (
    403, "booking_reference_denied", "This reference is unavailable. Select a reference you can access.",
)
_INTERVAL_ERROR = (
    422, "invalid_ticket_interval", "The Ticket cannot validate this interval. Check the work dates and duration.",
)

_BOOKING_ERRORS = {
    OriginalBookingCreationExceeded: (
        422, "original_creation_exceeded",
        "The corrected work must end on or before the original booking creation time. "
        "Please adjust the start time or duration.",
    ),
    SavedTicketIntervalDenied: _INTERVAL_ERROR,
    TicketIntervalError: _INTERVAL_ERROR,
    BookingInputError: _INPUT_ERROR,
    WorkContextValidationError: _INPUT_ERROR,
    BookingMetadataValidationError: _INPUT_ERROR,
    BookingOwnershipError: _ACCESS_ERROR,
    TechnicianIdentityError: _ACCESS_ERROR,
    BookingTransactionDenied: _ACCESS_ERROR,
    FrappePermissionError: _ACCESS_ERROR,
    BookingReferenceDenied: _REFERENCE_ERROR,
    BookingCustomerConfigurationError: _REFERENCE_ERROR,
    OverlapError: (
        409, "booking_overlap", "This work overlaps another Timesheet entry. Adjust the start time or duration.",
    ),
    TimestampMismatchError: (
        409, "booking_changed", "The booking changed. Reload My Time Bookings before trying again.",
    ),
    LinkValidationError: _REFERENCE_ERROR,
    CancelledLinkError: _REFERENCE_ERROR,
    LinkExistsError: (
        409, "booking_linked", "Another record is linked to this booking. Ask an administrator to review the link.",
    ),
}
_EXPECTED_BOOKING_ERRORS = tuple(_BOOKING_ERRORS)


def _booking_http_errors(method):
    """Render recognized business errors after the booking transaction rolls back."""
    @wraps(method)
    def respond(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except _EXPECTED_BOOKING_ERRORS as exc:
            error = _BOOKING_ERRORS.get(type(exc))
            if error is None or not isinstance(getattr(frappe.local, "request", None), Request):
                raise
            status, code, message = error
            return Response(
                json.dumps({"error": {"code": code, "message": frappe._(message)}}),
                status=status,
                mimetype="application/json",
            )
    return respond


@contextmanager
def _discard_internal_permission_messages():
    # Native controller permission checks may add a message even on a boolean read check.
    previous = frappe.local.message_log
    frappe.local.message_log = []
    try:
        yield
    finally:
        frappe.local.message_log = previous


def _identifier(value):
    return type(value) is str and bool(value.strip()) and value == value.strip()


def _require_booking_activity_type(activity_type):
    if type(activity_type) is not str or activity_type not in BOOKING_ACTIVITY_TYPES:
        raise BookingInputError()


def _visible(doctype, name, *, silent=False):
    if not _identifier(name):
        raise BookingReferenceDenied()
    try:
        with _discard_internal_permission_messages() if silent else nullcontext():
            doc = frappe.get_doc(doctype, name)
            if silent:
                if not doc.has_permission("read"):
                    raise BookingReferenceDenied()
            else:
                doc.check_permission("read")
    except (frappe.DoesNotExistError, frappe.PermissionError) as exc:
        raise BookingReferenceDenied() from exc
    if doc.doctype != doctype:
        raise BookingReferenceDenied()

    if doc.name != name:
        canonical_numeric_ticket = (
            doctype == "HD Ticket"
            and type(doc.name) is int
            and doc.name > 0
            and name == str(doc.name)
        )

        if not canonical_numeric_ticket:
            raise BookingReferenceDenied()

    return doc


def _allowed_service_areas():
    """Read permitted Service Areas from server-controlled HD Ticket metadata."""
    field = frappe.get_meta("HD Ticket").get_field("custom_service_area")

    if (
        field is None
        or field.fieldtype != "Select"
        or type(field.options) is not str
    ):
        raise BookingMetadataValidationError(
            "Invalid permitted Service Area configuration"
        )

    options = tuple(
        value for value in field.options.splitlines()
        if value
    )

    if len(options) != len(set(options)):
        raise BookingMetadataValidationError(
            "Invalid permitted Service Area configuration"
        )

    return options


def _authorize_references(row, identity, *, start=None, end=None):
    """Return the authorized Ticket or the Project Customer from the grant lock."""
    context = row["custom_work_context"]
    if context == "Helpdesk":
        ticket = _visible("HD Ticket", row["custom_hd_ticket"])

        # An optional Customer reference requires independent authorization.
        if row.get("custom_hd_customer"):
            _visible("HD Customer", row["custom_hd_customer"])
        return ticket
    elif context == "Project":
        try:
            project_customer = require_project_booking_grant(
                identity=identity, project=row["project"], task=row.get("task") or None,
                start=start, end=end,
            )
        except ProjectBookingGrantError as exc:
            raise BookingReferenceDenied() from exc
        # Optional HD Customer requires independent read authorization.
        if row.get("custom_hd_customer"):
            _visible("HD Customer", row["custom_hd_customer"])
        return project_customer
    elif context == "Customer Support":
        if row.get("custom_hd_customer"):
            _visible("HD Customer", row["custom_hd_customer"])
    elif context != "Internal":
        raise BookingReferenceDenied()


def _require_customer_mapping_transaction(db):
    if db.db_type != "mariadb":
        raise BookingReferenceDenied()
    settings = dict(db.sql("""
        SHOW SESSION VARIABLES
        WHERE Variable_name IN (
            'autocommit', 'in_transaction', 'innodb_snapshot_isolation', 'tx_isolation'
        )
    """))
    if settings != {
        "autocommit": "OFF",
        "in_transaction": "1",
        "innodb_snapshot_isolation": "OFF",
        "tx_isolation": "REPEATABLE-READ",
    }:
        raise BookingReferenceDenied()


def _require_customer_mapping_index(db):
    # The range must use the full, visible, non-unique InnoDB index.
    index = db.sql("""
        SELECT s.SEQ_IN_INDEX, s.COLUMN_NAME, s.NON_UNIQUE, s.INDEX_TYPE,
               s.SUB_PART, s.IGNORED, hd.ENGINE, erp.ENGINE
        FROM information_schema.STATISTICS s
        JOIN information_schema.TABLES hd
          ON hd.TABLE_SCHEMA = s.TABLE_SCHEMA AND hd.TABLE_NAME = s.TABLE_NAME
        JOIN information_schema.TABLES erp
          ON erp.TABLE_SCHEMA = s.TABLE_SCHEMA AND erp.TABLE_NAME = 'tabCustomer'
        WHERE s.TABLE_SCHEMA = DATABASE()
          AND s.TABLE_NAME = 'tabHD Customer'
          AND s.INDEX_NAME = 'custom_erp_customer_index'
    """)
    if index != ((1, "custom_erp_customer", 1, "BTREE", None, "NO", "InnoDB", "InnoDB"),):
        raise BookingReferenceDenied()


def _lock_booking_ticket(ticket):
    """Reload and reauthorize the Ticket under its write-boundary row lock."""
    if ticket is None:
        raise BookingReferenceDenied()
    try:
        locked = frappe.db.get_value(
            "HD Ticket", str(ticket.name), "*", as_dict=True,
            order_by=None, for_update=True, wait=False,
        )
        if not locked or str(locked.name) != str(ticket.name):
            raise BookingReferenceDenied()
        current_ticket = frappe.get_doc({**locked, "doctype": "HD Ticket"})
        current_ticket.check_permission("read")
    except (frappe.PermissionError, frappe.QueryDeadlockError, frappe.QueryTimeoutError) as exc:
        raise BookingReferenceDenied() from exc
    return current_ticket


def _validate_helpdesk_interval(row, *, ticket, locked_ticket, start, end, previous=None):
    if row["custom_work_context"] != "Helpdesk" or not ticket_interval_changed(previous, row, start, end):
        return None
    if locked_ticket is None:
        locked_ticket = _lock_booking_ticket(ticket)
    try:
        return validate_ticket_interval(locked_ticket, start, end, now=frappe.utils.now_datetime(), db=frappe.db)
    except (frappe.QueryDeadlockError, frappe.QueryTimeoutError) as exc:
        raise BookingReferenceDenied() from exc


def _locked_hd_customer_names(db, erp_customer):
    return db.sql("""
        SELECT name FROM `tabHD Customer` FORCE INDEX (custom_erp_customer_index)
        WHERE custom_erp_customer = %s
        FOR UPDATE NOWAIT
    """, (erp_customer,))


def _validate_customer_consistency(row, *, ticket=None, project_customer=None, previous=None):
    """Resolve and persist the operational HD Customer at the authorized write boundary."""
    context = row["custom_work_context"]
    customer_name = row.get("custom_hd_customer") or None
    reference_field = {"Helpdesk": "custom_hd_ticket", "Project": "project"}.get(context)
    if (reference_field and previous and previous["custom_work_context"] == context
            and str(previous.get(reference_field)) == str(row.get(reference_field))
            and customer_name in (None, previous.get("custom_hd_customer"))):
        # A saved identity, including a legacy blank, survives changes to master data.
        row["custom_hd_customer"] = previous.get("custom_hd_customer")
        return

    # Retain the read checks before exact locks for an explicit selection.
    hd_customer = _visible("HD Customer", customer_name) if customer_name else None
    db = frappe.db
    if customer_name:
        _require_customer_mapping_transaction(db)

    locked_ticket = None
    authoritative_customer = None
    if context == "Helpdesk":
        locked_ticket = _lock_booking_ticket(ticket)
        ticket_customer = locked_ticket.get("customer")
        if ticket_customer and customer_name not in (None, ticket_customer):
            raise BookingReferenceDenied()
        customer_name = ticket_customer or customer_name
        authoritative_customer = locked_ticket.get("custom_customer")
    elif context == "Project":
        authoritative_customer = project_customer
        if customer_name and not authoritative_customer:
            raise BookingReferenceDenied()

    if not customer_name and not authoritative_customer:
        return locked_ticket
    if hd_customer is None:
        _require_customer_mapping_transaction(db)
        if customer_name:
            hd_customer = _visible("HD Customer", customer_name)

    candidate = authoritative_customer or (hd_customer and hd_customer.get("custom_erp_customer")) or None
    reverse_resolved = customer_name is None
    try:
        if candidate is not None and (
            not _identifier(candidate)
            or db.get_value(
                "Customer", candidate, "name", order_by=None, for_update=True, wait=False,
            ) != candidate
        ):
            raise BookingReferenceDenied()

        if reverse_resolved:
            _require_customer_mapping_index(db)
            matches = _locked_hd_customer_names(db, candidate)
            if not matches and context == "Project":
                raise BookingCustomerConfigurationError()
            if len(matches) != 1:
                raise BookingReferenceDenied()
            customer_name = matches[0][0]
            _visible("HD Customer", customer_name)

        locked = db.get_value(
            "HD Customer", customer_name, "*", as_dict=True,
            order_by=None, for_update=True, wait=False,
        )
        if not locked or locked.name != customer_name:
            raise BookingReferenceDenied()
        current_customer = frappe.get_doc({**locked, "doctype": "HD Customer"})
        current_customer.check_permission("read")
        if (current_customer.get("custom_erp_customer") or None) != candidate:
            raise BookingReferenceDenied()

        if not reverse_resolved:
            _require_customer_mapping_index(db)
            if candidate is not None:
                matches = _locked_hd_customer_names(db, candidate)
                if not matches and context == "Project":
                    raise BookingCustomerConfigurationError()
                if matches != ((customer_name,),):
                    raise BookingReferenceDenied()
    except BookingCustomerConfigurationError:
        raise
    except (frappe.PermissionError, frappe.QueryDeadlockError, frappe.QueryTimeoutError) as exc:
        raise BookingReferenceDenied() from exc
    row["custom_hd_customer"] = customer_name
    return locked_ticket


def _period(from_time, duration_minutes, *, precise=False):
    pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}"
    if precise:
        pattern += r"(\.[0-9]{1,6})?"
    if not _identifier(from_time) or re.fullmatch(pattern, from_time) is None:
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

def _booking_identity():
    if frappe.conf.get("telectro_time_booking_enabled") not in (1, True, "1"):
        raise ActivationConfigurationError()
    _require_activation_configuration(mode=ACTIVE_RUNTIME)
    return resolve_current_technician_identity()


@frappe.whitelist(methods=["GET"])
def get_booking_form():
    """Return options only for a technician who can use managed booking."""
    try:
        identity = _booking_identity()
    except (ActivationConfigurationError, TechnicianIdentityError):
        return None

    return {
        "company": identity.company,
        "activity_types": BOOKING_ACTIVITY_TYPES,
        "service_areas": _allowed_service_areas(),
        "work_locations": WORK_LOCATIONS,
        "work_origins": WORK_ORIGINS,
    }


@frappe.whitelist(methods=["GET"])
def get_booking_ticket_area(ticket_name):
    """Expose only a readable ticket's Service Area to the booking form."""
    _booking_identity()
    ticket = _visible("HD Ticket", ticket_name)
    return {"service_area": ticket.get("custom_service_area")}


@frappe.whitelist(methods=["GET"])
def get_booking_reference_customer(*, ticket_name=None, project_name=None, from_time=None, duration_minutes=None):
    """Preview only the authorized operational Customer. Writes resolve it again."""
    identity = _booking_identity()
    if bool(ticket_name) == bool(project_name):
        raise BookingInputError()
    if ticket_name:
        row = {"custom_work_context": "Helpdesk", "custom_hd_ticket": ticket_name}
        ticket = _authorize_references(row, identity)
        _validate_customer_consistency(row, ticket=ticket)
    else:
        start, end, _ = _period(from_time, duration_minutes)
        row = {"custom_work_context": "Project", "project": project_name}
        project_customer = _authorize_references(row, identity, start=start, end=end)
        try:
            _validate_customer_consistency(row, project_customer=project_customer)
        except BookingCustomerConfigurationError as exc:
            return {"configuration_error": str(exc)}
    return {"customer_name": row.get("custom_hd_customer")}


@frappe.whitelist()
def search_booking_tickets(doctype, txt, searchfield, start, page_len, filters):
    '''Adapt native HD Ticket Link results for the booking dialog.'''
    if doctype != "HD Ticket":
        raise BookingReferenceDenied()
    from frappe.desk.search import search_widget

    _booking_identity()
    results = search_widget(doctype, txt, start=start, page_length=page_len)
    return [(str(name) if type(name) is int and name > 0 else name, *columns)
            for name, *columns in results]


def _booking_lookup(lookup, from_time, duration_minutes, query, page, name, **scope):
    try:
        identity = _booking_identity()
        start, end, _ = _period(from_time, duration_minutes)
    except (ActivationConfigurationError, TechnicianIdentityError, BookingInputError):
        return []
    if type(page) is str and re.fullmatch(r"[0-9]", page):
        page = int(page)
    if (
        type(query) is not str or len(query) > 80
        or type(page) is not int or not 0 <= page <= MAX_PAGE
        or (name is not None and (not _identifier(name) or len(name) > 140 or query or page))
    ):
        return []
    evaluated_at = frappe.utils.now_datetime()
    if end > evaluated_at:
        return []
    return lookup(
        identity=identity, start=start, end=end, evaluated_at=evaluated_at,
        term=query.strip(), page=page, name=name, **scope,
    )


@frappe.whitelist(methods=["GET"])
def get_booking_projects(from_time, duration_minutes, query="", page=0, name=None):
    """Find entitled same-company Projects for a completed booking interval."""
    return _booking_lookup(project_options, from_time, duration_minutes, query, page, name)


@frappe.whitelist(methods=["GET"])
def get_booking_tasks(project_name, from_time, duration_minutes, query="", page=0, name=None):
    """Find explicitly entitled Tasks under one eligible booking Project."""
    if not _identifier(project_name) or len(project_name) > 140:
        return []
    return _booking_lookup(
        task_options, from_time, duration_minutes, query, page, name, project_name=project_name,
    )


@frappe.whitelist(methods=["GET"])
def list_own_bookings(start=0):
    """List one page of managed entries without granting native Timesheet read."""
    identity = _booking_identity()
    if type(start) is str and re.fullmatch(r"[0-9]{1,7}", start):
        start = int(start)
    if type(start) is not int or not 0 <= start <= 9_999_999:
        raise BookingInputError()

    page_size = 20
    names = frappe.get_all(
        "Timesheet",
        filters={
            "custom_telectro_booking_origin": "Phase 2",
            "user": identity.user,
            "employee": identity.employee,
            "company": identity.company,
        },
        pluck="name",
        order_by="creation desc, name desc",
        limit_start=start,
        limit_page_length=page_size + 1,
    )
    bookings = []
    for name in names[:page_size]:
        try:
            doc = frappe.get_doc("Timesheet", name)
        except frappe.DoesNotExistError:
            continue
        if len(doc.time_logs) != 1:
            continue
        parent = doc.as_dict()
        row = parent.time_logs[0]
        try:
            authorize_child(identity, parent, row)
        except BookingOwnershipError:
            continue

        bookings.append({
            "name": doc.name,
            "docstatus": int(doc.docstatus),
            "modified": str(doc.modified),
            "from_time": str(row.from_time),
            "duration_minutes": round(row.hours * 60),
            "description": row.description,
            "activity_type": row.activity_type,
            "work_context": row.custom_work_context,
            "ticket_name": str(row.custom_hd_ticket) if row.custom_hd_ticket else None,
            "project_name": row.project,
            "task_name": row.task,
            "customer_name": row.custom_hd_customer,
            "unlisted_customer_name": row.custom_unlisted_customer_name,
            "service_area": row.custom_service_area,
            "work_location": row.custom_work_location,
            "work_origin": row.custom_work_origin,
            "external_reference": row.custom_external_reference,
            "other_origin_description": row.custom_other_origin_description,
            "emergency": row.custom_emergency,
            **attribution_response(doc.time_logs[0]),
        })
    return {
        "bookings": bookings,
        "next_start": start + page_size if len(names) > page_size else None,
        "previous_start": max(0, start - page_size) if start else None,
    }


@frappe.whitelist(methods=["POST"])
@_booking_http_errors
def book_technician_time(*, work_context, from_time, duration_minutes,
                         description, activity_type, ticket_name=None,
                         project_name=None, task_name=None, customer_name=None,
                         unlisted_customer_name=None, service_area=None,
                         work_location=None, work_origin=None,
                         external_reference=None, other_origin_description=None,
                         emergency=None):
    with _top_level_booking_transaction(expected_command=COMMAND):
        # Source registration is not authorization. Require both the explicit
        # site enable switch and the complete live controller/hook invariant.
        identity = _booking_identity()
        if not _identifier(description) or len(description) > 2000:
            raise BookingInputError()
        start, end, minutes = _period(from_time, duration_minutes)
        row = {
            "custom_work_context": work_context,
            "custom_hd_ticket": ticket_name,
            "custom_hd_customer": customer_name,
            "custom_unlisted_customer_name": unlisted_customer_name,
            "project": project_name,
            "task": task_name,
        }
        validate_work_context(row)
        authorized_reference = _authorize_references(row, identity, start=start, end=end)
        ticket = authorized_reference if work_context == "Helpdesk" else None
        _require_booking_activity_type(activity_type)
        _visible("Activity Type", activity_type)
        locked_ticket = _validate_customer_consistency(
            row, ticket=ticket,
            project_customer=authorized_reference if work_context == "Project" else None,
        )

        if work_context == "Helpdesk":
            ticket_area = ticket.get("custom_service_area")

            if service_area not in (None, "", ticket_area):
                raise BookingMetadataValidationError(
                    "Helpdesk Service Area must match its ticket"
                )

            effective_service_area = ticket_area
        else:
            effective_service_area = service_area

        row.update(normalize_booking_metadata(
            work_context=work_context,
            service_area=effective_service_area,
            allowed_service_areas=_allowed_service_areas(),
            activity_type=activity_type,
            work_location=work_location,
            work_origin=work_origin,
            external_reference=external_reference,
            other_origin_description=other_origin_description,
            emergency=emergency,
        ))

        portion = _validate_helpdesk_interval(row, ticket=ticket, locked_ticket=locked_ticket, start=start, end=end)
        attribution = prepare_attribution(row, start, end, portion=portion)
        row.update(attribution)

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
            with _authorized_native_creation(timesheet, identity), authorized_attribution(timesheet, attribution):
                inserted = timesheet.insert()
        if (inserted is not timesheet or not _identifier(timesheet.name)
                or len(timesheet.time_logs) != 1
                or timesheet.get("employee") != identity.employee
                or timesheet.get("company") != identity.company
                or timesheet.get("user") != identity.user
                or timesheet.get("owner") != identity.user):
            raise ActivationConfigurationError()
        return {
            "timesheet": timesheet.name,
            **(attribution_response(timesheet.time_logs[0]) if attribution else {}),
        }
