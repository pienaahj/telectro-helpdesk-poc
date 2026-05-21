import frappe
from frappe.model.document import Document


class TELECTROServiceCoverage(Document):
    def validate(self):
        self._set_defaults()
        self._validate_scope_requirements()

    def _set_defaults(self):
        if self.enabled is None:
            self.enabled = 1

        if not self.coverage_role:
            self.coverage_role = "Eligible"

        if self.priority in (None, ""):
            self.priority = 100

    def _validate_scope_requirements(self):
        scope = (self.coverage_scope or "").strip()

        if scope == "Customer/Campus":
            if not self.customer:
                frappe.throw("Customer is required when Coverage Scope is Customer/Campus.")
            if not self.campus:
                frappe.throw("Campus is required when Coverage Scope is Customer/Campus.")

        elif scope == "Customer":
            if not self.customer:
                frappe.throw("Customer is required when Coverage Scope is Customer.")

        elif scope == "Campus":
            if not self.campus:
                frappe.throw("Campus is required when Coverage Scope is Campus.")

        elif scope == "Default":
            # Default rows intentionally do not require Customer or Campus.
            return

        else:
            frappe.throw("Coverage Scope must be Customer/Campus, Customer, Campus, or Default.")
