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
mkdir -p "${DST_BASE}/ftelephony/report"
mkdir -p "${DST_BASE}/ftelephony/page"
mkdir -p "${DST_BASE}/public/js"
mkdir -p "${DST_BASE}/api"

mirror_dir_from_container() {
  local src_dir="$1"
  local dst_dir="$2"

  if ! docker compose exec -T backend bash -lc "test -d '/home/frappe/frappe-bench/apps/telephony/telephony/${src_dir}'"; then
    echo "↪ dir missing in container (mirror skipped): ${dst_dir}"
    return 0
  fi

  echo "⇄ mirror dir ${dst_dir}/"
  mkdir -p "${DST_BASE}/${dst_dir}"

  local tmp_manifest
  local tmp_host_manifest
  tmp_manifest="$(mktemp)"
  tmp_host_manifest="$(mktemp)"

  docker compose exec -T backend bash -lc "
    cd /home/frappe/frappe-bench/apps/telephony/telephony/${src_dir} &&
    find . \
      -path './__pycache__' -prune -o \
      -path '*/__pycache__' -prune -o \
      -name '.DS_Store' -prune -o \
      -print |
    sed 's#^\./##' |
    awk 'NF'
  " | sort > "${tmp_manifest}"

  echo "  manifest entries: $(wc -l < "${tmp_manifest}" | tr -d ' ')"

  while IFS= read -r rel; do
    [ -z "${rel}" ] && continue

    if docker compose exec -T backend bash -lc "test -d '/home/frappe/frappe-bench/apps/telephony/telephony/${src_dir}/${rel}'"; then
      echo "  ↪ mkdir ${dst_dir}/${rel}/"
      mkdir -p "${DST_BASE}/${dst_dir}/${rel}"
    else
      echo "  → copy ${dst_dir}/${rel}"
      mkdir -p "$(dirname "${DST_BASE}/${dst_dir}/${rel}")"
      docker compose cp \
        "${SRC_BASE}/${src_dir}/${rel}" \
        "${DST_BASE}/${dst_dir}/${rel}"

      if [ ! -e "${DST_BASE}/${dst_dir}/${rel}" ]; then
        echo "ERROR: mirrored file missing after copy: ${dst_dir}/${rel}" >&2
        rm -f "${tmp_manifest}" "${tmp_host_manifest}"
        return 1
      fi
    fi
  done < "${tmp_manifest}"

  find "${DST_BASE}/${dst_dir}" \
    \( -name '__pycache__' -o -name '.DS_Store' \) -prune -o \
    -mindepth 1 -print | \
    sed "s#^${DST_BASE}/${dst_dir}/##" | sort > "${tmp_host_manifest}"

  comm -23 "${tmp_host_manifest}" "${tmp_manifest}" | while IFS= read -r stale; do
    [ -z "${stale}" ] && continue
    echo "  ✗ remove stale ${dst_dir}/${stale}"
    rm -rf "${DST_BASE}/${dst_dir}/${stale}"
  done

  rm -f "${tmp_manifest}" "${tmp_host_manifest}"
}

cp_from_container() {
  local src="$1"
  local dst="$2"

  if ! docker compose exec -T backend bash -lc "test -e '/home/frappe/frappe-bench/apps/telephony/telephony/${src}'"; then
    echo "❌ Missing in container: telephony/${src}" >&2
    exit 1
  fi

  echo "→ ${dst}"
  # Ensure dst dir exists to avoid `docker compose cp` nesting issues (it doesn't auto-create intermediate dirs, and if dst doesn't exist it creates a dst file instead of copying into it)
  mkdir -p "$(dirname "${DST_BASE}/${dst}")"
  docker compose cp "${SRC_BASE}/${src}" "${DST_BASE}/${dst}"
}

cp_optional_from_container() {
  local src="$1"
  local dst="$2"

  if docker compose exec -T backend bash -lc "test -e '/home/frappe/frappe-bench/apps/telephony/telephony/${src}'"; then
    echo "→ ${dst}"
    # Ensure dst dir exists to avoid `docker compose cp` nesting issues (it doesn't auto-create intermediate dirs, and if dst doesn't exist it creates a dst file instead of copying into it)
    mkdir -p "$(dirname "${DST_BASE}/${dst}")"
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

  docker compose exec -T backend bash -lc "
    cd /home/frappe/frappe-bench/apps/telephony/telephony/${src_dir} &&
    for p in * .*; do
      [ \"\$p\" = \".\" ] && continue
      [ \"\$p\" = \"..\" ] && continue
      [ \"\$p\" = \".DS_Store\" ] && continue
      [ ! -e \"\$p\" ] && continue
      printf '%s\n' \"\$p\"
    done
  " | while IFS= read -r entry; do
    if docker compose exec -T backend bash -lc "test -d '/home/frappe/frappe-bench/apps/telephony/telephony/${src_dir}/${entry}'"; then
      mkdir -p "${DST_BASE}/${dst_dir}/${entry}"
      docker compose exec -T backend bash -lc "
        cd /home/frappe/frappe-bench/apps/telephony/telephony/${src_dir}/${entry} &&
        for p in * .*; do
          [ \"\$p\" = \".\" ] && continue
          [ \"\$p\" = \"..\" ] && continue
          [ \"\$p\" = \".DS_Store\" ] && continue
          [ ! -e \"\$p\" ] && continue
          printf '%s\n' \"\$p\"
        done
      " | while IFS= read -r subentry; do
        docker compose cp \
          "${SRC_BASE}/${src_dir}/${entry}/${subentry}" \
          "${DST_BASE}/${dst_dir}/${entry}/${subentry}"
      done
    else
      docker compose cp \
        "${SRC_BASE}/${src_dir}/${entry}" \
        "${DST_BASE}/${dst_dir}/${entry}"
    fi
  done
}

# --------------------------------------------------------------------
# 2) “Low-risk” directory sync (new)
#    These are areas where new files are expected and should be pulled
#    without you updating the script each time.
# --------------------------------------------------------------------

# Optional: keep these dirs fully synced too (comment out if you want strict lists only)
# cp_dir_from_container "overrides" "overrides"
# cp_dir_from_container "scripts" "scripts"
# cp_dir_from_container "monkey_patches" "monkey_patches"

# Standard report files
mirror_dir_from_container "ftelephony/report" "ftelephony/report"

# Explicitly pull report files too (since they can be edited in-place in the container, and we want to ensure we get them even if new files are added without updating the script)
# Report files are also pulled explicitly because mirror_dir_from_container
# alone did not reliably propagate in-place updates for already-existing host files.
# Keep these explicit pulls unless/update propagation is re-proved.
cp_from_container \
  "ftelephony/report/active_tickets_by_technician/active_tickets_by_technician.py" \
  "ftelephony/report/active_tickets_by_technician/active_tickets_by_technician.py"

cp_from_container \
  "ftelephony/report/active_tickets_by_technician/active_tickets_by_technician.json" \
  "ftelephony/report/active_tickets_by_technician/active_tickets_by_technician.json"

cp_from_container \
  "ftelephony/report/active_tickets_by_technician/active_tickets_by_technician.js" \
  "ftelephony/report/active_tickets_by_technician/active_tickets_by_technician.js"
# --------------------------------------------------------------------
cp_from_container \
  "ftelephony/report/aging_and_at_risk_tickets/aging_and_at_risk_tickets.py" \
  "ftelephony/report/aging_and_at_risk_tickets/aging_and_at_risk_tickets.py"

cp_from_container \
  "ftelephony/report/aging_and_at_risk_tickets/aging_and_at_risk_tickets.json" \
  "ftelephony/report/aging_and_at_risk_tickets/aging_and_at_risk_tickets.json"

cp_from_container \
  "ftelephony/report/aging_and_at_risk_tickets/aging_and_at_risk_tickets.js" \
  "ftelephony/report/aging_and_at_risk_tickets/aging_and_at_risk_tickets.js"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/coordinator_uplift_history/__init__.py" \
  "ftelephony/report/coordinator_uplift_history/__init__.py"

cp_from_container \
  "ftelephony/report/coordinator_uplift_history/coordinator_uplift_history.js" \
  "ftelephony/report/coordinator_uplift_history/coordinator_uplift_history.js"

cp_from_container \
  "ftelephony/report/coordinator_uplift_history/coordinator_uplift_history.json" \
  "ftelephony/report/coordinator_uplift_history/coordinator_uplift_history.json"

cp_from_container \
  "ftelephony/report/coordinator_uplift_history/coordinator_uplift_history.py" \
  "ftelephony/report/coordinator_uplift_history/coordinator_uplift_history.py"
cp_from_container \
  "ftelephony/report/supervisor_team_snapshot/supervisor_team_snapshot.py" \
  "ftelephony/report/supervisor_team_snapshot/supervisor_team_snapshot.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/first_response_missed/__init__.py" \
  "ftelephony/report/first_response_missed/__init__.py"

cp_from_container \
  "ftelephony/report/first_response_missed/first_response_missed.js" \
  "ftelephony/report/first_response_missed/first_response_missed.js"

cp_from_container \
  "ftelephony/report/first_response_missed/first_response_missed.json" \
  "ftelephony/report/first_response_missed/first_response_missed.json"

cp_from_container \
  "ftelephony/report/first_response_missed/first_response_missed.py" \
  "ftelephony/report/first_response_missed/first_response_missed.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/partner_acceptance_review_queue/__init__.py" \
  "ftelephony/report/partner_acceptance_review_queue/__init__.py"

cp_from_container \
  "ftelephony/report/partner_acceptance_review_queue/partner_acceptance_review_queue.js" \
  "ftelephony/report/partner_acceptance_review_queue/partner_acceptance_review_queue.js"

cp_from_container \
  "ftelephony/report/partner_acceptance_review_queue/partner_acceptance_review_queue.json" \
  "ftelephony/report/partner_acceptance_review_queue/partner_acceptance_review_queue.json"

cp_from_container \
  "ftelephony/report/partner_acceptance_review_queue/partner_acceptance_review_queue.py" \
  "ftelephony/report/partner_acceptance_review_queue/partner_acceptance_review_queue.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/partner_acceptance_rework_queue/__init__.py" \
  "ftelephony/report/partner_acceptance_rework_queue/__init__.py"

cp_from_container \
  "ftelephony/report/partner_acceptance_rework_queue/partner_acceptance_rework_queue.js" \
  "ftelephony/report/partner_acceptance_rework_queue/partner_acceptance_rework_queue.js"

cp_from_container \
  "ftelephony/report/partner_acceptance_rework_queue/partner_acceptance_rework_queue.json" \
  "ftelephony/report/partner_acceptance_rework_queue/partner_acceptance_rework_queue.json"

cp_from_container \
  "ftelephony/report/partner_acceptance_rework_queue/partner_acceptance_rework_queue.py" \
  "ftelephony/report/partner_acceptance_rework_queue/partner_acceptance_rework_queue.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/my_tickets/__init__.py" \
  "ftelephony/report/my_tickets/__init__.py"

cp_from_container \
  "ftelephony/report/my_tickets/my_tickets.js" \
  "ftelephony/report/my_tickets/my_tickets.js"

cp_from_container \
  "ftelephony/report/my_tickets/my_tickets.json" \
  "ftelephony/report/my_tickets/my_tickets.json"

cp_from_container \
  "ftelephony/report/my_tickets/my_tickets.py" \
  "ftelephony/report/my_tickets/my_tickets.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/tickets_assigned_to_partner/__init__.py" \
  "ftelephony/report/tickets_assigned_to_partner/__init__.py"

cp_from_container \
  "ftelephony/report/tickets_assigned_to_partner/tickets_assigned_to_partner.js" \
  "ftelephony/report/tickets_assigned_to_partner/tickets_assigned_to_partner.js"

cp_from_container \
  "ftelephony/report/tickets_assigned_to_partner/tickets_assigned_to_partner.json" \
  "ftelephony/report/tickets_assigned_to_partner/tickets_assigned_to_partner.json"

cp_from_container \
  "ftelephony/report/tickets_assigned_to_partner/tickets_assigned_to_partner.py" \
  "ftelephony/report/tickets_assigned_to_partner/tickets_assigned_to_partner.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/partner_archived_tickets/__init__.py" \
  "ftelephony/report/partner_archived_tickets/__init__.py"

cp_from_container \
  "ftelephony/report/partner_archived_tickets/partner_archived_tickets.js" \
  "ftelephony/report/partner_archived_tickets/partner_archived_tickets.js"

cp_from_container \
  "ftelephony/report/partner_archived_tickets/partner_archived_tickets.json" \
  "ftelephony/report/partner_archived_tickets/partner_archived_tickets.json"

cp_from_container \
  "ftelephony/report/partner_archived_tickets/partner_archived_tickets.py" \
  "ftelephony/report/partner_archived_tickets/partner_archived_tickets.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/telectro_assignment_handoff_audit/__init__.py" \
  "ftelephony/report/telectro_assignment_handoff_audit/__init__.py"

cp_from_container \
  "ftelephony/report/telectro_assignment_handoff_audit/telectro_assignment_handoff_audit.json" \
  "ftelephony/report/telectro_assignment_handoff_audit/telectro_assignment_handoff_audit.json"

cp_from_container \
  "ftelephony/report/telectro_assignment_handoff_audit/telectro_assignment_handoff_audit.py" \
  "ftelephony/report/telectro_assignment_handoff_audit/telectro_assignment_handoff_audit.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/telectro_repeat_faults_by_location/__init__.py" \
  "ftelephony/report/telectro_repeat_faults_by_location/__init__.py"

cp_from_container \
  "ftelephony/report/telectro_repeat_faults_by_location/telectro_repeat_faults_by_location.js" \
  "ftelephony/report/telectro_repeat_faults_by_location/telectro_repeat_faults_by_location.js"

cp_from_container \
  "ftelephony/report/telectro_repeat_faults_by_location/telectro_repeat_faults_by_location.json" \
  "ftelephony/report/telectro_repeat_faults_by_location/telectro_repeat_faults_by_location.json"

cp_from_container \
  "ftelephony/report/telectro_repeat_faults_by_location/telectro_repeat_faults_by_location.py" \
  "ftelephony/report/telectro_repeat_faults_by_location/telectro_repeat_faults_by_location.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/tickets_submitted_by_partner/__init__.py" \
  "ftelephony/report/tickets_submitted_by_partner/__init__.py"

cp_from_container \
  "ftelephony/report/tickets_submitted_by_partner/tickets_submitted_by_partner.js" \
  "ftelephony/report/tickets_submitted_by_partner/tickets_submitted_by_partner.js"

cp_from_container \
  "ftelephony/report/tickets_submitted_by_partner/tickets_submitted_by_partner.json" \
  "ftelephony/report/tickets_submitted_by_partner/tickets_submitted_by_partner.json"

cp_from_container \
  "ftelephony/report/tickets_submitted_by_partner/tickets_submitted_by_partner.py" \
  "ftelephony/report/tickets_submitted_by_partner/tickets_submitted_by_partner.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/supervisor_active_work_by_bucket/__init__.py" \
  "ftelephony/report/supervisor_active_work_by_bucket/__init__.py"

cp_from_container \
  "ftelephony/report/supervisor_active_work_by_bucket/supervisor_active_work_by_bucket.py" \
  "ftelephony/report/supervisor_active_work_by_bucket/supervisor_active_work_by_bucket.py"

cp_from_container \
  "ftelephony/report/supervisor_active_work_by_bucket/supervisor_active_work_by_bucket.json" \
  "ftelephony/report/supervisor_active_work_by_bucket/supervisor_active_work_by_bucket.json"

cp_from_container \
  "ftelephony/report/supervisor_active_work_by_bucket/supervisor_active_work_by_bucket.js" \
  "ftelephony/report/supervisor_active_work_by_bucket/supervisor_active_work_by_bucket.js"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/supervisor_active_work_by_owner_bucket/__init__.py" \
  "ftelephony/report/supervisor_active_work_by_owner_bucket/__init__.py"

cp_from_container \
  "ftelephony/report/supervisor_active_work_by_owner_bucket/supervisor_active_work_by_owner_bucket.py" \
  "ftelephony/report/supervisor_active_work_by_owner_bucket/supervisor_active_work_by_owner_bucket.py"

cp_from_container \
  "ftelephony/report/supervisor_active_work_by_owner_bucket/supervisor_active_work_by_owner_bucket.json" \
  "ftelephony/report/supervisor_active_work_by_owner_bucket/supervisor_active_work_by_owner_bucket.json"

cp_from_container \
  "ftelephony/report/supervisor_active_work_by_owner_bucket/supervisor_active_work_by_owner_bucket.js" \
  "ftelephony/report/supervisor_active_work_by_owner_bucket/supervisor_active_work_by_owner_bucket.js"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/supervisor_team_load_snapshot/__init__.py" \
  "ftelephony/report/supervisor_team_load_snapshot/__init__.py"

cp_from_container \
  "ftelephony/report/supervisor_team_load_snapshot/supervisor_team_load_snapshot.py" \
  "ftelephony/report/supervisor_team_load_snapshot/supervisor_team_load_snapshot.py"

cp_from_container \
  "ftelephony/report/supervisor_team_load_snapshot/supervisor_team_load_snapshot.json" \
  "ftelephony/report/supervisor_team_load_snapshot/supervisor_team_load_snapshot.json"

cp_from_container \
  "ftelephony/report/supervisor_team_load_snapshot/supervisor_team_load_snapshot.js" \
  "ftelephony/report/supervisor_team_load_snapshot/supervisor_team_load_snapshot.js"
# --------------------------------------------------------------------
cp_from_container \
  "ftelephony/report/supervisor_team_snapshot/__init__.py" \
  "ftelephony/report/supervisor_team_snapshot/__init__.py"
cp_from_container \
  "ftelephony/report/supervisor_team_snapshot/supervisor_team_snapshot.json" \
  "ftelephony/report/supervisor_team_snapshot/supervisor_team_snapshot.json"
cp_from_container \
  "ftelephony/report/supervisor_team_snapshot/supervisor_team_snapshot.js" \
  "ftelephony/report/supervisor_team_snapshot/supervisor_team_snapshot.js"
cp_from_container \
  "ftelephony/report/supervisor_team_snapshot/supervisor_team_snapshot.py" \
  "ftelephony/report/supervisor_team_snapshot/supervisor_team_snapshot.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/report/unclaimed_over_1_day/__init__.py" \
  "ftelephony/report/unclaimed_over_1_day/__init__.py"

cp_from_container \
  "ftelephony/report/unclaimed_over_1_day/unclaimed_over_1_day.js" \
  "ftelephony/report/unclaimed_over_1_day/unclaimed_over_1_day.js"

cp_from_container \
  "ftelephony/report/unclaimed_over_1_day/unclaimed_over_1_day.json" \
  "ftelephony/report/unclaimed_over_1_day/unclaimed_over_1_day.json"

cp_from_container \
  "ftelephony/report/unclaimed_over_1_day/unclaimed_over_1_day.py" \
  "ftelephony/report/unclaimed_over_1_day/unclaimed_over_1_day.py"
# --------------------------------------------------------------------

# Standard page files
mirror_dir_from_container "ftelephony/page" "ftelephony/page"
# -----------------------------page---------------------------------------
cp_optional_from_container \
  "ftelephony/page/partner_request/__init__.py" \
  "ftelephony/page/partner_request/__init__.py"

cp_from_container \
  "ftelephony/page/partner_request/partner_request.js" \
  "ftelephony/page/partner_request/partner_request.js"

cp_from_container \
  "ftelephony/page/partner_request/partner_request.json" \
  "ftelephony/page/partner_request/partner_request.json"

cp_from_container \
  "ftelephony/page/partner_request/partner_request.py" \
  "ftelephony/page/partner_request/partner_request.py"
# --------------------------------------------------------------------
cp_optional_from_container \
  "ftelephony/page/partner_ticket/__init__.py" \
  "ftelephony/page/partner_ticket/__init__.py"

cp_from_container \
  "ftelephony/page/partner_ticket/partner_ticket.js" \
  "ftelephony/page/partner_ticket/partner_ticket.js"

cp_from_container \
  "ftelephony/page/partner_ticket/partner_ticket.json" \
  "ftelephony/page/partner_ticket/partner_ticket.json"

cp_from_container \
  "ftelephony/page/partner_ticket/partner_ticket.py" \
  "ftelephony/page/partner_ticket/partner_ticket.py"
# --------------------------------------------------------------------
# --- workspace api ---
cp_from_container "api/workspace.py" "api/workspace.py"
#  --- ops_kpis ---
cp_from_container "ops_kpis.py" "ops_kpis.py"
# --- overrides we care about ---
cp_from_container "overrides/assign_to.py" "overrides/assign_to.py"
cp_from_container "overrides/query_report.py" "overrides/query_report.py"

# --- core telephony pilot logic ---
cp_from_container "telectro_round_robin.py" "telectro_round_robin.py"
cp_from_container "telectro_claim.py" "telectro_claim.py"
cp_from_container "telectro_intake.py" "telectro_intake.py"
cp_from_container "telectro_site_guard.py" "telectro_site_guard.py"
cp_from_container "telectro_assign_sync.py" "telectro_assign_sync.py"
cp_from_container "telectro_ticket_routing.py" "telectro_ticket_routing.py"
cp_from_container "telectro_ticket_edit_guard.py" "telectro_ticket_edit_guard.py"
cp_from_container "telectro_reassign_on_update.py" "telectro_reassign_on_update.py"

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
cp_from_container "scripts/backfill_stage_a_v2_recent.py" "backfill_stage_a_v2_recent.py"
cp_from_container "scripts/harness_customer_from_sender.py" "scripts/harness_customer_from_sender.py"
cp_from_container "scripts/verify_stage_c_matrix.py" "scripts/verify_stage_c_matrix.py"
cp_from_container "scripts/stage_g_status.py" "scripts/stage_g_status.py"
cp_from_container "scripts/debug_location_map.py" "scripts/debug_location_map.py"
cp_from_container "scripts/repair_kmz_location_names.py" "scripts/repair_kmz_location_names.py"
cp_from_container "scripts/proof_report_my_hd_tickets.py" "scripts/proof_report_my_hd_tickets.py"
cp_from_container "scripts/proof_mail_health.py" "scripts/proof_mail_health.py"
cp_from_container "scripts/proof_pull_pilot_inboxes.py" "scripts/proof_pull_pilot_inboxes.py"
cp_from_container "scripts/proof_runtime_state.py" "scripts/proof_runtime_state.py"


# --- jobs (explicit: avoid docker cp directory nesting) ---
cp_from_container "jobs/__init__.py" "jobs/__init__.py"
cp_from_container "jobs/pull_pilot_inboxes.py" "jobs/pull_pilot_inboxes.py"
cp_from_container "scripts/job_status_pull_pilot_inboxes.py" "scripts/job_status_pull_pilot_inboxes.py"
cp_from_container "scripts/proof_stage_a_v2.py" "scripts/proof_stage_a_v2.py"


# --- notification guard ---
cp_from_container "monkey_patches/notification_log_guard.py" "monkey_patches/notification_log_guard.py"

# --- datetime guard ---
cp_from_container "public/js/telectro_datetime_guard.js" "public/js/telectro_datetime_guard.js"

# --- telectro_ ops_workspace ---
cp_from_container "public/js/telectro_ops_workspace.js" "public/js/telectro_ops_workspace.js"

# --- telectro_home_redirect ---
cp_from_container "public/js/telectro_home_redirect.js" "public/js/telectro_home_redirect.js"

# --- partner_acceptance_review ---
cp_from_container "public/js/partner_acceptance_review.js" "public/js/partner_acceptance_review.js"

# --- handoff actions ---
cp_from_container "public/js/telectro_handoff_action.js" "public/js/telectro_handoff_action.js"

# --- app config (fixtures, includes, doc_events, overrides) ---
cp_from_container "hooks.py" "hooks.py"

# --- fixtures directory (export-fixtures output) ---
cp_from_container "fixtures" "fixtures"

# --- main directory files ---
cp_optional_from_container "partner_create.py" "partner_create.py"

# --- partner permissions ---
cp_from_container "permissions.py" "permissions.py"

# -- partner kpis ---
cp_from_container "partner_kpis.py" "partner_kpis.py"

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
