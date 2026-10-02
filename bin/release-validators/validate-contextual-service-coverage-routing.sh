#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import ast
import inspect
import json
import textwrap
from pathlib import Path

from telephony import native_team_assignment
from telephony import service_coverage
from telephony import telectro_reassign_on_update
from telephony import telectro_round_robin
from telephony.setup import contextual_assignment_durability


TELEPHONY_ROOT = Path("apps/telephony/telephony")

HOOKS_PATH = TELEPHONY_ROOT / "hooks.py"

CUSTOM_FIELD_FIXTURE_PATH = (
    TELEPHONY_ROOT
    / "fixtures/custom_field.json"
)

TEST_PATHS = {
    "contextual_assignment_durability": (
        TELEPHONY_ROOT
        / "tests/test_contextual_assignment_durability.py"
    ),
    "contextual_assignment_fixture": (
        TELEPHONY_ROOT
        / "tests/test_contextual_assignment_fixture.py"
    ),
    "service_coverage_assignment": (
        TELEPHONY_ROOT
        / "tests/test_service_coverage_assignment.py"
    ),
    "telectro_round_robin": (
        TELEPHONY_ROOT
        / "tests/test_telectro_round_robin.py"
    ),
    "telectro_reassign_on_update": (
        TELEPHONY_ROOT
        / "tests/test_telectro_reassign_on_update.py"
    ),
}

HD_TEAM_HOOK = (
    "telephony.setup.hd_team_durability.after_migrate"
)

CONTEXTUAL_HOOK = (
    "telephony.setup.contextual_assignment_durability.after_migrate"
)

TICKET_STATUS_HOOK = (
    "telephony.setup.ticket_status_durability.after_migrate"
)


def require(condition, message):
    if not condition:
        raise SystemExit(
            "CONTEXTUAL_ROUTING_RELEASE_VALIDATION_ERROR: "
            + message
        )


def source_tree(function):
    source = textwrap.dedent(
        inspect.getsource(function)
    )

    return source, ast.parse(source)


def function_calls(tree, function_name):
    return [
        node
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Call)
            and (
                (
                    isinstance(node.func, ast.Name)
                    and node.func.id == function_name
                )
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == function_name
                )
            )
        )
    ]


def literal_arg(call, index):
    if len(call.args) <= index:
        return None

    node = call.args[index]

    if isinstance(node, ast.Constant):
        return node.value

    return None


print(
    "=== Contextual assignment hold fixture contract ==="
)

require(
    CUSTOM_FIELD_FIXTURE_PATH.is_file(),
    (
        "missing Custom Field fixture: "
        f"{CUSTOM_FIELD_FIXTURE_PATH}"
    ),
)

fixture_rows = json.loads(
    CUSTOM_FIELD_FIXTURE_PATH.read_text()
)

hold_rows = [
    row
    for row in fixture_rows
    if (
        row.get("dt") == "HD Ticket"
        and row.get("fieldname")
        == "custom_contextual_assignment_hold"
    )
]

require(
    len(hold_rows) == 1,
    (
        "expected exactly one HD Ticket "
        "custom_contextual_assignment_hold fixture"
    ),
)

hold_row = hold_rows[0]

expected_hold_spec = {
    "name": (
        "HD Ticket-custom_contextual_assignment_hold"
    ),
    "dt": "HD Ticket",
    "fieldname": (
        "custom_contextual_assignment_hold"
    ),
    "label": "Contextual Assignment Hold",
    "fieldtype": "Check",
    "default": "0",
    "hidden": 1,
    "read_only": 1,
    "no_copy": 1,
    "insert_after": (
        "custom_take_ownership_on_create"
    ),
}

observed_hold_spec = {
    key: hold_row.get(key)
    for key in expected_hold_spec
}

print(
    "CONTEXTUAL_HOLD_FIXTURE_SPEC=",
    observed_hold_spec,
)

require(
    observed_hold_spec == expected_hold_spec,
    "contextual hold fixture contract changed",
)

require(
    HOOKS_PATH.is_file(),
    f"missing hooks.py: {HOOKS_PATH}",
)

hooks_source = HOOKS_PATH.read_text()

require(
    hooks_source.count(
        '"HD Ticket-custom_contextual_assignment_hold"'
    )
    == 1,
    (
        "contextual hold Custom Field must appear "
        "exactly once in the fixture whitelist"
    ),
)

print(
    "CONTEXTUAL_HOLD_FIXTURE_COUNT=",
    len(hold_rows),
)

print(
    "CONTEXTUAL_HOLD_FIXTURE_CONTRACT=PASS"
)


print()
print(
    "=== Contextual after_migrate ordering contract ==="
)

hooks_tree = ast.parse(hooks_source)

hook_lines = {}

for node in ast.walk(hooks_tree):
    if (
        isinstance(node, ast.Constant)
        and node.value
        in {
            HD_TEAM_HOOK,
            CONTEXTUAL_HOOK,
            TICKET_STATUS_HOOK,
        }
    ):
        hook_lines.setdefault(
            node.value,
            [],
        ).append(node.lineno)

for hook_path in (
    HD_TEAM_HOOK,
    CONTEXTUAL_HOOK,
    TICKET_STATUS_HOOK,
):
    require(
        len(hook_lines.get(hook_path, [])) == 1,
        (
            "after_migrate hook must appear exactly "
            f"once: {hook_path}"
        ),
    )

hd_team_line = hook_lines[HD_TEAM_HOOK][0]
contextual_line = hook_lines[CONTEXTUAL_HOOK][0]
ticket_status_line = hook_lines[TICKET_STATUS_HOOK][0]

require(
    hd_team_line
    < contextual_line
    < ticket_status_line,
    (
        "required durability order changed: "
        "hd_team -> contextual -> ticket_status"
    ),
)

require(
    (
        "if contextual_assignment_durability_after_migrate "
        "not in after_migrate:"
    )
    in hooks_source,
    "contextual after_migrate dedupe guard is missing",
)

require(
    (
        "after_migrate.append(\n"
        "        contextual_assignment_durability_after_migrate\n"
        "    )"
    )
    in hooks_source,
    "contextual after_migrate append is missing",
)

print(
    "CONTEXTUAL_AFTER_MIGRATE_ORDER=",
    [
        HD_TEAM_HOOK,
        CONTEXTUAL_HOOK,
        TICKET_STATUS_HOOK,
    ],
)

print(
    "CONTEXTUAL_AFTER_MIGRATE_ORDER_CONTRACT=PASS"
)


print()
print(
    "=== Contextual Assignment Rule durability contract ==="
)

expected_condition = (
    "status == 'Open' and "
    "agent_group == 'PABX' and "
    "not custom_contextual_assignment_hold"
)

observed_condition = (
    contextual_assignment_durability
    .expected_assignment_condition("PABX")
)

print(
    "CONTEXTUAL_ASSIGNMENT_RULE_CONDITION=",
    observed_condition,
)

require(
    observed_condition == expected_condition,
    (
        "canonical contextual Assignment Rule "
        "condition changed"
    ),
)

expected_entry_points = [
    "verify_contextual_assignment_rules",
    "ensure_contextual_assignment_rules",
    "apply_contextual_assignment_rules",
    "after_migrate",
]

for name in expected_entry_points:
    function = getattr(
        contextual_assignment_durability,
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
        (
            f"{name} must remain a no-argument "
            "lifecycle entry point"
        ),
    )

ensure_source, ensure_tree = source_tree(
    contextual_assignment_durability
    .ensure_contextual_assignment_rules
)

set_value_calls = function_calls(
    ensure_tree,
    "set_value",
)

require(
    len(set_value_calls) == 1,
    (
        "contextual reconciliation must have exactly "
        "one db.set_value mutation path"
    ),
)

set_value_call = set_value_calls[0]

require(
    literal_arg(set_value_call, 0)
    == "Assignment Rule",
    (
        "contextual reconciliation must mutate "
        "Assignment Rule only"
    ),
)

require(
    literal_arg(set_value_call, 2)
    == "assign_condition",
    (
        "contextual reconciliation may mutate only "
        "Assignment Rule.assign_condition"
    ),
)

require(
    "frappe.delete_doc" not in ensure_source,
    "contextual reconciliation must not delete state",
)

require(
    ".save(" not in ensure_source,
    (
        "contextual reconciliation must not rewrite "
        "Assignment Rule documents"
    ),
)

apply_source = inspect.getsource(
    contextual_assignment_durability
    .apply_contextual_assignment_rules
)

after_migrate_source = inspect.getsource(
    contextual_assignment_durability.after_migrate
)

require(
    "frappe.db.commit()" in apply_source,
    "explicit apply entry point must commit success",
)

require(
    "frappe.db.rollback()" in apply_source,
    "explicit apply entry point must roll back failure",
)

require(
    "ensure_contextual_assignment_rules()"
    in after_migrate_source,
    (
        "after_migrate must delegate to idempotent "
        "contextual reconciliation"
    ),
)

require(
    "commit" not in after_migrate_source,
    (
        "after_migrate must not take transaction "
        "ownership"
    ),
)

require(
    "rollback" not in after_migrate_source,
    (
        "after_migrate must not take transaction "
        "ownership"
    ),
)

print(
    "CONTEXTUAL_ASSIGNMENT_RULE_MUTATION="
    "assign_condition_only"
)

print(
    "CONTEXTUAL_ASSIGNMENT_RULE_OPERATIONAL_STATE_REWRITE=NO"
)

print(
    "CONTEXTUAL_ASSIGNMENT_DURABILITY_CONTRACT=PASS"
)


print()
print(
    "=== Service Coverage native-capability contract ==="
)

resolver_source, resolver_tree = source_tree(
    service_coverage.resolve_contextual_team_assignment
)

required_resolver_fragments = [
    'if not rows:',
    '"coverage_applies": False',
    'covered_users = {',
    'native_team_users = []',
    'eligible_users = [',
    'if user in covered_users',
    'if last_user in native_team_users',
    'if candidate in covered_users',
    'selected_user = eligible_users[0]',
    '"coverage_applies": True',
]

for fragment in required_resolver_fragments:
    require(
        fragment in resolver_source,
        (
            "contextual resolver contract fragment "
            f"is missing: {fragment}"
        ),
    )

for forbidden_call in (
    "set_value",
    "insert",
    "save",
    "delete_doc",
):
    require(
        not function_calls(
            resolver_tree,
            forbidden_call,
        ),
        (
            "contextual resolver must remain read-only; "
            f"found call: {forbidden_call}"
        ),
    )

require(
    "_advance_native_team_cursor"
    not in resolver_source,
    (
        "contextual resolver must not advance the "
        "native cursor itself"
    ),
)

print(
    "CONTEXTUAL_COVERAGE_EXPANDS_NATIVE_CAPABILITY=NO"
)

print(
    "CONTEXTUAL_ELIGIBILITY="
    "native_team_users_intersect_coverage_users"
)

print(
    "CONTEXTUAL_NATIVE_ORDER_AUTHORITATIVE=YES"
)

print(
    "CONTEXTUAL_RESOLVER_READ_ONLY=YES"
)

print(
    "CONTEXTUAL_SERVICE_COVERAGE_CONTRACT=PASS"
)


print()
print(
    "=== Native Assignment Rule cursor contract ==="
)

native_state_source, native_state_tree = source_tree(
    native_team_assignment.native_team_assignment_state
)

require(
    '"Assignment Rule User"'
    in native_state_source,
    (
        "native assignment state must obtain users "
        "from Assignment Rule User"
    ),
)

require(
    '"idx asc"' in native_state_source,
    (
        "native Assignment Rule user order must remain "
        "idx ascending"
    ),
)

require(
    '"last_user"' in native_state_source,
    (
        "native assignment state must expose the "
        "existing last_user cursor"
    ),
)

for forbidden_call in (
    "set_value",
    "insert",
    "save",
    "delete_doc",
):
    require(
        not function_calls(
            native_state_tree,
            forbidden_call,
        ),
        (
            "native assignment state helper must "
            f"remain read-only; found {forbidden_call}"
        ),
    )

cursor_source, cursor_tree = source_tree(
    native_team_assignment.advance_native_team_cursor
)

cursor_writes = function_calls(
    cursor_tree,
    "set_value",
)

require(
    len(cursor_writes) == 1,
    (
        "native cursor helper must contain exactly "
        "one db.set_value write"
    ),
)

cursor_write = cursor_writes[0]

require(
    literal_arg(cursor_write, 0)
    == "Assignment Rule",
    (
        "native cursor helper must update "
        "Assignment Rule"
    ),
)

require(
    literal_arg(cursor_write, 2)
    == "last_user",
    (
        "native cursor helper may update only "
        "Assignment Rule.last_user"
    ),
)

print(
    "CONTEXTUAL_CURSOR="
    "native_assignment_rule_last_user"
)

print(
    "CONTEXTUAL_SEPARATE_CURSOR=NO"
)

print(
    "CONTEXTUAL_NATIVE_CURSOR_CONTRACT=PASS"
)


print()
print(
    "=== After-insert routing precedence contract ==="
)

after_insert_source, after_insert_tree = source_tree(
    telectro_round_robin.assign_after_insert
)

partner_index = after_insert_source.find(
    'if party == "Partner":'
)

direct_index = after_insert_source.find(
    "policy = resolve_ticket_routing_policy(doc)"
)

contextual_index = after_insert_source.find(
    "contextual = resolve_contextual_team_assignment("
)

require(
    min(
        partner_index,
        direct_index,
        contextual_index,
    )
    >= 0,
    "after-insert routing precedence markers are missing",
)

require(
    partner_index
    < direct_index
    < contextual_index,
    (
        "after-insert precedence must remain "
        "Partner -> direct owner -> contextual/native"
    ),
)

hold_calls = function_calls(
    after_insert_tree,
    "_set_contextual_assignment_hold",
)

hold_values = [
    literal_arg(call, 2)
    for call in hold_calls
]

require(
    True in hold_values,
    (
        "after-insert true-pool path must set "
        "contextual hold"
    ),
)

require(
    hold_values.count(False) >= 2,
    (
        "after-insert selected/no-coverage paths "
        "must clear contextual hold"
    ),
)

require(
    len(
        function_calls(
            after_insert_tree,
            "_advance_native_team_cursor",
        )
    )
    >= 1,
    (
        "after-insert contextual assignment must "
        "advance the native cursor"
    ),
)

print(
    "AFTER_INSERT_ROUTING_PRECEDENCE="
    "partner,direct,contextual_native"
)

print(
    "AFTER_INSERT_TRUE_POOL_HOLD=YES"
)

print(
    "AFTER_INSERT_CONTEXTUAL_ROUTING_CONTRACT=PASS"
)


print()
print(
    "=== On-update routing transition contract ==="
)

update_source, update_tree = source_tree(
    telectro_reassign_on_update
    .reassign_if_routing_changed
)

partner_index = update_source.find(
    'if party == "Partner":'
)

direct_index = update_source.find(
    "policy = resolve_ticket_routing_policy(doc)"
)

contextual_index = update_source.find(
    "contextual = resolve_contextual_team_assignment("
)

require(
    min(
        partner_index,
        direct_index,
        contextual_index,
    )
    >= 0,
    "on-update routing precedence markers are missing",
)

require(
    partner_index
    < direct_index
    < contextual_index,
    (
        "on-update precedence must remain "
        "Partner -> direct owner -> contextual/native"
    ),
)

hold_write_values = []

for call in function_calls(
    update_tree,
    "set_value",
):
    if (
        literal_arg(call, 0) == "HD Ticket"
        and literal_arg(call, 2)
        == "custom_contextual_assignment_hold"
    ):
        hold_write_values.append(
            literal_arg(call, 3)
        )

require(
    1 in hold_write_values,
    (
        "on-update true-pool transition must set "
        "contextual hold"
    ),
)

require(
    hold_write_values.count(0) >= 3,
    (
        "on-update authoritative/non-contextual paths "
        "must clear contextual hold"
    ),
)

require(
    len(
        function_calls(
            update_tree,
            "_release_for_native_team_assignment",
        )
    )
    >= 1,
    (
        "on-update true-pool/native transitions must "
        "retain the release-to-pool path"
    ),
)

require(
    len(
        function_calls(
            update_tree,
            "_advance_native_team_cursor",
        )
    )
    >= 1,
    (
        "on-update contextual reassignment must "
        "advance the native cursor"
    ),
)

release_source, release_tree = source_tree(
    telectro_reassign_on_update
    ._release_for_native_team_assignment
)

require(
    '"status": ("!=", "Cancelled")'
    in release_source,
    (
        "pool release must retire every "
        "non-Cancelled ToDo"
    ),
)

require(
    'doc._assign = assign_json'
    in release_source,
    (
        "pool release must clear in-memory "
        "_assign state"
    ),
)

require(
    '"_assign"' in release_source,
    (
        "pool release must clear persisted "
        "_assign state"
    ),
)

print(
    "UPDATE_ROUTING_PRECEDENCE="
    "partner,direct,contextual_native"
)

print(
    "UPDATE_TRUE_POOL_RELEASE=YES"
)

print(
    "UPDATE_CONTEXTUAL_HOLD_CLEAR_PATHS=YES"
)

print(
    "UPDATE_CONTEXTUAL_ROUTING_CONTRACT=PASS"
)


print()
print(
    "=== Contextual routing regression-test contract ==="
)

expected_tests = {
    "contextual_assignment_durability": {
        "test_after_migrate_runs_non_committing_reconciliation",
        "test_apply_commits_successful_reconciliation",
        "test_apply_rolls_back_failed_reconciliation",
        "test_canonical_linked_rule_is_idempotent",
        "test_expected_condition_includes_contextual_hold_guard",
        "test_legacy_linked_rule_updates_only_assign_condition",
        "test_linked_rule_with_contextual_condition_is_valid",
        "test_linked_rule_with_legacy_condition_is_reported",
        "test_reconciliation_fails_if_post_write_verification_is_not_clean",
    },
    "contextual_assignment_fixture": {
        "test_contextual_assignment_durability_hook_is_registered_after_hd_team_durability",
        "test_hold_field_is_defined_as_hidden_system_state",
        "test_hold_field_is_whitelisted_for_custom_field_fixture",
    },
    "service_coverage_assignment": {
        "test_contextual_rotation_wraps_in_native_team_order",
        "test_duplicate_coverage_rows_do_not_duplicate_assignment_population",
        "test_last_user_inside_team_but_outside_coverage_advances_to_next_eligible",
        "test_matching_coverage_is_intersected_with_native_team_membership",
        "test_matching_coverage_with_empty_intersection_does_not_fall_back",
        "test_native_team_order_controls_contextual_rotation",
        "test_no_matching_coverage_leaves_native_team_path_untouched",
        "test_unknown_last_user_starts_with_first_eligible_native_team_member",
    },
    "telectro_round_robin": {
        "test_matching_contextual_coverage_assigns_selected_team_member",
        "test_matching_coverage_with_no_capable_team_member_stays_true_pool",
        "test_no_contextual_coverage_still_falls_through_to_native_assignment",
        "test_normal_internal_ticket_falls_through_to_native_team_assignment",
        "test_partner_fulfilment_resolves_default_dispatch_user",
    },
    "telectro_reassign_on_update": {
        "test_boschendal_routing_change_falls_through_to_native_team",
        "test_contextual_coverage_preserves_current_owner_when_still_eligible",
        "test_contextual_coverage_replaces_native_owner_outside_eligible_population",
        "test_direct_owner_clears_contextual_hold_when_owner_is_already_correct",
        "test_fulfilment_partner_is_routing_relevant",
        "test_matching_coverage_without_capable_team_member_sets_hold_and_releases_owner",
        "test_no_contextual_coverage_clears_stale_hold_and_preserves_valid_native_owner",
        "test_partner_fulfilment_clears_contextual_hold_and_resolves_dispatch_user",
    },
}

total_tests = 0

for contract_name, path in TEST_PATHS.items():
    require(
        path.is_file(),
        f"missing regression test file: {path}",
    )

    tree = ast.parse(
        path.read_text()
    )

    observed = {
        node.name
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.FunctionDef)
            and node.name.startswith("test_")
        )
    }

    expected = expected_tests[contract_name]

    print(
        f"{contract_name.upper()}_TESTS=",
        sorted(observed),
    )

    require(
        observed == expected,
        (
            "regression-test contract changed for "
            f"{contract_name}"
        ),
    )

    total_tests += len(observed)

require(
    total_tests == 33,
    (
        "expected 33 focused contextual-routing "
        f"regression tests, observed {total_tests}"
    ),
)

print(
    "CONTEXTUAL_ROUTING_REGRESSION_TEST_COUNT=",
    total_tests,
)

print(
    "CONTEXTUAL_ROUTING_TEST_CONTRACT=PASS"
)


print()
print(
    "CONTEXTUAL_SERVICE_COVERAGE_ROUTING=PASS"
)
PY
