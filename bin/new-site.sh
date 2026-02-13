#!/usr/bin/env bash
set -euo pipefail

# --- pick env file (.env.local wins if present) ---
ENV_FILE=".env"
[[ -f ".env.local" ]] && ENV_FILE=".env.local"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ No $ENV_FILE found. Create one from .env.template and try again."
  echo "   cp .env.template .env  &&  edit secrets and SITE_NAME"
  exit 1
fi

# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

# --- sanity checks ---
need() { var="$1"; [[ -n "${!var:-}" ]] || { echo "❌ Missing $var in $ENV_FILE"; exit 1; }; }
need SITE_NAME
need DB_ROOT_USER
need DB_ROOT_PASSWORD
need ADMIN_PASSWORD

echo "➡️  Creating site (ERPNext): $SITE_NAME"

# Ensure common config points to mariadb service
./bin/bench.sh set-mariadb-host db

# Create the site and install ERPNext (not just frappe)
./bin/bench.sh new-site "$SITE_NAME" \
  --db-root-username "$DB_ROOT_USER" \
  --db-root-password "$DB_ROOT_PASSWORD" \
  --admin-password "$ADMIN_PASSWORD" \
  --install-app erpnext \
  --set-default

# (optional) make it the current site for bench
./bin/bench.sh use "$SITE_NAME" || echo "$SITE_NAME" | docker compose -f compose.yaml exec backend bash -lc 'cat > sites/currentsite.txt'

echo "✅ Site created: $SITE_NAME"
