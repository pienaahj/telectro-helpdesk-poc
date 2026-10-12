import frappe
from frappe.model.document import Document
from frappe.utils import cint


VALID_SCOPES = {
    "Customer/Campus",
    "Customer",
    "Campus",
    "Default",
}

VALID_ASSIGNMENT_MODES = {
    "Round Robin",
    "True Pool",
}


def _clean(value) -> str:
    return str(value or "").strip()


class TELECTROAssignmentPolicy(Document):
    def validate(self):
        self._normalize_fields()
        self._validate_scope_requirements()
        self._validate_assignment_mode()
        self._validate_enabled_uniqueness()

    def _normalize_fields(self):
        self.coverage_scope = _clean(self.coverage_scope)
        self.customer = _clean(self.customer) or None
        self.campus = _clean(self.campus) or None
        self.service_area = _clean(self.service_area)
        self.assignment_mode = _clean(self.assignment_mode)

        if self.enabled is None:
            self.enabled = 1

    def _validate_scope_requirements(self):
        scope = self.coverage_scope

        if scope not in VALID_SCOPES:
            frappe.throw(
                "Coverage Scope must be Customer/Campus, "
                "Customer, Campus, or Default."
            )

        if not self.service_area:
            frappe.throw("Service Area is required.")

        if scope == "Customer/Campus":
            if not self.customer or not self.campus:
                frappe.throw(
                    "Customer and Campus are both required "
                    "for Customer/Campus scope."
                )

        elif scope == "Customer":
            if not self.customer:
                frappe.throw(
                    "Customer is required for Customer scope."
                )

            if self.campus:
                frappe.throw(
                    "Campus must be empty for Customer scope."
                )

        elif scope == "Campus":
            if not self.campus:
                frappe.throw(
                    "Campus is required for Campus scope."
                )

            if self.customer:
                frappe.throw(
                    "Customer must be empty for Campus scope."
                )

        elif scope == "Default":
            if self.customer or self.campus:
                frappe.throw(
                    "Customer and Campus must be empty "
                    "for Default scope."
                )

    def _validate_assignment_mode(self):
        if self.assignment_mode not in VALID_ASSIGNMENT_MODES:
            frappe.throw(
                "Assignment Mode must be "
                "Round Robin or True Pool."
            )

    def _validate_enabled_uniqueness(self):
        if not cint(self.enabled):
            return

        existing = frappe.get_all(
            "TELECTRO Assignment Policy",
            filters={
                "enabled": 1,
                "coverage_scope": self.coverage_scope,
                "service_area": self.service_area,
            },
            fields=[
                "name",
                "customer",
                "campus",
            ],
        )

        for row in existing:
            if row["name"] == self.name:
                continue

            if (
                _clean(row.get("customer")) == _clean(self.customer)
                and _clean(row.get("campus")) == _clean(self.campus)
            ):
                frappe.throw(
                    "An enabled Assignment Policy already exists "
                    "for this exact Scope, Customer, Campus, "
                    "and Service Area: {0}".format(
                        frappe.bold(row["name"])
                    )
                )
