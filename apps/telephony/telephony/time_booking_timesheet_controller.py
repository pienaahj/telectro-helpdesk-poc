"""Unregistered native Timesheet insert wrapper; no lifecycle activation.

Trusted callers must supply creation intent and authenticated identity. This
does not prove final-name absence, transaction commit, update provenance or
authorization of references. Direct writes and native RPC containment remain
separate integration requirements.
"""

from erpnext.projects.doctype.timesheet.timesheet import Timesheet

from telephony.time_booking_provenance import BookingProvenanceError
from telephony.time_booking_provenance_adapter import (
    _complete_insertion,
    _insertion_attempt,
)


class TelectroBookingTimesheet(Timesheet):
    """Preserve native behavior while bounding one trusted insertion attempt."""

    def insert(
        self,
        ignore_permissions=None,
        ignore_links=None,
        ignore_if_duplicate=False,
        ignore_mandatory=None,
        set_name=None,
        set_child_names=True,
    ):
        with _insertion_attempt(self) as frame:
            managed = frame.identity is not None
            if managed:
                # Native Document.insert checks this Document-local flag first.
                # Print rendering sets doc.flags.in_print, not frappe.flags.
                if self.flags.in_print or ignore_if_duplicate is not False:
                    raise BookingProvenanceError()
            result = super().insert(
                ignore_permissions=ignore_permissions,
                ignore_links=ignore_links,
                ignore_if_duplicate=ignore_if_duplicate,
                ignore_mandatory=ignore_mandatory,
                set_name=set_name,
                set_child_names=set_child_names,
            )
            if managed:
                if result is not self:
                    raise BookingProvenanceError()
                _complete_insertion(frame, self, frame.identity)
            return result
