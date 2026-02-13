#!/usr/bin/env bash
set -euo pipefail

# -------- config (override via env) ----------
COMPOSE="${COMPOSE:-docker compose}"
SITE="${SITE:-frontend}"

BACKEND_SVC="${BACKEND_SVC:-backend}"
FRONTEND_SVC="${FRONTEND_SVC:-frontend}"
WEBSOCKET_SVC="${WEBSOCKET_SVC:-websocket}"
SCHEDULER_SVC="${SCHEDULER_SVC:-scheduler}"
QUEUE_LONG_SVC="${QUEUE_LONG_SVC:-queue-long}"
QUEUE_SHORT_SVC="${QUEUE_SHORT_SVC:-queue-short}"
NEED_BACKEND_RESTART=0

TELEPHONY_REPO="${TELEPHONY_REPO:-https://github.com/frappe/telephony.git}"
TELEPHONY_BRANCH="${TELEPHONY_BRANCH:-develop}"
HELPDESK_REPO="${HELPDESK_REPO:-https://github.com/frappe/helpdesk.git}"
HELPDESK_BRANCH="${HELPDESK_BRANCH:-main}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }
warn(){ printf "\n\033[1;33mWARN:\033[0m %s\n" "$*" >&2; }
die() { printf "\n\033[1;31mERROR:\033[0m %s\n\n" "$*" >&2; exit 1; }

compose() { (cd "$ROOT_DIR" && $COMPOSE "$@"); }

backend_as_root()   { compose exec -T -u root   "$BACKEND_SVC" bash -lc "$*"; }
backend_as_frappe() { compose exec -T -u frappe "$BACKEND_SVC" bash -lc "$*"; }
frontend_sh()       { compose exec -T "$FRONTEND_SVC" sh -lc "$*"; }

BENCH_DIR="/home/frappe/frappe-bench"

# -------- guards ----------
ensure_up() {
  log "Checking required containers..."
  compose ps "$BACKEND_SVC" >/dev/null 2>&1 || die "Missing compose service: $BACKEND_SVC"
  compose ps "$FRONTEND_SVC" >/dev/null 2>&1 || die "Missing compose service: $FRONTEND_SVC"

  local cid
  cid="$(compose ps -q "$BACKEND_SVC")"
  [[ -n "$cid" ]] || die "Backend not running. Run ./bin/up.sh first."
}

list_sites() {
  backend_as_frappe "ls -1 ${BENCH_DIR}/sites | egrep -v '^(assets|logs|common_site_config\\.json|apps\\.txt|currentsite\\.txt)$' || true"
}

ensure_site_exists() {
  log "Checking site exists: $SITE"
  if backend_as_frappe "cd ${BENCH_DIR} && bench --site '$SITE' list-apps >/dev/null" >/dev/null 2>&1; then
    log "Site OK: $SITE ✅"
    return 0
  fi

  warn "Site '$SITE' not found."
  local sites
  sites="$(list_sites || true)"
  echo "Known sites:"
  echo "$sites" | sed 's/^/ - /'
  die "Site '$SITE' not found. Set SITE=<your-site> or run ./bin/new-site.sh first."
}

# -------- node/yarn PATH fix ----------
ensure_tools_in_backend() {
  log "Ensuring node+yarn are reachable for bench subprocesses..."

  if backend_as_frappe "command -v node >/dev/null && command -v yarn >/dev/null"; then
    log "node+yarn already visible for frappe user ✅"
    backend_as_frappe "node -v && yarn -v"
    return 0
  fi

  backend_as_root '
    set -euo pipefail
    mkdir -p /usr/local/bin

    NODE_BIN="$(command -v node || true)"
    if [[ -z "$NODE_BIN" ]]; then
      for p in /home/frappe/.nvm/versions/node/*/bin/node /root/.nvm/versions/node/*/bin/node; do
        [[ -x "$p" ]] && NODE_BIN="$p" && break
      done
    fi

    YARN_BIN="$(command -v yarn || true)"
    if [[ -z "$YARN_BIN" ]]; then
      if command -v corepack >/dev/null 2>&1; then
        export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
        corepack enable >/dev/null 2>&1 || true
        corepack prepare yarn@1.22.22 --activate >/dev/null 2>&1 || true
        YARN_BIN="$(command -v yarn || true)"
      fi
    fi
    if [[ -z "$YARN_BIN" ]]; then
      for p in /home/frappe/.nvm/versions/node/*/bin/yarn /root/.nvm/versions/node/*/bin/yarn; do
        [[ -x "$p" ]] && YARN_BIN="$p" && break
      done
    fi

    if [[ -z "$NODE_BIN" ]]; then
      echo "node not found; last-resort installing nodejs + yarn..." >&2
      apt-get update
      apt-get install -y --no-install-recommends curl ca-certificates gnupg
      curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
      apt-get install -y --no-install-recommends nodejs
      npm i -g yarn@1.22.22
      NODE_BIN="$(command -v node)"
      YARN_BIN="$(command -v yarn)"
    fi

    [[ -n "$NODE_BIN" ]] || { echo "node still not found" >&2; exit 1; }
    [[ -n "$YARN_BIN" ]] || { echo "yarn still not found" >&2; exit 1; }

    ln -sf "$NODE_BIN" /usr/local/bin/node
    ln -sf "$YARN_BIN" /usr/local/bin/yarn

    echo "node => $(readlink -f /usr/local/bin/node)"
    echo "yarn => $(readlink -f /usr/local/bin/yarn)"
  '

  backend_as_frappe '
    set -euo pipefail
    command -v node && node -v
    command -v yarn && yarn -v
  '
}

# -------- app install helpers ----------
app_dir_exists() {
  local dir="$1"
  backend_as_frappe "[[ -d ${BENCH_DIR}/apps/$dir ]]"
}

python_can_import() {
  local mod="$1"
  backend_as_frappe "cd ${BENCH_DIR} && ./env/bin/python -c 'import ${mod}' >/dev/null 2>&1"
}

ensure_editable_installed() {
  local app="$1"
  log "Ensuring Python can import '${app}' (editable install into venv if needed)..."

  if python_can_import "$app"; then
    log "Import OK: ${app} ✅"
    return 0
  fi

  backend_as_frappe "
    set -euo pipefail
    cd ${BENCH_DIR}
    ./env/bin/python -m pip install -e apps/${app}
  "

  python_can_import "$app" || die "Still cannot import ${app} after editable install."
  log "Import OK after install: ${app} ✅"

  NEED_BACKEND_RESTART=1
}


site_has_app() {
  local app="$1"
  backend_as_frappe "cd ${BENCH_DIR} && bench --site '$SITE' list-apps | awk '{print \$1}' | grep -qx '$app'"
}

get_app_if_missing() {
  local repo="$1"
  local branch="$2"
  local expected_dir="$3"

  if app_dir_exists "$expected_dir"; then
    log "App already present: apps/$expected_dir (skip get-app)"
    return 0
  fi

  log "Fetching app into apps volume: $expected_dir ($branch)"
  backend_as_frappe "
    set -euo pipefail
    cd ${BENCH_DIR}
    bench get-app --branch '$branch' '$repo'
    ls -1 apps > sites/apps.txt
  "

  app_dir_exists "$expected_dir" || die "Expected apps/$expected_dir after get-app, but it wasn't found."
}

install_app_if_missing() {
  local app="$1"

  if site_has_app "$app"; then
    log "App already installed on site: $app (skip install-app)"
    return 0
  fi

  log "Installing app on site '$SITE': $app"
  backend_as_frappe "
    set -euo pipefail
    cd ${BENCH_DIR}
    bench --site '$SITE' install-app '$app'
  "
}

migrate_and_cache_clear() {
  log "Migrating + clearing cache..."
  backend_as_frappe "
    set -euo pipefail
    cd ${BENCH_DIR}
    bench --site '$SITE' migrate
    bench --site '$SITE' clear-cache
    bench --site '$SITE' clear-website-cache
  "
}

build_assets_safe() {
  log "Building assets (safe default)..."
  backend_as_frappe "
    set -euo pipefail
    cd ${BENCH_DIR}
    # Don't hard-fail the whole install on asset hiccups during pilot.
    bench build || (echo 'bench build failed (non-fatal for pilot)'; exit 0)
  "
}

restart_services() {
  log "Restarting services..."
  compose restart \
    "$BACKEND_SVC" \
    "$WEBSOCKET_SVC" \
    "$QUEUE_LONG_SVC" \
    "$QUEUE_SHORT_SVC" \
    "$SCHEDULER_SVC" \
    "$FRONTEND_SVC"
}

ping_check() {
  log "Ping check through nginx frontend -> backend..."
  frontend_sh "
    set -euo pipefail
    curl -fsS -H 'X-Frappe-Site-Name: ${SITE}' http://${BACKEND_SVC}:8000/api/method/ping >/dev/null
    echo 'pong ✅'
  "
}

# -------- main ----------
main() {
  log "Helpdesk installer (repo: $ROOT_DIR)"
  log "SITE=$SITE BACKEND=$BACKEND_SVC"

  ensure_up
  ensure_site_exists
  ensure_tools_in_backend

  # get apps (idempotent)
  get_app_if_missing "$TELEPHONY_REPO" "$TELEPHONY_BRANCH" "telephony"
  get_app_if_missing "$HELPDESK_REPO"  "$HELPDESK_BRANCH"  "helpdesk"

  # critical: ensure python can import them (fixes ModuleNotFoundError after recreate)
  ensure_editable_installed "helpdesk"
  ensure_editable_installed "telephony"

  if [[ "${NEED_BACKEND_RESTART}" == "1" ]]; then
    log "Restarting backend to ensure gunicorn picks up new venv installs..."
    compose restart "$BACKEND_SVC"
  fi


  # install apps (idempotent)
  install_app_if_missing "telephony"
  install_app_if_missing "helpdesk"

  migrate_and_cache_clear
  build_assets_safe
  restart_services
  ping_check

  log "Done."
  echo "Next:"
  echo " - Open http://localhost:8080"
  echo " - Create Email Account helpdesk@local.test (IMAP 143, SMTP 587, no SSL/TLS for pilot)"
  echo " - Send a test email to create a Ticket"
}

main "$@"
