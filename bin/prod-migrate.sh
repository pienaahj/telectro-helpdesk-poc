#!/usr/bin/env bash
set -euo pipefail

# Production migration wrapper.
#
# This script runs `bench --site <site> migrate` inside the production backend
# container through bin/prod-bench.sh.
#
# It records replay-safe migration evidence before and after the command.
#
# It intentionally does not use:
#
# - .env
# - .env.local
# - pwd.yml
# - compose.override.yaml
# - plain docker compose
#
# Required:
#
#   SITE=<production-site-name>
#   RELEASE_ID=<release-id>
#
# Optional overrides:
#
#   EVIDENCE_DIR=/opt/telectro/erpnext/deploy-evidence
#   PROD_BENCH=/custom/path/prod-bench.sh
#   STATE_WRITER=/custom/path/write-release-state.py
#   DATE_BIN=/custom/path/date
#
# Usage:
#
#   SITE=erp.telectro.co.za \
#   RELEASE_ID=20260724-0690c32 \
#     ./bin/prod-migrate.sh

umask 077

SITE="${SITE:-}"
RELEASE_ID="${RELEASE_ID:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

EVIDENCE_DIR="${EVIDENCE_DIR:-$(dirname "$ROOT_DIR")/deploy-evidence}"
PROD_BENCH="${PROD_BENCH:-${ROOT_DIR}/bin/prod-bench.sh}"
STATE_WRITER="${STATE_WRITER:-${ROOT_DIR}/bin/write-release-state.py}"
DATE_BIN="${DATE_BIN:-date}"

RELEASE_DIR="${EVIDENCE_DIR}/releases/${RELEASE_ID}"
MIGRATION_DIR="${RELEASE_DIR}/production-migration"

STARTED_RECORD="$MIGRATION_DIR/migration-started.env"
COMPLETED_RECORD="$MIGRATION_DIR/migration-completed.env"
FAILED_RECORD="$MIGRATION_DIR/migration-failed.env"
REVIEW_RECORD="$MIGRATION_DIR/migration-review-required.env"
OUTPUT_LOG="$MIGRATION_DIR/migration-output.log"

die() {
  printf '\nERROR: %s\n\n' "$*" >&2
  exit 1
}

log() {
  printf '\n==> %s\n' "$*" >&2
}

utc_now() {
  "$DATE_BIN" -u '+%Y-%m-%dT%H:%M:%SZ'
}

write_started_record() {
  local started_utc="$1"

  "$STATE_WRITER" \
    --output "$STARTED_RECORD" \
    --allowed-key RELEASE_ID \
    --allowed-key SITE \
    --allowed-key MIGRATION_STATE \
    --allowed-key MIGRATION_STARTED_UTC \
    --allowed-key MIGRATION_OUTPUT_LOG \
    --required-key RELEASE_ID \
    --required-key SITE \
    --required-key MIGRATION_STATE \
    --required-key MIGRATION_STARTED_UTC \
    --required-key MIGRATION_OUTPUT_LOG \
    --field "RELEASE_ID=$RELEASE_ID" \
    --field "SITE=$SITE" \
    --field 'MIGRATION_STATE=STARTED' \
    --field "MIGRATION_STARTED_UTC=$started_utc" \
    --field "MIGRATION_OUTPUT_LOG=$OUTPUT_LOG"
}

write_final_record() {
  local output="$1"
  local state="$2"
  local started_utc="$3"
  local finished_utc="$4"
  local exit_status="$5"

  "$STATE_WRITER" \
    --output "$output" \
    --allowed-key RELEASE_ID \
    --allowed-key SITE \
    --allowed-key MIGRATION_STATE \
    --allowed-key MIGRATION_STARTED_UTC \
    --allowed-key MIGRATION_FINISHED_UTC \
    --allowed-key MIGRATION_EXIT_STATUS \
    --allowed-key MIGRATION_OUTPUT_LOG \
    --required-key RELEASE_ID \
    --required-key SITE \
    --required-key MIGRATION_STATE \
    --required-key MIGRATION_STARTED_UTC \
    --required-key MIGRATION_FINISHED_UTC \
    --required-key MIGRATION_EXIT_STATUS \
    --required-key MIGRATION_OUTPUT_LOG \
    --field "RELEASE_ID=$RELEASE_ID" \
    --field "SITE=$SITE" \
    --field "MIGRATION_STATE=$state" \
    --field "MIGRATION_STARTED_UTC=$started_utc" \
    --field "MIGRATION_FINISHED_UTC=$finished_utc" \
    --field "MIGRATION_EXIT_STATUS=$exit_status" \
    --field "MIGRATION_OUTPUT_LOG=$OUTPUT_LOG"
}

write_review_record() {
  local reason="$1"
  local review_utc="$2"
  local migration_exit_status="$3"
  local output_capture_status="$4"

  "$STATE_WRITER" \
    --output "$REVIEW_RECORD" \
    --allowed-key RELEASE_ID \
    --allowed-key SITE \
    --allowed-key MIGRATION_STATE \
    --allowed-key MIGRATION_STARTED_UTC \
    --allowed-key MIGRATION_REVIEW_UTC \
    --allowed-key MIGRATION_EXIT_STATUS \
    --allowed-key MIGRATION_OUTPUT_CAPTURE_STATUS \
    --allowed-key MIGRATION_OUTPUT_LOG \
    --allowed-key MIGRATION_REVIEW_REASON \
    --required-key RELEASE_ID \
    --required-key SITE \
    --required-key MIGRATION_STATE \
    --required-key MIGRATION_STARTED_UTC \
    --required-key MIGRATION_REVIEW_UTC \
    --required-key MIGRATION_EXIT_STATUS \
    --required-key MIGRATION_OUTPUT_CAPTURE_STATUS \
    --required-key MIGRATION_OUTPUT_LOG \
    --required-key MIGRATION_REVIEW_REASON \
    --field "RELEASE_ID=$RELEASE_ID" \
    --field "SITE=$SITE" \
    --field 'MIGRATION_STATE=REVIEW_REQUIRED' \
    --field "MIGRATION_STARTED_UTC=$MIGRATION_STARTED_UTC" \
    --field "MIGRATION_REVIEW_UTC=$review_utc" \
    --field "MIGRATION_EXIT_STATUS=$migration_exit_status" \
    --field "MIGRATION_OUTPUT_CAPTURE_STATUS=$output_capture_status" \
    --field "MIGRATION_OUTPUT_LOG=$OUTPUT_LOG" \
    --field "MIGRATION_REVIEW_REASON=$reason"
}

write_timestamp_failure_review_record() {
  local timestamp_status="$1"

  "$STATE_WRITER" \
    --output "$REVIEW_RECORD" \
    --allowed-key RELEASE_ID \
    --allowed-key SITE \
    --allowed-key MIGRATION_STATE \
    --allowed-key MIGRATION_STARTED_UTC \
    --allowed-key MIGRATION_REVIEW_UTC \
    --allowed-key MIGRATION_EXIT_STATUS \
    --allowed-key MIGRATION_OUTPUT_CAPTURE_STATUS \
    --allowed-key MIGRATION_TIMESTAMP_STATUS \
    --allowed-key MIGRATION_OUTPUT_LOG \
    --allowed-key MIGRATION_REVIEW_REASON \
    --required-key RELEASE_ID \
    --required-key SITE \
    --required-key MIGRATION_STATE \
    --required-key MIGRATION_STARTED_UTC \
    --required-key MIGRATION_REVIEW_UTC \
    --required-key MIGRATION_EXIT_STATUS \
    --required-key MIGRATION_OUTPUT_CAPTURE_STATUS \
    --required-key MIGRATION_TIMESTAMP_STATUS \
    --required-key MIGRATION_OUTPUT_LOG \
    --required-key MIGRATION_REVIEW_REASON \
    --field "RELEASE_ID=$RELEASE_ID" \
    --field "SITE=$SITE" \
    --field 'MIGRATION_STATE=REVIEW_REQUIRED' \
    --field "MIGRATION_STARTED_UTC=$MIGRATION_STARTED_UTC" \
    --field 'MIGRATION_REVIEW_UTC=UNAVAILABLE' \
    --field "MIGRATION_EXIT_STATUS=$MIGRATION_EXIT_STATUS" \
    --field "MIGRATION_OUTPUT_CAPTURE_STATUS=$OUTPUT_CAPTURE_STATUS" \
    --field "MIGRATION_TIMESTAMP_STATUS=$timestamp_status" \
    --field "MIGRATION_OUTPUT_LOG=$OUTPUT_LOG" \
    --field 'MIGRATION_REVIEW_REASON=FINISHED_TIMESTAMP_FAILED'
}

report_review_record_result() {
  local review_record_status="$1"

  if [[ "$review_record_status" -eq 0 ]]; then
    printf '%s\n' \
      "MIGRATION_REVIEW_RECORD=$REVIEW_RECORD" \
      >&2
  else
    printf '%s\n' \
      "MIGRATION_REVIEW_RECORD_STATUS=$review_record_status" \
      'MIGRATION_REVIEW_RECORD_FAILED=YES' \
      >&2
  fi
}

[[ -n "$SITE" ]] || {
  die "SITE is required. Example: SITE=erp.telectro.co.za RELEASE_ID=<release-id> ./bin/prod-migrate.sh"
}

[[ -n "$RELEASE_ID" ]] || {
  die "RELEASE_ID is required. Example: SITE=$SITE RELEASE_ID=<release-id> ./bin/prod-migrate.sh"
}

[[ "$RELEASE_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || {
  die "RELEASE_ID contains unsafe characters: $RELEASE_ID"
}

cd "$ROOT_DIR"

[[ -x "$PROD_BENCH" ]] || {
  die "Production Bench wrapper is missing or not executable: $PROD_BENCH"
}

[[ -x "$STATE_WRITER" ]] || {
  die "Release-state writer is missing or not executable: $STATE_WRITER"
}

command -v "$DATE_BIN" >/dev/null 2>&1 || {
  die "UTC timestamp command was not found: $DATE_BIN"
}

mkdir -p "$RELEASE_DIR"

if ! mkdir "$MIGRATION_DIR"; then
  if [[ -e "$MIGRATION_DIR" ]]; then
    die "Migration evidence already exists; automatic replay is prohibited: $MIGRATION_DIR"
  fi

  die "Unable to claim the migration evidence directory: $MIGRATION_DIR"
fi

chmod 700 "$MIGRATION_DIR"

MIGRATION_STARTED_UTC="$(utc_now)"

set +e

write_started_record "$MIGRATION_STARTED_UTC"

STARTED_RECORD_STATUS=$?

set -e

if [[ "$STARTED_RECORD_STATUS" -ne 0 ]]; then
  set +e

  rmdir "$MIGRATION_DIR"

  START_CLAIM_RELEASE_STATUS=$?

  set -e

  if [[ "$START_CLAIM_RELEASE_STATUS" -eq 0 ]]; then
    printf '%s\n' \
      'MIGRATION_START_CLAIM_RELEASED=YES' \
      >&2
  else
    printf '%s\n' \
      "MIGRATION_START_CLAIM_RELEASE_STATUS=$START_CLAIM_RELEASE_STATUS" \
      'MIGRATION_START_CLAIM_RELEASED=NO' \
      'MIGRATION_REVIEW_REQUIRED=YES' \
      >&2
  fi

  exit "$STARTED_RECORD_STATUS"
fi

log "Running production migration"
log "Release ID: $RELEASE_ID"
log "Site: $SITE"
log "Evidence directory: $MIGRATION_DIR"
log "Migration output: $OUTPUT_LOG"

set +e

"$PROD_BENCH" \
  --site "$SITE" \
  migrate \
  2>&1 |
  tee "$OUTPUT_LOG"

PIPELINE_STATUS=("${PIPESTATUS[@]}")
MIGRATION_EXIT_STATUS="${PIPELINE_STATUS[0]}"
OUTPUT_CAPTURE_STATUS="${PIPELINE_STATUS[1]}"

set -e

set +e

MIGRATION_FINISHED_UTC="$(utc_now)"

MIGRATION_TIMESTAMP_STATUS=$?

set -e

if [[ "$MIGRATION_TIMESTAMP_STATUS" -ne 0 ]]; then
  set +e

  write_timestamp_failure_review_record \
    "$MIGRATION_TIMESTAMP_STATUS"

  REVIEW_RECORD_STATUS=$?

  set -e

  printf '%s\n' \
    "MIGRATION_EXIT_STATUS=$MIGRATION_EXIT_STATUS" \
    "MIGRATION_OUTPUT_CAPTURE_STATUS=$OUTPUT_CAPTURE_STATUS" \
    "MIGRATION_TIMESTAMP_STATUS=$MIGRATION_TIMESTAMP_STATUS" \
    'MIGRATION_FINISHED_TIMESTAMP_FAILED=YES' \
    'MIGRATION_REVIEW_REQUIRED=YES' \
    >&2

  report_review_record_result "$REVIEW_RECORD_STATUS"

  exit "$MIGRATION_TIMESTAMP_STATUS"
fi

if [[ "$OUTPUT_CAPTURE_STATUS" -ne 0 ]]; then
  set +e

  write_review_record \
    "OUTPUT_CAPTURE_FAILED" \
    "$MIGRATION_FINISHED_UTC" \
    "$MIGRATION_EXIT_STATUS" \
    "$OUTPUT_CAPTURE_STATUS"

  REVIEW_RECORD_STATUS=$?

  set -e

  printf '%s\n' \
    "MIGRATION_EXIT_STATUS=$MIGRATION_EXIT_STATUS" \
    "MIGRATION_OUTPUT_CAPTURE_STATUS=$OUTPUT_CAPTURE_STATUS" \
    'MIGRATION_OUTPUT_CAPTURE_FAILED=YES' \
    'MIGRATION_REVIEW_REQUIRED=YES' \
    >&2

  report_review_record_result "$REVIEW_RECORD_STATUS"

  exit "$OUTPUT_CAPTURE_STATUS"
fi

if [[ "$MIGRATION_EXIT_STATUS" -eq 0 ]]; then
  set +e

  write_final_record \
    "$COMPLETED_RECORD" \
    "COMPLETED" \
    "$MIGRATION_STARTED_UTC" \
    "$MIGRATION_FINISHED_UTC" \
    "$MIGRATION_EXIT_STATUS"

  FINAL_RECORD_STATUS=$?

  set -e

  if [[ "$FINAL_RECORD_STATUS" -ne 0 ]]; then
    set +e

    write_review_record \
      "COMPLETED_ACTION_EVIDENCE_COMMIT_FAILED" \
      "$MIGRATION_FINISHED_UTC" \
      "$MIGRATION_EXIT_STATUS" \
      "$OUTPUT_CAPTURE_STATUS"

    REVIEW_RECORD_STATUS=$?

    set -e

    printf '%s\n' \
      'MIGRATION_ACTION_COMPLETED=YES' \
      'MIGRATION_EVIDENCE_COMMIT_FAILED=YES' \
      'MIGRATION_REVIEW_REQUIRED=YES' \
      >&2

    report_review_record_result "$REVIEW_RECORD_STATUS"

    exit "$FINAL_RECORD_STATUS"
  fi

  printf '%s\n' \
    "MIGRATION_OUTPUT_LOG=$OUTPUT_LOG" \
    "MIGRATION_COMPLETED_RECORD=$COMPLETED_RECORD" \
    'PRODUCTION_MIGRATION_COMMAND_OK=YES'

  exit 0
fi

set +e

write_final_record \
  "$FAILED_RECORD" \
  "FAILED" \
  "$MIGRATION_STARTED_UTC" \
  "$MIGRATION_FINISHED_UTC" \
  "$MIGRATION_EXIT_STATUS"

FINAL_RECORD_STATUS=$?

set -e

if [[ "$FINAL_RECORD_STATUS" -ne 0 ]]; then
  set +e

  write_review_record \
    "FAILED_ACTION_EVIDENCE_COMMIT_FAILED" \
    "$MIGRATION_FINISHED_UTC" \
    "$MIGRATION_EXIT_STATUS" \
    "$OUTPUT_CAPTURE_STATUS"

  REVIEW_RECORD_STATUS=$?

  set -e

  printf '%s\n' \
    "MIGRATION_EXIT_STATUS=$MIGRATION_EXIT_STATUS" \
    'MIGRATION_ACTION_FAILED=YES' \
    'MIGRATION_EVIDENCE_COMMIT_FAILED=YES' \
    'MIGRATION_REVIEW_REQUIRED=YES' \
    >&2

  report_review_record_result "$REVIEW_RECORD_STATUS"

  exit "$FINAL_RECORD_STATUS"
fi

printf '%s\n' \
  "MIGRATION_EXIT_STATUS=$MIGRATION_EXIT_STATUS" \
  "MIGRATION_OUTPUT_LOG=$OUTPUT_LOG" \
  "MIGRATION_FAILED_RECORD=$FAILED_RECORD" \
  'PRODUCTION_MIGRATION_COMMAND_OK=NO' \
  >&2

exit "$MIGRATION_EXIT_STATUS"
