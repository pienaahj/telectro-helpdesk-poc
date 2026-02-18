#!/usr/bin/env bash
set -euo pipefail

trap 'echo "❌ pull-helpdesk-changes failed on line $LINENO" >&2' ERR

# Pull edited Helpdesk app files out of the running backend container
# into the host repo, so they can be committed + pushed.

docker compose ps backend >/dev/null

mkdir -p apps/helpdesk/helpdesk/overrides

SRC_BASE="backend:/home/frappe/frappe-bench/apps/helpdesk/helpdesk"
DST_BASE="apps/helpdesk/helpdesk"

cp_from_container() {
  local src="$1"
  local dst="$2"

  if ! docker compose exec -T backend bash -lc "test -e '/home/frappe/frappe-bench/apps/helpdesk/helpdesk/${src}'"; then
    echo "❌ Missing in container: helpdesk/${src}" >&2
    exit 1
  fi

  echo "→ ${dst}"
  docker compose cp "${SRC_BASE}/${src}" "${DST_BASE}/${dst}"
}

# --- overrides we changed ---
cp_from_container "overrides/email_account.py" "overrides/email_account.py"

echo
echo "✅ Pulled helpdesk changes from container."
echo

git status --porcelain
echo
git diff --stat