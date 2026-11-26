"""Read-only DEV export entry point for the existing Supervisor reporting scope."""

from datetime import timedelta

import frappe
from frappe import _

from telephony.customer_labour_workbook import make_workbook
from telephony.ftelephony.page.technician_work_overview.technician_work_overview import (
    _authorized_scope,
    _employee_labels,
    _period,
)
from telephony.ftelephony.report.supervisor_booked_hours.supervisor_booked_hours import authorized_bookings

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _selection(preset, from_date, to_date):
    roster = _authorized_scope()
    if not isinstance(preset, str) or set(frappe.form_dict or {}) - {"cmd", "preset", "from_date", "to_date"}:
        frappe.throw(_("Select a valid reporting period."))
    return roster, _period(preset, from_date, to_date)


@frappe.whitelist(methods=["GET"])
def get_period(preset="this_month", from_date=None, to_date=None):
    _, (start, end, _) = _selection(preset, from_date, to_date)
    return {"from_date": start.date().isoformat(), "to_date": (end.date() - timedelta(days=1)).isoformat()}


@frappe.whitelist(methods=["GET"])
def download_workbook(preset="this_month", from_date=None, to_date=None):
    roster, (start, end, _) = _selection(preset, from_date, to_date)
    bookings = authorized_bookings(roster, start, end)
    last = (end.date() - timedelta(days=1)).isoformat()
    frappe.local.response.update(
        type="download",
        content_type=XLSX,
        filecontent=make_workbook(bookings, start, end, _employee_labels(bookings),
                                  {identity.company for identity in roster}),
        filename=f"Customer Labour Cost Analysis {start.date().isoformat()} to {last}.xlsx",
    )
