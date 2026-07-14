#!/usr/bin/env bash
set -euo pipefail

# Verify or repair the controlled Workspace visibility policy on production.
#
# Usage:
#
#   ./bin/prod-workspace-visibility.sh check
#   ./bin/prod-workspace-visibility.sh apply
#   ./bin/prod-workspace-visibility.sh evidence
#
# Optional overrides:
#
#   SITE_NAME=erp.telectro.co.za
#   EVIDENCE_DIR=/opt/telectro/erpnext/deploy-evidence
#   PROD_BENCH=/custom/path/prod-bench.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SITE_NAME="${SITE_NAME:-erp.telectro.co.za}"
PROD_BENCH="${PROD_BENCH:-${ROOT_DIR}/bin/prod-bench.sh}"
EVIDENCE_DIR="${EVIDENCE_DIR:-$(dirname "${ROOT_DIR}")/deploy-evidence}"

ACTION="${1:-check}"


die() {
  printf "\nERROR: %s\n\n" "$*" >&2
  exit 1
}


log() {
  printf "\n==> %s\n" "$*" >&2
}


usage() {
  cat <<'EOF'
Usage:
  ./bin/prod-workspace-visibility.sh check
  ./bin/prod-workspace-visibility.sh apply
  ./bin/prod-workspace-visibility.sh evidence

Actions:
  check      Read-only verification. Fails when Workspace visibility drifts.
  apply      Adds missing expected roles and verifies the final state.
  evidence   Runs the read-only check and records timestamped evidence.

Environment overrides:
  SITE_NAME      Frappe site name.
  EVIDENCE_DIR   Directory used for evidence output.
  PROD_BENCH     Path to the production Bench wrapper.
EOF
}


run_method() {
  local method="$1"

  "$PROD_BENCH" \
    --site "$SITE_NAME" \
    execute "$method"
}


[[ "$#" -le 1 ]] || {
  usage >&2
  die "Too many arguments"
}

case "$ACTION" in
  check)
    METHOD="telephony.setup.workspace_visibility.assert_workspace_visibility"
    ;;

  apply)
    METHOD="telephony.setup.workspace_visibility.repair_workspace_visibility"
    ;;

  evidence)
    METHOD="telephony.setup.workspace_visibility.assert_workspace_visibility"
    ;;

  -h|--help|help)
    usage
    exit 0
    ;;

  *)
    usage >&2
    die "Unknown action: $ACTION"
    ;;
esac


cd "$ROOT_DIR"

[[ -x "$PROD_BENCH" ]] || {
  die "Production Bench wrapper is missing or not executable: $PROD_BENCH"
}


case "$ACTION" in
  check)
    log "Checking Workspace visibility"
    log "Site: $SITE_NAME"

    run_method "$METHOD"
    ;;

  apply)
    log "Applying Workspace visibility policy"
    log "Site: $SITE_NAME"

    run_method "$METHOD"
    ;;

  evidence)
    timestamp="$(date -u '+%Y%m%dT%H%M%SZ')"
    safe_site="${SITE_NAME//[^A-Za-z0-9_.-]/_}"

    mkdir -p "$EVIDENCE_DIR"

    evidence_file="${EVIDENCE_DIR}/workspace-visibility-${safe_site}-${timestamp}.txt"

    log "Recording Workspace visibility evidence"
    log "Site: $SITE_NAME"
    log "Evidence file: $evidence_file"

    {
      printf 'Workspace visibility evidence\n'
      printf 'Generated UTC: %s\n' "$timestamp"
      printf 'Site: %s\n' "$SITE_NAME"
      printf 'Action: read-only verification\n'
      printf 'Method: %s\n' "$METHOD"
      printf '\n'

      run_method "$METHOD"
    } 2>&1 | tee "$evidence_file"

    printf '\nEvidence recorded: %s\n' "$evidence_file"
    ;;
esac
