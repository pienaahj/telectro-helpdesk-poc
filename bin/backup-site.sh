#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./bin/backup-site.sh              # defaults to SITE=frontend
#   SITE=mysite ./bin/backup-site.sh  # override site name
#
# What it does:
# - Runs a full Frappe site backup (DB + public files + private files)
# - Copies the resulting artifacts to your host under ./backups/<SITE>/
# - Prints the newest backup set so you can confirm it worked
#
# Notes:
# - This is a local/manual helper, not the final production backup system.
# - The ./backups directory contains sensitive data and must not be committed.

SITE="${SITE:-frontend}"

COMPOSE_FILES=(
  -f compose.yaml
  -f compose.local.yaml
  -f compose.override.yaml
)

IN_CONTAINER_DIR="/home/frappe/frappe-bench/sites/${SITE}/private/backups"
HOST_DIR="backups/${SITE}"

echo "== backup-site =="
echo "SITE: ${SITE}"
echo "Host dir: ${HOST_DIR}"
echo "Container dir: ${IN_CONTAINER_DIR}"
echo

mkdir -p "${HOST_DIR}"

echo "== running bench backup (DB + files) =="
docker compose "${COMPOSE_FILES[@]}" exec -T backend bash -lc "
set -euo pipefail
cd /home/frappe/frappe-bench
bench --site '${SITE}' backup --with-files
"

echo
echo "== latest backup artifacts inside container =="
docker compose "${COMPOSE_FILES[@]}" exec -T backend bash -lc "
set -euo pipefail
ls -1t '${IN_CONTAINER_DIR}' | head -n 10
"

echo
echo "== copying backups to host =="
docker compose "${COMPOSE_FILES[@]}" cp "backend:${IN_CONTAINER_DIR}" "${HOST_DIR}/"

echo
echo "== newest backup set on host =="
ls -1t "${HOST_DIR}/backups" | head -n 10

LATEST_DB="$(ls -1t "${HOST_DIR}/backups"/*-database.sql.gz | head -n 1 || true)"
if [[ -n "${LATEST_DB}" ]]; then
  echo
  echo "== gzip integrity check: ${LATEST_DB##*/} =="
  gzip -t "${LATEST_DB}" && echo "gzip ok"
else
  echo
  echo "WARNING: no database gzip found under ${HOST_DIR}/backups"
fi

echo
echo "backup-site: done"