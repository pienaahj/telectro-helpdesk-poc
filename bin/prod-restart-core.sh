#!/usr/bin/env bash
set -euo pipefail

# Guarded production core restart wrapper.
#
# This script restarts the core production application services through
# bin/prod-compose.sh.
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
#   CONFIRM_PROD_RESTART=restart-core ./bin/prod-restart-core.sh
#
# Optional overrides:
#
#   BACKEND_SVC=backend \
#   FRONTEND_SVC=frontend \
#   WEBSOCKET_SVC=websocket \
#   SCHEDULER_SVC=scheduler \
#   QUEUE_LONG_SVC=queue-long \
#   QUEUE_SHORT_SVC=queue-short \
#   CONFIRM_PROD_RESTART=restart-core \
#   ./bin/prod-restart-core.sh

CONFIRM_PROD_RESTART="${CONFIRM_PROD_RESTART:-}"

BACKEND_SVC="${BACKEND_SVC:-backend}"
FRONTEND_SVC="${FRONTEND_SVC:-frontend}"
WEBSOCKET_SVC="${WEBSOCKET_SVC:-websocket}"
SCHEDULER_SVC="${SCHEDULER_SVC:-scheduler}"
QUEUE_LONG_SVC="${QUEUE_LONG_SVC:-queue-long}"
QUEUE_SHORT_SVC="${QUEUE_SHORT_SVC:-queue-short}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() {
  printf "\nERROR: %s\n\n" "$*" >&2
  exit 1
}

log() {
  printf "\n==> %s\n" "$*" >&2
}

[[ "$CONFIRM_PROD_RESTART" == "restart-core" ]] || die "Refusing to restart production core services. Re-run with CONFIRM_PROD_RESTART=restart-core"

cd "$ROOT_DIR"

[[ -x ./bin/prod-compose.sh ]] || die "Missing executable ./bin/prod-compose.sh"

log "Restarting production core services"
printf '%s\n' \
  "$BACKEND_SVC" \
  "$WEBSOCKET_SVC" \
  "$QUEUE_LONG_SVC" \
  "$QUEUE_SHORT_SVC" \
  "$SCHEDULER_SVC" \
  "$FRONTEND_SVC" \
  | sed 's/^/ - /'

exec ./bin/prod-compose.sh restart \
  "$BACKEND_SVC" \
  "$WEBSOCKET_SVC" \
  "$QUEUE_LONG_SVC" \
  "$QUEUE_SHORT_SVC" \
  "$SCHEDULER_SVC" \
  "$FRONTEND_SVC"
