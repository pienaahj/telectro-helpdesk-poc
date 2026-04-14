#!/usr/bin/env bash
set -euo pipefail

echo "==> Exporting fixtures from backend container..."
docker compose exec -T backend bash -lc '
  set -euo pipefail
  cd /home/frappe/frappe-bench
  bench --site frontend export-fixtures
  cd apps/telephony/telephony/fixtures
  echo "=== fixtures dir ==="
  ls -la
'
echo "==> Fixture export complete."