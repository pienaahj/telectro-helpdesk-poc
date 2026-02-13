#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root (folder containing this script)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Choose compose file automatically:
# - prefer pwd.yml if present (matches the upstream quick stack)
# - else fall back to compose.yaml
if [[ -f "${ROOT_DIR}/pwd.yml" ]]; then
  COMPOSE_FILE="-f ${ROOT_DIR}/pwd.yml"
else
  COMPOSE_FILE="-f ${ROOT_DIR}/compose.yaml"
fi

# Optional: load .env if present (so SITE_NAME/DB creds etc. are available)
ENV_FILE_OPT=""
if [[ -f "${ROOT_DIR}/.env" ]]; then
  ENV_FILE_OPT="--env-file ${ROOT_DIR}/.env"
fi

# Service that runs bench
SERVICE="backend"

# Pass all args to bench (e.g., --site frontend version)
docker compose ${ENV_FILE_OPT} ${COMPOSE_FILE} exec -T "${SERVICE}" bash -lc "bench $*"
