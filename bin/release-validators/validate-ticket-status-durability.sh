#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import ast
import inspect
from pathlib import Path

from telephony.setup import ticket_status_durability


TELEPHONY_ROOT = Path("apps/telephony/telephony")
HOOKS_PATH = TELEPHONY_ROOT / "hooks.py"
TEST_PATH = (
    TELEPHONY_ROOT
    / "tests/test_ticket_status_durability.py"
)

HOOK_PATH = (
    "telephony.setup.ticket_status_durability.after_migrate"
)


def require(condition, message):
    if not condition:
        raise SystemExit(
            f"TICKET_STATUS_RELEASE_VALIDATION_ERROR: {message}"
        )


print("=== Archived status canonical contract ===")

expected_name = "Archived"

expected_spec = {
    "label_agent": "Archived",
    "enabled": 1,
    "category": "Resolved",
    "order": 5,
    "color": "Gray",
    "different_view": 0,
    "label_customer": "",
}

print(
    "ARCHIVED_STATUS_NAME=",
    ticket_status_durability.ARCHIVED_STATUS_NAME,
)

print(
    "ARCHIVED_STATUS_SPEC=",
    ticket_status_durability.ARCHIVED_STATUS_SPEC,
)

require(
    ticket_status_durability.ARCHIVED_STATUS_NAME
    == expected_name,
    "Archived status name changed",
)

require(
    ticket_status_durability.ARCHIVED_STATUS_SPEC
    == expected_spec,
    "Archived status canonical field contract changed",
)

print("ARCHIVED_STATUS_CANONICAL_CONTRACT=PASS")


print()
print("=== Archived status lifecycle entry-point contract ===")

expected_entry_points = [
    "verify_archived_status",
    "ensure_archived_status",
    "apply_archived_status",
    "after_migrate",
]

for name in expected_entry_points:
    function = getattr(
        ticket_status_durability,
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
    "ARCHIVED_STATUS_ENTRY_POINTS=",
    expected_entry_points,
)

print("ARCHIVED_STATUS_ENTRY_POINT_CONTRACT=PASS")


print()
print("=== Archived status ownership contract ===")

require(
    HOOKS_PATH.is_file(),
    f"missing hooks.py: {HOOKS_PATH}",
)

hooks_source = HOOKS_PATH.read_text()

require(
    '"dt": "HD Ticket Status"' not in hooks_source,
    (
        "HD Ticket Status must not become fixture-owned "
        "while durability owns Archived"
    ),
)

print("ARCHIVED_STATUS_FIXTURE_OWNERSHIP=NO")
print("ARCHIVED_STATUS_OWNERSHIP_CONTRACT=PASS")


print()
print("=== Archived status after_migrate hook contract ===")

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
        "Archived status durability after_migrate hook "
        "must appear exactly once"
    ),
)

require(
    (
        "if ticket_status_durability_after_migrate "
        "not in after_migrate:"
    )
    in hooks_source,
    "Archived status hook dedupe guard is missing",
)

require(
    (
        "after_migrate.append("
        "ticket_status_durability_after_migrate)"
    )
    in hooks_source,
    "Archived status hook append is missing",
)

print(
    "ARCHIVED_STATUS_AFTER_MIGRATE_HOOK=",
    HOOK_PATH,
)

print(
    "ARCHIVED_STATUS_AFTER_MIGRATE_HOOK_COUNT=",
    len(hook_literals),
)

print("ARCHIVED_STATUS_HOOK_CONTRACT=PASS")


print()
print("=== Archived status conflict-safety contract ===")

verify_source = inspect.getsource(
    ticket_status_durability.verify_archived_status
)

ensure_source = inspect.getsource(
    ticket_status_durability.ensure_archived_status
)

require(
    "missing_archived_status"
    in verify_source,
    "missing Archived status detection is absent",
)

require(
    "archived_status_name_conflict"
    in verify_source,
    "Archived label/name conflict detection is absent",
)

require(
    "archived_status_field_mismatch"
    in verify_source,
    "Archived field mismatch detection is absent",
)

require(
    '"missing_archived_status"'
    in ensure_source,
    "missing Archived status must remain reconcilable",
)

require(
    "Archived Status Conflict"
    in ensure_source,
    "unexpected Archived state must stop reconciliation",
)

print("ARCHIVED_STATUS_CONFLICT_DETECTION=PASS")


print()
print("=== Archived status creation-only reconciliation contract ===")

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
    (
        "ensure_archived_status must create missing state "
        "through one new_doc path"
    ),
)

require(
    'frappe.new_doc("HD Ticket Status")'
    in ensure_source,
    "Archived creation must use HD Ticket Status new_doc",
)

require(
    "status.insert()"
    in ensure_source,
    "new Archived status must be inserted explicitly",
)

require(
    "status.save("
    not in ensure_source,
    "existing Archived status must not be rewritten",
)

require(
    "frappe.db.set_value"
    not in ensure_source,
    "existing Archived status must not be rewritten through db.set_value",
)

require(
    "frappe.delete_doc"
    not in ensure_source,
    "Archived reconciliation must not delete statuses",
)

print("ARCHIVED_STATUS_CREATE_IF_MISSING=PASS")
print("ARCHIVED_STATUS_EXISTING_STATE_REWRITE=NO")
print("ARCHIVED_STATUS_DELETE=NO")


print()
print("=== Archived status regression-test contract ===")

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
    "test_valid_archived_status_is_accepted",
    "test_missing_archived_status_is_reported",
    "test_archived_status_name_conflict_is_reported",
    "test_archived_status_field_mismatch_is_reported",
    "test_existing_valid_status_is_not_rewritten",
    "test_missing_status_is_created_with_canonical_values",
    "test_conflicting_existing_status_is_not_rewritten",
    "test_after_migrate_uses_idempotent_ensure",
    "test_apply_commits_successful_reconciliation",
    "test_apply_rolls_back_failed_reconciliation",
}

print(
    "ARCHIVED_STATUS_REGRESSION_TESTS=",
    sorted(observed_tests),
)

require(
    observed_tests == expected_tests,
    "Archived status regression-test contract changed",
)

print(
    "ARCHIVED_STATUS_REGRESSION_TEST_COUNT=",
    len(observed_tests),
)

print("ARCHIVED_STATUS_TEST_CONTRACT=PASS")


print()
print("TICKET_STATUS_DURABILITY=PASS")
PY
