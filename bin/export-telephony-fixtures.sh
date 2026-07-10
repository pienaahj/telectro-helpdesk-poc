#!/usr/bin/env bash
set -euo pipefail

APP_NAME="telephony"
SITE_NAME="frontend"
SERVICE_NAME="backend"

CONTAINER_BENCH_DIR="/home/frappe/frappe-bench"
CONTAINER_FIXTURES_DIR="${CONTAINER_BENCH_DIR}/apps/${APP_NAME}/${APP_NAME}/fixtures"
HOST_FIXTURES_DIR="apps/${APP_NAME}/${APP_NAME}/fixtures"

echo "==> Exporting fixtures from ${SERVICE_NAME} container..."

docker compose exec -T "${SERVICE_NAME}" bash -lc "
  set -euo pipefail

  cd '${CONTAINER_BENCH_DIR}'

  echo '=== exporting fixtures ==='
  bench --site '${SITE_NAME}' export-fixtures

  echo
  echo '=== container fixtures dir ==='
  cd '${CONTAINER_FIXTURES_DIR}'
  ls -la

  echo
  echo '=== container hd_team.json summary ==='
  python - <<'PY'
import json
from pathlib import Path

path = Path('hd_team.json')

if not path.exists():
    print('hd_team.json not found')
    raise SystemExit(0)

data = json.loads(path.read_text())

print('count:', len(data))
for row in data:
    print(row.get('name'), 'users:', [u.get('user') for u in row.get('users', [])])
PY
"

echo
echo "==> Copying exported fixtures back to host repo..."

mkdir -p "${HOST_FIXTURES_DIR}"

docker compose cp \
  "${SERVICE_NAME}:${CONTAINER_FIXTURES_DIR}/." \
  "${HOST_FIXTURES_DIR}/"

echo
echo "==> Host hd_team.json summary..."

python3 - <<'PY'
import json
from pathlib import Path

path = Path('apps/telephony/telephony/fixtures/hd_team.json')

if not path.exists():
    print('host hd_team.json not found')
    raise SystemExit(1)

data = json.loads(path.read_text())

print('count:', len(data))
for row in data:
    print(row.get('name'), 'users:', [u.get('user') for u in row.get('users', [])])
PY

echo
echo "==> Fixture export complete."