#!/usr/bin/env bash
set -euo pipefail

SITE_HEADER="${SITE_HEADER:-frontend}"

say() { printf "\n== %s ==\n" "$*"; }

say "compose ps"
docker compose ps

say "backend ping (inside container)"
docker compose exec -T backend bash -lc \
  "curl -fsS -H 'X-Frappe-Site-Name: ${SITE_HEADER}' http://localhost:8000/api/method/ping >/dev/null && echo PING_OK"

say "helpdesk/telephony importable (venv python)"
docker compose exec -T backend bash -lc '
set -euo pipefail
cd /home/frappe/frappe-bench
./env/bin/python -c "import helpdesk, telephony; print(\"IMPORTS_OK\")"
'

say "scheduler/queues running?"
for svc in scheduler queue-short queue-long; do
  state="$(docker inspect "$(docker compose ps -q "$svc")" --format "{{.State.Status}}" 2>/dev/null || true)"
  echo "$svc: ${state:-unknown}"
done

say "mail reachability from backend container"
docker compose exec -T backend bash -lc "timeout 2 bash -c '</dev/tcp/mail/143' && echo IMAP_OK || (echo IMAP_FAIL && exit 1)"
docker compose exec -T backend bash -lc "timeout 2 bash -c '</dev/tcp/mail/587' && echo SMTP_OK || (echo SMTP_FAIL && exit 1)"

say "init jobs (expected to be exited)"
docker compose ps -a | awk '/configurator|create-site/ {print}'

echo
echo "pilot-check: OK"
