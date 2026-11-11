#!/usr/bin/env bash
set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("apps/telephony/telephony")
TESTS = ROOT / "tests"
HOOKS = ROOT / "hooks.py"
PORTAL = Path("apps/helpdesk/desk/src/pages/ticket/TicketNew.vue")

def require(condition, message):
    if not condition:
        raise SystemExit(
            f"DATA_REQUEST_RELEASE_VALIDATION_ERROR: {message}"
        )

expected = {
    "test_customer_portal_ticket_type.py": 12,
    "test_customer_ticket_list_isolation.py": 8,
    "test_data_request_arrival_contract.py": 13,
    "test_data_request_arrival_hook_registration.py": 5,
    "test_data_request_arrival_outbox.py": 16,
    "test_data_request_completion.py": 10,
    "test_data_request_escalation_intent.py": 9,
    "test_data_request_escalation_outbox.py": 13,
    "test_data_request_escalation_policy.py": 10,
    "test_data_request_escalation_recipients.py": 13,
    "test_data_request_escalation_scheduler.py": 12,
    "test_data_request_intake.py": 17,
    "test_data_request_notification_batch.py": 31,
    "test_data_request_notification_delivery.py": 10,
    "test_data_request_notification_dispatcher.py": 20,
    "test_data_request_notification_email.py": 19,
    "test_data_request_notification_intent_schema.py": 9,
    "test_data_request_notification_reconciliation.py": 18,
    "test_data_request_notification_recording.py": 14,
    "test_data_request_notification_reporting.py": 14,
    "test_data_request_notification_scheduler.py": 12,
    "test_data_request_notification_selection.py": 16,
    "test_data_request_notification_unhandled_failure.py": 15,
    "test_data_request_notification_worker.py": 19,
    "test_data_request_notification_worker_policy.py": 19,
}

require(len(expected) == 25, "Module count changed")
require(sum(expected.values()) == 354, "Test inventory changed")

print("=== Data Request source contract ===")

require(HOOKS.is_file(), "Missing hooks.py")
require(PORTAL.is_file(), "Missing TicketNew.vue")

hooks = HOOKS.read_text()
portal = PORTAL.read_text()

hook_paths = (
    "telephony.data_request_intake.prepare_data_request_insert",
    "telephony.data_request_intake.validate_data_request_intake",
    "telephony.customer_portal_ticket_type.validate_customer_portal_ticket_type",
    "telephony.data_request_arrival_outbox.capture_arrival_intents",
)

for path in hook_paths:
    require(
        hooks.count(f'"{path}"') == 1,
        f"Expected one hook registration: {path}",
    )

require(
    hooks.index(hook_paths[1]) < hooks.index(hook_paths[2]),
    "Data Request validation order changed",
)

portal_markers = (
    'const customerTicketType = ref<"" | "Faults" | "Service Request">("");',
    'v-model="customerTicketType"',
    'value="Faults"',
    'value="Service Request"',
    'ticket_type: customerTicketType.value',
    'custom_request_type: "Other"',
    'if (isCustomerPortal.value && !customerTicketType.value)',
    'params.doc.custom_service_area === "Data Request"',
    'customerTicketType.value !== "Faults"',
    'custom_site_group: selectedCampus.value',
)

for marker in portal_markers:
    require(
        marker in portal,
        f"Customer Portal contract missing: {marker}",
    )

print("DATA_REQUEST_SOURCE_CONTRACT=PASS")

print("\n=== Exact regression inventory ===")

actual = {p.name for p in TESTS.glob("test_data_request*.py")}
actual.update({
    "test_customer_portal_ticket_type.py",
    "test_customer_ticket_list_isolation.py",
})

require(actual == set(expected), "Test module inventory changed")

for name, count in expected.items():
    path = TESTS / name
    require(path.is_file(), f"Missing test module: {name}")

    tree = ast.parse(path.read_text(), filename=str(path))
    observed = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]

    require(
        len(observed) == count,
        f"Test count changed: {name}: {len(observed)} != {count}",
    )

print("DATA_REQUEST_TEST_INVENTORY=PASS")
print(f"DATA_REQUEST_REGRESSION_MODULES={len(expected)}")
print(f"DATA_REQUEST_EXPECTED_TEST_COUNT={sum(expected.values())}")

print("\n=== Isolated Python regressions ===")

completed = 0

for name, count in expected.items():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(TESTS),
            "-p",
            name,
        ],
        text=True,
        capture_output=True,
    )

    output = result.stdout + "\n" + result.stderr
    summary = re.search(r"Ran\s+(\d+)\s+tests?\s+in", output)

    if result.returncode != 0:
        print(output, flush=True)

    require(result.returncode == 0, f"Regressions failed: {name}")
    require(summary is not None, f"Missing test summary: {name}")
    require(
        int(summary.group(1)) == count,
        f"Executed test count mismatch: {name}",
    )
    require(
        "skipped=" not in output,
        f"Skipped tests detected: {name}",
    )

    completed += count
    print(f"MODULE={name} TESTS={count} PASS", flush=True)

require(completed == 354, "Total executed test count mismatch")

print(f"DATA_REQUEST_REGRESSION_TEST_COUNT={completed}")
print("DATA_REQUEST_PYTHON_REGRESSIONS=PASS")
print("DATA_REQUEST_RELEASE_SEMANTIC_VALIDATION=PASS")
PY
