import frappe
from frappe.model.document import Document
from frappe.utils import cint


class TELECTROPartner(Document):
    def validate(self):
        self._set_defaults()
        self._validate_members()
        self._validate_default_dispatch_user()

    def _set_defaults(self):
        if self.enabled is None:
            self.enabled = 1

        for row in self.members or []:
            if row.enabled is None:
                row.enabled = 1

    def _validate_members(self):
        seen = set()

        for row in self.members or []:
            user = str(row.user or "").strip()
            row.user = user

            if not user:
                frappe.throw("User is required for every Partner Member row.")

            if user in seen:
                frappe.throw(
                    f"Partner member {frappe.bold(user)} is duplicated."
                )

            seen.add(user)

    def _validate_default_dispatch_user(self):
        dispatch_user = str(self.default_dispatch_user or "").strip()
        self.default_dispatch_user = dispatch_user or None

        if not dispatch_user:
            return

        enabled_members = {
            str(row.user or "").strip()
            for row in self.members or []
            if cint(row.enabled)
        }

        if dispatch_user not in enabled_members:
            frappe.throw(
                "Default Dispatch User must be an enabled member "
                "of this Partner organisation."
            )
