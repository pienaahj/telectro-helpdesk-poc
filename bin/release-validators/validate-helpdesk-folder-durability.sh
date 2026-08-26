#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import ast
import inspect
from pathlib import Path

from helpdesk.setup.file import (
    create_helpdesk_folder as upstream_create_helpdesk_folder,
)
from telephony.setup import helpdesk_folder


TELEPHONY_ROOT = Path("apps/telephony/telephony")
HOOKS_PATH = TELEPHONY_ROOT / "hooks.py"
TEST_PATH = (
    TELEPHONY_ROOT
    / "tests/test_helpdesk_folder.py"
)

HOOK_PATH = (
    "telephony.setup.helpdesk_folder.after_migrate"
)


def require(condition, message):
    if not condition:
        raise SystemExit(
            f"HELPDESK_FOLDER_RELEASE_VALIDATION_ERROR: {message}"
        )


print("=== Helpdesk folder constant contract ===")

expected_constants = {
    "HELPDESK_FOLDER": "Home/Helpdesk",
    "HELPDESK_FOLDER_NAME": "Helpdesk",
    "HELPDESK_PARENT_FOLDER": "Home",
}

observed_constants = {
    name: getattr(helpdesk_folder, name, None)
    for name in expected_constants
}

print(
    "HELPDESK_FOLDER_CONSTANTS=",
    observed_constants,
)

require(
    observed_constants == expected_constants,
    "Helpdesk folder constants changed",
)

print("HELPDESK_FOLDER_CONSTANT_CONTRACT=PASS")


print()
print("=== Helpdesk upstream helper contract ===")

require(
    helpdesk_folder.create_helpdesk_folder
    is upstream_create_helpdesk_folder,
    (
        "Telephony must reuse "
        "helpdesk.setup.file.create_helpdesk_folder"
    ),
)

print(
    "HELPDESK_FOLDER_HELPER=",
    (
        "helpdesk.setup.file."
        "create_helpdesk_folder"
    ),
)

print("HELPDESK_FOLDER_HELPER_CONTRACT=PASS")


print()
print("=== Helpdesk lifecycle entry-point contract ===")

expected_entry_points = [
    "verify_helpdesk_folder",
    "ensure_helpdesk_folder",
    "apply_helpdesk_folder",
    "after_migrate",
]

for name in expected_entry_points:
    function = getattr(
        helpdesk_folder,
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
    "HELPDESK_FOLDER_ENTRY_POINTS=",
    expected_entry_points,
)

print("HELPDESK_FOLDER_ENTRY_POINT_CONTRACT=PASS")


print()
print("=== Helpdesk reconciliation helper-use contract ===")

ensure_source = inspect.getsource(
    helpdesk_folder.ensure_helpdesk_folder
)

ensure_tree = ast.parse(ensure_source)

helper_calls = [
    node
    for node in ast.walk(ensure_tree)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "create_helpdesk_folder"
    )
]

verify_calls = [
    node
    for node in ast.walk(ensure_tree)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "verify_helpdesk_folder"
    )
]

require(
    len(helper_calls) == 1,
    (
        "ensure_helpdesk_folder must call the "
        "upstream Helpdesk folder helper exactly once"
    ),
)

require(
    len(verify_calls) == 2,
    (
        "ensure_helpdesk_folder must verify state "
        "before and after reconciliation"
    ),
)

print(
    "HELPDESK_FOLDER_HELPER_CALL_COUNT=",
    len(helper_calls),
)

print(
    "HELPDESK_FOLDER_VERIFY_CALL_COUNT=",
    len(verify_calls),
)

print("HELPDESK_FOLDER_RECONCILIATION_CONTRACT=PASS")


print()
print("=== Helpdesk after_migrate hook contract ===")

require(
    HOOKS_PATH.is_file(),
    f"missing hooks.py: {HOOKS_PATH}",
)

hooks_source = HOOKS_PATH.read_text()
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
        "Helpdesk folder after_migrate hook must "
        "appear exactly once"
    ),
)

require(
    (
        "if helpdesk_folder_after_migrate "
        "not in after_migrate:"
    )
    in hooks_source,
    "Helpdesk folder hook dedupe guard is missing",
)

require(
    (
        "after_migrate.append("
        "helpdesk_folder_after_migrate)"
    )
    in hooks_source,
    "Helpdesk folder hook append is missing",
)

print(
    "HELPDESK_FOLDER_AFTER_MIGRATE_HOOK=",
    HOOK_PATH,
)

print(
    "HELPDESK_FOLDER_AFTER_MIGRATE_HOOK_COUNT=",
    len(hook_literals),
)

print("HELPDESK_FOLDER_HOOK_CONTRACT=PASS")


print()
print("=== Helpdesk regression-test contract ===")

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
    "test_correct_helpdesk_folder_is_valid",
    "test_missing_helpdesk_folder_is_reported",
    "test_existing_correct_folder_is_noop",
    "test_missing_folder_is_recreated_with_helpdesk_helper",
    "test_unexpected_state_is_not_silently_repaired",
    "test_after_migrate_uses_idempotent_ensure",
    "test_apply_commits_successful_repair",
    "test_apply_rolls_back_failed_repair",
}

print(
    "HELPDESK_FOLDER_REGRESSION_TESTS=",
    sorted(observed_tests),
)

require(
    observed_tests == expected_tests,
    "Helpdesk folder regression-test contract changed",
)

print(
    "HELPDESK_FOLDER_REGRESSION_TEST_COUNT=",
    len(observed_tests),
)

print("HELPDESK_FOLDER_TEST_CONTRACT=PASS")


print()
print("HELPDESK_FOLDER_DURABILITY=PASS")
PY
