#!/usr/bin/env bash
set -euo pipefail

# Guarded production app install wrapper.
#
# Installs required apps into an existing production site through bin/prod-bench.sh.
#
# This script intentionally does not run migrate. Run migration separately with:
#
#   SITE=<production-site-name> ./bin/prod-migrate.sh
#
# Usage:
#
#   SITE=<production-site-name> \
#   CONFIRM_PROD_INSTALL_APPS=install-apps \
#   ./bin/prod-install-apps.sh
#
# Optional:
#
#   APP_NAMES="helpdesk telephony" \
#   SITE=<production-site-name> \
#   CONFIRM_PROD_INSTALL_APPS=install-apps \
#   ./bin/prod-install-apps.sh

SITE="${SITE:-}"
CONFIRM_PROD_INSTALL_APPS="${CONFIRM_PROD_INSTALL_APPS:-}"
APP_NAMES="${APP_NAMES:-helpdesk telephony}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() {
  printf "\nERROR: %s\n\n" "$*" >&2
  exit 1
}

log() {
  printf "\n==> %s\n" "$*" >&2
}

[[ -n "$SITE" ]] || die "SITE is required. Example: SITE=erp.telectro.co.za ./bin/prod-install-apps.sh"
[[ "$CONFIRM_PROD_INSTALL_APPS" == "install-apps" ]] || die "Refusing to install apps. Re-run with CONFIRM_PROD_INSTALL_APPS=install-apps"

cd "$ROOT_DIR"

[[ -x ./bin/prod-bench.sh ]] || die "Missing executable ./bin/prod-bench.sh"

list_apps() {
  ./bin/prod-bench.sh --site "$SITE" list-apps
}

app_installed() {
  local app="$1"

  list_apps \
    | awk '{print $1}' \
    | grep -qx "$app"
}

log "Production site: $SITE"
log "Required apps: $APP_NAMES"

log "Currently installed apps"
list_apps

for app in $APP_NAMES; do
  if app_installed "$app"; then
    log "App already installed: $app"
    continue
  fi

  log "Installing app: $app"
  ./bin/prod-bench.sh --site "$SITE" install-app "$app"
done

log "Installed apps after install step"
list_apps

log "Done. Run migration separately:"
printf 'PROD_ENV_FILE=%q SITE=%q ./bin/prod-migrate.sh\n' "${PROD_ENV_FILE:-.env.production}" "$SITE"
