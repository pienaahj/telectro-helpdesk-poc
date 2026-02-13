#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./bin/mail-user.sh list
#   ./bin/mail-user.sh add    helpdesk@local.test 'Password123'
#   ./bin/mail-user.sh passwd helpdesk@local.test 'NewPassword123'
#   ./bin/mail-user.sh del    helpdesk@local.test
#   ./bin/mail-user.sh show   helpdesk@local.test
#
# Notes:
# - docker-mailserver stores hashed passwords in /tmp/docker-mailserver/postfix-accounts.cf
# - "passwd" is implemented via `setup email add` (portable across versions).

COMPOSE="${COMPOSE:-docker compose}"
MAIL_SVC="${MAIL_SVC:-mail}"

usage() {
  cat <<'EOF'
mail-user.sh — manage docker-mailserver accounts

Commands:
  list
  add <email> <password>
  passwd <email> <new_password>
  del <email>
  show <email>

Examples:
  ./bin/mail-user.sh list
  ./bin/mail-user.sh add helpdesk@local.test 'Password123'
  ./bin/mail-user.sh passwd helpdesk@local.test 'NewPassword123'
  ./bin/mail-user.sh show helpdesk@local.test
  ./bin/mail-user.sh del helpdesk@local.test

Env overrides:
  COMPOSE="docker compose"
  MAIL_SVC="mail"
EOF
}

die() { echo "ERROR: $*" >&2; exit 1; }

need_container() {
  $COMPOSE ps "$MAIL_SVC" >/dev/null 2>&1 || die "Compose service '$MAIL_SVC' not found/running. Start stack first (./bin/up.sh)."
}

cmd="${1:-}"
shift || true

need_container

case "$cmd" in
  list)
    $COMPOSE exec -T "$MAIL_SVC" sh -lc "cut -d'|' -f1 /tmp/docker-mailserver/postfix-accounts.cf | sort"
    ;;


  add)
    email="${1:-}"; pass="${2:-}"
    [[ -n "$email" && -n "$pass" ]] || die "Usage: add <email> <password>"

    $COMPOSE exec -T "$MAIL_SVC" setup email add "$email" "$pass"

    echo
    echo "✅ Added. Accounts file entry:"
    $COMPOSE exec -T "$MAIL_SVC" sh -lc "grep -nF '$email|' /tmp/docker-mailserver/postfix-accounts.cf || true"

    echo
    echo "📬 Current users (from postfix-accounts.cf):"
    $COMPOSE exec -T "$MAIL_SVC" sh -lc "cut -d'|' -f1 /tmp/docker-mailserver/postfix-accounts.cf | sort"
    ;;


passwd|password|change-pass)
    email="${1:-}"; pass="${2:-}"
    [[ -n "$email" && -n "$pass" ]] || die "Usage: passwd <email> <new_password>"
    echo "Updating password for $email ..."

    # docker-mailserver v14+ supports: setup email update <email> <password>
    if $COMPOSE exec -T "$MAIL_SVC" setup email update "$email" "$pass" >/dev/null 2>&1; then
      $COMPOSE exec -T "$MAIL_SVC" setup email update "$email" "$pass"
      echo "Done."
      exit 0
    fi

    # fallback: delete + add (will lose mailbox contents)
    echo "No 'setup email update' available; falling back to delete+add (WARNING: may remove mailbox contents)."
    $COMPOSE exec -T "$MAIL_SVC" setup email del "$email"
    $COMPOSE exec -T "$MAIL_SVC" setup email add "$email" "$pass"
    echo "Done."
    ;;


  del|rm|remove)
    email="${1:-}"
    [[ -n "$email" ]] || die "Usage: del <email>"
    $COMPOSE exec -T "$MAIL_SVC" setup email del "$email"
    echo
    $COMPOSE exec -T "$MAIL_SVC" setup email list
    ;;

  show)
    email="${1:-}"
    [[ -n "$email" ]] || die "Usage: show <email>"
    # Show the raw postfix account line (hashed password) if present
    $COMPOSE exec -T "$MAIL_SVC" bash -lc \
      "grep -nE '^${email//./\\.}\|' /tmp/docker-mailserver/postfix-accounts.cf || true"
    ;;

  -h|--help|help|"")
    usage
    ;;

  *)
    die "Unknown command: $cmd (try: ./bin/mail-user.sh help)"
    ;;
esac
