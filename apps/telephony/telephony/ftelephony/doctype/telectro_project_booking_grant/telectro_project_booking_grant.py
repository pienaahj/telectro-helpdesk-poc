"""Private, writer-controlled Project booking entitlement history."""

from frappe.model.document import Document

from telephony.time_booking_project_grant import (
    ProjectBookingGrantError,
    validate_project_booking_grant,
)


class TELECTROProjectBookingGrant(Document):
    def validate(self):
        validate_project_booking_grant(self, self.get_doc_before_save())

    def before_rename(self, old, new, merge=False):
        raise ProjectBookingGrantError()

    def on_trash(self):
        raise ProjectBookingGrantError()
