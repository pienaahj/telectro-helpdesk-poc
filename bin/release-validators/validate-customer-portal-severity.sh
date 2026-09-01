#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import json
from pathlib import Path


TELEPHONY_ROOT = Path("apps/telephony/telephony")

TEMPLATE_PATH = (
    TELEPHONY_ROOT
    / "fixtures/hd_ticket_template.json"
)

CUSTOM_FIELD_PATH = (
    TELEPHONY_ROOT
    / "fixtures/custom_field.json"
)

TICKET_NEW_PATH = Path(
    "apps/helpdesk/desk/src/pages/ticket/TicketNew.vue"
)


def require(condition, message):
    if not condition:
        raise SystemExit(
            "CUSTOMER_PORTAL_SEVERITY_RELEASE_VALIDATION_ERROR: "
            f"{message}"
        )


print("=== Customer portal Default template contract ===")

require(
    TEMPLATE_PATH.is_file(),
    f"missing HD Ticket Template fixture: {TEMPLATE_PATH}",
)

template_fixture = json.loads(
    TEMPLATE_PATH.read_text()
)

default_templates = [
    row
    for row in template_fixture
    if (
        row.get("doctype") == "HD Ticket Template"
        and row.get("name") == "Default"
    )
]

require(
    len(default_templates) == 1,
    "expected exactly one Default HD Ticket Template",
)

default_template = default_templates[0]
template_fields = default_template.get("fields")

require(
    isinstance(template_fields, list),
    "Default HD Ticket Template fields must be a list",
)

severity_rows = [
    row
    for row in template_fields
    if (
        isinstance(row, dict)
        and row.get("fieldname") == "custom_severity"
    )
]

require(
    len(severity_rows) == 1,
    (
        "Default HD Ticket Template must contain "
        "custom_severity exactly once"
    ),
)

severity_template_field = severity_rows[0]

print(
    "CUSTOMER_PORTAL_SEVERITY_TEMPLATE_FIELD=",
    severity_template_field,
)

require(
    severity_template_field.get("hide_from_customer") == 0,
    "Severity must remain visible to Customer portal users",
)

require(
    severity_template_field.get("required") == 1,
    "Severity must remain required in the Customer portal",
)

require(
    severity_template_field.get("parent") == "Default",
    "Severity template parent must remain Default",
)

require(
    severity_template_field.get("parentfield") == "fields",
    "Severity template parentfield must remain fields",
)

require(
    severity_template_field.get("parenttype")
    == "HD Ticket Template",
    "Severity template parenttype changed",
)

print(
    "CUSTOMER_PORTAL_SEVERITY_TEMPLATE_CONTRACT=PASS"
)


print()
print("=== Severity Custom Field contract ===")

require(
    CUSTOM_FIELD_PATH.is_file(),
    f"missing Custom Field fixture: {CUSTOM_FIELD_PATH}",
)

custom_field_fixture = json.loads(
    CUSTOM_FIELD_PATH.read_text()
)

severity_fields = [
    row
    for row in custom_field_fixture
    if (
        row.get("dt") == "HD Ticket"
        and row.get("fieldname") == "custom_severity"
    )
]

require(
    len(severity_fields) == 1,
    "custom_severity Custom Field must appear exactly once",
)

severity_field = severity_fields[0]

severity_options = [
    value.strip()
    for value in (
        severity_field.get("options") or ""
    ).splitlines()
    if value.strip()
]

print(
    "CUSTOMER_PORTAL_SEVERITY_OPTIONS=",
    severity_options,
)

print(
    "CUSTOMER_PORTAL_SEVERITY_DEFAULT=",
    severity_field.get("default"),
)

require(
    severity_field.get("fieldtype") == "Select",
    "Severity must remain a Select field",
)

require(
    severity_options
    == ["Sev1", "Sev2", "Sev3", "Sev4"],
    "Severity options changed",
)

require(
    severity_field.get("default") == "",
    (
        "Severity must not acquire a hidden "
        "Custom Field default"
    ),
)

print(
    "CUSTOMER_PORTAL_SEVERITY_FIELD_CONTRACT=PASS"
)


print()
print("=== Customer portal template render contract ===")

require(
    TICKET_NEW_PATH.is_file(),
    f"missing Customer ticket create component: {TICKET_NEW_PATH}",
)

ticket_new_source = TICKET_NEW_PATH.read_text()

require(
    (
        "!isCustomerPortal.value || "
        "!f.hide_from_customer"
    )
    in ticket_new_source,
    (
        "Customer portal must continue rendering "
        "template fields not hidden from customers"
    ),
)

print(
    "CUSTOMER_PORTAL_TEMPLATE_VISIBILITY_CONTRACT=PASS"
)


print()
print("=== Customer portal create-payload contract ===")

require(
    "...templateFields,"
    in ticket_new_source,
    (
        "Customer ticket create payload must continue "
        "including template fields"
    ),
)

print(
    "CUSTOMER_PORTAL_TEMPLATE_PAYLOAD_CONTRACT=PASS"
)


print()
print("CUSTOMER_PORTAL_SEVERITY=PASS")
PY
