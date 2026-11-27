"""Private durable co-option foundation; issuer/revoker policy belongs to callers.

No DocShare, Comment, or assignment is evidence of a co-option grant.
"""

from hashlib import sha256

from telephony.time_booking_identity import TechnicianBookingIdentity


DOCTYPE = "TELECTRO Ticket Worker Grant"


class BookingCooptionError(PermissionError):
    def __init__(self):
        super().__init__("Ticket worker grant is unavailable.")


def _identifier(value):
    return type(value) is str and bool(value.strip())


def _active_key(ticket, user):
    if not _identifier(ticket) or not _identifier(user):
        raise BookingCooptionError()
    return sha256(f"{len(ticket)}:{ticket}{len(user)}:{user}".encode()).hexdigest()


def _require_recipient_identity(user):
    """Resolve an internal Technician and one active Employee without HR read rights."""
    import frappe
    from telephony.customer_communication_privacy import classify_actor_roles

    if not _identifier(user) or user in ("Guest", "Administrator"):
        raise BookingCooptionError()
    account = frappe.db.get_value("User", user, ["name", "enabled", "user_type"], as_dict=True)
    roles = set(frappe.get_all("Has Role", filters={
        "parent": user, "parenttype": "User", "parentfield": "roles",
    }, pluck="role", limit_page_length=0))
    if (not account or account.get("name") != user or account.get("enabled") != 1
            or account.get("user_type") != "System User"
            or "TELECTRO-POC Role - Tech" not in roles
            or classify_actor_roles(roles) != "internal"):
        raise BookingCooptionError()
    employees = frappe.get_all("Employee", filters={
        "user_id": user, "status": "Active", "docstatus": ["<", 2],
    }, fields=["name", "user_id", "status", "docstatus", "company"],
        order_by="name asc", limit_page_length=2)
    if len(employees) != 1:
        raise BookingCooptionError()
    employee = employees[0]
    company = employee.get("company")
    if (employee.get("user_id") != user or employee.get("status") != "Active"
            or employee.get("docstatus") not in (0, 1)
            or not _identifier(employee.get("name")) or not _identifier(company)
            or frappe.db.get_value("Company", company, "name") != company):
        raise BookingCooptionError()
    return TechnicianBookingIdentity(user, employee["name"], company)


def _lock_ticket(ticket):
    """Serialize ticket grant mutations before any authorization-dependent reads."""
    import frappe

    if not _identifier(ticket):
        raise BookingCooptionError()
    rows = frappe.db.sql("SELECT name FROM `tabHD Ticket` WHERE name = %s FOR UPDATE",
                         ticket, as_dict=True)
    if len(rows) != 1 or rows[0].get("name") != ticket:
        raise BookingCooptionError()


def _active_row(ticket, user):
    """Use a current locking read, never a transaction snapshot query."""
    import frappe

    key = _active_key(ticket, user)
    rows = frappe.db.sql(
        "SELECT name, ticket, technician_user, employee, company, state, active_key, "
        "revoked_at FROM `tabTELECTRO Ticket Worker Grant` WHERE active_key = %s FOR UPDATE",
        key, as_dict=True,
    )
    if len(rows) > 1:
        raise BookingCooptionError()
    if not rows:
        return None
    row = rows[0]
    if (row.get("ticket") != ticket or row.get("technician_user") != user
            or row.get("state") != "Active" or row.get("active_key") != key
            or row.get("revoked_at") or not _identifier(row.get("name"))):
        raise BookingCooptionError()
    return row


def _active_grant(ticket, identity):
    """Return one current authoritative episode or None; reject inconsistent state."""
    if not isinstance(identity, TechnicianBookingIdentity):
        raise BookingCooptionError()
    row = _active_row(ticket, identity.user)
    if row is None:
        return None
    if row.get("employee") != identity.employee or row.get("company") != identity.company:
        raise BookingCooptionError()
    return row["name"]


def _grant_after_authorization(*, ticket, user, issuer, reason):
    """Persist after a future caller has enforced issuer and ticket policy.

    The ticket row lock serializes repeat requests; unique active_key is the
    database backstop. No commit is issued here.
    """
    import frappe
    from frappe.utils import now_datetime

    if not all(_identifier(v) for v in (ticket, issuer, reason)):
        raise BookingCooptionError()
    _lock_ticket(ticket)
    identity = _require_recipient_identity(user)
    existing = _active_grant(ticket, identity)
    if existing:
        return existing
    grant = frappe.get_doc({
        "doctype": DOCTYPE, "ticket": ticket, "technician_user": user,
        "employee": identity.employee, "company": identity.company,
        "granted_by": issuer, "reason": reason, "granted_at": now_datetime(),
        "state": "Active", "active_key": _active_key(ticket, user),
    })
    try:
        grant.insert(ignore_permissions=True)
    except frappe.UniqueValidationError as exc:
        # A writer bypassed the ticket lock. The caller must roll back the unit;
        # recovering inside this transaction could retain insertion side effects.
        raise BookingCooptionError() from exc
    return grant.name


def _revoke_after_authorization(*, ticket, user, revoker, reason):
    """Retain the episode; future callers must authorize the revoker."""
    import frappe
    from frappe.utils import now_datetime

    if not all(_identifier(v) for v in (ticket, user, revoker, reason)):
        raise BookingCooptionError()
    _lock_ticket(ticket)
    row = _active_row(ticket, user)
    if row is None:
        return None
    grant = frappe.get_doc(DOCTYPE, row["name"])
    grant.state = "Revoked"
    grant.active_key = None
    grant.revoked_by = revoker
    grant.revoked_at = now_datetime()
    grant.revocation_reason = reason
    grant.save(ignore_permissions=True)
    return grant.name
