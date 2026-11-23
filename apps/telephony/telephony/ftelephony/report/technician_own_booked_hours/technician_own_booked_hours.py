"""Own booked hours from managed Timesheet rows."""

from collections.abc import Mapping
from functools import lru_cache
import unicodedata

import frappe
from frappe import _

from telephony.booked_hours import date_window, hours_rows
from telephony.time_booking_identity import (
    TechnicianIdentityError,
    resolve_current_technician_identity,
)

_REPORT_ROWS = """
    SELECT parent.name AS booking, parent.docstatus,
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
       AND parent.user = %(user)s AND parent.employee = %(employee)s
       AND parent.company = %(company)s AND parent.docstatus IN (0, 1)
       AND detail.from_time < %(end)s AND detail.to_time > %(start)s
       AND detail.to_time > detail.from_time
     ORDER BY detail.from_time, detail.name
"""

_REFERENCES = {
    "customer": "HD Customer",
    "project": "Project",
    "task": "Task",
    "ticket": "HD Ticket",
}

_FILTER_FIELDS = (
    "work_context", "service_area", "work_origin", "emergency",
    "customer", "project", "task", "ticket", "snapfix_reference",
)

_DETAIL_COLUMNS = (
    ("booking", "Booking", "Data", 145),
    ("from_time", "Start (Site Time)", "Data", 165),
    ("to_time", "End (Site Time)", "Data", 165),
    ("status", "Status", "Data", 100),
    ("activity_type", "Activity Type", "Data", 145),
    ("work_context", "Work Context", "Data", 140),
    ("service_area", "Service Area", "Data", 130),
    ("work_origin", "Work Origin", "Data", 125),
    ("emergency", "Emergency / Unplanned", "Data", 145),
    ("customer", "HD Customer", "Data", 160),
    ("unlisted_customer", "Unlisted Customer", "Data", 160),
    ("project", "Project", "Data", 140),
    ("task", "Task", "Data", 140),
    ("ticket", "Helpdesk Ticket", "Data", 135),
    ("snapfix_reference", "Snapfix Reference", "Data", 165),
)


def execute(filters=None):
    try:
        identity = resolve_current_technician_identity()
    except TechnicianIdentityError:
        frappe.throw(_("You do not have access to Technician Own Booked Hours."), frappe.PermissionError)

    filters = filters or {}
    try:
        if not isinstance(filters, Mapping):
            raise ValueError
        start, end = date_window(filters.get("from_date"), filters.get("to_date"))
    except (OverflowError, ValueError):
        frappe.throw(_("Enter a valid From Date and To Date in chronological order."), frappe.ValidationError)

    detail = filters.get("view") == "Booking Detail"
    if filters.get("view") not in (None, "", "Daily Summary", "Booking Detail"):
        frappe.throw(_("Select a valid report view."), frappe.ValidationError)
    criteria = {}
    for field in _FILTER_FIELDS:
        value = filters.get(field)
        if value in (None, ""):
            continue
        if not isinstance(value, str) or (field == "emergency" and value not in ("Yes", "No")):
            frappe.throw(_("Select a valid report filter."), frappe.ValidationError)
        criteria[field] = value.strip().casefold()

    bookings = frappe.db.sql(
        _REPORT_ROWS,
        dict(user=identity.user, employee=identity.employee, company=identity.company, start=start, end=end),
        as_dict=True,
    )
    can_read = lru_cache(maxsize=512)(_can_read_reference)
    rows = (_report_booking(booking, can_read) for booking in bookings)
    rows = (row for row in rows if _matches(row, criteria))
    result = hours_rows(rows, start, end, detail=detail)
    for row in result:
        if detail:
            row.pop("docstatus")
            row["emergency"] = _("Yes") if row["emergency"] else _("No")
            for field in ("from_time", "to_time"):
                row[field] = row[field].isoformat(sep=" ", timespec="seconds")
            for field, value in row.items():
                if isinstance(value, str):
                    row[field] = _spreadsheet_text(value)
    return _columns(detail), result


def _can_read_reference(doctype, name):
    try:
        doc = frappe.get_doc(doctype, name)
        return str(doc.name) == name and bool(doc.has_permission("read"))
    except (frappe.DoesNotExistError, frappe.PermissionError):
        return False


def _report_booking(booking, can_read):
    row = dict(booking)
    row["status"] = _("Draft") if row["docstatus"] == 0 else _("Submitted")
    for field in _REFERENCES:
        row[field] = str(row[field]) if row[field] else None
    if any(row[field] and not can_read(doctype, row[field]) for field, doctype in _REFERENCES.items()):
        # Suppress the associated reference metadata together to avoid disclosing relationships.
        for field in (*_REFERENCES, "unlisted_customer", "snapfix_reference"):
            row[field] = None
    if row["work_origin"] != "Snapfix":
        row["snapfix_reference"] = None
    row["emergency"] = int(row["emergency"] == 1)
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


def _spreadsheet_text(value):
    # Native CSV and XLSX export render cells as spreadsheet values.
    significant = next(
        (char for char in value if not char.isspace() and unicodedata.category(char) not in ("Cc", "Cf")),
        "",
    )
    if significant in ("=", "+", "-", "@") or ("<" in value and ">" in value):
        return "'" + value
    return value


def _columns(detail):
    columns = [
        ("day", "Date", "Date", 120),
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
