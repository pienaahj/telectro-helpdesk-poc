#!/usr/bin/env bash
set -euo pipefail

# Launch an interactive bench console inside the backend container
# Usage:
#   ./bin/bench-launch.sh

docker compose exec -it backend bash -lc '
  cd /home/frappe/frappe-bench
  exec bench --site frontend console
'
