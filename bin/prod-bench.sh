#!/usr/bin/env bash
set -euo pipefail

# Production bench wrapper.
#
# This script runs bench inside the production backend container using the
# production Compose file set via bin/prod-compose.sh.
#
# It intentionally does not use:
#
# - .env
# - .env.local
# - pwd.yml
# - compose.override.yaml
# - plain docker compose
#
# Usage:
#
#   ./bin/prod-bench.sh --site frontend version
#   ./bin/prod-bench.sh --site frontend migrate
#   ./bin/prod-bench.sh --site frontend list-apps
#
# Override if needed:
#
#   BACKEND_SVC=backend ./bin/prod-bench.sh --site frontend version

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

[[ "$#" -gt 0 ]] || die "No bench arguments supplied"

cd "$ROOT_DIR"

[[ -x ./bin/prod-compose.sh ]] || die "Missing executable ./bin/prod-compose.sh"

log "Running production bench command in service: $BACKEND_SVC"
log "Bench directory: $BENCH_DIR"

exec ./bin/prod-compose.sh exec -T -u frappe "$BACKEND_SVC" \
  bash -lc 'cd "$1" && shift && exec bench "$@"' bash "$BENCH_DIR" "$@"