"""Private immutable correction audit document."""

from frappe.model.document import Document
from telephony.time_booking_correction_audit import (
    ACTIONS, BookingCorrectionAuditError, _snapshot, _text,
)


class TELECTROBookingCorrectionAudit(Document):
    def validate(self):
        # Reject edits before inspecting supplied fields; an existing audit
        # record cannot be rewritten even with malformed replacement data.
        if self.get_doc_before_save():
            raise BookingCorrectionAuditError()
        if (not _text(self.event_id) or self.action not in ACTIONS
                or not _text(self.actor) or not self.recorded_at
                or not _text(self.reason)
                or not _text(self.original_timesheet)
                or not _text(self.original_time_log)):
            raise BookingCorrectionAuditError()
        frozen = _snapshot(__import__("json").loads(self.before_snapshot))
        original = __import__("json").loads(frozen)
        if (self.before_snapshot != frozen
                or original["name"] != self.original_timesheet
                or original["time_logs"][0]["name"] != self.original_time_log):
            raise BookingCorrectionAuditError()
        if self.after_snapshot:
            after = _snapshot(__import__("json").loads(self.after_snapshot))
            if after != self.after_snapshot:
                raise BookingCorrectionAuditError()

    def on_trash(self):
        raise BookingCorrectionAuditError()
