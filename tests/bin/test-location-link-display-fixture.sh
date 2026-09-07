#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

HOOKS_FILE="${ROOT_DIR}/apps/telephony/telephony/hooks.py"
PROPERTY_SETTER_FILE="${ROOT_DIR}/apps/telephony/telephony/fixtures/property_setter.json"

python3 - \
  "$HOOKS_FILE" \
  "$PROPERTY_SETTER_FILE" <<'PY'
import ast
import json
import sys
from pathlib import Path


hooks_path = Path(sys.argv[1])
property_setter_path = Path(sys.argv[2])

TARGETS = {
    "Location-main-title_field": {
        "doc_type": "Location",
        "doctype_or_field": "DocType",
        "field_name": None,
        "property": "title_field",
        "property_type": "Data",
        "value": "location_name",
    },
    "Location-main-show_title_field_in_link": {
        "doc_type": "Location",
        "doctype_or_field": "DocType",
        "field_name": None,
        "property": "show_title_field_in_link",
        "property_type": "Check",
        "value": "1",
    },
}


def fail(message):
    raise SystemExit(
        f"LOCATION_LINK_DISPLAY_FIXTURE_ERROR: {message}"
    )


def load_hooks_fixtures(path):
    tree = ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        if not any(
            isinstance(target, ast.Name)
            and target.id == "fixtures"
            for target in node.targets
        ):
            continue

        value = ast.literal_eval(node.value)

        if not isinstance(value, list):
            fail("hooks.py fixtures contract is not a list")

        return value

    fail("hooks.py fixtures assignment not found")


def property_setter_hook_names(fixtures):
    matches = [
        row
        for row in fixtures
        if row.get("dt") == "Property Setter"
    ]

    if len(matches) != 1:
        fail(
            "expected exactly one Property Setter fixture contract; "
            f"found {len(matches)}"
        )

    for row in matches[0].get("filters") or []:
        if (
            isinstance(row, list)
            and len(row) == 3
            and row[0] == "name"
            and row[1] == "in"
            and isinstance(row[2], list)
        ):
            return row[2]

    fail("Property Setter fixture has no bounded name/in filter")


rows = json.loads(
    property_setter_path.read_text(
        encoding="utf-8"
    )
)

if not isinstance(rows, list):
    fail("Property Setter fixture is not a JSON list")

print("=== Location Link display fixture contract ===")

by_name = {}

for row in rows:
    name = row.get("name")

    if not name:
        continue

    if name in by_name:
        fail(f"duplicate Property Setter name: {name}")

    by_name[name] = row


for name, expected in TARGETS.items():
    row = by_name.get(name)

    if row is None:
        fail(f"missing Property Setter: {name}")

    for key, expected_value in expected.items():
        actual = row.get(key)

        if actual != expected_value:
            fail(
                f"{name}.{key}: "
                f"expected {expected_value!r}, "
                f"received {actual!r}"
            )

    print(
        "PROPERTY_SETTER",
        {
            "name": name,
            "property": row.get("property"),
            "value": row.get("value"),
        },
    )


location_display_rows = [
    row
    for row in rows
    if row.get("doc_type") == "Location"
    and row.get("doctype_or_field") == "DocType"
    and row.get("property")
    in {
        "title_field",
        "show_title_field_in_link",
    }
]

actual_location_names = sorted(
    row.get("name")
    for row in location_display_rows
)

expected_location_names = sorted(TARGETS)

if actual_location_names != expected_location_names:
    fail(
        "unexpected Location display Property Setter set: "
        f"{actual_location_names!r}"
    )

print()
print(
    "LOCATION_DISPLAY_PROPERTY_SETTER_COUNT="
    f"{len(location_display_rows)}"
)


fixtures = load_hooks_fixtures(hooks_path)
hook_names = property_setter_hook_names(fixtures)

print()
print("=== hooks.py transport contract ===")

for name in TARGETS:
    count = hook_names.count(name)

    if count != 1:
        fail(
            f"{name} occurs {count} times "
            "in Property Setter fixture whitelist"
        )

    print(
        "HOOK_TRANSPORT",
        {
            "name": name,
            "count": count,
        },
    )


print()
print(
    "LOCATION_LINK_DISPLAY_FIXTURE_REGRESSION=PASS"
)
PY
