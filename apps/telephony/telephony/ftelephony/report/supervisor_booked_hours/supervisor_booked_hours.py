"""Live Supervisor reporting over the authorized Phase 2 ledger."""

from collections.abc import Mapping
from functools import lru_cache

import frappe
from frappe import _
from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions

from telephony.booked_hours import date_window, hours_rows
from telephony.customer_identity_sync import _hd_customers_for
from telephony.ftelephony.report.technician_own_booked_hours.technician_own_booked_hours import (
    _DETAIL_COLUMNS,
    _spreadsheet_text,
)
from telephony.supervisor_reporting_grant import resolve_supervisor_reporting_scope

_REPORT_ROWS = """
    SELECT parent.name AS booking, parent.docstatus,
           parent.user, parent.employee, parent.company,
           detail.from_time, detail.to_time, detail.activity_type, detail.description,
           detail.custom_work_context AS work_context,
           detail.custom_service_area AS service_area,
           detail.custom_work_origin AS work_origin,
           detail.custom_emergency AS emergency,
           detail.custom_hd_customer AS customer,
           detail.custom_unlisted_customer_name AS unlisted_customer,
           detail.project, detail.task, detail.custom_hd_ticket AS ticket,
           detail.custom_external_reference AS snapfix_reference
      FROM `tabTimesheet` parent
      JOIN `tabTimesheet Detail` detail
        ON detail.parent = parent.name
       AND detail.parenttype = 'Timesheet'
       AND detail.parentfield = 'time_logs'
     WHERE parent.custom_telectro_booking_origin = 'Phase 2'
       AND (parent.user, parent.employee, parent.company) IN %(roster)s
       AND parent.docstatus IN (0, 1)
       AND detail.from_time < %(end)s AND detail.to_time > %(start)s
       AND detail.to_time > detail.from_time
     ORDER BY detail.from_time, detail.name
"""

_FILTER_FIELDS = (
    "company", "employee", "customer", "customer_type", "work_context", "service_area",
    "work_origin", "emergency", "activity_type", "reference_state", "ticket", "project", "task",
    "snapfix_reference", "reference_kind",
)
_ROSTER = ("company", "employee")
_CUSTOMER = ("customer_type", "customer", "unlisted_customer")
_WORK_REFERENCE = ("ticket", "project", "task", "snapfix_reference", "reference_state")
_BREAKDOWNS = {
    "Technician Breakdown": (*_ROSTER, "work_context", *_CUSTOMER, *_WORK_REFERENCE),
    "Customer Breakdown": (*_CUSTOMER, "work_context", *_ROSTER),
    "Work Context Breakdown": ("work_context", *_ROSTER),
    "Project / Reference Breakdown": ("work_context", *_WORK_REFERENCE, *_ROSTER),
    "Service Area Breakdown": ("service_area", "work_context", *_ROSTER),
    "Activity Breakdown": ("activity_type", "work_context", *_ROSTER),
}
_REFERENCE_STATES = ("Available", "Restricted reference", "Missing historical reference", "Unattributed", "Not applicable")
_CUSTOMER_STATES = ("Listed Customer", "Unlisted Customer", "Unattributed", "Not applicable")
_REFERENCES = {"project": "Project", "task": "Task", "ticket": "HD Ticket"}
_REFERENCE_KINDS = {
    "Snapfix": "snapfix_reference", "Ticket": "ticket", "Project": "project", "Task": "task",
}
_CUSTOMER_TYPES = ("HD Customer", "Customer")
_CUSTOMER_CONTEXTS = (*_CUSTOMER_TYPES, "Timesheet", "Timesheet Detail")


def execute(filters=None):
    roster = resolve_supervisor_reporting_scope()
    start, end, view, criteria = _report_filters(filters)
    columns = _columns(view)
    bookings = authorized_bookings(roster, start, end, criteria)
    detail = view == "Booking Detail"
    if detail:
        result = hours_rows(bookings, start, end, detail=True)
    else:
        result = hours_rows(
            bookings, start, end,
            group_by=_BREAKDOWNS.get(view, _ROSTER), by_day=view == "Daily Summary",
        )
    names = employee_labels({row["employee"] for row in result})
    fields = tuple(column["fieldname"] for column in columns)
    for row in result:
        row["technician"] = names.get(row["employee"]) or _("Technician")
    return columns, [_format_row(row, fields) for row in result]


def employee_labels(employee_ids):
    """Resolve names for Employee IDs from an already-authorized report projection."""
    if not employee_ids:
        return {}
    return {
        row.name: row.employee_name or _("Technician")
        for row in frappe.get_all("Employee", filters={"name": ["in", sorted(employee_ids)]},
                                  fields=["name", "employee_name"])
    }


def authorized_bookings(roster, start, end, criteria=None):
    """Return the shared grant-scoped, permission-projected operational rows."""
    criteria = criteria or {}
    scope = {
        (identity.user, identity.employee, identity.company)
        for identity in roster
        if all(
            field not in criteria or getattr(identity, field).casefold() == criteria[field]
            for field in ("employee", "company")
        )
    }
    if not scope:
        return []
    permissions = get_user_permissions(frappe.session.user)
    if not isinstance(permissions, Mapping):
        raise frappe.PermissionError(_("Customer permissions are unavailable."))

    customer_limits = {
        (kind, context): allowed
        for kind in _CUSTOMER_TYPES
        for context in (*_CUSTOMER_CONTEXTS, "HD Ticket", "Project")
        if (allowed := get_allowed_docs_for_doctype(permissions.get(kind, ()), context))
    }
    load = lru_cache(maxsize=512)(_load_reference)
    customer_mapping = lru_cache(maxsize=512)(_customer_mapping)
    rows = frappe.db.sql(_REPORT_ROWS, dict(roster=sorted(scope), start=start, end=end), as_dict=True)
    bookings = []
    for row in rows:
        if (row.user, row.employee, row.company) not in scope:
            continue
        if not _customer_allowed(row, customer_limits, load, customer_mapping):
            continue
        row = _project_booking(row, load)
        if _matches(row, criteria):
            bookings.append(row)

    return bookings


def _report_filters(filters):
    filters = filters or {}
    try:
        if not isinstance(filters, Mapping):
            raise ValueError
        start, end = date_window(filters.get("from_date"), filters.get("to_date"))
    except (OverflowError, ValueError):
        raise frappe.ValidationError(_("Enter a valid From Date and To Date in chronological order.")) from None
    view = filters.get("view")
    if view in (None, ""):
        view = "Daily Summary"
    if not isinstance(view, str) or view not in ("Daily Summary", "Booking Detail", *_BREAKDOWNS):
        raise frappe.ValidationError(_("Select a valid report view."))
    criteria = {}
    fixed_options = {
        "emergency": ("Yes", "No"), "customer_type": _CUSTOMER_STATES,
        "reference_state": _REFERENCE_STATES,
        "reference_kind": (*_REFERENCE_KINDS, "No visible reference"),
    }
    for field in _FILTER_FIELDS:
        value = filters.get(field)
        if value in (None, ""):
            continue
        if not isinstance(value, str) or (field in fixed_options and value not in fixed_options[field]):
            raise frappe.ValidationError(_("Select a valid report filter."))
        criteria[field] = value.strip().casefold()
    return start, end, view, criteria


def _load_reference(doctype, name):
    # Reference permission hooks can write to the request message log.
    # These lookups are internal to the authorized report projection.
    messages = frappe.local.message_log
    frappe.local.message_log = []
    try:
        doc = frappe.get_doc(doctype, name)
        if str(doc.name) == name:
            if doc.has_permission("read"):
                return doc, True, "Available"
            return doc, False, "Restricted reference"
    except frappe.DoesNotExistError:
        pass
    except frappe.PermissionError:
        return None, False, "Restricted reference"
    finally:
        frappe.local.message_log = messages
    return None, False, "Missing historical reference"


def _customer_mapping(erp_customer):
    """Identify an exact ERP Customer and at most one operational counterpart."""
    if frappe.db.get_value("Customer", erp_customer, "name") != erp_customer:
        return None
    matches = _hd_customers_for(erp_customer)
    return tuple(matches) if len(matches) <= 1 else None


def _customer_allowed(row, limits, load, customer_mapping):
    contexts = _CUSTOMER_CONTEXTS + tuple(
        doctype for field, doctype in (("ticket", "HD Ticket"), ("project", "Project")) if row[field]
    )
    allowed = {kind: [limits[kind, context] for context in contexts if (kind, context) in limits]
               for kind in _CUSTOMER_TYPES}
    restricted = any(allowed.values())
    saved_customer = row.customer
    if restricted and (not saved_customer or row.unlisted_customer):
        return False
    if row.unlisted_customer and (saved_customer or row.ticket or row.project):
        return False

    if not saved_customer:
        # Keep unattributed work in authorized overall totals without assigning
        # a historical Customer from today's Ticket or Project mapping.
        project = load("Project", str(row.project))[0] if row.project else None
        return project is None or project.get("company") == row.company

    hd_customer, erp_customer = saved_customer, None
    for field, doctype in (("ticket", "HD Ticket"), ("project", "Project")):
        if not row[field]:
            continue
        document = load(doctype, str(row[field]))[0]
        if document is None:
            if restricted:
                return False
            continue
        if field == "ticket":
            ticket_hd = document.get("customer")
            if hd_customer and ticket_hd and hd_customer != ticket_hd:
                return False
            hd_customer = hd_customer or ticket_hd
            erp_customer = document.get("custom_customer")
        else:
            if document.get("company") != row.company:
                return False
            project_customer = document.get("customer")
            if erp_customer and project_customer and erp_customer != project_customer:
                return False
            erp_customer = erp_customer or project_customer

    if hd_customer:
        hd_doc, can_read, _ = load("HD Customer", hd_customer)
        if not can_read:
            return False
        mapped_customer = hd_doc.get("custom_erp_customer")
        if erp_customer and mapped_customer != erp_customer:
            return False
        erp_customer = mapped_customer
    if erp_customer:
        mapping = customer_mapping(erp_customer)
        if mapping is None or (hd_customer and mapping != (hd_customer,)):
            return False
        if not hd_customer and mapping and not load("HD Customer", mapping[0])[1]:
            return False

    return all(
        value in permission
        for kind, value in (("HD Customer", saved_customer), ("Customer", erp_customer))
        for permission in allowed[kind]
    )


def _project_booking(row, load):
    row = dict(row)
    row["emergency"] = int(row["emergency"] == 1)
    row["activity_type"] = row["activity_type"] or "Unattributed"
    row["work_context"] = row["work_context"] or "Unattributed"
    row["status"] = _("Draft") if row["docstatus"] == 0 else _("Submitted")
    row["recorded_start"], row["recorded_end"] = row["from_time"], row["to_time"]
    if row["customer"]:
        row["customer_type"] = "Listed Customer"
    elif row["unlisted_customer"]:
        row["customer_type"] = "Unlisted Customer"
    elif row["work_context"] == "Internal":
        row["customer_type"] = "Not applicable"
    else:
        row["customer_type"] = "Unattributed"

    expected = {"Helpdesk": "ticket", "Project": "project"}.get(row["work_context"])
    unattributed = expected is not None and not row[expected]
    states = set()
    row["project_name"] = None
    for field, doctype in _REFERENCES.items():
        if not row[field]:
            continue
        name = str(row[field])
        document, readable, state = load(doctype, name)
        if field == "task" and readable and (not row["project"] or document.get("project") != row["project"]):
            readable, state = False, "Restricted reference"
        row[field] = name if readable else None
        if field == "project" and readable:
            row["project_name"] = document.get("project_name")
        states.add(state)

    blocked = states & {"Restricted reference", "Missing historical reference"}
    if row["work_origin"] != "Snapfix" or blocked or unattributed:
        row["snapfix_reference"] = None
    if blocked or unattributed:
        row["description"] = None
    if "Restricted reference" in states:
        row["reference_state"] = "Restricted reference"
    elif "Missing historical reference" in states:
        row["reference_state"] = "Missing historical reference"
    elif states or row["snapfix_reference"]:
        row["reference_state"] = "Available"
    elif row["work_context"] in ("Helpdesk", "Project") or row["work_origin"] == "Snapfix":
        row["reference_state"] = "Unattributed"
    else:
        row["reference_state"] = "Not applicable"
    row["reference_kind"] = next(
        (kind for kind, field in _REFERENCE_KINDS.items() if row[field]), "No visible reference",
    )
    if not row["service_area"]:
        row["service_area"] = "Not applicable" if row["work_context"] == "Internal" else "Unattributed"
    return row


def _matches(row, criteria):
    for field, value in criteria.items():
        actual = row[field]
        if field == "emergency":
            actual = "yes" if actual else "no"
        elif field == "customer":
            actual = actual or row["unlisted_customer"]
        if str(actual or "").casefold() != value:
            return False
    return True


def _format_row(row, fields):
    result = {}
    for field in fields:
        value = row[field]
        if field == "emergency":
            value = _("Yes") if value else _("No")
        elif field in ("from_time", "to_time", "recorded_start", "recorded_end"):
            value = value.isoformat(sep=" ")
        if isinstance(value, str):
            value = _spreadsheet_text(value)
        result[field] = value
    return result


def _columns(view):
    day = ("day", "Date", "Date", 120)
    technician = ("technician", "Technician", "Data", 165)
    roster = (technician, ("company", "Company", "Data", 160))
    hours = (
        ("booked_hours", "Booked Hours", "Float", 125),
        ("draft_hours", "Draft Hours", "Float", 120),
        ("submitted_hours", "Submitted Hours", "Float", 135),
        ("emergency_hours", "Emergency Hours", "Float", 145),
    )
    extra = (
        ("customer_type", "Customer Attribution", "Data", 145),
        ("reference_state", "Reference Status", "Data", 175),
    )
    if view == "Daily Summary":
        columns = (day, *roster, *hours)
    elif view == "Booking Detail":
        columns = (
            day, *roster, *hours, *_DETAIL_COLUMNS, *extra,
            ("recorded_start", "Recorded Start (Site Time)", "Data", 185),
            ("recorded_end", "Recorded End (Site Time)", "Data", 185),
            ("description", "Booking Description", "Data", 330),
        )
    else:
        dimensions = {column[0]: column for column in (*roster, *_DETAIL_COLUMNS, *extra)}
        dimensions["employee"] = technician
        group = _BREAKDOWNS[view]
        leading = 3 if view in ("Technician Breakdown", "Customer Breakdown") else 1
        columns = (
            *(dimensions[field] for field in group[:leading]),
            *hours,
            *(dimensions[field] for field in group[leading:]),
        )
    return [
        dict(fieldname=name, label=_(label), fieldtype=kind, width=width)
        for name, label, kind, width in (*columns, ("employee", "Employee ID", "Data", 145))
    ]
