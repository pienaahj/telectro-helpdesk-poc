#!/usr/bin/env bash
set -euo pipefail

mkdir -p apps/telephony/telephony/overrides
mkdir -p apps/telephony/telephony/scripts

SRC_BASE="backend:/home/frappe/frappe-bench/apps/telephony/telephony"
DST_BASE="apps/telephony/telephony"

# --- overrides we care about ---
docker compose cp "${SRC_BASE}/overrides/assign_to.py" \
  "${DST_BASE}/overrides/assign_to.py"

# --- core telephony pilot logic ---
docker compose cp "${SRC_BASE}/telectro_round_robin.py" \
  "${DST_BASE}/telectro_round_robin.py"

docker compose cp "${SRC_BASE}/telectro_claim.py" \
  "${DST_BASE}/telectro_claim.py"

# --- scripts folder: pull the proof/diag helpers we rely on ---
# Existing
docker compose cp "${SRC_BASE}/scripts/diag_assign_roundtrip.py" \
  "${DST_BASE}/scripts/diag_assign_roundtrip.py"

# New / used today
docker compose cp "${SRC_BASE}/scripts/proof_ticket_assignment.py" \
  "${DST_BASE}/scripts/proof_ticket_assignment.py"

docker compose cp "${SRC_BASE}/scripts/inspect_ticket_todos.py" \
  "${DST_BASE}/scripts/inspect_ticket_todos.py"

docker compose cp "${SRC_BASE}/scripts/find_recent_hd_tickets.py" \
  "${DST_BASE}/scripts/find_recent_hd_tickets.py"

docker compose cp "${SRC_BASE}/scripts/email_account_snapshot.py" \
  "${DST_BASE}/scripts/email_account_snapshot.py"

docker compose cp "${SRC_BASE}/scripts/run_claim_handoff_proof.py" \
  "${DST_BASE}/scripts/run_claim_handoff_proof.py"

echo "Pulled telephony changes from container."
git status --porcelain

docker compose cp "${SRC_BASE}/scripts/repair_ticket_assignments.py" \
  "${DST_BASE}/scripts/repair_ticket_assignments.py"

docker compose cp "${SRC_BASE}/scripts/diagnose_assign_without_todo.py" \
  "${DST_BASE}/scripts/diagnose_assign_without_todo.py"


