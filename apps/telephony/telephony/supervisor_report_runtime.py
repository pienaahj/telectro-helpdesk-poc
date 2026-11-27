"""Keep the grant-scoped report on Frappe's live Script Report path."""

import frappe
from frappe import _
from frappe.core.doctype.report.report import Report
from frappe.desk.query_report import get_reference_report

REPORT_NAME = "Supervisor Booked Hours"


class TelectroReport(Report):
    def is_permitted(self):
        if self.name == REPORT_NAME:
            # Frappe also copies the prepared flag from saved report variants.
            self.prepared_report = 0
        return super().is_permitted()

    def execute_script_report(self, filters):
        if self.name != REPORT_NAME:
            return super().execute_script_report(filters)
        # The native method only starts its auto-prepare timer when this flag is false.
        prepared_report = self.prepared_report
        self.prepared_report = 1
        try:
            return super().execute_script_report(filters)
        finally:
            self.prepared_report = prepared_report


def prevent_supervisor_prepared_report(doc, method=None):
    report = get_reference_report(frappe.get_doc("Report", doc.report_name))
    if report.name == REPORT_NAME:
        raise frappe.PermissionError(_("Supervisor Booked Hours must run live."))
