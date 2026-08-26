#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import ast
import inspect
from pathlib import Path

from telephony.setup import hd_team_durability


TELEPHONY_ROOT = Path("apps/telephony/telephony")
HOOKS_PATH = TELEPHONY_ROOT / "hooks.py"
FIXTURE_PATH = TELEPHONY_ROOT / "fixtures/hd_team.json"
TEST_PATH = TELEPHONY_ROOT / "tests/test_hd_team_durability.py"

HOOK_PATH = (
    "telephony.setup.hd_team_durability.after_migrate"
)


def require(condition, message):
    if not condition:
        raise SystemExit(
            f"HD_TEAM_RELEASE_VALIDATION_ERROR: {message}"
        )


print("=== Required HD Team contract ===")

expected_teams = (
    "PABX",
    "Routing",
    "SIM",
    "CCTV",
    "Internet Connection",
    "Helpdesk Team",
)

observed_teams = tuple(
    hd_team_durability.REQUIRED_HD_TEAMS
)

print(
    "REQUIRED_HD_TEAMS=",
    observed_teams,
)

require(
    observed_teams == expected_teams,
    "required HD Team set changed",
)

print("HD_TEAM_REQUIRED_SET_CONTRACT=PASS")


print()
print("=== HD Team lifecycle entry-point contract ===")

expected_entry_points = [
    "verify_hd_teams",
    "ensure_hd_teams",
    "apply_hd_teams",
    "after_migrate",
]

for name in expected_entry_points:
    function = getattr(
        hd_team_durability,
        name,
        None,
    )

    require(
        callable(function),
        f"missing callable entry point: {name}",
    )

    signature = inspect.signature(function)

    require(
        len(signature.parameters) == 0,
        f"{name} must remain a no-argument entry point",
    )

print(
    "HD_TEAM_ENTRY_POINTS=",
    expected_entry_points,
)

print("HD_TEAM_ENTRY_POINT_CONTRACT=PASS")


print()
print("=== HD Team fixture-ownership contract ===")

require(
    not FIXTURE_PATH.exists(),
    "hd_team.json must not exist as a runtime fixture",
)

require(
    HOOKS_PATH.is_file(),
    f"missing hooks.py: {HOOKS_PATH}",
)

hooks_source = HOOKS_PATH.read_text()

require(
    '"dt": "HD Team"' not in hooks_source,
    "HD Team fixture declaration must remain removed",
)

print("HD_TEAM_FIXTURE_REMOVED=YES")
print("HD_TEAM_FIXTURE_OWNERSHIP_CONTRACT=PASS")


print()
print("=== HD Team after_migrate hook contract ===")

hooks_tree = ast.parse(hooks_source)

hook_literals = [
    node.value
    for node in ast.walk(hooks_tree)
    if (
        isinstance(node, ast.Constant)
        and node.value == HOOK_PATH
    )
]

require(
    len(hook_literals) == 1,
    (
        "HD Team durability after_migrate hook must "
        "appear exactly once"
    ),
)

require(
    (
        "if hd_team_durability_after_migrate "
        "not in after_migrate:"
    )
    in hooks_source,
    "HD Team durability hook dedupe guard is missing",
)

require(
    (
        "after_migrate.append("
        "hd_team_durability_after_migrate)"
    )
    in hooks_source,
    "HD Team durability hook append is missing",
)

print(
    "HD_TEAM_AFTER_MIGRATE_HOOK=",
    HOOK_PATH,
)

print(
    "HD_TEAM_AFTER_MIGRATE_HOOK_COUNT=",
    len(hook_literals),
)

print("HD_TEAM_HOOK_CONTRACT=PASS")


print()
print("=== HD Team operational-state preservation contract ===")

ensure_source = inspect.getsource(
    hd_team_durability.ensure_hd_teams
)

ensure_tree = ast.parse(ensure_source)

new_doc_calls = [
    node
    for node in ast.walk(ensure_tree)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "new_doc"
    )
]

require(
    len(new_doc_calls) == 1,
    "ensure_hd_teams must create missing teams through one new_doc path",
)

for node in ast.walk(ensure_tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr in {
                    "users",
                    "assignment_rule",
                }
            ):
                raise SystemExit(
                    "HD_TEAM_RELEASE_VALIDATION_ERROR: "
                    "ensure_hd_teams must not assign operational "
                    f"state field: {target.attr}"
                )

print("HD_TEAM_OPERATIONAL_STATE_REWRITE=NO")
print("HD_TEAM_OPERATIONAL_STATE_CONTRACT=PASS")


print()
print("=== HD Team Assignment Rule integrity contract ===")

verify_source = inspect.getsource(
    hd_team_durability.verify_hd_teams
)

require(
    "missing_hd_team_assignment_rule"
    in verify_source,
    "blank HD Team assignment_rule detection is missing",
)

require(
    "missing_assignment_rule"
    in verify_source,
    "missing linked Assignment Rule detection is missing",
)

print("HD_TEAM_ASSIGNMENT_RULE_INTEGRITY_CONTRACT=PASS")


print()
print("=== HD Team regression-test contract ===")

require(
    TEST_PATH.is_file(),
    f"missing regression test file: {TEST_PATH}",
)

test_tree = ast.parse(
    TEST_PATH.read_text()
)

observed_tests = {
    node.name
    for node in ast.walk(test_tree)
    if (
        isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
    )
}

expected_tests = {
    "test_required_hd_teams_are_valid",
    "test_missing_hd_team_is_reported",
    "test_missing_assignment_rule_link_is_reported",
    "test_missing_linked_assignment_rule_is_reported",
    "test_existing_teams_are_not_rewritten",
    "test_missing_team_is_created_without_members",
    "test_unexpected_team_state_is_not_rewritten",
    "test_after_migrate_uses_idempotent_ensure",
    "test_apply_commits_successful_reconciliation",
    "test_apply_rolls_back_failed_reconciliation",
    "test_hd_team_fixture_ownership_is_removed",
}

print(
    "HD_TEAM_REGRESSION_TESTS=",
    sorted(observed_tests),
)

require(
    observed_tests == expected_tests,
    "HD Team regression-test contract changed",
)

print(
    "HD_TEAM_REGRESSION_TEST_COUNT=",
    len(observed_tests),
)

print("HD_TEAM_TEST_CONTRACT=PASS")


print()
print("HD_TEAM_DURABILITY=PASS")
PY
