#!/usr/bin/env bash
set -euo pipefail

# Pull edited Telephony app files out of the running backend container
# into the host repo, so they can be committed + pushed.

# --- ensure container exists (and is up) ---
docker compose ps backend >/dev/null

mkdir -p apps/telephony/telephony/overrides
mkdir -p apps/telephony/telephony/scripts
mkdir -p apps/telephony/telephony/fixtures

SRC_BASE="backend:/home/frappe/frappe-bench/apps/telephony/telephony"
DST_BASE="apps/telephony/telephony"

cp_from_container() {
  local src="$1"
  local dst="$2"
  echo "→ ${dst}"
  docker compose cp "${SRC_BASE}/${src}" "${DST_BASE}/${dst}"
}

# --- overrides we care about ---
cp_from_container "overrides/assign_to.py" "overrides/assign_to.py"
cp_from_container "overrides/query_report.py" "overrides/query_report.py"

# --- core telephony pilot logic ---
cp_from_container "telectro_round_robin.py" "telectro_round_robin.py"
cp_from_container "telectro_claim.py" "telectro_claim.py"

# --- scripts folder: proof/diag helpers we rely on ---
cp_from_container "scripts/diag_assign_roundtrip.py" "scripts/diag_assign_roundtrip.py"
cp_from_container "scripts/proof_ticket_assignment.py" "scripts/proof_ticket_assignment.py"
cp_from_container "scripts/inspect_ticket_todos.py" "scripts/inspect_ticket_todos.py"
cp_from_container "scripts/find_recent_hd_tickets.py" "scripts/find_recent_hd_tickets.py"
cp_from_container "scripts/email_account_snapshot.py" "scripts/email_account_snapshot.py"
cp_from_container "scripts/run_claim_handoff_proof.py" "scripts/run_claim_handoff_proof.py"
cp_from_container "scripts/repair_ticket_assignments.py" "scripts/repair_ticket_assignments.py"
cp_from_container "scripts/diagnose_assign_without_todo.py" "scripts/diagnose_assign_without_todo.py"

# --- fixtures (custom fields, client scripts, etc.) ---
# This is where UI-created pilot customizations land after `bench export-fixtures`.
cp_from_container "fixtures" "fixtures"

# normalize fixtures path (host may already have fixtures/fixtures nesting)
if [ -d "${DST_BASE}/fixtures/fixtures" ]; then
  echo "↪ flatten fixtures/fixtures -> fixtures"
  rsync -a "${DST_BASE}/fixtures/fixtures/" "${DST_BASE}/fixtures/"
  rm -rf "${DST_BASE}/fixtures/fixtures"
fi

echo
echo "✅ Pulled telephony changes from container."
echo

# Show what's changed (short + useful)
git status --porcelain
echo
git diff --stat
