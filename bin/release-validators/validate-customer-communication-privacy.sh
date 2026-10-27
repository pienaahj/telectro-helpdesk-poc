#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import sys
import unittest

from pathlib import Path


def require(condition, message):
    if not condition:
        raise SystemExit(
            "CUSTOMER_COMMUNICATION_PRIVACY_VALIDATION_ERROR: "
            + message
        )


print("=== Customer Communication Privacy regressions ===")

# Run existing regressions against Python modules packaged
# inside the immutable production candidate.
#
# These suites use unittest and mocked Frappe dependencies.
# No production site or database is required by design.

expected_modules = {
    "customer_communication_permission": 18,
    "customer_communication_privacy": 26,
    "customer_communication_projection": 8,
    "customer_communication_query_permission": 10,
    "customer_ticket_activity_privacy": 4,
    "customer_ticket_api_guard": 8,
    "customer_ticket_detail_api_privacy": 4,
    "customer_ticket_detail_projection": 8,
    "realtime_ticket_authorization": 14,
    "customer_outbound_communication_authority": 18,
}

expected_total = 118

require(
    sum(expected_modules.values()) == expected_total,
    "Regression inventory totals are inconsistent",
)

loader = unittest.TestLoader()
suite = unittest.TestSuite()

for module_name, expected_count in expected_modules.items():
    module_path = (
        Path("apps/telephony/telephony/tests")
        / f"test_{module_name}.py"
    )

    require(
        module_path.is_file(),
        f"Missing regression module: {module_path}",
    )

    target = f"telephony.tests.test_{module_name}"

    loaded = loader.loadTestsFromName(target)

    require(
        not loader.errors,
        f"Unable to load regression module: {target}",
    )

    actual_count = loaded.countTestCases()

    require(
        actual_count == expected_count,
        (
            f"Unexpected regression count for {target}: "
            f"{actual_count}; expected {expected_count}"
        ),
    )

    print(
        f"PRIVACY_TEST_MODULE={module_name} "
        f"COUNT={actual_count}"
    )

    suite.addTests(loaded)

require(
    suite.countTestCases() == expected_total,
    (
        "Unexpected total privacy regression count: "
        f"{suite.countTestCases()}; expected {expected_total}"
    ),
)

print()
print("=== Execute focused privacy regressions ===")

result = unittest.TextTestRunner(
    stream=sys.stdout,
    verbosity=1,
).run(suite)

require(
    result.wasSuccessful(),
    "Customer Communication Privacy regressions failed",
)

require(
    result.testsRun == expected_total,
    (
        f"Executed {result.testsRun} tests; "
        f"expected {expected_total}"
    ),
)

print()
print(
    "CUSTOMER_COMMUNICATION_PRIVACY_REGRESSION_TEST_COUNT="
    f"{result.testsRun}"
)

print(
    "CUSTOMER_COMMUNICATION_PRIVACY_PYTHON_REGRESSIONS=PASS"
)

print()
print("=== Customer Communication Privacy hook integration ===")

import ast

print()
print("=== Customer Communication Privacy hook source contract ===")

hooks_path = Path("apps/telephony/telephony/hooks.py")

require(
    hooks_path.is_file(),
    "Telephony hooks.py is missing",
)

hooks_tree = ast.parse(
    hooks_path.read_text(encoding="utf-8"),
    filename=str(hooks_path),
)


def normalized_expression(expression):
    return ast.unparse(
        ast.parse(expression, mode="eval").body
    )


def require_append_hook(target, event, handler, contract):
    expected_target = normalized_expression(target)

    matches = [
        node
        for node in ast.walk(hooks_tree)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_append_hook"
            and len(node.args) == 3
            and ast.unparse(node.args[0]) == expected_target
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == event
            and isinstance(node.args[2], ast.Constant)
            and node.args[2].value == handler
        )
    ]

    require(
        len(matches) == 1,
        (
            f"{contract}: expected exactly one registration, "
            f"observed {len(matches)}"
        ),
    )

    print(f"PRIVACY_HOOK_SOURCE={contract} PASS")


require_append_hook(
    'doc_events.setdefault("Communication", {})',
    "before_insert",
    "telephony.customer_communication_privacy.classify_new_customer_communication",
    "communication_before_insert",
)

require_append_hook(
    'doc_events["Communication"]',
    "validate",
    "telephony.customer_communication_privacy.validate_communication_audience_integrity",
    "communication_validate",
)

require_append_hook(
    "has_permission",
    "Communication",
    "telephony.customer_communication_permission.communication_has_permission",
    "communication_has_permission",
)

require_append_hook(
    "permission_query_conditions",
    "Communication",
    "telephony.customer_communication_permission.communication_query_conditions",
    "communication_query_conditions",
)


print()
print("=== Helpdesk API override source contract ===")

override_mappings = []

for node in ast.walk(hooks_tree):
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "override_whitelisted_methods"
        and node.func.attr == "update"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Dict)
    ):
        continue

    override_mappings.append(
        ast.literal_eval(node.args[0])
    )


expected_api_overrides = {
    "get_ticket_activities": "get_ticket_activities",
    "get_one": "get_one",
    "get_ticket_assignees": "get_ticket_assignees",
    "get_ticket_contact": "get_ticket_contact",
    "get_recent_similar_tickets": "get_recent_similar_tickets",
}

for upstream_method, guarded_method in expected_api_overrides.items():
    upstream = (
        "helpdesk.helpdesk.doctype.hd_ticket.api."
        + upstream_method
    )

    expected_guard = (
        "telephony.customer_ticket_api_guard."
        + guarded_method
    )

    matches = sum(
        mapping.get(upstream) == expected_guard
        for mapping in override_mappings
    )

    require(
        matches == 1,
        (
            f"API override {upstream_method}: "
            f"expected one guarded registration, "
            f"observed {matches}"
        ),
    )

    print(
        f"PRIVACY_HOOK_SOURCE=api_override_{upstream_method} PASS"
    )


print()
print(
    "CUSTOMER_COMMUNICATION_PRIVACY_HOOK_SOURCE_CONTRACT=PASS"
)

print()
print("=== Hardened realtime JavaScript integrity ===")

import hashlib
import subprocess

expected_js_hashes = {
    "apps/frappe/realtime/utils.js": (
        "e5daace2a357d21673be184fdf8053f1c3544e3200f2c0f3865318da57805092"
    ),
    "apps/frappe/realtime/middlewares/authenticate.js": (
        "e05f517c353d300833fcf9376038718ca76a248098ffa74b5c0cd1f4d57c271f"
    ),
    "apps/frappe/realtime/index.js": (
        "acf2ef802d3f68c8016c08685e24eaf83488ba63392ae63855218a4d70ea89c3"
    ),
    "apps/frappe/realtime/handlers/frappe_handlers.js": (
        "d484f2c63ef7c7ae16f1a876acc07e77d378638dad83c8649bce22458907fc86"
    ),
    "apps/helpdesk/realtime/handlers.js": (
        "633df0811e0a75dd5e2b0e7814ca46a9d767896cec61139b1e2a8f9a0c119e69"
    ),
}

require(
    len(expected_js_hashes) == 5,
    "Expected exactly five hardened JavaScript files",
)

for filename, expected_sha256 in expected_js_hashes.items():
    path = Path(filename)

    require(
        path.is_file(),
        f"Missing hardened JavaScript file: {filename}",
    )

    actual_sha256 = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    require(
        actual_sha256 == expected_sha256,
        (
            f"JavaScript SHA-256 mismatch: {filename}; "
            f"expected {expected_sha256}, "
            f"observed {actual_sha256}"
        ),
    )

    print(f"PRIVACY_JS_SHA256=PASS FILE={filename}")

    try:
        result = subprocess.run(
            ["node", "--check", filename],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise SystemExit(
            "CUSTOMER_COMMUNICATION_PRIVACY_VALIDATION_ERROR: "
            "Node.js executable is missing"
        )

    require(
        result.returncode == 0,
        (
            f"JavaScript syntax failure: {filename}\n"
            f"{result.stderr}"
        ),
    )

    print(f"PRIVACY_JS_SYNTAX=PASS FILE={filename}")


print()
print(
    "CUSTOMER_COMMUNICATION_PRIVACY_JS_INTEGRITY=PASS"
)

print()
print("=== Global HD Ticket realtime authority integrity ===")

authority_path = Path(
    "apps/telephony/telephony/realtime_ticket_authorization.py"
)

expected_authority_sha256 = (
    "9a836df13b8880437494ddd140423f840e06a899db5abf0b291ba673f903680d"
)

require(
    authority_path.is_file(),
    f"Missing realtime authority module: {authority_path}",
)

actual_authority_sha256 = hashlib.sha256(
    authority_path.read_bytes()
).hexdigest()

print(
    "GLOBAL_ROOM_AUTHORITY_SHA256="
    f"{actual_authority_sha256}"
)

require(
    actual_authority_sha256 == expected_authority_sha256,
    (
        "Global HD Ticket authority source mismatch; "
        f"expected {expected_authority_sha256}, "
        f"observed {actual_authority_sha256}"
    ),
)

print(
    "CUSTOMER_COMMUNICATION_PRIVACY_GLOBAL_ROOM_AUTHORITY=PASS"
)

print()
print("=== Communication audience fixture integrity ===")

import json

fixture_path = Path(
    "apps/telephony/telephony/fixtures/custom_field.json"
)

require(
    fixture_path.is_file(),
    f"Missing Custom Field fixture: {fixture_path}",
)

fixture_records = json.loads(
    fixture_path.read_text(encoding="utf-8")
)

require(
    isinstance(fixture_records, list),
    "Custom Field fixture must contain a JSON list",
)

audience_field_name = "Communication-custom_telectro_audience"

matches = [
    record
    for record in fixture_records
    if (
        isinstance(record, dict)
        and record.get("name") == audience_field_name
    )
]

require(
    len(matches) == 1,
    (
        "Expected exactly one Communication audience field, "
        f"observed {len(matches)}"
    ),
)

field = matches[0]

expected_attributes = {
    "dt": "Communication",
    "fieldname": "custom_telectro_audience",
    "fieldtype": "Select",
    "options": "\nCustomer\nInternal\nPartner",
    "reqd": 0,
    "hidden": 1,
    "read_only": 1,
    "permlevel": 0,
}

for attribute, expected in expected_attributes.items():
    actual = field.get(attribute)

    require(
        actual == expected,
        (
            f"Communication audience field {attribute}: "
            f"expected {expected!r}, observed {actual!r}"
        ),
    )

require(
    field.get("default") in (None, ""),
    "Communication audience must have no default",
)

print("PRIVACY_AUDIENCE_FIELD_DEFINITION=PASS")


print()
print("=== Communication audience fixture registration ===")

# hooks_tree was parsed earlier in this same validator.
# Inspect the declared Custom Field fixture filters without
# importing hooks.py or initialising a Frappe site.

registration_count = 0

for node in ast.walk(hooks_tree):
    if not isinstance(node, ast.Dict):
        continue

    try:
        entry = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        continue

    if not isinstance(entry, dict):
        continue

    if entry.get("dt") != "Custom Field":
        continue

    for filter_entry in entry.get("filters", []):
        if not (
            isinstance(filter_entry, (list, tuple))
            and len(filter_entry) == 3
            and filter_entry[0] == "name"
            and filter_entry[1] == "in"
            and isinstance(filter_entry[2], (list, tuple))
        ):
            continue

        registration_count += filter_entry[2].count(
            audience_field_name
        )

require(
    registration_count == 1,
    (
        "Expected exactly one Communication audience "
        "fixture registration; "
        f"observed {registration_count}"
    ),
)

print("PRIVACY_AUDIENCE_FIXTURE_REGISTRATION=PASS")


print()
print(
    "CUSTOMER_COMMUNICATION_PRIVACY_AUDIENCE_FIXTURE=PASS"
)

print()
print("=== Customer Communication Privacy final acceptance ===")
print("CUSTOMER_COMMUNICATION_PRIVACY_SEMANTIC_VALIDATION=PASS")
PY
