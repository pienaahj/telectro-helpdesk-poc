"""Private grant episode; no user-facing DocType permissions."""

import frappe
from frappe.model.document import Document

from telephony.time_booking_cooption import BookingCooptionError, _active_key


class TELECTROTicketWorkerGrant(Document):
    def validate(self):
        if self.state == "Active":
            if (self.active_key != _active_key(self.ticket, self.technician_user)
                    or self.revoked_at or self.revoked_by or self.revocation_reason):
                raise BookingCooptionError()
        elif self.state == "Revoked":
            if self.active_key or not self.revoked_at or not self.revoked_by or not self.revocation_reason:
                raise BookingCooptionError()
        else:
            raise BookingCooptionError()
        previous = self.get_doc_before_save()
        if previous:
            for field in ("ticket", "technician_user", "employee", "company",
                          "granted_by", "granted_at", "reason"):
                if self.get(field) != previous.get(field):
                    raise BookingCooptionError()
            if previous.state == "Revoked":
                raise BookingCooptionError()
