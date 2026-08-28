#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import ast
import inspect
import json
from pathlib import Path

import frappe

from telephony import telectro_intake
from telephony import telectro_site_guard


TELEPHONY_ROOT = Path("apps/telephony/telephony")

INTAKE_PATH = (
    TELEPHONY_ROOT
    / "telectro_intake.py"
)

SITE_GUARD_PATH = (
    TELEPHONY_ROOT
    / "telectro_site_guard.py"
)

TEST_PATH = (
    TELEPHONY_ROOT
    / "tests/test_email_intake_classification.py"
)

CUSTOM_FIELD_PATH = (
    TELEPHONY_ROOT
    / "fixtures/custom_field.json"
)


def require(condition, message):
    if not condition:
        raise SystemExit(
            "EMAIL_INTAKE_RELEASE_VALIDATION_ERROR: "
            f"{message}"
        )


print("=== Request Source business-origin contract ===")

require(
    CUSTOM_FIELD_PATH.is_file(),
    f"missing custom field fixture: {CUSTOM_FIELD_PATH}",
)

fixture = json.loads(
    CUSTOM_FIELD_PATH.read_text()
)

request_source_fields = [
    row
    for row in fixture
    if (
        row.get("dt") == "HD Ticket"
        and row.get("fieldname") == "custom_request_source"
    )
]

require(
    len(request_source_fields) == 1,
    "custom_request_source fixture must appear exactly once",
)

request_source = request_source_fields[0]

expected_options = (
    "Customer\n"
    "Telectro\n"
    "Partner\n"
    "Supplier"
)

print(
    "REQUEST_SOURCE_DEFAULT=",
    request_source.get("default"),
)

print(
    "REQUEST_SOURCE_OPTIONS=",
    request_source.get("options"),
)

require(
    request_source.get("default") == "Customer",
    "Request Source default must remain Customer",
)

require(
    request_source.get("options") == expected_options,
    "Request Source options changed",
)

require(
    "Email"
    not in {
        value.strip()
        for value in expected_options.splitlines()
    },
    "Email must not be a Request Source business-origin value",
)

print("REQUEST_SOURCE_BUSINESS_ORIGIN_CONTRACT=PASS")


print()
print("=== Email intake classifier entry-point contract ===")

classifier = getattr(
    telectro_site_guard,
    "_is_email_intake",
    None,
)

require(
    callable(classifier),
    "_is_email_intake is missing",
)

signature = inspect.signature(classifier)

require(
    list(signature.parameters) == ["doc"],
    "_is_email_intake must accept exactly doc",
)

print(
    "EMAIL_INTAKE_CLASSIFIER=",
    "_is_email_intake",
)

print("EMAIL_INTAKE_ENTRY_POINT_CONTRACT=PASS")


print()
print("=== Email intake classifier field contract ===")

classifier_source = inspect.getsource(
    telectro_site_guard._is_email_intake
)

classifier_tree = ast.parse(
    classifier_source
)

get_field_literals = [
    node.args[0].value
    for node in ast.walk(classifier_tree)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    )
]

print(
    "EMAIL_INTAKE_CLASSIFIER_FIELDS=",
    get_field_literals,
)

require(
    get_field_literals == ["email_account"],
    (
        "email intake must be classified only from "
        "HD Ticket.email_account"
    ),
)

print("EMAIL_INTAKE_FIELD_CONTRACT=PASS")


print()
print("=== Email intake semantic contract ===")

portal_ticket = frappe._dict(
    {
        "custom_request_source": "Customer",
        "via_customer_portal": 1,
        "email_account": None,
        "raised_by": "customer@example.com",
        "contact_email": None,
    }
)

email_ticket = frappe._dict(
    {
        "custom_request_source": "Customer",
        "via_customer_portal": 0,
        "email_account": "Helpdesk",
        "raised_by": "sender@example.com",
        "contact_email": None,
    }
)

invalid_legacy_source = frappe._dict(
    {
        "custom_request_source": "Email",
        "via_customer_portal": 0,
        "email_account": None,
        "raised_by": None,
        "contact_email": None,
    }
)

portal_result = (
    telectro_site_guard._is_email_intake(
        portal_ticket
    )
)

email_result = (
    telectro_site_guard._is_email_intake(
        email_ticket
    )
)

legacy_result = (
    telectro_site_guard._is_email_intake(
        invalid_legacy_source
    )
)

print(
    "PORTAL_CUSTOMER_IS_EMAIL_INTAKE=",
    portal_result,
)

print(
    "MAILBOX_TICKET_IS_EMAIL_INTAKE=",
    email_result,
)

print(
    "LEGACY_SOURCE_ONLY_IS_EMAIL_INTAKE=",
    legacy_result,
)

require(
    portal_result is False,
    "Customer portal identity was classified as email intake",
)

require(
    email_result is True,
    "populated email_account was not classified as email intake",
)

require(
    legacy_result is False,
    "Request Source must not define the email channel",
)

print("EMAIL_INTAKE_SEMANTIC_CONTRACT=PASS")


print()
print("=== Intake Request Source ownership contract ===")

populate_source = inspect.getsource(
    telectro_intake.populate_from_email
)

populate_tree = ast.parse(
    populate_source
)

request_source_assignments = []

for node in ast.walk(populate_tree):
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    else:
        continue

    for target in targets:
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "custom_request_source"
        ):
            request_source_assignments.append(target)

require(
    len(request_source_assignments) == 0,
    (
        "populate_from_email must not write "
        "custom_request_source"
    ),
)

print(
    "POPULATE_FROM_EMAIL_REQUEST_SOURCE_WRITES=",
    len(request_source_assignments),
)

print("EMAIL_INTAKE_REQUEST_SOURCE_OWNERSHIP_CONTRACT=PASS")


print()
print("=== Email intake regression-test contract ===")

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
    "test_portal_customer_email_identity_is_not_email_intake",
    "test_email_account_identifies_email_intake",
    "test_request_source_does_not_define_email_channel",
    "test_populate_from_email_does_not_write_request_source",
}

print(
    "EMAIL_INTAKE_REGRESSION_TESTS=",
    sorted(observed_tests),
)

require(
    observed_tests == expected_tests,
    "email intake regression-test contract changed",
)

print(
    "EMAIL_INTAKE_REGRESSION_TEST_COUNT=",
    len(observed_tests),
)

print("EMAIL_INTAKE_TEST_CONTRACT=PASS")


print()
print("EMAIL_INTAKE_CLASSIFICATION=PASS")
PY
