import frappe
from frappe import _

def _is_pilot_tech():
    user = frappe.session.user
    if user in ("Administrator",) or user == "Guest":
        return False

    roles = frappe.get_roles(user) or []
    if "System Manager" in roles:
        return False

    # Keep this narrowly scoped: only block the pilot tech role
    return "TELECTRO-POC Tech" in roles


def _deny():
    frappe.throw(
        _("Pilot: direct Assign/Unassign is disabled. Use Claim / Handoff."),
        frappe.PermissionError,
    )


@frappe.whitelist()
def add(args=None, *, ignore_permissions=False):
    if _is_pilot_tech():
        _deny()
    from frappe.desk.form import assign_to
    return assign_to.add(args=args, ignore_permissions=ignore_permissions)


@frappe.whitelist()
def add_multiple(args=None):
    if _is_pilot_tech():
        _deny()
    from frappe.desk.form import assign_to
    return assign_to.add_multiple(args=args)


@frappe.whitelist()
def remove(doctype, name, assign_to, ignore_permissions=False):
    if _is_pilot_tech():
        _deny()
    from frappe.desk.form import assign_to as a
    return a.remove(doctype, name, assign_to, ignore_permissions=ignore_permissions)


@frappe.whitelist()
def remove_multiple(doctype, names, ignore_permissions=False):
    if _is_pilot_tech():
        _deny()
    from frappe.desk.form import assign_to as a
    return a.remove_multiple(doctype, names, ignore_permissions=ignore_permissions)


@frappe.whitelist()
def close(doctype: str, name: str, assign_to: str, ignore_permissions=False):
    if _is_pilot_tech():
        _deny()
    from frappe.desk.form import assign_to as a
    return a.close(doctype, name, assign_to, ignore_permissions=ignore_permissions)
