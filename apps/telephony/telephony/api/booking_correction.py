"""Owned technician booking correction, withdrawal and cancellation; no internal commits."""
from contextlib import contextmanager, nullcontext
import json

import frappe

from telephony.api.time_booking import (
    _identifier,
    _period,
    _visible,
    _authorize_references,
    BookingInputError,
    BookingReferenceDenied,
    OriginalBookingCreationExceeded,
    SavedTicketIntervalDenied,
    _booking_http_errors,
    _authorized_native_creation,
    _allowed_service_areas,
    _require_booking_activity_type,
    _validate_customer_consistency,
    _validate_helpdesk_interval,
)
from telephony.time_booking_attribution import (
    authorized_attribution,
    booking_snapshot,
    prepare_attribution,
)
from telephony.time_booking_metadata_policy import (
    BookingMetadataValidationError,
    normalize_booking_metadata,
)
from telephony.time_booking_activation_adapter import _require_activation_configuration
from telephony.time_booking_activation_policy import ACTIVE_RUNTIME, ActivationConfigurationError
from telephony.time_booking_identity import resolve_current_technician_identity
from telephony.time_booking_ownership import authorize_parent, authorize_child, BookingOwnershipError
from telephony.time_booking_policy import validate_work_context
from telephony.time_booking_project_grant import ProjectBookingGrantError, _lock_project
from telephony.time_booking_correction_audit import (
    record_correction_event,
    _snapshot,
    DOCTYPE,
    _validated_replacement_request,
    _REPLACEMENT_REQUEST_FIELDS,
    BookingCorrectionAuditError,
)
from telephony.time_booking_timesheet_controller import (
    TelectroBookingTimesheet,
    retain_missing_booking_links,
)
from telephony.time_booking_ticket_interval import (
    ORIGIN_FIELD, TicketIntervalError, _timestamp, ticket_interval_changed, validate_ticket_interval,
)
from telephony.time_booking_transaction import (
    _active_booking,
    _top_level_booking_transaction,
)
from datetime import datetime
from telephony.time_booking_provenance_adapter import _phase2_creation_intent

PREFIX = "telephony.api.booking_correction."

def _revision_matches(persisted_modified, expected_modified):
    """Compare exact revisions across Frappe and JSON datetime formats.

    Audit snapshots use ISO timestamps with 'T', while Frappe normally
    exposes modified timestamps with a space separator. Preserve
    microsecond precision and reject malformed or timezone-aware values.
    """
    if (
        type(persisted_modified) is not str
        or type(expected_modified) is not str
    ):
        return False

    try:
        persisted = datetime.fromisoformat(persisted_modified)
        expected = datetime.fromisoformat(expected_modified)
    except ValueError:
        return False

    if persisted.tzinfo is not None or expected.tzinfo is not None:
        return False

    return persisted == expected


def _guard():
    if frappe.conf.get("telectro_time_booking_enabled") not in (1, True, "1"):
        raise ActivationConfigurationError()
    _require_activation_configuration(mode=ACTIVE_RUNTIME)
    if not frappe.db.table_exists(DOCTYPE, cached=False):
        raise ActivationConfigurationError()
    return resolve_current_technician_identity()


def _audit(event_id):
    rows = frappe.db.sql(
        "SELECT name, actor, action, reason, original_timesheet, before_snapshot, after_snapshot "
        "FROM `tabTELECTRO Booking Correction Audit` WHERE event_id=%s FOR UPDATE",
        event_id, as_dict=True)
    if len(rows) > 1:
        raise BookingOwnershipError()
    return rows[0] if rows else None

def _replacement_audit(event_id):
    """Retrieve immutable evidence for a Submitted Replacement retry."""
    rows = frappe.db.sql(
        "SELECT name, actor, action, reason, original_timesheet, "
        "before_snapshot, after_snapshot, replacement_timesheet, "
        "replacement_request_snapshot "
        "FROM `tabTELECTRO Booking Correction Audit` "
        "WHERE event_id=%s FOR UPDATE",
        event_id,
        as_dict=True,
    )

    if len(rows) > 1:
        raise BookingOwnershipError()

    return rows[0] if rows else None

def _replacement_request_snapshot(
    *,
    work_context,
    from_time,
    duration_minutes,
    description,
    activity_type,
    ticket_name=None,
    project_name=None,
    task_name=None,
    customer_name=None,
    unlisted_customer_name=None,
    service_area=None,
    work_location=None,
    work_origin=None,
    external_reference=None,
    other_origin_description=None,
    emergency=None,
    allowed_service_areas=None,
):
    """Canonicalize validated replacement input for immutable retry evidence."""
    if (
        not _identifier(description)
        or len(description) > 2000
        or not _identifier(activity_type)
    ):
        raise BookingInputError()

    # An absent unlisted customer identity must be represented
    # by None, never an empty or whitespace-only string.
    if (
        isinstance(unlisted_customer_name, str)
        and not unlisted_customer_name.strip()
    ):
        raise BookingInputError()

    start, end, minutes = _period(from_time, duration_minutes)

    row = {
        "custom_work_context": work_context,
        "custom_hd_ticket": ticket_name,
        "custom_hd_customer": customer_name,
        "project": project_name,
        "task": task_name,
        "custom_unlisted_customer_name": unlisted_customer_name,
    }

    validate_work_context(row)

    permitted_areas = (
        _allowed_service_areas()
        if allowed_service_areas is None
        else allowed_service_areas
    )

    metadata = normalize_booking_metadata(
        work_context=work_context,
        service_area=service_area,
        allowed_service_areas=permitted_areas,
        activity_type=activity_type,
        work_location=work_location,
        work_origin=work_origin,
        external_reference=external_reference,
        other_origin_description=other_origin_description,
        emergency=emergency,
    )

    request = {
        "work_context": work_context,
        "from_time": start.isoformat(),
        "to_time": end.isoformat(),
        "duration_minutes": minutes,
        "description": description,
        "activity_type": activity_type,
        "ticket_name": ticket_name,
        "project_name": project_name,
        "task_name": task_name,
        "customer_name": customer_name,
        "unlisted_customer_name": unlisted_customer_name,
        "service_area": metadata["custom_service_area"],
        "work_location": metadata["custom_work_location"],
        "work_origin": metadata["custom_work_origin"],
        "external_reference": metadata["custom_external_reference"],
        "other_origin_description": metadata["custom_other_origin_description"],
        "emergency": metadata["custom_emergency"],
    }

    return json.dumps(
        request,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

def _legacy_replacement_request_snapshot(
    *,
    work_context,
    from_time,
    duration_minutes,
    description,
    activity_type,
    ticket_name=None,
    project_name=None,
    task_name=None,
    customer_name=None,
):
    """Reconstruct the immutable historical 10-field request contract."""

    if (
        not _identifier(description)
        or len(description) > 2000
        or not _identifier(activity_type)
    ):
        raise BookingInputError()

    start, end, minutes = _period(from_time, duration_minutes)

    validate_work_context({
        "custom_work_context": work_context,
        "custom_hd_ticket": ticket_name,
        "custom_hd_customer": customer_name,
        "project": project_name,
        "task": task_name,
    })

    request = {
        "work_context": work_context,
        "from_time": start.isoformat(),
        "to_time": end.isoformat(),
        "duration_minutes": minutes,
        "description": description,
        "activity_type": activity_type,
        "ticket_name": ticket_name,
        "project_name": project_name,
        "task_name": task_name,
        "customer_name": customer_name,
    }

    return json.dumps(
        request,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

def _owned(snapshot, identity):
    authorize_parent(identity, snapshot, operation="correct")
    if len(snapshot.get("time_logs", [])) != 1:
        raise BookingOwnershipError()
    authorize_child(identity, snapshot, snapshot["time_logs"][0], operation="correct")

def _saved_work_request(saved_work, description, from_time, duration_minutes):
    # Check the original request because Frappe discards unknown callable arguments.
    if saved_work is not True or set(frappe.local.form_dict) - {
        "cmd", "timesheet_name", "event_id", "reason", "expected_modified",
        "saved_work", "description", "from_time", "duration_minutes",
    }:
        raise BookingInputError()
    if not _identifier(description) or len(description) > 2000:
        raise BookingInputError()
    if from_time is not None or duration_minutes is not None:
        start, _, duration_minutes = _period(from_time, duration_minutes, precise=True)
        from_time = start.isoformat()
    return json.dumps(
        dict(saved_work=True, description=description, from_time=from_time,
             duration_minutes=duration_minutes),
        sort_keys=True, separators=(",", ":"),
    )


def _original_creation(booking, identity):
    """Resolve the root of an owned booking through immutable replacement evidence."""
    name = booking["name"]
    creation = _timestamp(booking.get("creation"))
    visited = set()
    while creation is not None and name not in visited:
        visited.add(name)
        rows = frappe.db.sql(
            """SELECT actor, action, original_timesheet, original_time_log, before_snapshot
                 FROM `tabTELECTRO Booking Correction Audit`
                WHERE replacement_timesheet = %s LIMIT 2 LOCK IN SHARE MODE NOWAIT""",
            name, as_dict=True,
        )
        if not rows:
            return creation
        if len(rows) != 1:
            break
        event = rows[0]
        if event["actor"] != identity.user or event["action"] != "Submitted Replacement":
            break
        try:
            predecessor = json.loads(event["before_snapshot"])
            previous_row, = predecessor["time_logs"]
            authorize_child(identity, predecessor, previous_row, operation="replace_submitted")
            previous_creation = _timestamp(predecessor.get("creation"))
            if (
                predecessor["name"] != event["original_timesheet"]
                or previous_row["name"] != event["original_time_log"]
                or previous_creation is None or previous_creation > creation
            ):
                break
            name, creation = predecessor["name"], previous_creation
        except (ValueError, KeyError, TypeError, BookingOwnershipError):
            break
    raise BookingReferenceDenied("The original booking creation could not be verified.")


def _saved_ticket_portion(booking, row, start, end, identity):
    """Use current Ticket authority or validate only the owned booking's saved Ticket."""
    ticket_name = row["custom_hd_ticket"]
    try:
        ticket = _visible("HD Ticket", ticket_name, silent=True)
    except BookingReferenceDenied:
        ticket = None
    if ticket is not None:
        return _validate_helpdesk_interval(
            row, ticket=ticket, locked_ticket=None, start=start, end=end, previous=row,
        )

    now = frappe.utils.now_datetime()
    try:
        try:
            creation = _original_creation(booking, identity)
        except BookingReferenceDenied:
            raise SavedTicketIntervalDenied() from None
        if creation > now:
            raise SavedTicketIntervalDenied()
        if end > creation:
            raise OriginalBookingCreationExceeded()
        locked = frappe.db.get_value(
            "HD Ticket", ticket_name,
            ("name", "creation", "status", "status_category", "resolution_date", ORIGIN_FIELD),
            as_dict=True, order_by=None, for_update=True, wait=False,
        )
        if not locked or str(locked.name) != ticket_name:
            raise TicketIntervalError()
        return validate_ticket_interval(locked, start, end, now=now, db=frappe.db)
    except (TicketIntervalError, frappe.QueryDeadlockError, frappe.QueryTimeoutError):
        raise SavedTicketIntervalDenied() from None


def _retain_blank_origin(row, previous):
    """Keep an unknown origin only when it is already saved in the same context."""
    if "custom_work_origin" not in row or row["custom_work_origin"] is not None:
        return
    origin = previous.get("custom_work_origin")
    if origin not in (None, "") or row["custom_work_context"] != previous.get("custom_work_context"):
        raise BookingMetadataValidationError("Only a saved blank Work Origin can remain unknown")
    row["custom_work_origin"] = origin


def _saved_work_values(before, identity, request):
    previous = before["time_logs"][0]
    context = previous["custom_work_context"]
    if context not in ("Helpdesk", "Project"):
        raise BookingReferenceDenied()
    data = json.loads(request)
    values = {"description": data["description"]}
    start, end = _timestamp(previous["from_time"]), _timestamp(previous["to_time"])
    changed = False
    portion = None
    if data["from_time"] is not None:
        if context != "Helpdesk":
            raise BookingReferenceDenied()
        start, end, minutes = _period(data["from_time"], data["duration_minutes"], precise=True)
        changed = ticket_interval_changed(previous, previous, start, end)
        if changed:
            portion = _saved_ticket_portion(before, previous, start, end, identity)
            values.update(from_time=start, to_time=end, hours=minutes / 60)

    attribution = prepare_attribution(previous, start, end, portion=portion, previous=previous)
    return values, attribution, not changed


def _lock_projects_for_cancellation(original_project, replacement_project=None):
    # Native cancellation writes Task before Project. Take any original
    # Project lock first, ordered with a different replacement Project lock.
    # When both references match, the entitlement check takes the sole lock.
    if not original_project or original_project == replacement_project:
        return
    projects = {original_project}
    if replacement_project:
        projects.add(replacement_project)
    try:
        for project in sorted(projects):
            _lock_project(project)
    except ProjectBookingGrantError as exc:
        raise BookingReferenceDenied() from exc


@contextmanager
def _authorized_native_cancellation(doc):
    """Temporarily permit native operations on one authorized Timesheet."""
    if (
        not _active_booking.get()
        or type(doc) is not TelectroBookingTimesheet
    ):
        raise BookingOwnershipError()

    flags = getattr(doc, "flags", None)

    if flags is None:
        raise BookingOwnershipError()

    previous = getattr(flags, "ignore_permissions", None)

    # Never inherit an already elevated document.
    if previous:
        raise BookingOwnershipError()

    try:
        flags.ignore_permissions = True
        yield
    finally:
        flags.ignore_permissions = previous

@contextmanager
def _authorized_native_draft_mutation(doc):
    """Permit native mutation only on a managed Draft booking."""
    if getattr(doc, "docstatus", None) != 0:
        raise BookingOwnershipError()
    with _authorized_native_cancellation(doc):
        yield


def _execute(
    *, name, event_id, reason, action, values=None, expected_modified=None, ticket=None,
    saved_request=None,
):
    identity = _guard()
    if (not _identifier(name) or not _identifier(event_id) or len(event_id) > 140
            or not _identifier(reason) or len(reason) > 2000):
        raise BookingInputError()
    # Serialize all operations on this booking, then perform current audit read.
    locked = frappe.db.sql("SELECT name FROM `tabTimesheet` WHERE name=%s FOR UPDATE",
                           name, as_dict=True)
    prior = _audit(event_id)
    if prior:
        if (prior["actor"] != identity.user or prior["action"] != action
                or prior["reason"] != reason or prior["original_timesheet"] != name):
            raise BookingOwnershipError()
        before = json.loads(prior["before_snapshot"])
        _owned(before, identity)
        if not _revision_matches(before.get("modified"), expected_modified):
            raise BookingOwnershipError()
        if values is not None or saved_request is not None:
            after = json.loads(prior["after_snapshot"])
            if saved_request != after.get("saved_work_request"):
                raise BookingOwnershipError()
            if saved_request is not None:
                return {"timesheet": name, "audit": prior["name"]}
            for key, value in values.items():
                stored = after["time_logs"][0].get(key)
                if key == "custom_hd_customer" and "requested_customer_name" in after:
                    stored = after["requested_customer_name"]

                if hasattr(value, "isoformat"):
                    value = value.isoformat()

                if key == "hours":
                    if (
                        type(stored) not in (int, float)
                        or type(value) not in (int, float)
                        or round(stored, 6) != round(value, 6)
                    ):
                        raise BookingOwnershipError()

                elif (
                    (
                        key in (
                            "custom_work_origin",
                            "custom_external_reference",
                            "custom_other_origin_description",
                            "custom_unlisted_customer_name",
                        )
                        or (
                            key == "custom_service_area"
                            and after["time_logs"][0].get(
                                "custom_work_context"
                            ) == "Internal"
                        )
                    )
                    and stored in (None, "")
                    and value in (None, "")
                ):
                    continue

                elif stored != value:
                    raise BookingOwnershipError()
        return {"timesheet": name, "audit": prior["name"]}
    if len(locked) != 1:
        raise BookingOwnershipError()
    doc = frappe.get_doc("Timesheet", name, for_update=True)
    if type(doc) is not TelectroBookingTimesheet:
        raise BookingOwnershipError()
    # Managed ownership below is the authorization boundary.
    current = booking_snapshot(doc)
    before = json.loads(_snapshot(current))
    _owned(before, identity)
    if not _revision_matches(before.get("modified"), expected_modified):
        raise BookingOwnershipError()
    if values is not None or saved_request is not None:
        previous = current["time_logs"][0]
        links = nullcontext()
        requested_customer = None
        if saved_request is not None:
            saved_row = before["time_logs"][0]
            updates, attribution, unchanged = _saved_work_values(before, identity, saved_request)
            if unchanged:
                links = retain_missing_booking_links(doc, saved_row)
        else:
            _retain_blank_origin(values, previous)
            effective_row = {**current["time_logs"][0], **values}
            project_customer = None
            if effective_row.get("custom_work_context") == "Project":
                # Both correction paths lock the Timesheet before the Project.
                project_customer = _authorize_references(
                    effective_row, identity,
                    start=effective_row["from_time"], end=effective_row["to_time"],
                )
            locked_ticket = _validate_customer_consistency(
                effective_row, ticket=ticket, project_customer=project_customer, previous=previous,
            )
            start, end = effective_row["from_time"], effective_row["to_time"]
            portion = _validate_helpdesk_interval(
                effective_row, ticket=ticket, locked_ticket=locked_ticket,
                start=start, end=end, previous=previous,
            )
            attribution = prepare_attribution(effective_row, start, end, portion=portion, previous=previous)
            requested_customer = values.get("custom_hd_customer")
            updates = {**values, "custom_hd_customer": effective_row.get("custom_hd_customer")}
        doc.time_logs[0].update({**updates, **attribution})
        with _authorized_native_draft_mutation(doc), authorized_attribution(doc, attribution), links:
            doc.save()
        after = json.loads(_snapshot(booking_snapshot(doc)))
        _owned(after, identity)
        if after["time_logs"][0]["name"] != before["time_logs"][0]["name"]:
            raise BookingOwnershipError()
        if saved_request is not None:
            after["saved_work_request"] = saved_request
        elif requested_customer != after["time_logs"][0]["custom_hd_customer"]:
            # Keep request identity independent of the resolved Customer for replay.
            after["requested_customer_name"] = requested_customer
        audit = record_correction_event(event_id=event_id, action=action,
                                        reason=reason, before=before, after=after)
    else:
        audit = record_correction_event(event_id=event_id, action=action,
                                        reason=reason, before=before)
        with _authorized_native_draft_mutation(doc):
            doc.delete()  # native link and lifecycle checks; no force flags
    return {"timesheet": name, "audit": audit}


@frappe.whitelist(methods=["POST"])
@_booking_http_errors
def correct_draft_booking(
    *,
    timesheet_name,
    event_id,
    reason,
    work_context=None,
    from_time=None,
    duration_minutes=None,
    description=None,
    activity_type=None,
    ticket_name=None,
    project_name=None,
    task_name=None,
    customer_name=None,
    unlisted_customer_name=None,
    expected_modified=None,
    service_area=None,
    work_location=None,
    work_origin=None,
    external_reference=None,
    other_origin_description=None,
    emergency=None,
    saved_work=None,
):
    with _top_level_booking_transaction(
        expected_command=PREFIX + "correct_draft_booking"
    ):
        if saved_work is not None:
            requested = _saved_work_request(saved_work, description, from_time, duration_minutes)
            return _execute(
                name=timesheet_name, event_id=event_id, reason=reason,
                action="Draft Correction", expected_modified=expected_modified,
                saved_request=requested,
            )

        identity = _guard()

        if not _identifier(description) or len(description) > 2000:
            raise BookingInputError()

        start, end, minutes = _period(from_time, duration_minutes)

        values = dict(
            custom_work_context=work_context,
            custom_hd_ticket=ticket_name,
            custom_hd_customer=customer_name,
            custom_unlisted_customer_name=unlisted_customer_name,
            project=project_name,
            task=task_name,
        )

        validate_work_context(values)

        ticket = None
        if work_context != "Project":
            ticket = _authorize_references(values, identity)
        _require_booking_activity_type(activity_type)
        _visible("Activity Type", activity_type)

        if work_context == "Helpdesk":
            ticket_area = ticket.get("custom_service_area")

            if service_area not in (None, "", ticket_area):
                raise BookingMetadataValidationError(
                    "Helpdesk Service Area must match its ticket"
                )

            effective_service_area = ticket_area
        else:
            effective_service_area = service_area

        values.update(
            normalize_booking_metadata(
                work_context=work_context,
                service_area=effective_service_area,
                allowed_service_areas=_allowed_service_areas(),
                activity_type=activity_type,
                work_location=work_location,
                work_origin=work_origin,
                external_reference=external_reference,
                other_origin_description=other_origin_description,
                emergency=emergency,
            )
        )

        values.update(
            from_time=start,
            to_time=end,
            hours=minutes / 60,
            description=description,
            activity_type=activity_type,
        )

        return _execute(
            name=timesheet_name,
            event_id=event_id,
            reason=reason,
            action="Draft Correction",
            values=values,
            expected_modified=expected_modified,
            ticket=ticket,
        )


@frappe.whitelist(methods=["POST"])
@_booking_http_errors
def withdraw_draft_booking(*, timesheet_name, event_id, reason, expected_modified=None):
    with _top_level_booking_transaction(expected_command=PREFIX + "withdraw_draft_booking"):
        return _execute(name=timesheet_name, event_id=event_id, reason=reason,
                        action="Draft Withdrawal", expected_modified=expected_modified)


@frappe.whitelist(methods=["POST"])
@_booking_http_errors
def cancel_submitted_booking(
    *,
    timesheet_name,
    event_id,
    reason,
    expected_modified=None,
):
    with _top_level_booking_transaction(
        expected_command=PREFIX + "cancel_submitted_booking"
    ):
        identity = _guard()

        if (
            not _identifier(timesheet_name)
            or not _identifier(event_id)
            or len(event_id) > 140
            or not _identifier(reason)
            or len(reason) > 2000
            or not _identifier(expected_modified)
        ):
            raise BookingInputError()

        # Serialize operations against the original Timesheet.
        locked = frappe.db.sql(
            "SELECT name FROM `tabTimesheet` WHERE name=%s FOR UPDATE",
            timesheet_name,
            as_dict=True,
        )

        if len(locked) != 1:
            raise BookingOwnershipError()

        # A repeated event must match the original operation exactly.
        prior = _audit(event_id)

        if prior:
            if (
                prior["actor"] != identity.user
                or prior["action"] != "Submitted Cancellation"
                or prior["reason"] != reason
                or prior["original_timesheet"] != timesheet_name
            ):
                raise BookingOwnershipError()

            before = json.loads(prior["before_snapshot"])

            authorize_parent(
                identity,
                before,
                operation="cancel_submitted",
            )

            if len(before.get("time_logs", [])) != 1:
                raise BookingOwnershipError()

            authorize_child(
                identity,
                before,
                before["time_logs"][0],
                operation="cancel_submitted",
            )

            if not _revision_matches(before.get("modified"), expected_modified):
                raise BookingOwnershipError()

            return {
                "timesheet": timesheet_name,
                "audit": prior["name"],
            }

        # First execution: use the current locked document.
        doc = frappe.get_doc(
            "Timesheet",
            timesheet_name,
            for_update=True,
        )

        if type(doc) is not TelectroBookingTimesheet:
            raise BookingOwnershipError()

        before = json.loads(_snapshot(booking_snapshot(doc)))

        authorize_parent(
            identity,
            before,
            operation="cancel_submitted",
        )

        if len(before.get("time_logs", [])) != 1:
            raise BookingOwnershipError()

        authorize_child(
            identity,
            before,
            before["time_logs"][0],
            operation="cancel_submitted",
        )

        if not _revision_matches(before.get("modified"), expected_modified):
            raise BookingOwnershipError()

        # Identity, ownership, state and revision are already authorized.
        _lock_projects_for_cancellation(before["time_logs"][0].get("project"))
        # Record the audit without elevated document permissions.
        audit = record_correction_event(
            event_id=event_id,
            action="Submitted Cancellation",
            reason=reason,
            before=before,
        )

        # Elevate only this Timesheet instance for native cancellation.
        # The permission flag is restored even if cancellation fails.
        with _authorized_native_cancellation(doc):
            doc.cancel()

        return {
            "timesheet": timesheet_name,
            "audit": audit,
        }

@frappe.whitelist(methods=["POST"])
@_booking_http_errors
def replace_submitted_booking(
    *,
    timesheet_name,
    event_id,
    reason,
    expected_modified,
    work_context=None,
    from_time=None,
    duration_minutes=None,
    description=None,
    activity_type=None,
    ticket_name=None,
    project_name=None,
    task_name=None,
    customer_name=None,
    unlisted_customer_name=None,
    service_area=None,
    work_location=None,
    work_origin=None,
    external_reference=None,
    other_origin_description=None,
    emergency=None,
    saved_work=None,
):
    """Cancel one owned submitted booking and insert its replacement atomically."""
    with _top_level_booking_transaction(
        expected_command=PREFIX + "replace_submitted_booking"
    ):
        identity = _guard()

        if (
            not _identifier(timesheet_name)
            or not _identifier(event_id)
            or len(event_id) > 140
            or not _identifier(reason)
            or len(reason) > 2000
            or not _identifier(expected_modified)
        ):
            raise BookingInputError()

        saved_request = None
        if saved_work is not None:
            saved_request = _saved_work_request(saved_work, description, from_time, duration_minutes)

        # Serialize operations against the submitted original.
        locked = frappe.db.sql(
            "SELECT name FROM `tabTimesheet` WHERE name=%s FOR UPDATE",
            timesheet_name,
            as_dict=True,
        )

        if len(locked) != 1:
            raise BookingOwnershipError()

        prior = _replacement_audit(event_id)

        if prior:
            if (
                prior["actor"] != identity.user
                or prior["action"] != "Submitted Replacement"
                or prior["reason"] != reason
                or prior["original_timesheet"] != timesheet_name
                or prior.get("after_snapshot") is not None
                or not _identifier(prior.get("replacement_timesheet"))
            ):
                raise BookingOwnershipError()

            before = json.loads(prior["before_snapshot"])

            authorize_parent(
                identity,
                before,
                operation="replace_submitted",
            )

            if len(before.get("time_logs", [])) != 1:
                raise BookingOwnershipError()

            authorize_child(
                identity,
                before,
                before["time_logs"][0],
                operation="replace_submitted",
            )

            if not _revision_matches(before.get("modified"), expected_modified):
                raise BookingOwnershipError()

            evidence = prior.get("replacement_request_snapshot")

            try:
                canonical_evidence = _validated_replacement_request(evidence)
            except BookingCorrectionAuditError as exc:
                raise BookingOwnershipError() from exc

            recorded = json.loads(canonical_evidence)
            historical = set(recorded) == _REPLACEMENT_REQUEST_FIELDS
            saved_evidence = recorded.get("saved_work") is True
            if saved_evidence != (saved_request is not None):
                raise BookingOwnershipError()
            if saved_evidence:
                requested = saved_request
            elif historical:
                # A legacy retry must not silently ignore new metadata.
                if any(
                    value is not None
                    for value in (
                        unlisted_customer_name,
                        service_area,
                        work_location,
                        work_origin,
                        external_reference,
                        other_origin_description,
                        emergency,
                    )
                ):
                    raise BookingOwnershipError()

                requested = _legacy_replacement_request_snapshot(
                    work_context=work_context,
                    from_time=from_time,
                    duration_minutes=duration_minutes,
                    description=description,
                    activity_type=activity_type,
                    ticket_name=ticket_name,
                    project_name=project_name,
                    task_name=task_name,
                    customer_name=customer_name,
                )

            else:
                recorded_area = recorded["service_area"]

                # Historical audit evidence is the authority for
                # retry comparison, not current HD Ticket metadata.
                retry_areas = (
                    (recorded_area,)
                    if recorded_area is not None
                    else ("Other",)
                )
                # A Helpdesk caller may omit Service Area because the
                # authorized ticket supplied it during first execution.
                # Reuse immutable audit evidence; do not reload the ticket.
                retry_service_area = service_area

                if (
                    work_context == "Helpdesk"
                    and service_area in (None, "")
                ):
                    retry_service_area = recorded_area
                try:
                    requested = _replacement_request_snapshot(
                        work_context=work_context,
                        from_time=from_time,
                        duration_minutes=duration_minutes,
                        description=description,
                        activity_type=activity_type,
                        ticket_name=ticket_name,
                        project_name=project_name,
                        task_name=task_name,
                        customer_name=customer_name,
                        unlisted_customer_name=unlisted_customer_name,
                        service_area=retry_service_area,
                        work_location=work_location,
                        work_origin=work_origin,
                        external_reference=external_reference,
                        other_origin_description=other_origin_description,
                        emergency=emergency,
                        allowed_service_areas=retry_areas,
                    )
                except BookingMetadataValidationError as exc:
                    raise BookingOwnershipError() from exc

            if prior.get("replacement_request_snapshot") != requested:
                raise BookingOwnershipError()

            # The original replacement was already committed.
            # Return its immutable audit identity without loading
            # or modifying either Timesheet.
            return {
                "original_timesheet": timesheet_name,
                "replacement_timesheet": prior["replacement_timesheet"],
                "audit": prior["name"],
            }

        doc = frappe.get_doc(
            "Timesheet",
            timesheet_name,
            for_update=True,
        )

        if type(doc) is not TelectroBookingTimesheet:
            raise BookingOwnershipError()

        before = json.loads(_snapshot(booking_snapshot(doc)))

        authorize_parent(
            identity,
            before,
            operation="replace_submitted",
        )

        if len(before.get("time_logs", [])) != 1:
            raise BookingOwnershipError()

        authorize_child(
            identity,
            before,
            before["time_logs"][0],
            operation="replace_submitted",
        )

        if not _revision_matches(before.get("modified"), expected_modified):
            raise BookingOwnershipError()

        previous = before["time_logs"][0]
        retain_links = False
        if saved_request is not None:
            updates, attribution, retain_links = _saved_work_values(before, identity, saved_request)
            requested = saved_request
            row = {
                field: previous.get(field) for field in (
                    "custom_work_context", "custom_hd_ticket", "custom_hd_customer",
                    "custom_unlisted_customer_name", "project", "task", "custom_service_area",
                    "custom_work_location", "custom_work_origin", "custom_external_reference",
                    "custom_other_origin_description", "custom_emergency", "activity_type",
                    "from_time", "to_time", "hours",
                )
            }
            row.update(updates)
            row.update(attribution)
        else:
            # Authorize references before any lifecycle mutation.
            reference_row = {
                "custom_work_context": work_context,
                "custom_hd_ticket": ticket_name,
                "custom_hd_customer": customer_name,
                "custom_unlisted_customer_name": unlisted_customer_name,
                "project": project_name,
                "task": task_name,
            }

            validate_work_context(reference_row)

            ticket = None
            if work_context != "Project":
                ticket = _authorize_references(reference_row, identity)

            _require_booking_activity_type(activity_type)
            _visible("Activity Type", activity_type)

            # Helpdesk Service Area must come from the authorized ticket.
            if work_context == "Helpdesk":
                ticket_area = ticket.get("custom_service_area")

                if service_area not in (None, "", ticket_area):
                    raise BookingMetadataValidationError(
                        "Helpdesk Service Area must match its ticket"
                    )

                effective_service_area = ticket_area
            else:
                effective_service_area = service_area

            # Create complete, canonical replacement request evidence.
            requested = _replacement_request_snapshot(
                work_context=work_context,
                from_time=from_time,
                duration_minutes=duration_minutes,
                description=description,
                activity_type=activity_type,
                ticket_name=ticket_name,
                project_name=project_name,
                task_name=task_name,
                customer_name=customer_name,
                unlisted_customer_name=unlisted_customer_name,
                service_area=effective_service_area,
                work_location=work_location,
                work_origin=work_origin,
                external_reference=external_reference,
                other_origin_description=other_origin_description,
                emergency=emergency,
            )

            values = json.loads(requested)

            # Keep requested Customer evidence intact and resolve the persisted identity separately.
            row = {
                "custom_work_context": values["work_context"],
                "custom_hd_ticket": values["ticket_name"],
                "custom_hd_customer": values["customer_name"],
                "custom_unlisted_customer_name": values[
                    "unlisted_customer_name"
                ],
                "project": values["project_name"],
                "task": values["task_name"],
                "custom_service_area": values["service_area"],
                "custom_work_location": values["work_location"],
                "custom_work_origin": values["work_origin"],
                "custom_external_reference": values["external_reference"],
                "custom_other_origin_description": values[
                    "other_origin_description"
                ],
                "custom_emergency": values["emergency"],
            }

            _retain_blank_origin(row, previous)
            start = datetime.fromisoformat(values["from_time"])
            end = datetime.fromisoformat(values["to_time"])
            minutes = values["duration_minutes"]
            _lock_projects_for_cancellation(
                before["time_logs"][0].get("project"), row["project"],
            )
            project_customer = None
            if work_context == "Project":
                project_customer = _authorize_references(reference_row, identity, start=start, end=end)
            previous = before["time_logs"][0]
            locked_ticket = _validate_customer_consistency(
                row, ticket=ticket, project_customer=project_customer, previous=previous,
            )
            portion = _validate_helpdesk_interval(
                row, ticket=ticket, locked_ticket=locked_ticket,
                start=start, end=end, previous=previous,
            )
            attribution = prepare_attribution(row, start, end, portion=portion, previous=previous)
            row.update(
                attribution, activity_type=values["activity_type"], from_time=start, to_time=end,
                hours=minutes / 60, description=values["description"],
            )

        # Original ownership, Submitted state and revision have already
        # been verified against the locked persisted document.
        #
        # Native cancellation must occur before inserting the replacement
        # so that ERPNext's time-overlap validation sees the cancelled
        # original rather than a second concurrent booking.
        links = retain_missing_booking_links(doc, previous) if retain_links else nullcontext()
        with _authorized_native_cancellation(doc), links:
            doc.cancel()

        # Create a separate Draft, deliberately without amended_from.
        # The correction audit records the original/replacement relation.
        replacement = frappe.get_doc({
            "doctype": "Timesheet",
            "naming_series": "TS-.YYYY.-",
            "custom_telectro_booking_origin": "Phase 2",
            "employee": identity.employee,
            "company": identity.company,
            "user": identity.user,
            "docstatus": 0,
            "time_logs": [{
                "doctype": "Timesheet Detail",
                **row,
            }],
        })

        if (
            type(replacement) is not TelectroBookingTimesheet
            or len(replacement.time_logs) != 1
        ):
            raise ActivationConfigurationError()

        # Reuse the same one-use creation intent and narrowly scoped
        # native permission elevation as ordinary Technician bookings.
        links = retain_missing_booking_links(replacement, previous) if retain_links else nullcontext()
        with (
            _phase2_creation_intent(replacement, identity),
            _authorized_native_creation(replacement, identity),
            authorized_attribution(replacement, attribution),
            links,
        ):
            inserted = replacement.insert()

        # Preserve the ordinary booking endpoint's post-insert checks.
        if (
            inserted is not replacement
            or not _identifier(replacement.name)
            or len(replacement.time_logs) != 1
            or replacement.get("employee") != identity.employee
            or replacement.get("company") != identity.company
            or replacement.get("user") != identity.user
            or replacement.get("owner") != identity.user
        ):
            raise ActivationConfigurationError()

        # Both native permission scopes have ended before audit insertion.
        audit = record_correction_event(
            event_id=event_id,
            action="Submitted Replacement",
            reason=reason,
            before=before,
            replacement_timesheet=replacement.name,
            replacement_request_snapshot=requested,
        )

        return {
            "original_timesheet": timesheet_name,
            "replacement_timesheet": replacement.name,
            "audit": audit,
        }
