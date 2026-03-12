import json

import frappe
from frappe import _

TECH_ROLE = "TELECTRO-POC Tech"


def _parse_assign_users(assign_val) -> list[str]:
    if not assign_val:
        return []
    if isinstance(assign_val, list):
        return [str(x).strip() for x in assign_val if str(x).strip()]
    if not isinstance(assign_val, str):
        return []
    s = assign_val.strip()
    if not s:
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return []


def validate_ticket_edit_rights(doc, method=None):
    user = frappe.session.user

    if user == "Administrator":
        return

    roles = frappe.get_roles(user) or []
    if TECH_ROLE not in roles:
        return

    # Allow first save of a newly created ticket
    if doc.is_new():
        return

    # IMPORTANT: for existing tickets, use persisted assignment state,
    # not the incoming form payload (which may omit _assign)
    assign_val = frappe.db.get_value("HD Ticket", doc.name, "_assign") or ""
    assignees = _parse_assign_users(assign_val)

    # True pool: editable
    if not assignees:
        return

    # Assigned to me: editable
    if user in assignees:
        return

    frappe.throw(
        _("You may only edit tickets that are in the pool or assigned to you."),
        frappe.PermissionError,
    )