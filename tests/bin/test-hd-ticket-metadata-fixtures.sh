#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

HOOKS_FILE="${ROOT_DIR}/apps/telephony/telephony/hooks.py"
CUSTOM_FIELD_FILE="${ROOT_DIR}/apps/telephony/telephony/fixtures/custom_field.json"
PROPERTY_SETTER_FILE="${ROOT_DIR}/apps/telephony/telephony/fixtures/property_setter.json"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f "$HOOKS_FILE" ]] || fail "missing hooks file: $HOOKS_FILE"
[[ -f "$CUSTOM_FIELD_FILE" ]] || {
  fail "missing Custom Field fixture: $CUSTOM_FIELD_FILE"
}
[[ -f "$PROPERTY_SETTER_FILE" ]] || {
  fail "missing Property Setter fixture: $PROPERTY_SETTER_FILE"
}

"$PYTHON_BIN" - \
  "$HOOKS_FILE" \
  "$CUSTOM_FIELD_FILE" \
  "$PROPERTY_SETTER_FILE" <<'PY'
import ast
import json
import sys
from pathlib import Path


hooks_path = Path(sys.argv[1])
custom_field_path = Path(sys.argv[2])
property_setter_path = Path(sys.argv[3])

failures = []


def fail(message):
    failures.append(message)


def assert_equal(actual, expected, label):
    if actual != expected:
        fail(
            f"{label}: expected {expected!r}, "
            f"received {actual!r}"
        )


def load_json(path):
    try:
        value = json.loads(path.read_text())
    except Exception as exc:
        raise RuntimeError(
            f"cannot load JSON fixture {path}: {exc}"
        ) from exc

    if not isinstance(value, list):
        raise RuntimeError(
            f"fixture must contain a JSON list: {path}"
        )

    return value


def index_by_name(rows, label):
    indexed = {}

    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(
                f"{label} contains a non-object row: {row!r}"
            )

        name = row.get("name")

        if not name:
            raise RuntimeError(
                f"{label} contains a row without a name: {row!r}"
            )

        if name in indexed:
            raise RuntimeError(
                f"{label} contains duplicate name: {name}"
            )

        indexed[name] = row

    return indexed


def load_fixture_contract(path):
    tree = ast.parse(path.read_text(), filename=str(path))

    fixture_value = None

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        if not any(
            isinstance(target, ast.Name)
            and target.id == "fixtures"
            for target in node.targets
        ):
            continue

        fixture_value = ast.literal_eval(node.value)
        break

    if fixture_value is None:
        raise RuntimeError(
            f"fixtures assignment not found in {path}"
        )

    if not isinstance(fixture_value, list):
        raise RuntimeError(
            f"fixtures assignment is not a list in {path}"
        )

    return fixture_value


def get_fixture_name_filter(fixtures, doctype):
    matching = [
        fixture
        for fixture in fixtures
        if fixture.get("dt") == doctype
    ]

    if len(matching) != 1:
        raise RuntimeError(
            f"expected exactly one {doctype!r} fixture contract; "
            f"found {len(matching)}"
        )

    filters = matching[0].get("filters") or []

    for row in filters:
        if (
            isinstance(row, list)
            and len(row) == 3
            and row[0] == "name"
            and row[1] == "in"
            and isinstance(row[2], list)
        ):
            return row[2]

    raise RuntimeError(
        f"{doctype!r} fixture has no bounded name/in filter"
    )


expected_structural_fields = {
    "HD Ticket-custom_section_break_n0d4t": {
        "dt": "HD Ticket",
        "fieldname": "custom_section_break_n0d4t",
        "label": "Identifiers",
        "fieldtype": "Section Break",
        "insert_after": "description",
        "collapsible": 1,
    },
    "HD Ticket-custom_section_break_kxmjz": {
        "dt": "HD Ticket",
        "fieldname": "custom_section_break_kxmjz",
        "label": "Partner Tickets",
        "fieldtype": "Section Break",
        "insert_after": "content_type",
        "collapsible": 0,
    },
    "HD Ticket-custom_column_break_pxt06": {
        "dt": "HD Ticket",
        "fieldname": "custom_column_break_pxt06",
        "label": "",
        "fieldtype": "Column Break",
        "insert_after": "custom_section_break_kxmjz",
        "collapsible": 0,
    },
    "HD Ticket-custom_partner_completion": {
        "dt": "HD Ticket",
        "fieldname": "custom_partner_completion",
        "label": "Partner Acceptance",
        "fieldtype": "Heading",
        "insert_after": "custom_column_break_pxt06",
        "collapsible": 0,
    },
    "HD Ticket-custom_column_break_uzsoi": {
        "dt": "HD Ticket",
        "fieldname": "custom_column_break_uzsoi",
        "label": "",
        "fieldtype": "Column Break",
        "insert_after": "custom_partner_accepted_on",
        "collapsible": 0,
    },
    "HD Ticket-custom_partner_work_": {
        "dt": "HD Ticket",
        "fieldname": "custom_partner_work_",
        "label": "Partner Work ",
        "fieldtype": "Heading",
        "insert_after": "custom_column_break_uzsoi",
        "collapsible": 0,
    },
}

expected_field_order = [
    "subject_section",
    "custom_customer",
    "custom_site_group",
    "custom_fault_category",
    "custom_fault_asset",
    "custom_site",
    "custom_ownership_model",
    "ticket_type",
    "custom_request_type",
    "custom_due_date",
    "custom_service_area",
    "custom_fulfilment_party",
    "custom_severity",
    "custom_request_source",
    "custom_take_ownership_on_create",
    "cb00",
    "subject",
    "summary",
    "description",
    "custom_section_break_n0d4t",
    "custom_equipment_ref",
    "sb_details",
    "agent_group",
    "status",
    "priority",
    "raised_by",
    "status_category",
    "template",
    "key",
    "sla_tab",
    "service_level_section",
    "sla",
    "response_by",
    "cb",
    "agreement_status",
    "resolution_by",
    "service_level_agreement_creation",
    "on_hold_since",
    "total_hold_time",
    "response_tab",
    "response",
    "first_response_time",
    "first_responded_on",
    "column_break_26",
    "avg_response_time",
    "resolution_tab",
    "section_break_19",
    "resolution_details",
    "column_break1",
    "opening_date",
    "opening_time",
    "resolution_date",
    "resolution_time",
    "user_resolution_time",
    "reference_tab",
    "additional_info",
    "contact",
    "customer",
    "email_account",
    "column_break_16",
    "via_customer_portal",
    "attachment",
    "content_type",
    "custom_section_break_kxmjz",
    "custom_column_break_pxt06",
    "custom_partner_completion",
    "custom_partner_acceptance_state",
    "custom_partner_accepted_on",
    "custom_column_break_uzsoi",
    "custom_partner_work_",
    "custom_partner_work_state",
    "custom_partner_work_completed",
    "split_and_merge_section",
    "is_merged",
    "merged_with",
    "ticket_split_from",
    "feedback_tab",
    "customer_feedback_section",
    "feedback_rating",
    "feedback",
    "feedback_extra",
    "meta_tab",
]

expected_property_setters = {
    "HD Ticket-main-field_order": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocType",
        "field_name": None,
        "property": "field_order",
        "property_type": "Data",
    },
    "HD Ticket-main-quick_entry": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocType",
        "field_name": None,
        "property": "quick_entry",
        "property_type": "Check",
        "value": "0",
    },
    "HD Ticket-description-depends_on": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "description",
        "property": "depends_on",
        "property_type": "Data",
        "value": "doc.name",
    },
    "HD Ticket-description-description": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "description",
        "property": "description",
        "property_type": "Text",
        "value": "A place where Technical Notes live",
    },
    "HD Ticket-description-label": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "description",
        "property": "label",
        "property_type": "Data",
        "value": "Tech Notes / Work Notes",
    },
    "HD Ticket-sb_details-collapsible_depends_on": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "sb_details",
        "property": "collapsible_depends_on",
        "property_type": "Data",
        "value": 'doc.status!="Closed"',
    },
    "HD Ticket-sb_details-label": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "sb_details",
        "property": "label",
        "property_type": "Data",
        "value": "System / Routing",
    },
    "HD Ticket-subject-placeholder": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "subject",
        "property": "placeholder",
        "property_type": "Data",
        "value": 'e.g. "Boschendal – Camera offline – Villa"',
    },
    "HD Ticket-subject_section-label": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "subject_section",
        "property": "label",
        "property_type": "Data",
        "value": "Intake",
    },
    "HD Ticket-summary-description": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "summary",
        "property": "description",
        "property_type": "Text",
        "value": "A place where Call Intake Note live",
    },
    "HD Ticket-summary-label": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "summary",
        "property": "label",
        "property_type": "Data",
        "value": "Caller Summary / Quick Notes",
    },
    "HD Ticket-summary-placeholder": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "summary",
        "property": "placeholder",
        "property_type": "Data",
        "value": "Caller symptoms + when it started + impact",
    },
    "HD Ticket-ticket_type-default": {
        "doc_type": "HD Ticket",
        "doctype_or_field": "DocField",
        "field_name": "ticket_type",
        "property": "default",
        "property_type": "Text",
        "value": "Faults",
    },
}


fixtures = load_fixture_contract(hooks_path)

custom_hook_names = get_fixture_name_filter(
    fixtures,
    "Custom Field",
)
setter_hook_names = get_fixture_name_filter(
    fixtures,
    "Property Setter",
)

custom_rows = load_json(custom_field_path)
setter_rows = load_json(property_setter_path)

custom_by_name = index_by_name(
    custom_rows,
    "Custom Field fixture",
)
setter_by_name = index_by_name(
    setter_rows,
    "Property Setter fixture",
)


print("=== hooks.py fixture contract ===")

if len(custom_hook_names) != len(set(custom_hook_names)):
    fail("Custom Field hooks whitelist contains duplicate names")

if len(setter_hook_names) != len(set(setter_hook_names)):
    fail("Property Setter hooks whitelist contains duplicate names")

assert_equal(
    set(custom_hook_names),
    set(custom_by_name),
    "Custom Field hooks/JSON name parity",
)

assert_equal(
    set(setter_hook_names),
    set(expected_property_setters),
    "Property Setter hooks bounded-name contract",
)

assert_equal(
    set(setter_hook_names),
    set(setter_by_name),
    "Property Setter hooks/JSON name parity",
)

print(
    "custom_field_hook_count:",
    len(custom_hook_names),
)
print(
    "property_setter_hook_count:",
    len(setter_hook_names),
)


print("\n=== Structural Custom Field contract ===")

for name, expected in expected_structural_fields.items():
    row = custom_by_name.get(name)

    if row is None:
        fail(f"missing structural Custom Field: {name}")
        continue

    for key, expected_value in expected.items():
        assert_equal(
            row.get(key),
            expected_value,
            f"{name}.{key}",
        )

    print(
        "STRUCTURAL_FIELD",
        {
            "name": name,
            "fieldtype": row.get("fieldtype"),
            "insert_after": row.get("insert_after"),
        },
    )


print("\n=== Property Setter contract ===")

for name, expected in expected_property_setters.items():
    row = setter_by_name.get(name)

    if row is None:
        fail(f"missing Property Setter: {name}")
        continue

    for key, expected_value in expected.items():
        assert_equal(
            row.get(key),
            expected_value,
            f"{name}.{key}",
        )

    print(
        "PROPERTY_SETTER",
        {
            "name": name,
            "property": row.get("property"),
            "value": (
                "<field-order>"
                if name == "HD Ticket-main-field_order"
                else row.get("value")
            ),
        },
    )


print("\n=== HD Ticket field-order contract ===")

field_order_row = setter_by_name.get(
    "HD Ticket-main-field_order"
)

if field_order_row is None:
    fail("HD Ticket-main-field_order is missing")
    actual_field_order = []
else:
    try:
        actual_field_order = json.loads(
            field_order_row.get("value") or ""
        )
    except Exception as exc:
        fail(
            "HD Ticket-main-field_order value is not valid JSON: "
            f"{exc}"
        )
        actual_field_order = []

if not isinstance(actual_field_order, list):
    fail("HD Ticket-main-field_order must decode to a list")
    actual_field_order = []

assert_equal(
    actual_field_order,
    expected_field_order,
    "HD Ticket exact field order",
)

assert_equal(
    len(actual_field_order),
    82,
    "HD Ticket field-order count",
)

assert_equal(
    len(actual_field_order),
    len(set(actual_field_order)),
    "HD Ticket field-order uniqueness",
)

hd_ticket_custom_fieldnames = {
    row.get("fieldname")
    for row in custom_rows
    if row.get("dt") == "HD Ticket"
}

missing_custom_fieldnames = sorted(
    fieldname
    for fieldname in hd_ticket_custom_fieldnames
    if fieldname not in actual_field_order
)

assert_equal(
    missing_custom_fieldnames,
    [],
    "HD Ticket fixture fields absent from field order",
)

print("field_order_count:", len(actual_field_order))
print(
    "hd_ticket_custom_field_count:",
    len(hd_ticket_custom_fieldnames),
)
print(
    "missing_custom_fields_from_order:",
    missing_custom_fieldnames,
)


print("\n=== Final result ===")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}")

    print("HD_TICKET_METADATA_FIXTURE_REGRESSION=FAIL")
    raise SystemExit(1)

print("HOOKS_CUSTOM_FIELD_CONTRACT=PASS")
print("HOOKS_PROPERTY_SETTER_CONTRACT=PASS")
print("STRUCTURAL_CUSTOM_FIELD_CONTRACT=PASS")
print("PROPERTY_SETTER_FIXTURE_CONTRACT=PASS")
print("HD_TICKET_FIELD_ORDER_CONTRACT=PASS")
print("HD_TICKET_METADATA_FIXTURE_REGRESSION=PASS")
PY
