"""Live Supervisor reporting over the authorized Phase 2 ledger."""

from collections import defaultdict
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
           detail.from_time, detail.to_time, detail.activity_type,
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

_FILTER_FIELDS = ("company", "employee", "customer", "work_context", "service_area", "work_origin", "emergency")
_REFERENCES = {"project": "Project", "task": "Task", "ticket": "HD Ticket"}
_CUSTOMER_TYPES = ("HD Customer", "Customer")
_CUSTOMER_CONTEXTS = (*_CUSTOMER_TYPES, "Timesheet", "Timesheet Detail")


def execute(filters=None):
    roster = resolve_supervisor_reporting_scope()
    start, end, detail, criteria = _report_filters(filters)
    scope = {
        (identity.user, identity.employee, identity.company)
        for identity in roster
        if all(
            field not in criteria or getattr(identity, field).casefold() == criteria[field]
            for field in ("employee", "company")
        )
    }
    columns = _columns(detail)
    if not scope:
        return columns, []

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
        row = _project_booking(row, load, detail=detail)
        if _matches(row, criteria):
            bookings.append(row)

    if detail:
        result = hours_rows(bookings, start, end, detail=True)
    else:
        by_employee = defaultdict(list)
        for row in bookings:
            by_employee[row["company"], row["employee"]].append(row)
        result = [
            dict(row, company=company, employee=employee)
            for (company, employee), group in sorted(by_employee.items())
            for row in hours_rows(group, start, end)
        ]
    return columns, [_format_row(row, detail) for row in result]


def _report_filters(filters):
    filters = filters or {}
    try:
        if not isinstance(filters, Mapping):
            raise ValueError
        start, end = date_window(filters.get("from_date"), filters.get("to_date"))
    except (OverflowError, ValueError):
        raise frappe.ValidationError(_("Enter a valid From Date and To Date in chronological order.")) from None
    view = filters.get("view")
    if view not in (None, "", "Daily Summary", "Booking Detail"):
        raise frappe.ValidationError(_("Select a valid report view."))
    criteria = {}
    for field in _FILTER_FIELDS:
        value = filters.get(field)
        if value in (None, ""):
            continue
        if not isinstance(value, str) or (field == "emergency" and value not in ("Yes", "No")):
            raise frappe.ValidationError(_("Select a valid report filter."))
        criteria[field] = value.strip().casefold()
    return start, end, view == "Booking Detail", criteria


def _load_reference(doctype, name):
    try:
        doc = frappe.get_doc(doctype, name)
        if str(doc.name) == name:
            return doc, bool(doc.has_permission("read"))
    except (frappe.DoesNotExistError, frappe.PermissionError):
        pass
    return None, False


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

    hd_customer, erp_customer = saved_customer, None
    for field, doctype in (("ticket", "HD Ticket"), ("project", "Project")):
        if not row[field]:
            continue
        document, _ = load(doctype, str(row[field]))
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
        hd_doc, can_read = load("HD Customer", hd_customer)
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


def _project_booking(row, load, *, detail):
    row = dict(row)
    row["emergency"] = int(row["emergency"] == 1)
    if not detail:
        return row
    row["status"] = _("Draft") if row["docstatus"] == 0 else _("Submitted")
    references = {}
    for field, doctype in _REFERENCES.items():
        name = str(row[field]) if row[field] else None
        references[field] = load(doctype, name) if name else (None, True)

    task_doc, task_read = references["task"]
    if task_doc and (task_doc.get("project") != row["project"] or not references["project"][1]):
        task_read = False
    references["task"] = task_doc, task_read
    for field, (_document, readable) in references.items():
        row[field] = str(row[field]) if row[field] and readable else None
    if row["work_origin"] != "Snapfix" or not all(readable for _, readable in references.values()):
        row["snapfix_reference"] = None
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


def _format_row(row, detail):
    if detail:
        row.pop("user")
        row.pop("docstatus")
        row["emergency"] = _("Yes") if row["emergency"] else _("No")
        for field in ("from_time", "to_time"):
            row[field] = row[field].isoformat(sep=" ", timespec="seconds")
    return {field: _spreadsheet_text(value) if isinstance(value, str) else value for field, value in row.items()}


def _columns(detail):
    columns = [
        ("day", "Date", "Date", 120),
        ("employee", "Technician (Employee)", "Data", 165),
        ("company", "Company", "Data", 160),
        ("booked_hours", "Booked Hours", "Float", 125),
        ("draft_hours", "Draft Hours", "Float", 120),
        ("submitted_hours", "Submitted Hours", "Float", 135),
        ("emergency_hours", "Emergency Hours", "Float", 145),
    ]
    if detail:
        columns.extend(_DETAIL_COLUMNS)
    return [
        dict(fieldname=name, label=_(label), fieldtype=kind, width=width)
        for name, label, kind, width in columns
    ]
