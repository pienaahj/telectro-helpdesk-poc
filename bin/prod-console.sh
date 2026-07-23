#!/usr/bin/env bash
set -euo pipefail

# Open an interactive Bench console for the production site.
#
# This script uses the production Docker Compose wrapper and intentionally
# preserves the interactive terminal required by `bench console`.
#
# Usage:
#
#   ./bin/prod-console.sh
#
# Optional overrides:
#
#   SITE=erp.telectro.co.za ./bin/prod-console.sh
#   BACKEND_SVC=backend ./bin/prod-console.sh
#   BENCH_DIR=/home/frappe/frappe-bench ./bin/prod-console.sh

SITE="${SITE:-erp.telectro.co.za}"
BACKEND_SVC="${BACKEND_SVC:-backend}"
BENCH_DIR="${BENCH_DIR:-/home/frappe/frappe-bench}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() {
  printf "\nERROR: %s\n\n" "$*" >&2
  exit 1
}

log() {
  printf "\n==> %s\n" "$*" >&2
}

[[ -n "$SITE" ]] || die "SITE must not be empty"
[[ -n "$BACKEND_SVC" ]] || die "BACKEND_SVC must not be empty"
[[ -n "$BENCH_DIR" ]] || die "BENCH_DIR must not be empty"
[[ -t 0 && -t 1 ]] || die "An interactive terminal is required"

cd "$ROOT_DIR"

[[ -x ./bin/prod-compose.sh ]] ||
  die "Missing executable ./bin/prod-compose.sh"

log "Opening production Bench console"
log "Site: $SITE"
log "Backend service: $BACKEND_SVC"
log "Bench directory: $BENCH_DIR"

exec ./bin/prod-compose.sh exec -u frappe "$BACKEND_SVC" \
  bash -lc 'cd "$1" && exec bench --site "$2" console' \
  bash "$BENCH_DIR" "$SITE"
