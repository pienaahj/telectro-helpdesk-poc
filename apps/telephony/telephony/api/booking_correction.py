"""Owned single-row Draft correction and withdrawal; no internal commits."""
import json

import frappe

from telephony.api.time_booking import (
    _identifier, _period, _visible, _authorize_references, BookingInputError,
)
from telephony.time_booking_activation_adapter import _require_activation_configuration
from telephony.time_booking_activation_policy import ACTIVE_RUNTIME, ActivationConfigurationError
from telephony.time_booking_identity import resolve_current_technician_identity
from telephony.time_booking_ownership import authorize_parent, authorize_child, BookingOwnershipError
from telephony.time_booking_policy import validate_work_context
from telephony.time_booking_correction_audit import record_correction_event, _snapshot, DOCTYPE
from telephony.time_booking_timesheet_controller import TelectroBookingTimesheet
from telephony.time_booking_transaction import _top_level_booking_transaction


PREFIX = "telephony.api.booking_correction."


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


def _owned(snapshot, identity):
    authorize_parent(identity, snapshot, operation="correct")
    if len(snapshot.get("time_logs", [])) != 1:
        raise BookingOwnershipError()
    authorize_child(identity, snapshot, snapshot["time_logs"][0], operation="correct")


def _execute(*, name, event_id, reason, action, values=None, expected_modified=None):
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
        if str(before.get("modified")) != str(expected_modified):
            raise BookingOwnershipError()
        if values is not None:
            after = json.loads(prior["after_snapshot"])
            for key, value in values.items():
                stored = after["time_logs"][0].get(key)
                if hasattr(value, "isoformat"):
                    value = value.isoformat()
                if stored != value:
                    raise BookingOwnershipError()
        return {"timesheet": name, "audit": prior["name"]}
    if len(locked) != 1:
        raise BookingOwnershipError()
    doc = frappe.get_doc("Timesheet", name, for_update=True)
    if type(doc) is not TelectroBookingTimesheet:
        raise BookingOwnershipError()
    doc.check_permission("read")
    doc.check_permission("write" if values is not None else "delete")
    before = json.loads(_snapshot(doc.as_dict()))
    _owned(before, identity)
    if (not expected_modified or not before.get("modified")
            or str(before["modified"]) != str(expected_modified)):
        raise BookingOwnershipError()
    if values is not None:
        doc.time_logs[0].update(values)
        doc.save()  # native overlap, link, permission and lifecycle checks
        after = json.loads(_snapshot(doc.as_dict()))
        _owned(after, identity)
        if after["time_logs"][0]["name"] != before["time_logs"][0]["name"]:
            raise BookingOwnershipError()
        audit = record_correction_event(event_id=event_id, action=action,
                                        reason=reason, before=before, after=after)
    else:
        audit = record_correction_event(event_id=event_id, action=action,
                                        reason=reason, before=before)
        doc.delete()  # native permissions, links and lifecycle; no force flags
    return {"timesheet": name, "audit": audit}


@frappe.whitelist(methods=["POST"])
def correct_draft_booking(*, timesheet_name, event_id, reason, work_context,
                          from_time, duration_minutes, description, activity_type,
                          ticket_name=None, project_name=None, task_name=None,
                          customer_name=None, expected_modified=None):
    with _top_level_booking_transaction(expected_command=PREFIX + "correct_draft_booking"):
        # Validate references under the same request boundary. No writes here.
        identity = _guard()
        if not _identifier(description) or len(description) > 2000:
            raise BookingInputError()
        start, end, minutes = _period(from_time, duration_minutes)
        values = dict(custom_work_context=work_context, custom_hd_ticket=ticket_name,
                      custom_hd_customer=customer_name, project=project_name, task=task_name)
        validate_work_context(values)
        _authorize_references(values, identity.company)
        _visible("Activity Type", activity_type)
        values.update(from_time=start, to_time=end, hours=minutes / 60,
                      description=description, activity_type=activity_type)
        return _execute(name=timesheet_name, event_id=event_id, reason=reason,
                        action="Draft Correction", values=values, expected_modified=expected_modified)


@frappe.whitelist(methods=["POST"])
def withdraw_draft_booking(*, timesheet_name, event_id, reason, expected_modified=None):
    with _top_level_booking_transaction(expected_command=PREFIX + "withdraw_draft_booking"):
        return _execute(name=timesheet_name, event_id=event_id, reason=reason,
                        action="Draft Withdrawal", expected_modified=expected_modified)
