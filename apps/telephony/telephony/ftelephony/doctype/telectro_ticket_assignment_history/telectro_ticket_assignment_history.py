"""Private assignment episode; no user-facing DocType permissions."""

from frappe.model.document import Document
from telephony.time_booking_assignment_history import AssignmentHistoryError, _active_key, _time


class TELECTROTicketAssignmentHistory(Document):
    def validate(self):
        if self.state == "Active":
            if (self.active_key != _active_key(self.ticket, self.technician_user)
                    or any(self.get(field) for field in (
                        "effective_end", "recorded_end", "ended_by", "end_source",
                        "end_reason", "end_event_id"))):
                raise AssignmentHistoryError()
        elif self.state == "Closed":
            if self.active_key or not all(self.get(field) for field in (
                    "effective_end", "recorded_end", "ended_by", "end_source",
                    "end_reason", "end_event_id")):
                raise AssignmentHistoryError()
            if (_time(self.effective_end) < _time(self.effective_start)
                    or _time(self.recorded_end) < _time(self.recorded_start)
                    or _time(self.effective_end) > _time(self.recorded_end)):
                raise AssignmentHistoryError()
        else:
            raise AssignmentHistoryError()
        if not all(self.get(field) for field in (
                "ticket", "technician_user", "employee", "company", "effective_start",
                "recorded_start", "started_by", "start_source", "start_reason",
                "start_event_id")) or _time(self.effective_start) > _time(self.recorded_start):
            raise AssignmentHistoryError()
        previous = self.get_doc_before_save()
        if previous:
            for field in ("ticket", "technician_user", "employee", "company",
                          "effective_start", "recorded_start", "started_by",
                          "start_source", "start_reason", "start_event_id"):
                if self.get(field) != previous.get(field):
                    raise AssignmentHistoryError()
            if previous.state != "Active" or self.state != "Closed":
                raise AssignmentHistoryError()
