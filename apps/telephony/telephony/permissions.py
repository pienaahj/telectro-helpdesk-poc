import frappe

PARTNER_ROLES = {
    "TELECTRO-POC Role - Partner",
    "TELECTRO-POC Role - Partner Creator",
}

INTERNAL_BYPASS_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
}

def _get_roles(user: str) -> set[str]:
    if not user:
        return set()
    return set(frappe.get_roles(user))

def _is_internal_bypass_user(user: str) -> bool:
    if not user:
        return False
    if user == "Administrator":
        return True
    roles = _get_roles(user)
    return bool(roles & INTERNAL_BYPASS_ROLES)

def _is_partner_user(user: str) -> bool:
    if not user or user == "Guest":
        return False
    roles = _get_roles(user)
    return bool(roles & PARTNER_ROLES)

def hd_ticket_query_conditions(user: str | None = None) -> str:
    user = user or frappe.session.user

    if _is_internal_bypass_user(user):
        return ""

    if not _is_partner_user(user):
        return ""

    # Conservative v1 rule:
    # Partner users only see tickets they own through generic HD Ticket access.
    return f"`tabHD Ticket`.`owner` = {frappe.db.escape(user)}"