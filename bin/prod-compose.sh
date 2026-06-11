#!/usr/bin/env bash
set -euo pipefail

# Production-safe Docker Compose wrapper.
#
# This script does not start, stop, or mutate anything by itself.
# It only standardizes the Compose command and production file set.
#
# Usage examples:
#
#   ./bin/prod-compose.sh config
#   ./bin/prod-compose.sh ps
#   ./bin/prod-compose.sh up -d
#   ./bin/prod-compose.sh logs --tail=100 backend
#
# Override if needed:
#
#   COMPOSE="docker compose" ./bin/prod-compose.sh config
#   PROD_ENV_FILE=/secure/path/.env.production ./bin/prod-compose.sh config

COMPOSE="${COMPOSE:-docker compose}"
PROD_ENV_FILE="${PROD_ENV_FILE:-.env.production}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() {
  printf "\nERROR: %s\n\n" "$*" >&2
  exit 1
}

log() {
  printf "\n==> %s\n" "$*" >&2
}

cd "$ROOT_DIR"

[[ -f "compose.yaml" ]] || die "Missing compose.yaml in $ROOT_DIR"
[[ -f "compose.production.yaml" ]] || die "Missing compose.production.yaml in $ROOT_DIR"
[[ -f "$PROD_ENV_FILE" ]] || die "Missing production env file: $PROD_ENV_FILE"

if ! command -v docker >/dev/null 2>&1; then
  die "docker command not found"
fi

if ! $COMPOSE version >/dev/null 2>&1; then
  die "Compose command failed: $COMPOSE version"
fi

log "Using Compose: $COMPOSE"
log "Using env file: $PROD_ENV_FILE"

# shellcheck disable=SC2086
exec $COMPOSE \
  --env-file "$PROD_ENV_FILE" \
  -f compose.yaml \
  -f compose.production.yaml \
  "$@"