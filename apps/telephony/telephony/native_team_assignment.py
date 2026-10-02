import frappe


def _clean(value) -> str:
    return str(value or "").strip()


def native_team_assignment_state(group: str) -> dict:
    """
    Return the enabled native HD Team Assignment Rule state.

    The Assignment Rule user order is preserved exactly because that order
    defines the native round-robin population.

    This helper is read-only.
    """
    empty = {
        "rule": "",
        "users": [],
        "last_user": "",
    }

    group = _clean(group)
    if not group:
        return empty

    rule = _clean(
        frappe.db.get_value(
            "HD Team",
            group,
            "assignment_rule",
        )
    )
    if not rule:
        return empty

    rule_state = frappe.db.get_value(
        "Assignment Rule",
        rule,
        [
            "disabled",
            "last_user",
        ],
        as_dict=True,
    )

    if not rule_state:
        return empty

    if rule_state.get("disabled"):
        return empty

    users = frappe.get_all(
        "Assignment Rule User",
        filters={
            "parent": rule,
            "parenttype": "Assignment Rule",
            "parentfield": "users",
        },
        pluck="user",
        order_by="idx asc",
    )

    return {
        "rule": rule,
        "users": [
            _clean(user)
            for user in users or []
            if _clean(user)
        ],
        "last_user": _clean(rule_state.get("last_user")),
    }

def advance_native_team_cursor(rule: str, user: str) -> None:
    """
    Advance the existing native Assignment Rule round-robin cursor.

    Contextual assignment uses the same cursor as native team assignment
    rather than maintaining a separate Customer/Campus-specific cursor.
    """
    rule = _clean(rule)
    user = _clean(user)

    if not rule or not user:
        return

    if not frappe.db.exists("Assignment Rule", rule):
        return

    frappe.db.set_value(
        "Assignment Rule",
        rule,
        "last_user",
        user,
        update_modified=False,
    )
