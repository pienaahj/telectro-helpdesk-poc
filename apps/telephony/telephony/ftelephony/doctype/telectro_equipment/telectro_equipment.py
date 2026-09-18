import frappe
from frappe.model.document import Document


class TELECTROEquipment(Document):
    def validate(self):
        self._validate_location()

    def _validate_location(self):
        if not self.location:
            return

        row = frappe.db.get_value(
            "Location",
            self.location,
            ["is_group"],
            as_dict=True,
        )

        if not row:
            frappe.throw(
                f"Equipment Location '{self.location}' does not exist."
            )

        if row.is_group:
            frappe.throw(
                "Equipment Location must be a leaf Location."
            )
