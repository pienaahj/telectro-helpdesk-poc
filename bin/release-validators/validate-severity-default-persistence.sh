#!/usr/bin/env bash
set -euo pipefail

cd /home/frappe/frappe-bench

FIXTURE_FILE="apps/telephony/telephony/fixtures/client_script.json"
TEST_FILE="apps/telephony/telephony/tests/test-severity-default-persistence.sh"

fail() {
  printf 'SEVERITY_DEFAULT_PERSISTENCE_ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f "$FIXTURE_FILE" ]] ||
  fail "missing Client Script fixture"

[[ -f "$TEST_FILE" ]] ||
  fail "missing Severity persistence regression test"

printf '%s\n' \
  '=== Severity Client Script fixture contract ==='

./env/bin/python <<'PY'
import json
from pathlib import Path

fixture_path = Path(
    "apps/telephony/telephony/fixtures/client_script.json"
)

rows = json.loads(
    fixture_path.read_text()
)

matches = [
    row
    for row in rows
    if (
        row.get("doctype") == "Client Script"
        and row.get("dt") == "HD Ticket"
        and row.get("name") == "Clear Customer and filter List"
        and row.get("enabled") == 1
    )
]

if len(matches) != 1:
    raise SystemExit(
        "SEVERITY_DEFAULT_PERSISTENCE_ERROR: "
        "expected exactly one enabled "
        "'Clear Customer and filter List' Client Script"
    )

script = matches[0].get("script") or ""

expected_refresh = """\
      async refresh(frm) {
        set_queries(frm);

        if (frm.is_new()) {
          await apply_campus_defaults(frm);
        }

        sync_point_fields(frm);
        refresh_deps(frm);
      },
"""

if expected_refresh not in script:
    raise SystemExit(
        "SEVERITY_DEFAULT_PERSISTENCE_ERROR: "
        "new-ticket guard missing from refresh contract"
    )

if 'custom_severity: "Sev3"' not in script:
    raise SystemExit(
        "SEVERITY_DEFAULT_PERSISTENCE_ERROR: "
        "Sev3 new-ticket default is missing"
    )

print(
    "SEVERITY_REFRESH_NEW_TICKET_GUARD=PASS"
)
print(
    "SEVERITY_SEV3_DEFAULT_CONTRACT=PASS"
)
PY

printf '\n%s\n' \
  '=== Severity behavioural regression ==='

bash "$TEST_FILE"

printf '\n%s\n' \
  'SEVERITY_DEFAULT_PERSISTENCE=PASS'
