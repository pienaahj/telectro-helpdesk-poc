"""Resolve technician booking identity; this grants no Timesheet access."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicianBookingIdentity:
    user: str
    employee: str
    company: str


class TechnicianIdentityError(PermissionError):
    """Expected eligibility failure without disclosing identity details."""

    def __init__(self):
        super().__init__("Technician booking identity is unavailable.")


def resolve_current_technician_identity() -> TechnicianBookingIdentity:
    """Read current eligibility without writes, impersonation or caching.

    Employee reads intentionally bypass HR read permissions, using only the
    session principal and fixed projections. Results never expose HR documents.
    This does not authorize bookings, references or management access.
    """
    import frappe
    from telephony.customer_communication_privacy import classify_actor_roles

    user = getattr(frappe.session, "user", None)
    if (
        not isinstance(user, str)
        or not user.strip()
        or user in ("Guest", "Administrator")
    ):
        raise TechnicianIdentityError()

    account = frappe.db.get_value(
        "User", user, ["name", "enabled", "user_type"], as_dict=True
    )
    if (
        not account
        or account.get("name") != user
        or account.get("enabled") != 1
        or account.get("user_type") != "System User"
    ):
        raise TechnicianIdentityError()

    roles = set(frappe.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User", "parentfield": "roles"},
        pluck="role",
        limit_page_length=0,
    ))
    if (
        "TELECTRO-POC Role - Tech" not in roles
        or classify_actor_roles(roles) != "internal"
    ):
        raise TechnicianIdentityError()

    employees = frappe.get_all(
        "Employee",
        filters={"user_id": user, "status": "Active", "docstatus": ["<", 2]},
        fields=["name", "user_id", "status", "docstatus", "company"],
        order_by="name asc",
        limit_page_length=2,
    )
    if len(employees) != 1:
        raise TechnicianIdentityError()

    employee = employees[0]
    employee_name = employee.get("name")
    company = employee.get("company")
    if (
        employee.get("user_id") != user
        or employee.get("status") != "Active"
        or employee.get("docstatus") not in (0, 1)
        or not isinstance(employee_name, str)
        or not employee_name.strip()
        or not isinstance(company, str)
        or not company.strip()
    ):
        raise TechnicianIdentityError()
    if frappe.db.get_value("Company", company, "name") != company:
        raise TechnicianIdentityError()

    return TechnicianBookingIdentity(user=user, employee=employee_name, company=company)
