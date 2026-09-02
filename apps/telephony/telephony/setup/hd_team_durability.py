from __future__ import annotations

from typing import Any

import frappe


REQUIRED_HD_TEAMS = (
    "PABX",
    "Routing",
    "SIM",
    "CCTV",
    "Internet Connection",
    "Helpdesk Team",
)


def _get_team_state(team_name: str) -> dict[str, Any] | None:
    return frappe.db.get_value(
        "HD Team",
        team_name,
        [
            "name",
            "team_name",
            "assignment_rule",
        ],
        as_dict=True,
    )


def _expected_assignment_condition(team_name: str) -> str:
    return (
        "status == 'Open' and "
        f"agent_group == '{team_name}'"
    )


def _get_enabled_orphan_assignment_rules() -> list[dict[str, str]]:
    """
    Return enabled HD Ticket Assignment Rules that represent one of the
    required HD Teams but are not linked from any current HD Team.

    Rule names are deliberately ignored. Ownership is determined from:
    - document_type
    - exact native HD Team assignment condition
    - absence of any HD Team.assignment_rule link
    """
    linked_rules = {
        row.get("assignment_rule")
        for row in frappe.get_all(
            "HD Team",
            fields=["assignment_rule"],
            limit_page_length=500,
        )
        if row.get("assignment_rule")
    }

    orphan_rules: list[dict[str, str]] = []

    for team_name in REQUIRED_HD_TEAMS:
        rules = frappe.get_all(
            "Assignment Rule",
            filters={
                "document_type": "HD Ticket",
                "assign_condition": (
                    _expected_assignment_condition(
                        team_name
                    )
                ),
                "disabled": 0,
            },
            fields=["name"],
            order_by="creation asc",
            limit_page_length=500,
        )

        for row in rules:
            rule_name = row.get("name")

            if not rule_name:
                continue

            if rule_name in linked_rules:
                continue

            orphan_rules.append(
                {
                    "team": team_name,
                    "assignment_rule": rule_name,
                }
            )

    return orphan_rules

def verify_hd_teams() -> dict[str, Any]:
    """Return a read-only verification of required Telectro HD Teams."""

    teams: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    for team_name in REQUIRED_HD_TEAMS:
        row = _get_team_state(team_name)

        if row is None:
            teams.append(
                {
                    "name": team_name,
                    "exists": False,
                    "assignment_rule": None,
                }
            )
            issues.append(
                {
                    "type": "missing_hd_team",
                    "team": team_name,
                }
            )
            continue

        assignment_rule = row.get("assignment_rule")

        teams.append(
            {
                "name": team_name,
                "exists": True,
                "assignment_rule": assignment_rule,
            }
        )

        if row.get("name") != team_name:
            issues.append(
                {
                    "type": "hd_team_name_mismatch",
                    "team": team_name,
                    "actual": row.get("name"),
                }
            )

        if row.get("team_name") != team_name:
            issues.append(
                {
                    "type": "hd_team_team_name_mismatch",
                    "team": team_name,
                    "actual": row.get("team_name"),
                }
            )

        if not assignment_rule:
            issues.append(
                {
                    "type": "missing_hd_team_assignment_rule",
                    "team": team_name,
                }
            )
        elif not frappe.db.exists(
            "Assignment Rule",
            assignment_rule,
        ):
            issues.append(
                {
                    "type": "missing_assignment_rule",
                    "team": team_name,
                    "assignment_rule": assignment_rule,
                }
            )

    orphan_rules = (
        _get_enabled_orphan_assignment_rules()
    )

    for team_name in REQUIRED_HD_TEAMS:
        team_orphans = [
            orphan["assignment_rule"]
            for orphan in orphan_rules
            if orphan["team"] == team_name
        ]

        if team_orphans:
            issues.append(
                {
                    "type": (
                        "enabled_orphan_assignment_rules"
                    ),
                    "team": team_name,
                    "assignment_rules": team_orphans,
                }
            )

    return {
        "ok": not issues,
        "site": frappe.local.site,
        "required_teams": list(REQUIRED_HD_TEAMS),
        "teams": teams,
        "issue_count": len(issues),
        "issues": issues,
    }


def ensure_hd_teams() -> dict[str, Any]:
    """
    Ensure required Telectro HD Teams exist.

    Existing teams are deliberately left untouched. Their users and linked
    Assignment Rules are operational runtime state and are not reconciled
    from repository data.
    """

    before = verify_hd_teams()

    reconcilable_issue_types = {
        "missing_hd_team",
        "enabled_orphan_assignment_rules",
    }

    unexpected_issues = [
        issue
        for issue in before["issues"]
        if issue["type"]
        not in reconcilable_issue_types
    ]

    if unexpected_issues:
        frappe.throw(
            "HD Team reconciliation stopped because unexpected state "
            "was found:\n"
            + frappe.as_json(unexpected_issues, indent=2),
            title="HD Team Conflict",
        )

    changed: list[dict[str, Any]] = []

    for team_name in REQUIRED_HD_TEAMS:
        if frappe.db.exists("HD Team", team_name):
            continue

        team = frappe.new_doc("HD Team")
        team.team_name = team_name
        team.insert()

        changed.append(
            {
                "action": "create",
                "team": team_name,
            }
        )

    orphan_rules = (
        _get_enabled_orphan_assignment_rules()
    )

    for orphan in orphan_rules:
        team_name = orphan["team"]
        rule_name = orphan["assignment_rule"]

        rule = frappe.get_doc(
            "Assignment Rule",
            rule_name,
        )

        if rule.disabled:
            continue

        rule.disabled = True
        rule.save(ignore_permissions=True)

        changed.append(
            {
                "action": (
                    "disable_orphan_assignment_rule"
                ),
                "team": team_name,
                "assignment_rule": rule_name,
            }
        )

    after = verify_hd_teams()

    if not after["ok"]:
        frappe.throw(
            "HD Team reconciliation did not reach the expected state:\n"
            + frappe.as_json(after["issues"], indent=2),
            title="HD Team Verification Failed",
        )

    return {
        "ok": True,
        "site": after["site"],
        "changed_count": len(changed),
        "changed": changed,
        "verification": after,
    }


def apply_hd_teams() -> dict[str, Any]:
    """Explicit transactional entry point for deliberate operator use."""

    try:
        result = ensure_hd_teams()
        frappe.db.commit()
        return result
    except Exception:
        frappe.db.rollback()
        raise


def after_migrate() -> dict[str, Any]:
    """Ensure required Telectro HD Teams exist after each migration."""

    result = ensure_hd_teams()

    frappe.logger("telephony").info(
        "Required HD Teams verified: %s, %s changed",
        len(REQUIRED_HD_TEAMS),
        result["changed_count"],
    )

    return result
