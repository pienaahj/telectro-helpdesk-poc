#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python -B <<'PY'
import ast
import json
import sys
import unittest

from pathlib import Path


ROOT = Path("apps/telephony/telephony")
TESTS = ROOT / "tests"


def require(condition, message):
    if not condition:
        raise SystemExit(
            "TASK_NOTIFICATION_VALIDATION_ERROR: " + message
        )


def load_function(filename, name):
    path = ROOT / filename
    require(path.is_file(), f"Missing implementation: {path}")

    tree = ast.parse(path.read_text())

    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == name
    ]

    require(
        len(matches) == 1,
        f"Expected exactly one function: {filename}:{name}",
    )

    return matches[0]


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return dotted(node.value) + "." + node.attr

    return ""


def calls(node, target):
    return [
        item
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and dotted(item.func) == target
    ]


print("=== Task Notification regression inventory ===")

expected_modules = {
    "capture_boundary": 6,
    "claim_authorization": 18,
    "claim_boundary": 4,
    "claim_capture": 7,
    "claim_event_identity": 3,
    "claim_schema_guard": 5,
    "duplicate_identity": 6,
    "event_identity": 7,
    "intent_schema": 6,
    "locking_read": 4,
    "outbox": 6,
    "policy": 9,
    "stale_duplicate": 5,
    "transition": 14,
}

require(len(expected_modules) == 14, "Incorrect module inventory")
require(sum(expected_modules.values()) == 100, "Incorrect test total")

loader = unittest.TestLoader()
suite = unittest.TestSuite()

for name, expected_count in expected_modules.items():
    module_path = TESTS / f"test_task_notification_{name}.py"

    require(
        module_path.is_file(),
        f"Missing regression module: {module_path}",
    )

    loaded = loader.loadTestsFromName(
        f"telephony.tests.test_task_notification_{name}"
    )

    require(not loader.errors, f"Test loading failed: {name}")

    count = loaded.countTestCases()

    require(
        count == expected_count,
        f"{name}: expected {expected_count}, found {count}",
    )

    print(f"TASK_NOTIFICATION_MODULE={name} COUNT={count}")

    suite.addTests(loaded)

require(suite.countTestCases() == 100, "Suite total mismatch")

print()
print("=== Execute Task Notification regressions ===")

result = unittest.TextTestRunner(
    stream=sys.stdout,
    verbosity=1,
).run(suite)

require(result.testsRun == 100, "Incorrect executed test count")
require(result.wasSuccessful(), "Regression failures")
require(not result.skipped, "Skipped regressions are forbidden")
require(not result.expectedFailures, "Expected failures are forbidden")
require(not result.unexpectedSuccesses, "Unexpected successes are forbidden")

print("TASK_NOTIFICATION_REGRESSION_MODULES=14")
print("TASK_NOTIFICATION_REGRESSION_TEST_COUNT=100")
print("TASK_NOTIFICATION_PYTHON_REGRESSIONS=PASS")


print()
print("=== Claim schema prerequisite ===")

claim = load_function(
    "telectro_claim.py",
    "telectro_claim_ticket",
)

authorization = calls(claim, "_require_claim_authorization")
schema = calls(claim, "frappe.db.table_exists")
capture = calls(
    claim,
    "capture_verified_task_ownership_transition",
)
commit = calls(claim, "frappe.db.commit")

require(len(authorization) == 1, "Claim authorization changed")
require(len(schema) == 1, "Schema prerequisite missing")
require(len(capture) == 1, "Claim capture integration changed")
require(len(commit) == 1, "Claim commit boundary changed")

schema_call = schema[0]

require(
    len(schema_call.args) == 1
    and isinstance(schema_call.args[0], ast.Constant)
    and schema_call.args[0].value
        == "TELECTRO Task Notification Intent",
    "Wrong schema prerequisite",
)

require(
    any(
        keyword.arg == "cached"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is False
        for keyword in schema_call.keywords
    ),
    "Schema check must bypass cached table inventory",
)

source = (ROOT / "telectro_claim.py").read_text()

updates = [
    call
    for call in calls(claim, "frappe.db.sql")
    if "UPDATE `tabHD Ticket`"
    in (ast.get_source_segment(source, call) or "")
]

require(len(updates) == 1, "Claim UPDATE contract changed")

require(
    authorization[0].lineno
    < schema_call.lineno
    < updates[0].lineno
    < capture[0].lineno
    < commit[0].lineno,
    "Claim authorization/schema/update/capture/commit order changed",
)

require(
    "notification_schema_unavailable"
    in ast.get_source_segment(source, claim),
    "Missing schema rejection response",
)

capture_args = {
    keyword.arg: keyword.value
    for keyword in capture[0].keywords
}

require(
    isinstance(capture_args.get("action"), ast.Constant)
    and capture_args["action"].value == "claim",
    "Claim action identity changed",
)

require(
    isinstance(capture_args.get("transition_confirmed"), ast.Constant)
    and capture_args["transition_confirmed"].value is True,
    "Confirmed transition contract changed",
)

require(
    isinstance(capture_args.get("event_id"), ast.Name)
    and capture_args["event_id"].id == "claim_event_id",
    "Durable Claim event identity changed",
)

print("TASK_NOTIFICATION_CLAIM_SCHEMA_GUARD=PASS")
print("TASK_NOTIFICATION_CLAIM_CAPTURE_INTEGRATION=PASS")


print()
print("=== Verified transition and outbox boundary ===")

transition = load_function(
    "task_notification_transition.py",
    "capture_verified_task_ownership_transition",
)

require(
    len(calls(transition, "should_notify_assignment")) == 1,
    "Ownership notification policy integration changed",
)

require(
    len(calls(
        transition,
        "outbox.capture_task_notification_intent_safely",
    )) == 1,
    "Safe outbox adapter integration changed",
)

safe = load_function(
    "task_notification_outbox.py",
    "capture_task_notification_intent_safely",
)

require(
    len(calls(safe, "frappe.db.savepoint")) == 1,
    "Missing notification savepoint",
)

require(
    len(calls(safe, "frappe.db.rollback")) == 1,
    "Missing notification rollback",
)

require(
    len(calls(safe, "capture_task_notification_intent")) == 1,
    "Missing durable intent capture",
)

require(
    not calls(safe, "frappe.db.commit"),
    "Safe outbox must not commit caller transaction",
)

require(
    not calls(safe, "frappe.sendmail"),
    "Safe capture must not send email",
)

require(
    not calls(safe, "frappe.enqueue"),
    "Safe capture must not schedule delivery",
)

intent = load_function(
    "task_notification_outbox.py",
    "capture_task_notification_intent",
)

require(
    len(calls(intent, "task_notification_event_key")) == 1,
    "Deterministic event identity missing",
)

require(
    not calls(intent, "frappe.db.commit"),
    "Intent creation must not own transaction",
)

print("TASK_NOTIFICATION_OUTBOX_TRANSACTION_BOUNDARY=PASS")


print()
print("=== Notification Intent DocType schema ===")

doctype_path = (
    ROOT
    / "ftelephony"
    / "doctype"
    / "telectro_task_notification_intent"
    / "telectro_task_notification_intent.json"
)

require(doctype_path.is_file(), "Notification Intent JSON missing")

doctype = json.loads(doctype_path.read_text())

require(
    doctype.get("name") == "TELECTRO Task Notification Intent",
    "Incorrect DocType identity",
)

require(
    doctype.get("module") == "FTelephony",
    "Incorrect DocType module",
)

require(
    doctype.get("autoname") == "field:event_key",
    "Incorrect event naming",
)

fields = {
    row["fieldname"]: row
    for row in doctype["fields"]
}

require(
    len(fields) == len(doctype["fields"]),
    "Duplicate DocType fieldnames",
)

require(
    fields.get("event_key", {}).get("unique") == 1,
    "Event key must be unique",
)

for fieldname in (
    "ticket",
    "action",
    "event_id",
    "recipient",
    "status",
    "attempt_count",
):
    require(fieldname in fields, f"Missing field: {fieldname}")

controller = doctype_path.with_suffix(".py")
require(controller.is_file(), "Notification Intent controller missing")

print("TASK_NOTIFICATION_INTENT_SCHEMA=PASS")


print()
print("=== FTelephony module registration ===")

modules = ROOT / "modules.txt"

require(modules.is_file(), "Telephony modules.txt missing")
require(
    "FTelephony" in modules.read_text().splitlines(),
    "FTelephony module not registered",
)

print("TASK_NOTIFICATION_MODULE_REGISTRATION=PASS")


print()
print("=== Task Notification final acceptance ===")
print("TASK_NOTIFICATION_SEMANTIC_VALIDATION=PASS")
PY
