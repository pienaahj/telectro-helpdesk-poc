#!/usr/bin/env bash
set -euo pipefail

# Production migration wrapper.
#
# This script runs `bench --site <site> migrate` inside the production backend
# container through bin/prod-bench.sh.
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
#   SITE=<production-site-name> ./bin/prod-migrate.sh
#
# Example:
#
#   SITE=frontend ./bin/prod-migrate.sh

SITE="${SITE:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() {
  printf "\nERROR: %s\n\n" "$*" >&2
  exit 1
}

log() {
  printf "\n==> %s\n" "$*" >&2
}

[[ -n "$SITE" ]] || die "SITE is required. Example: SITE=frontend ./bin/prod-migrate.sh"

cd "$ROOT_DIR"

[[ -x ./bin/prod-bench.sh ]] || die "Missing executable ./bin/prod-bench.sh"

log "Running production migration for site: $SITE"

exec ./bin/prod-bench.sh --site "$SITE" migrate
