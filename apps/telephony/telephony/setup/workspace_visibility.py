from __future__ import annotations

from collections import Counter
from typing import Any

import frappe


STANDARD_WORKSPACE_ROLES = (
    "System Manager",
    "Administrator",
)

STANDARD_WORKSPACES = (
    "Accounting",
    "Assets",
    "Build",
    "Buying",
    "CRM",
    "ERPNext Integrations",
    "ERPNext Settings",
    "Financial Reports",
    "Helpdesk",
    "Home",
    "Integrations",
    "Manufacturing",
    "Payables",
    "Projects",
    "Quality",
    "Receivables",
    "Selling",
    "Stock",
    "Support",
    "Tools",
    "Users",
    "Website",
    "Welcome Workspace",
)

TELECTRO_WORKSPACE_ROLES = {
    "TELECTRO-POC Tech": (
        "TELECTRO-POC Role - Tech Workspace",
    ),
    "TELECTRO-POC Coordinator": (
        "TELECTRO-POC Role - Coordinator Workspace",
    ),
    "TELECTRO-POC Ops": (
        "TELECTRO-POC Role - Ops Workspace",
    ),
    "TELECTRO-POC Partner": (
        "TELECTRO-POC Role - Partner",
        "TELECTRO-POC Role - Partner Creator",
    ),
}


def get_workspace_role_policy() -> dict[str, tuple[str, ...]]:
    """Return the complete Workspace visibility policy owned by Telephony."""

    policy = {
        workspace_name: STANDARD_WORKSPACE_ROLES
        for workspace_name in STANDARD_WORKSPACES
    }

    policy.update(TELECTRO_WORKSPACE_ROLES)

    return policy


def _get_workspace_roles(workspace) -> list[str]:
    roles: list[str] = []

    for row in workspace.roles:
        if row.role:
            roles.append(row.role)

    return roles


def _inspect_workspace(
    workspace_name: str,
    expected_roles: tuple[str, ...],
) -> dict[str, Any]:
    if not frappe.db.exists("Workspace", workspace_name):
        return {
            "workspace": workspace_name,
            "exists": False,
            "expected_roles": list(expected_roles),
            "actual_roles": [],
            "missing_roles": list(expected_roles),
            "unexpected_roles": [],
            "duplicate_roles": [],
            "ok": False,
        }

    workspace = frappe.get_doc("Workspace", workspace_name)
    actual_roles = _get_workspace_roles(workspace)

    actual_role_set = set(actual_roles)
    expected_role_set = set(expected_roles)

    role_counts = Counter(actual_roles)
    duplicate_roles = sorted(
        role
        for role, count in role_counts.items()
        if count > 1
    )

    missing_roles = [
        role
        for role in expected_roles
        if role not in actual_role_set
    ]

    unexpected_roles = sorted(
        actual_role_set - expected_role_set
    )

    return {
        "workspace": workspace_name,
        "exists": True,
        "expected_roles": list(expected_roles),
        "actual_roles": actual_roles,
        "missing_roles": missing_roles,
        "unexpected_roles": unexpected_roles,
        "duplicate_roles": duplicate_roles,
        "ok": not (
            missing_roles
            or unexpected_roles
            or duplicate_roles
        ),
    }


def verify_workspace_visibility() -> dict[str, Any]:
    """Return a read-only verification of the Workspace visibility policy."""

    workspaces: list[dict[str, Any]] = []

    for workspace_name, expected_roles in get_workspace_role_policy().items():
        workspaces.append(
            _inspect_workspace(
                workspace_name,
                expected_roles,
            )
        )

    issues = [
        row
        for row in workspaces
        if not row["ok"]
    ]

    return {
        "ok": not issues,
        "site": frappe.local.site,
        "workspace_count": len(workspaces),
        "issue_count": len(issues),
        "issues": issues,
        "workspaces": workspaces,
    }


def assert_workspace_visibility() -> dict[str, Any]:
    """
    Verify Workspace visibility and fail when drift is present.

    This is the operator-facing read-only entry point used by deployment
    verification scripts.
    """

    result = verify_workspace_visibility()

    if not result["ok"]:
        frappe.throw(
            "Workspace visibility verification failed:\n"
            + frappe.as_json(result["issues"], indent=2),
            title="Workspace Visibility Verification Failed",
        )

    return {
        "ok": True,
        "site": result["site"],
        "workspace_count": result["workspace_count"],
        "issue_count": result["issue_count"],
    }


def ensure_workspace_visibility() -> dict[str, Any]:
    """
    Reconcile missing Workspace role rows without silently deleting drift.

    Missing expected roles are added.

    Missing Workspaces, unexpected roles, or duplicate roles are treated as
    configuration conflicts and cause the operation to fail.
    """

    policy = get_workspace_role_policy()
    before = verify_workspace_visibility()

    conflicts: list[dict[str, Any]] = []

    for row in before["issues"]:
        if (
            not row["exists"]
            or row["unexpected_roles"]
            or row["duplicate_roles"]
        ):
            conflicts.append(row)

    if conflicts:
        frappe.throw(
            "Workspace visibility reconciliation stopped because "
            "configuration conflicts were found:\n"
            + frappe.as_json(conflicts, indent=2),
            title="Workspace Visibility Conflict",
        )

    changed: list[dict[str, Any]] = []

    for workspace_name, expected_roles in policy.items():
        workspace = frappe.get_doc("Workspace", workspace_name)
        actual_roles = _get_workspace_roles(workspace)

        added_roles: list[str] = []

        for role in expected_roles:
            if role in actual_roles:
                continue

            workspace.append(
                "roles",
                {
                    "role": role,
                },
            )
            added_roles.append(role)

        if not added_roles:
            continue

        workspace.save(ignore_permissions=True)

        changed.append(
            {
                "workspace": workspace_name,
                "added_roles": added_roles,
            }
        )

    if changed:
        frappe.clear_cache()

    after = verify_workspace_visibility()

    if not after["ok"]:
        frappe.throw(
            "Workspace visibility reconciliation did not reach the "
            "expected state:\n"
            + frappe.as_json(after["issues"], indent=2),
            title="Workspace Visibility Verification Failed",
        )

    return {
        "ok": True,
        "site": frappe.local.site,
        "changed_count": len(changed),
        "changed": changed,
        "verification": after,
    }


def apply_workspace_visibility() -> dict[str, Any]:
    """
    Explicit transactional entry point for bench execute.

    The after_migrate hook will call ensure_workspace_visibility() directly
    and use the migration transaction. This function is for deliberate
    operator-initiated repair.
    """

    try:
        result = ensure_workspace_visibility()
        frappe.db.commit()
        return result
    except Exception:
        frappe.db.rollback()
        raise


def repair_workspace_visibility() -> dict[str, Any]:
    """
    Apply the Workspace visibility policy and return an operator summary.

    The underlying apply function owns the transaction and rollback.
    """

    result = apply_workspace_visibility()
    verification = result["verification"]

    return {
        "ok": result["ok"],
        "site": result["site"],
        "changed_count": result["changed_count"],
        "changed": result["changed"],
        "workspace_count": verification["workspace_count"],
        "issue_count": verification["issue_count"],
    }


def after_migrate() -> dict[str, Any]:
    """Restore and verify Workspace visibility after each migration."""

    result = ensure_workspace_visibility()

    frappe.logger("telephony").info(
        "Workspace visibility verified: %s workspace(s), %s changed",
        result["verification"]["workspace_count"],
        result["changed_count"],
    )

    return result
