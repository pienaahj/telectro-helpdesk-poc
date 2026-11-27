"""Suggestions from the same authorized projections as the booked-hours reports."""

import frappe
from frappe import _
from frappe.desk.query_report import get_report_doc

from telephony.api.time_booking import _allowed_service_areas
from telephony.booked_hours import date_window
from telephony.ftelephony.report.supervisor_booked_hours import supervisor_booked_hours
from telephony.ftelephony.report.technician_own_booked_hours import technician_own_booked_hours
from telephony.supervisor_reporting_grant import resolve_supervisor_reporting_scope
from telephony.time_booking_activity_types import BOOKING_ACTIVITY_TYPES
from telephony.time_booking_metadata_policy import BookingMetadataValidationError

TECHNICIAN_REPORT = "Technician Own Booked Hours"
SUPERVISOR_REPORT = "Supervisor Booked Hours"
_REFERENCE_LABELS = {
    "project": ("Project", "project_name"),
    "task": ("Task", "subject"),
    "ticket": ("HD Ticket", "subject"),
}


def _sort(values):
    return sorted(values, key=lambda value: (value.casefold(), value))


def _named_choices(doctype, field, values, fallback=None):
    if not values:
        return []
    # Only look up labels for the exact IDs already authorized by the report or roster.
    names = {
        str(row.name): row.get(field)
        for row in frappe.get_all(doctype, filters={"name": ("in", sorted(values))},
                                  fields=["name", field])
    }
    choices = []
    for value in values:
        label = (names.get(value) or fallback or value).strip() or fallback or value
        choices.append({"value": value, "label": f"{label} ({value})" if label != value else label})
    return sorted(choices, key=lambda choice: (choice["label"].casefold(), choice["value"]))


@frappe.whitelist(methods=["GET"])
def get_options(report_name, from_date, to_date, company=None, employee=None, project=None):
    if report_name not in (TECHNICIAN_REPORT, SUPERVISOR_REPORT):
        raise frappe.PermissionError(_("Booked-hours report is unavailable."))
    get_report_doc(report_name)
    try:
        start, end = date_window(from_date, to_date)
    except (OverflowError, ValueError):
        raise frappe.ValidationError(_("Enter a valid From Date and To Date in chronological order.")) from None

    if project is not None and not isinstance(project, str):
        raise frappe.ValidationError(_("Select a valid report filter."))
    result = {}
    if report_name == TECHNICIAN_REPORT:
        rows = technician_own_booked_hours.authorized_bookings(
            technician_own_booked_hours.report_identity(), start, end,
        )
    else:
        roster = resolve_supervisor_reporting_scope()
        criteria = supervisor_booked_hours._report_filters({
            "from_date": from_date, "to_date": to_date, "company": company, "employee": employee,
        })[-1]
        companies = {identity.company for identity in roster}
        employees = {
            identity.employee for identity in roster
            if "company" not in criteria or identity.company.casefold() == criteria["company"]
        }
        result.update(company=_sort(companies),
                      employee=_named_choices("Employee", "employee_name", employees, _("Technician")))
        rows = supervisor_booked_hours.authorized_bookings(roster, start, end, criteria)

    try:
        areas = set(_allowed_service_areas())
    except BookingMetadataValidationError:
        # Missing booking configuration should not disable historical reporting.
        areas = set()
    recorded = {field: set() for field in (*_REFERENCE_LABELS, "snapfix_reference")}
    customers = set()
    activities = set(BOOKING_ACTIVITY_TYPES)
    project_key = (project or "").strip().casefold()
    for row in rows:
        customer = row["customer"] or row["unlisted_customer"]
        if customer:
            customers.add(customer)
        if row["service_area"]:
            areas.add(row["service_area"])
        if row["activity_type"]:
            activities.add(row["activity_type"])
        for field, values in recorded.items():
            value = row[field]
            if value and (field != "task" or not project_key or (row["project"] or "").casefold() == project_key):
                values.add(value)

    result.update(customer=_sort(customers), service_area=_sort(areas),
                  snapfix_reference=_sort(recorded["snapfix_reference"]))
    result.update({
        field: _named_choices(doctype, label, recorded[field])
        for field, (doctype, label) in _REFERENCE_LABELS.items()
    })
    if report_name == SUPERVISOR_REPORT:
        result["activity_type"] = _sort(activities)
    return result
