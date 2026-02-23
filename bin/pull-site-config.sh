#!/usr/bin/env bash
set -euo pipefail
trap 'echo "❌ pull-site-config failed on line $LINENO" >&2' ERR

docker compose ps backend >/dev/null

SRC_COMMON="backend:/home/frappe/frappe-bench/sites/common_site_config.json"
DST_DIR="ops/site-config"
DST_FILE="${DST_DIR}/common_site_config.json"

mkdir -p "${DST_DIR}"

echo "→ ${DST_FILE}"
docker compose cp "${SRC_COMMON}" "${DST_FILE}"

echo
echo "✅ Pulled common_site_config.json (review before committing)."
echo
git status --porcelain || true