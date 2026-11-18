"""Private append-only correction evidence; performs no correction itself."""

from datetime import date, datetime
from decimal import Decimal
import json
from collections.abc import Mapping

DOCTYPE = "TELECTRO Booking Correction Audit"
ACTIONS = frozenset((
    "Draft Correction", "Draft Withdrawal",
    "Submitted Cancellation", "Submitted Replacement",
))


class BookingCorrectionAuditError(PermissionError):
    def __init__(self):
        super().__init__("Booking correction audit is unavailable.")


def _text(value):
    return type(value) is str and bool(value.strip()) and value == value.strip()


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError()


def _snapshot(value):
    """Freeze one complete caller-supplied persisted Timesheet projection."""
    if not isinstance(value, Mapping):
        raise BookingCorrectionAuditError()
    try:
        frozen = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                       default=_json_default, allow_nan=False))
    except (TypeError, ValueError, OverflowError) as exc:
        raise BookingCorrectionAuditError() from exc
    if type(frozen) is not dict or set((
            "name", "doctype", "employee", "company", "user", "owner",
            "creation", "docstatus", "custom_telectro_booking_origin",
            "time_logs")) - set(frozen):
        raise BookingCorrectionAuditError()
    if (frozen["doctype"] != "Timesheet"
            or frozen["custom_telectro_booking_origin"] != "Phase 2"
            or type(frozen["docstatus"]) is not int
            or frozen["docstatus"] not in (0, 1, 2)
            or not all(_text(frozen.get(field)) for field in (
                "name", "employee", "company", "user", "owner", "creation"))):
        raise BookingCorrectionAuditError()
    rows = frozen["time_logs"]
    if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict:
        raise BookingCorrectionAuditError()
    row = rows[0]
    required = ("name", "doctype", "parent", "parenttype", "parentfield",
                "custom_work_context", "from_time", "to_time", "hours",
                "description", "activity_type", "custom_hd_ticket",
                "custom_hd_customer", "project", "task")
    if set(required) - set(row) or not all(_text(row.get(field)) for field in (
            "name", "custom_work_context", "from_time", "to_time",
            "description", "activity_type")):
        raise BookingCorrectionAuditError()
    if (row["doctype"] != "Timesheet Detail" or row["parent"] != frozen["name"]
            or row["parenttype"] != "Timesheet" or row["parentfield"] != "time_logs"
            or type(row["hours"]) not in (int, float) or row["hours"] <= 0):
        raise BookingCorrectionAuditError()
    for field in ("custom_hd_ticket", "custom_hd_customer", "project", "task"):
        if row[field] is not None and type(row[field]) is not str:
            raise BookingCorrectionAuditError()
    return json.dumps(frozen, sort_keys=True, separators=(",", ":"), allow_nan=False)


_REPLACEMENT_REQUEST_FIELDS = frozenset((
    "work_context",
    "from_time",
    "to_time",
    "duration_minutes",
    "description",
    "activity_type",
    "ticket_name",
    "project_name",
    "task_name",
    "customer_name",
))


def _validated_replacement_request(value):
    """Accept only canonical, structurally valid replacement evidence."""
    if not _text(value):
        raise BookingCorrectionAuditError()

    try:
        data = json.loads(value)

        canonical = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise BookingCorrectionAuditError() from exc

    if (
        type(data) is not dict
        or set(data) != _REPLACEMENT_REQUEST_FIELDS
        or canonical != value
    ):
        raise BookingCorrectionAuditError()

    if not all(
        _text(data.get(field))
        for field in (
            "work_context",
            "from_time",
            "to_time",
            "description",
            "activity_type",
        )
    ):
        raise BookingCorrectionAuditError()

    minutes = data["duration_minutes"]

    if type(minutes) is not int or not 0 < minutes <= 1440:
        raise BookingCorrectionAuditError()

    for field in (
        "ticket_name",
        "project_name",
        "task_name",
        "customer_name",
    ):
        reference = data[field]

        if reference is not None and not _text(reference):
            raise BookingCorrectionAuditError()

    return canonical


def record_correction_event(
    *,
    event_id,
    action,
    reason,
    before,
    after=None,
    replacement_timesheet=None,
    replacement_request_snapshot=None,
):
    """Trusted caller supplies persisted snapshots; session supplies audit authority.

    No client endpoint, commit, delete, cancellation or Timesheet mutation lives
    here. Caller must keep this insert and its correction in one transaction.
    """
    import frappe
    from frappe.utils import now_datetime

    actor = getattr(frappe.session, "user", None)
    if (not _text(actor) or actor in ("Guest", "Administrator")
            or not _text(event_id) or len(event_id) > 140
            or action not in ACTIONS or not _text(reason)
            or len(reason) > 2000
            or replacement_timesheet is not None
            and not _text(replacement_timesheet)):
        raise BookingCorrectionAuditError()
    before_json = _snapshot(before)
    after_json = _snapshot(after) if after is not None else None
    original = json.loads(before_json)
    if (after_json is not None
            and json.loads(after_json)["name"] != original["name"]
            and action == "Draft Correction"):
        raise BookingCorrectionAuditError()
    if action in ("Draft Correction", "Draft Withdrawal") and original["docstatus"] != 0:
        raise BookingCorrectionAuditError()
    if action in ("Submitted Cancellation", "Submitted Replacement") and original["docstatus"] != 1:
        raise BookingCorrectionAuditError()
    if action == "Draft Correction" and after_json is None:
        raise BookingCorrectionAuditError()
    if action != "Draft Correction" and after_json is not None:
        raise BookingCorrectionAuditError()
    if (action == "Submitted Replacement") != (replacement_timesheet is not None):
        raise BookingCorrectionAuditError()
    if action == "Submitted Replacement":
        replacement_request_snapshot = _validated_replacement_request(
            replacement_request_snapshot
        )
    elif replacement_request_snapshot is not None:
        raise BookingCorrectionAuditError()

    rows = frappe.db.sql(
        "SELECT name, event_id, action, actor, reason, original_timesheet, "
        "original_time_log, before_snapshot, after_snapshot, "
        "replacement_timesheet, replacement_request_snapshot "
        "FROM `tabTELECTRO Booking Correction Audit` "
        "WHERE event_id=%s FOR UPDATE",
        event_id,
        as_dict=True,
    )
    if len(rows) > 1:
        raise BookingCorrectionAuditError()
    expected = dict(
        event_id=event_id, action=action, actor=actor, reason=reason,
        original_timesheet=original["name"],
        original_time_log=original["time_logs"][0]["name"],
        before_snapshot=before_json, after_snapshot=after_json,
        replacement_timesheet=replacement_timesheet,
        replacement_request_snapshot=replacement_request_snapshot,
    )
    if rows:
        row = rows[0]
        if not _text(row.get("name")) or any(row.get(key) != value for key, value in expected.items()):
            raise BookingCorrectionAuditError()
        return row["name"]
    doc = frappe.get_doc({"doctype": DOCTYPE, **expected,
                          "recorded_at": now_datetime()})
    try:
        doc.insert(ignore_permissions=True)
    except frappe.UniqueValidationError as exc:
        raise BookingCorrectionAuditError() from exc
    return doc.name
