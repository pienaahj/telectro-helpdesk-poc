from __future__ import annotations

from typing import Any

import frappe

from telephony.setup.hd_team_durability import REQUIRED_HD_TEAMS


def _clean(value) -> str:
    return str(value or "").strip()


def expected_assignment_condition(team_name: str) -> str:
    """
    Return the canonical native Assignment Rule condition for a Telectro team.

    Native assignment remains responsible for ordinary pool routing, but must
    not override an explicit contextual-assignment hold.
    """
    team_name = _clean(team_name)

    return (
        "status == 'Open' and "
        f"agent_group == '{team_name}' and "
        "not custom_contextual_assignment_hold"
    )


def _linked_team_rules() -> list[dict[str, str]]:
    """
    Return the Assignment Rules currently linked from required HD Teams.

    Rule names are operational runtime state and are deliberately not inferred
    from naming conventions.
    """
    rows: list[dict[str, str]] = []

    for team_name in REQUIRED_HD_TEAMS:
        rule_name = _clean(
            frappe.db.get_value(
                "HD Team",
                team_name,
                "assignment_rule",
            )
        )

        if not rule_name:
            continue

        rows.append(
            {
                "team": team_name,
                "assignment_rule": rule_name,
            }
        )

    return rows


def verify_contextual_assignment_rules() -> dict[str, Any]:
    """
    Verify that linked native HD Team Assignment Rules respect contextual hold.

    This function is read-only. Existing HD Team/link integrity remains owned
    by hd_team_durability.
    """
    issues: list[dict[str, str]] = []

    for row in _linked_team_rules():
        team_name = _clean(row.get("team"))
        rule_name = _clean(row.get("assignment_rule"))

        if not team_name or not rule_name:
            continue

        rule_state = frappe.db.get_value(
            "Assignment Rule",
            rule_name,
            [
                "name",
                "disabled",
                "assign_condition",
            ],
            as_dict=True,
        )

        # Missing linked-rule state is owned by hd_team_durability.
        if not rule_state:
            continue

        actual_condition = _clean(
            rule_state.get("assign_condition")
        )

        if actual_condition != expected_assignment_condition(team_name):
            issues.append(
                {
                    "type": "contextual_hold_condition_missing",
                    "team": team_name,
                    "assignment_rule": rule_name,
                }
            )

    return {
        "ok": not issues,
        "issues": issues,
    }

def ensure_contextual_assignment_rules() -> dict[str, Any]:
    """
    Ensure linked native HD Team Assignment Rules respect contextual hold.

    Only Assignment Rule.assign_condition is reconciled here.

    HD Team links, Assignment Rule users, rule names, enabled state, and
    round-robin cursor state remain operational runtime state and are not
    rewritten by this function.
    """
    changed: list[dict[str, str]] = []

    for row in _linked_team_rules():
        team_name = _clean(row.get("team"))
        rule_name = _clean(row.get("assignment_rule"))

        if not team_name or not rule_name:
            continue

        rule_state = frappe.db.get_value(
            "Assignment Rule",
            rule_name,
            [
                "name",
                "disabled",
                "assign_condition",
            ],
            as_dict=True,
        )

        # Missing linked-rule integrity remains owned by hd_team_durability.
        if not rule_state:
            continue

        expected_condition = expected_assignment_condition(
            team_name
        )

        actual_condition = _clean(
            rule_state.get("assign_condition")
        )

        if actual_condition == expected_condition:
            continue

        frappe.db.set_value(
            "Assignment Rule",
            rule_name,
            "assign_condition",
            expected_condition,
            update_modified=False,
        )

        changed.append(
            {
                "action": "update_assign_condition",
                "team": team_name,
                "assignment_rule": rule_name,
            }
        )

    verification = verify_contextual_assignment_rules()

    if not verification["ok"]:
        frappe.throw(
            "Contextual Assignment Rule reconciliation did not reach "
            "the expected state:\n"
            + frappe.as_json(
                verification["issues"],
                indent=2,
            ),
            title="Contextual Assignment Rule Verification Failed",
        )

    return {
        "ok": verification["ok"],
        "changed_count": len(changed),
        "changed": changed,
        "verification": verification,
    }
def apply_contextual_assignment_rules() -> dict[str, Any]:
    """
    Explicit transactional entry point for deliberate operator use.
    """
    try:
        result = ensure_contextual_assignment_rules()
        frappe.db.commit()
        return result
    except Exception:
        frappe.db.rollback()
        raise


def after_migrate() -> dict[str, Any]:
    """
    Ensure linked native HD Team Assignment Rules respect contextual hold
    after each migration.

    Transaction ownership remains with the migration lifecycle.
    """
    return ensure_contextual_assignment_rules()
