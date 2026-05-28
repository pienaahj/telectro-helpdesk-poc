#!/usr/bin/env bash
set -euo pipefail

trap 'echo "❌ pull-helpdesk-changes failed on line $LINENO" >&2' ERR

# Pull edited Helpdesk app files out of the running backend container
# into the host repo, so they can be committed + pushed.

docker compose ps backend >/dev/null

HELPDESK_PY_SRC_BASE="backend:/home/frappe/frappe-bench/apps/helpdesk/helpdesk"
HELPDESK_PY_DST_BASE="apps/helpdesk/helpdesk"

HELPDESK_DESK_SRC_BASE="backend:/home/frappe/frappe-bench/apps/helpdesk/desk"
HELPDESK_DESK_DST_BASE="apps/helpdesk/desk"

cp_helpdesk_py_from_container() {
  local src="$1"
  local dst="$2"

  if ! docker compose exec -T backend bash -lc "test -e '/home/frappe/frappe-bench/apps/helpdesk/helpdesk/${src}'"; then
    echo "❌ Missing in container: helpdesk/${src}" >&2
    exit 1
  fi

  mkdir -p "$(dirname "${HELPDESK_PY_DST_BASE}/${dst}")"

  echo "→ ${HELPDESK_PY_DST_BASE}/${dst}"
  docker compose cp "${HELPDESK_PY_SRC_BASE}/${src}" "${HELPDESK_PY_DST_BASE}/${dst}"
}

cp_helpdesk_desk_from_container() {
  local src="$1"
  local dst="$2"

  if ! docker compose exec -T backend bash -lc "test -e '/home/frappe/frappe-bench/apps/helpdesk/desk/${src}'"; then
    echo "❌ Missing in container: desk/${src}" >&2
    exit 1
  fi

  mkdir -p "$(dirname "${HELPDESK_DESK_DST_BASE}/${dst}")"

  echo "→ ${HELPDESK_DESK_DST_BASE}/${dst}"
  docker compose cp "${HELPDESK_DESK_SRC_BASE}/${src}" "${HELPDESK_DESK_DST_BASE}/${dst}"
}

# --- Helpdesk Python/app files we changed previously ---
cp_helpdesk_py_from_container "overrides/email_account.py" "overrides/email_account.py"

# --- Helpdesk desk frontend files changed for Customer portal lifecycle hardening ---
cp_helpdesk_desk_from_container "src/pages/ticket/TicketCustomer.vue" "src/pages/ticket/TicketCustomer.vue"

# --- Helpdesk desk frontend files changed for Service Coverage Model ---
cp_helpdesk_desk_from_container "src/components/layouts/layoutSettings.ts" "src/components/layouts/layoutSettings.ts"
cp_helpdesk_desk_from_container "src/components/SearchArticles.vue" "src/components/SearchArticles.vue"

# --- Helpdesk desk frontend files changed for Customer location logic ---
cp_helpdesk_desk_from_container "src/pages/ticket/TicketNew.vue" "src/pages/ticket/TicketNew.vue"
cp_helpdesk_desk_from_container "src/components/ticket/TicketCustomerSidebar.vue" "src/components/ticket/TicketCustomerSidebar.vue"
cp_helpdesk_desk_from_container "src/pages/ticket/TicketCustomerTemplateFields.vue" "src/pages/ticket/TicketCustomerTemplateFields.vue"

echo
echo "✅ Pulled helpdesk changes from container."
echo

git status --porcelain
echo
git diff --stat