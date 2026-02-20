#!/usr/bin/env bash
set -euo pipefail

trap 'echo "❌ pull-telephony-changes failed on line $LINENO" >&2' ERR

# Pull edited Telephony app files out of the running backend container
# into the host repo, so they can be committed + pushed.

# --- ensure container exists (and is up) ---
docker compose ps backend >/dev/null

SRC_BASE="backend:/home/frappe/frappe-bench/apps/telephony/telephony"
DST_BASE="apps/telephony/telephony"

# --- ensure common dirs exist on host (safe even if we later sync whole dir) ---
mkdir -p "${DST_BASE}/overrides"
mkdir -p "${DST_BASE}/scripts"
mkdir -p "${DST_BASE}/fixtures"
mkdir -p "${DST_BASE}/monkey_patches"
mkdir -p "${DST_BASE}/jobs"

cp_from_container() {
  local src="$1"
  local dst="$2"

  if ! docker compose exec -T backend bash -lc "test -e '/home/frappe/frappe-bench/apps/telephony/telephony/${src}'"; then
    echo "❌ Missing in container: telephony/${src}" >&2
    exit 1
  fi

  echo "→ ${dst}"
  docker compose cp "${SRC_BASE}/${src}" "${DST_BASE}/${dst}"
}

cp_optional_from_container() {
  local src="$1"
  local dst="$2"

  if docker compose exec -T backend bash -lc "test -e '/home/frappe/frappe-bench/apps/telephony/telephony/${src}'"; then
    echo "→ ${dst}"
    docker compose cp "${SRC_BASE}/${src}" "${DST_BASE}/${dst}"
  else
    echo "↪ optional missing (skipped): ${dst}"
  fi
}

# Sync a directory by copying its *contents* (not the directory itself),
# to avoid nested dst_dir/dst_dir issues with `docker compose cp`.
cp_dir_from_container() {
  local src_dir="$1"
  local dst_dir="$2"

  if ! docker compose exec -T backend bash -lc "test -d '/home/frappe/frappe-bench/apps/telephony/telephony/${src_dir}'"; then
    echo "↪ dir missing (skipped): ${dst_dir}"
    return 0
  fi

  echo "⇒ dir ${dst_dir}/"
  mkdir -p "${DST_BASE}/${dst_dir}"

  # Copy each entry in the source dir into the destination dir
  # This preserves structure under the dir but avoids `dst_dir/src_dir` nesting.
  docker compose exec -T backend bash -lc "
    cd /home/frappe/frappe-bench/apps/telephony/telephony/${src_dir} &&
    for p in * .*; do
      [ \"\$p\" = \".\" ] && continue
      [ \"\$p\" = \"..\" ] && continue
      [ \"\$p\" = \".DS_Store\" ] && continue
      [ ! -e \"\$p\" ] && continue
      echo \"  - \$p\"
    done
  " >/dev/null

  # Use docker compose cp per entry (works reliably)
  docker compose exec -T backend bash -lc "
    cd /home/frappe/frappe-bench/apps/telephony/telephony/${src_dir} &&
    for p in * .*; do
      [ \"\$p\" = \".\" ] && continue
      [ \"\$p\" = \"..\" ] && continue
      [ \"\$p\" = \".DS_Store\" ] && continue
      [ ! -e \"\$p\" ] && continue
      echo \"\$p\"
    done
  " | while IFS= read -r entry; do
    docker compose cp "${SRC_BASE}/${src_dir}/${entry}" "${DST_BASE}/${dst_dir}/${entry}"
  done
}

# --------------------------------------------------------------------
# 1) Explicit “must-have” files (tight guardrails)
# --------------------------------------------------------------------

# --- overrides we care about ---
cp_from_container "overrides/assign_to.py" "overrides/assign_to.py"
cp_from_container "overrides/query_report.py" "overrides/query_report.py"

# --- core telephony pilot logic ---
cp_from_container "telectro_round_robin.py" "telectro_round_robin.py"
cp_from_container "telectro_claim.py" "telectro_claim.py"

# --- small helpers / guard wrappers ---
cp_optional_from_container "assign_guard.py" "assign_guard.py"

# --- scripts folder: proof/diag helpers we rely on ---
cp_from_container "scripts/diag_assign_roundtrip.py" "scripts/diag_assign_roundtrip.py"
cp_from_container "scripts/proof_ticket_assignment.py" "scripts/proof_ticket_assignment.py"
cp_from_container "scripts/inspect_ticket_todos.py" "scripts/inspect_ticket_todos.py"
cp_from_container "scripts/find_recent_hd_tickets.py" "scripts/find_recent_hd_tickets.py"
cp_from_container "scripts/email_account_snapshot.py" "scripts/email_account_snapshot.py"
cp_from_container "scripts/run_claim_handoff_proof.py" "scripts/run_claim_handoff_proof.py"
cp_from_container "scripts/repair_ticket_assignments.py" "scripts/repair_ticket_assignments.py"
cp_from_container "scripts/diagnose_assign_without_todo.py" "scripts/diagnose_assign_without_todo.py"
cp_from_container "scripts/intake_stage_a_proof.py" "scripts/intake_stage_a_proof.py"
# --- jobs (explicit: avoid docker cp directory nesting) ---
cp_from_container "jobs/__init__.py" "jobs/__init__.py"
cp_from_container "jobs/pull_pilot_inboxes.py" "jobs/pull_pilot_inboxes.py"
cp_from_container "scripts/job_status_pull_pilot_inboxes.py" "scripts/job_status_pull_pilot_inboxes.py"
cp_from_container "scripts/proof_stage_a_v2.py" "scripts/proof_stage_a_v2.py"


# --- notification guard ---
cp_from_container "monkey_patches/notification_log_guard.py" "monkey_patches/notification_log_guard.py"

# --- app config (fixtures, includes, doc_events, overrides) ---
cp_from_container "hooks.py" "hooks.py"

# --- fixtures directory (export-fixtures output) ---
cp_from_container "fixtures" "fixtures"

# --------------------------------------------------------------------
# 2) “Low-risk” directory sync (new)
#    These are areas where new files are expected and should be pulled
#    without you updating the script each time.
# --------------------------------------------------------------------

# Optional: keep these dirs fully synced too (comment out if you want strict lists only)
# cp_dir_from_container "overrides" "overrides"
# cp_dir_from_container "scripts" "scripts"
# cp_dir_from_container "monkey_patches" "monkey_patches"

# --------------------------------------------------------------------
# 3) Normalize fixtures nesting (unchanged)
# --------------------------------------------------------------------
if [ -d "${DST_BASE}/fixtures/fixtures" ]; then
  echo "↪ flatten fixtures/fixtures -> fixtures"
  rsync -a "${DST_BASE}/fixtures/fixtures/" "${DST_BASE}/fixtures/"
  rm -rf "${DST_BASE}/fixtures/fixtures"
fi

echo
echo "✅ Pulled telephony changes from container."
echo

git status --porcelain
echo
git diff --stat
