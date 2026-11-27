"""Suggestions from the same authorized projections as the booked-hours reports."""

import frappe
from frappe import _
from frappe.desk.query_report import get_report_doc

from telephony.api.time_booking import _allowed_service_areas
from telephony.booked_hours import date_window
from telephony.ftelephony.report.supervisor_booked_hours import supervisor_booked_hours
from telephony.ftelephony.report.technician_own_booked_hours import technician_own_booked_hours
from telephony.supervisor_reporting_grant import resolve_supervisor_reporting_scope
from telephony.time_booking_metadata_policy import BookingMetadataValidationError

TECHNICIAN_REPORT = "Technician Own Booked Hours"
SUPERVISOR_REPORT = "Supervisor Booked Hours"


@frappe.whitelist(methods=["GET"])
def get_options(report_name, from_date, to_date, company=None, employee=None):
    if report_name not in (TECHNICIAN_REPORT, SUPERVISOR_REPORT):
        raise frappe.PermissionError(_("Booked-hours report is unavailable."))
    get_report_doc(report_name)
    try:
        start, end = date_window(from_date, to_date)
    except (OverflowError, ValueError):
        raise frappe.ValidationError(_("Enter a valid From Date and To Date in chronological order.")) from None

    if report_name == TECHNICIAN_REPORT:
        rows = technician_own_booked_hours.authorized_bookings(
            technician_own_booked_hours.report_identity(), start, end,
        )
    else:
        roster = resolve_supervisor_reporting_scope()
        _, _, _, criteria = supervisor_booked_hours._report_filters({
            "from_date": from_date, "to_date": to_date, "company": company, "employee": employee,
        })
        rows = supervisor_booked_hours.authorized_bookings(roster, start, end, criteria)

    try:
        areas = set(_allowed_service_areas())
    except BookingMetadataValidationError:
        # Missing booking configuration should not disable historical reporting.
        areas = set()
    customers = set()
    for row in rows:
        customer = row["customer"] or row["unlisted_customer"]
        if customer:
            customers.add(customer)
        if row["service_area"]:
            areas.add(row["service_area"])

    return {
        "customer": sorted(customers, key=lambda value: (value.casefold(), value)),
        "service_area": sorted(areas, key=lambda value: (value.casefold(), value)),
    }
