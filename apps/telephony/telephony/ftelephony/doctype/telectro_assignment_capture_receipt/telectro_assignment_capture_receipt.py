"""Private immutable receipt for completed assignment capture operations."""

from frappe.model.document import Document
from telephony.time_booking_assignment_capture import _validate_capture_receipt
from telephony.time_booking_assignment_history import AssignmentHistoryError


class TELECTROAssignmentCaptureReceipt(Document):
    def validate(self):
        if self.get_doc_before_save():
            raise AssignmentHistoryError()
        _validate_capture_receipt(self)

    def on_trash(self):
        raise AssignmentHistoryError()
