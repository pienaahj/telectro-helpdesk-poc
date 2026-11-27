"""A private, writer-controlled Supervisor reporting grant."""

from frappe.model.document import Document

from telephony.supervisor_reporting_grant import (
    SupervisorReportingGrantError,
    validate_supervisor_reporting_grant,
)


class TELECTROSupervisorReportingGrant(Document):
    def validate(self):
        validate_supervisor_reporting_grant(self, self.get_doc_before_save())

    def validate_share(self, share):
        raise SupervisorReportingGrantError()

    def before_rename(self, old, new, merge=False):
        raise SupervisorReportingGrantError()

    def on_trash(self):
        raise SupervisorReportingGrantError()
