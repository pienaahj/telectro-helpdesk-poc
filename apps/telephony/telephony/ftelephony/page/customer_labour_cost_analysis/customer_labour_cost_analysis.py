"""Confidential export using the shared Supervisor reporting projection."""

from datetime import timedelta

import frappe
from frappe import _

from telephony.commercial_reporting import DEV_FIRST_DATE, DEV_LAST_DATE, require_cost_scope
from telephony.customer_labour_workbook import make_workbook
from telephony.ftelephony.page.technician_work_overview.technician_work_overview import (
    _employee_labels,
    _period,
)
from telephony.ftelephony.report.supervisor_booked_hours.supervisor_booked_hours import authorized_bookings

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _selection(preset, from_date, to_date):
    frappe.flags.cost_private_response = True
    roster = require_cost_scope()
    if not isinstance(preset, str) or set(frappe.form_dict or {}) - {"cmd", "preset", "from_date", "to_date"}:
        frappe.throw(_("Select a valid reporting period."))
    admin_test = frappe.session.user == "Administrator"
    if admin_test and (preset, from_date, to_date) == ("this_month", None, None):
        preset, from_date, to_date = "custom", DEV_FIRST_DATE.isoformat(), DEV_LAST_DATE.isoformat()
    start, end, _today = _period(preset, from_date, to_date)
    if admin_test and not DEV_FIRST_DATE <= start.date() < end.date() <= DEV_LAST_DATE + timedelta(days=1):
        frappe.throw(_("Choose dates within the controlled DEV test period."))
    return roster, start, end, admin_test


@frappe.whitelist(methods=["GET"])
def get_period(preset="this_month", from_date=None, to_date=None):
    _, start, end, admin_test = _selection(preset, from_date, to_date)
    return {
        "from_date": start.date().isoformat(),
        "to_date": (end.date() - timedelta(days=1)).isoformat(),
        "dev_test": admin_test,
    }


@frappe.whitelist(methods=["GET"])
def download_workbook(preset="this_month", from_date=None, to_date=None):
    roster, start, end, admin_test = _selection(preset, from_date, to_date)
    bookings = authorized_bookings(roster, start, end)
    last = (end.date() - timedelta(days=1)).isoformat()
    frappe.local.response.update(
        type="download",
        content_type=XLSX,
        filecontent=make_workbook(bookings, start, end, _employee_labels(bookings),
                                  {identity.company for identity in roster}, dev_test=admin_test),
        filename=f"Customer Labour Cost Analysis {start.date().isoformat()} to {last}.xlsx",
    )
