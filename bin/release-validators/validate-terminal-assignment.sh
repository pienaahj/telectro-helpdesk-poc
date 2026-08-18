#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
from telephony import telectro_assign_sync

expected = ["Archived", "Closed", "Resolved"]
observed = sorted(telectro_assign_sync.TERMINAL_TICKET_STATUSES)

print("TERMINAL_TICKET_STATUSES=", observed)

if observed != expected:
    raise SystemExit(
        f"unexpected terminal ticket statuses: {observed!r}"
    )

print("TERMINAL_ASSIGNMENT_CHANGE=PASS")
PY
