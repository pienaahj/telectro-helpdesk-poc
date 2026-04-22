import frappe

PARTNER_ROLES = {
    "TELECTRO-POC Role - Partner",
    "TELECTRO-POC Role - Partner Creator",
}

def _is_partner_user(user: str) -> bool:
    return bool(PARTNER_ROLES.intersection(set(frappe.get_roles(user))))

def hd_ticket_query_conditions(user: str | None = None) -> str:
    user = user or frappe.session.user

    if not _is_partner_user(user):
        return ""

    # First safe test: partner only sees tickets they own.
    return f"`tabHD Ticket`.`owner` = {frappe.db.escape(user)}"

import frappe

def hd_ticket_query_conditions(user=None):
    user = user or frappe.session.user
    frappe.logger().info(f"[partner-perms] hd_ticket_query_conditions called for {user}")
    ...