#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

HELPER="${ROOT_DIR}/docker/apply-frappe-realtime-compat.py"
DOCKERFILE="${ROOT_DIR}/docker/telectro-runtime.Dockerfile"
COMPOSE_BASE="${ROOT_DIR}/compose.yaml"
COMPOSE_PRODUCTION="${ROOT_DIR}/compose.production.yaml"

FRAPPE_IMAGE="frappe/erpnext:v15.94.1"
HELPDESK_IMAGE="ghcr.io/frappe/helpdesk:v1.18.1"

EXPECTED_UTILS_SHA256="e5daace2a357d21673be184fdf8053f1c3544e3200f2c0f3865318da57805092"
EXPECTED_AUTHENTICATE_SHA256="e05f517c353d300833fcf9376038718ca76a248098ffa74b5c0cd1f4d57c271f"
EXPECTED_INDEX_SHA256="acf2ef802d3f68c8016c08685e24eaf83488ba63392ae63855218a4d70ea89c3"
EXPECTED_NATIVE_SHA256="d484f2c63ef7c7ae16f1a876acc07e77d378638dad83c8649bce22458907fc86"
EXPECTED_HELPDESK_SHA256="633df0811e0a75dd5e2b0e7814ca46a9d767896cec61139b1e2a8f9a0c119e69"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

sha256_file() {
  local path="$1"

  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" |
      awk '{print $1}'
    return
  fi

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" |
      awk '{print $1}'
    return
  fi

  fail "no SHA-256 command available"
}

TMP_ROOT="$(mktemp -d)"
SOURCE_ROOT="${TMP_ROOT}/source"
POSITIVE_ROOT="${TMP_ROOT}/positive"
NEGATIVE_ROOT="${TMP_ROOT}/negative"
COMPOSE_RENDER="${TMP_ROOT}/compose-production-rendered.yaml"

FRAPPE_CID=""
HELPDESK_CID=""

cleanup() {
  if [ -n "$FRAPPE_CID" ]; then
    docker rm -f "$FRAPPE_CID" >/dev/null 2>&1 || true
  fi

  if [ -n "$HELPDESK_CID" ]; then
    docker rm -f "$HELPDESK_CID" >/dev/null 2>&1 || true
  fi

  rm -rf "$TMP_ROOT"
}

trap cleanup EXIT

cd "$ROOT_DIR"

printf '%s\n' \
  '=== Frappe realtime compatibility regression ==='

test -f "$HELPER" ||
  fail "realtime compatibility helper is missing"

test -f "$DOCKERFILE" ||
  fail "runtime Dockerfile is missing"

test -f "$COMPOSE_BASE" ||
  fail "base Compose file is missing"

test -f "$COMPOSE_PRODUCTION" ||
  fail "production Compose file is missing"

command -v docker >/dev/null 2>&1 ||
  fail "docker command is unavailable"

printf '\n%s\n' \
  '=== Helper syntax ==='

PYTHONPYCACHEPREFIX="${TMP_ROOT}/pycache" \
  python3 -m py_compile "$HELPER" ||
  fail "realtime compatibility helper has invalid Python syntax"

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_HELPER_SYNTAX=PASS'

printf '\n%s\n' \
  '=== Prepare pristine pinned upstream source ==='

mkdir -p \
  "${SOURCE_ROOT}/apps/frappe/realtime/middlewares" \
  "${SOURCE_ROOT}/apps/frappe/realtime/handlers" \
  "${SOURCE_ROOT}/apps/helpdesk/realtime"

FRAPPE_CID="$(
  docker create \
    --platform linux/amd64 \
    "$FRAPPE_IMAGE"
)"

HELPDESK_CID="$(
  docker create \
    --platform linux/amd64 \
    "$HELPDESK_IMAGE"
)"

docker cp \
  "${FRAPPE_CID}:/home/frappe/frappe-bench/apps/frappe/realtime/utils.js" \
  "${SOURCE_ROOT}/apps/frappe/realtime/utils.js"

docker cp \
  "${FRAPPE_CID}:/home/frappe/frappe-bench/apps/frappe/realtime/middlewares/authenticate.js" \
  "${SOURCE_ROOT}/apps/frappe/realtime/middlewares/authenticate.js"

docker cp \
  "${FRAPPE_CID}:/home/frappe/frappe-bench/apps/frappe/realtime/index.js" \
  "${SOURCE_ROOT}/apps/frappe/realtime/index.js"

docker cp \
  "${FRAPPE_CID}:/home/frappe/frappe-bench/apps/frappe/realtime/handlers/frappe_handlers.js" \
  "${SOURCE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js"

docker cp \
  "${HELPDESK_CID}:/home/frappe/frappe-bench/apps/helpdesk/realtime/handlers.js" \
  "${SOURCE_ROOT}/apps/helpdesk/realtime/handlers.js"

docker rm "$FRAPPE_CID" >/dev/null
FRAPPE_CID=""

docker rm "$HELPDESK_CID" >/dev/null
HELPDESK_CID=""

mkdir -p \
  "$POSITIVE_ROOT" \
  "$NEGATIVE_ROOT"

cp -R \
  "${SOURCE_ROOT}/." \
  "${POSITIVE_ROOT}/"

cp -R \
  "${SOURCE_ROOT}/." \
  "${NEGATIVE_ROOT}/"

printf '%s\n' \
  'PINNED_REALTIME_SOURCE_PREPARED=PASS'

printf '\n%s\n' \
  '=== Positive-path compatibility transformation ==='

if POSITIVE_OUTPUT="$(
  FRAPPE_BENCH_ROOT="$POSITIVE_ROOT" \
    python3 "$HELPER" \
    2>&1
)"; then
  POSITIVE_STATUS=0
else
  POSITIVE_STATUS=$?
fi

printf '%s\n' "$POSITIVE_OUTPUT"
printf 'POSITIVE_STATUS=%s\n' "$POSITIVE_STATUS"

[ "$POSITIVE_STATUS" -eq 0 ] ||
  fail "compatibility helper rejected pristine pinned source"

grep -F \
  'FRAPPE_REALTIME_COMPAT_PATCH=PASS' \
  <<<"$POSITIVE_OUTPUT" \
  >/dev/null ||
  fail "compatibility helper success marker was not emitted"

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_POSITIVE_PATH=PASS'

printf '\n%s\n' \
  '=== Patched source SHA-256 contract ==='

ACTUAL_UTILS_SHA256="$(
  sha256_file \
    "${POSITIVE_ROOT}/apps/frappe/realtime/utils.js"
)"

ACTUAL_AUTHENTICATE_SHA256="$(
  sha256_file \
    "${POSITIVE_ROOT}/apps/frappe/realtime/middlewares/authenticate.js"
)"

ACTUAL_INDEX_SHA256="$(
  sha256_file \
    "${POSITIVE_ROOT}/apps/frappe/realtime/index.js"
)"

ACTUAL_NATIVE_SHA256="$(
  sha256_file "${POSITIVE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js"
)"
ACTUAL_HELPDESK_SHA256="$(
  sha256_file "${POSITIVE_ROOT}/apps/helpdesk/realtime/handlers.js"
)"

[ "$ACTUAL_NATIVE_SHA256" = "$EXPECTED_NATIVE_SHA256" ] ||
  fail "patched native handler SHA-256 changed"
[ "$ACTUAL_HELPDESK_SHA256" = "$EXPECTED_HELPDESK_SHA256" ] ||
  fail "patched Helpdesk handler SHA-256 changed"

[ "$ACTUAL_UTILS_SHA256" = "$EXPECTED_UTILS_SHA256" ] ||
  fail "patched utils.js SHA-256 changed"

[ "$ACTUAL_AUTHENTICATE_SHA256" = "$EXPECTED_AUTHENTICATE_SHA256" ] ||
  fail "patched authenticate.js SHA-256 changed"

printf 'UTILS_SHA256=%s\n' "$ACTUAL_UTILS_SHA256"
printf 'AUTHENTICATE_SHA256=%s\n' "$ACTUAL_AUTHENTICATE_SHA256"
printf 'INDEX_SHA256=%s\n' "$ACTUAL_INDEX_SHA256"
printf 'NATIVE_SHA256=%s\n' "$ACTUAL_NATIVE_SHA256"
printf 'HELPDESK_SHA256=%s\n' "$ACTUAL_HELPDESK_SHA256"

[ "$ACTUAL_INDEX_SHA256" = "$EXPECTED_INDEX_SHA256" ] ||
  fail "patched index.js SHA-256 changed"

node --check \
  "${POSITIVE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js" ||
  fail "patched native Frappe handler has invalid JavaScript syntax"

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_POST_HASHES=PASS'

printf '\n%s\n' \
  '=== Patched JavaScript syntax ==='
printf '\n%s\n' \
  '=== Helpdesk view_ticket room authorisation behaviour ==='

node \
  "${ROOT_DIR}/tests/node/test-helpdesk-ticket-room-authorization.js" \
  "${POSITIVE_ROOT}/apps/helpdesk/realtime/handlers.js" ||
  fail "Helpdesk view_ticket authorisation behaviour failed"

printf '\n%s\n' \
  '=== Helpdesk ticket_get_viewers authorisation behaviour ==='

node \
  "${ROOT_DIR}/tests/node/test-helpdesk-ticket-viewer-query.js" \
  "${POSITIVE_ROOT}/apps/helpdesk/realtime/handlers.js" ||
  fail "Helpdesk ticket_get_viewers authorisation behaviour failed"

node --check \
  "${POSITIVE_ROOT}/apps/frappe/realtime/utils.js" ||
  fail "patched utils.js has invalid JavaScript syntax"

node --check \
  "${POSITIVE_ROOT}/apps/frappe/realtime/middlewares/authenticate.js" ||
  fail "patched authenticate.js has invalid JavaScript syntax"

node --check \
  "${POSITIVE_ROOT}/apps/frappe/realtime/index.js" ||
  fail "patched index.js has invalid JavaScript syntax"

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_JS_SYNTAX=PASS'

printf '\n%s\n' \
  '=== Frappe realtime HTTP callback site-header authorisation ==='

node \
  "${ROOT_DIR}/tests/node/test-frappe-realtime-callback-site-header.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/utils.js" ||
  fail "Frappe realtime callback site-header behaviour failed"

printf '%s\n' \
  'FRAPPE_REALTIME_CALLBACK_SITE_HEADER=PASS'

printf '\n%s\n' \
  '=== Real recipient reauthorisation and revocation behaviour ==='
node \
  "${ROOT_DIR}/tests/node/test-realtime-recipient-delivery.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/utils.js" ||
  fail "realtime recipient reauthorisation failed"

printf '\n%s\n' \
  '=== Telectro internal-only HD Ticket DocType backend authority ==='
python3 \
  "${ROOT_DIR}/tests/bin/test-hd-ticket-internal-doctype-authority.py" \
  "${ROOT_DIR}/apps/telephony/telephony/realtime_ticket_authorization.py" ||
  fail "Telectro internal-only HD Ticket DocType policy failed"

printf '\n%s\n' \
  '=== HD Ticket DocType-wide room privacy boundary ==='
node \
  "${ROOT_DIR}/tests/node/test-hd-ticket-doctype-realtime-boundary.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/utils.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js" ||
  fail "HD Ticket DocType-wide room privacy boundary failed"

printf '\n%s\n' \
  '=== Redis ticket room recipient-delivery dispatch ==='
node \
  "${ROOT_DIR}/tests/node/test-realtime-redis-protected-delivery.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/index.js" ||
  fail "Redis protected ticket delivery dispatch failed"

printf '\n%s\n' \
  '=== Native and Helpdesk shared-room isolation ==='
node \
  "${ROOT_DIR}/tests/node/test-native-helpdesk-shared-room-isolation.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/utils.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js" ||
  fail "native and Helpdesk shared-room isolation failed"


printf '\n%s\n' \
  '=== Native HD Ticket socket authorisation behaviour ==='

node \
  "${ROOT_DIR}/tests/node/test-native-ticket-realtime-subscription.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js" ||
  fail "native HD Ticket socket authorisation behaviour failed"

printf '\n%s\n' \
  '=== Native HD Ticket asynchronous lifecycle behaviour ==='

node \
  "${ROOT_DIR}/tests/node/test-native-ticket-realtime-lifecycle.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js" ||
  fail "native HD Ticket asynchronous lifecycle behaviour failed"

printf '\n%s\n' \
  '=== Native HD Ticket pending-token cleanup behaviour ==='

node \
  "${ROOT_DIR}/tests/node/test-native-ticket-token-cleanup.js" \
  "${POSITIVE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js" ||
  fail "native HD Ticket pending-token cleanup behaviour failed"

node --check \
  "${POSITIVE_ROOT}/apps/helpdesk/realtime/handlers.js" ||
  fail "patched Helpdesk handler has invalid JavaScript syntax"

printf '\n%s\n' \
  '=== Runtime behavior source contracts ==='

grep -F \
  'conf.webserver_host && conf.webserver_port' \
  "${POSITIVE_ROOT}/apps/frappe/realtime/utils.js" \
  >/dev/null ||
  fail "internal webserver callback contract is missing"

grep -F \
  '"X-Frappe-Site-Name"' \
  "${POSITIVE_ROOT}/apps/frappe/realtime/middlewares/authenticate.js" \
  >/dev/null ||
  fail "Frappe site-name authentication header is missing"

grep -F \
  'const helpdesk_handlers = require("../../helpdesk/realtime/handlers");' \
  "${POSITIVE_ROOT}/apps/frappe/realtime/index.js" \
  >/dev/null ||
  fail "Helpdesk realtime handler import is missing"

grep -F \
  'helpdesk_handlers(socket);' \
  "${POSITIVE_ROOT}/apps/frappe/realtime/index.js" \
  >/dev/null ||
  fail "Helpdesk realtime handler registration is missing"

grep -F \
  'socket.on("open_in_editor"' \
  "${POSITIVE_ROOT}/apps/frappe/realtime/index.js" \
  >/dev/null ||
  fail "Frappe open_in_editor handler was not preserved"

printf '\n%s\n' \
  '=== Helpdesk stop_view_ticket membership behaviour ==='

node \
  "${ROOT_DIR}/tests/node/test-helpdesk-stop-view-ticket.js" \
  "${POSITIVE_ROOT}/apps/helpdesk/realtime/handlers.js" ||
  fail "Helpdesk stop_view_ticket membership behaviour failed"

printf '\n%s\n' \
  '=== Helpdesk typing-event authorisation behaviour ==='

node \
  "${ROOT_DIR}/tests/node/test-helpdesk-ticket-typing-authorization.js" \
  "${POSITIVE_ROOT}/apps/helpdesk/realtime/handlers.js" ||
  fail "Helpdesk typing-event authorisation behaviour failed"

printf '\n%s\n' \
  '=== Helpdesk pending view lifecycle behaviour ==='

node \
  "${ROOT_DIR}/tests/node/test-helpdesk-pending-view-lifecycle.js" \
  "${POSITIVE_ROOT}/apps/helpdesk/realtime/handlers.js" ||
  fail "Helpdesk pending view lifecycle behaviour failed"

NATIVE_HANDLER="${POSITIVE_ROOT}/apps/frappe/realtime/handlers/frappe_handlers.js"

grep -F \
  'if (doctype === "HD Ticket")' \
  "$NATIVE_HANDLER" >/dev/null ||
  fail "HD Ticket native subscription guard is missing"

grep -F \
  'telephony.realtime_ticket_authorization.require_ticket_realtime_access' \
  "$NATIVE_HANDLER" >/dev/null ||
  fail "Telectro realtime authority endpoint is missing"

grep -F \
  'channel: "native_doc"' \
  "$NATIVE_HANDLER" >/dev/null ||
  fail "native document channel is not specified"

grep -F \
  'res.body.message === true' \
  "$NATIVE_HANDLER" >/dev/null ||
  fail "strict native subscription approval check is missing"

grep -F -A 12 \
  'socket.on("doc_open", function (doctype, docname) {' \
  "$NATIVE_HANDLER" |
  grep -F \
    '? can_subscribe_hd_ticket_native' \
    >/dev/null ||
  fail "HD Ticket native doc_open policy is missing"

grep -F -A 12 \
  'socket.on("doc_open", function (doctype, docname) {' \
  "$NATIVE_HANDLER" |
  grep -F \
    ': can_subscribe_doc;' \
    >/dev/null ||
  fail "Other DocType doc_open Frappe fallback is missing"

printf '%s\n' \
  'NATIVE_HD_TICKET_DOC_OPEN_POLICY=PASS'

HELPDESK_HANDLER="${POSITIVE_ROOT}/apps/helpdesk/realtime/handlers.js"

grep -F \
  'await can_view_helpdesk_ticket(socket, ticket_id)' \
  "$HELPDESK_HANDLER" >/dev/null ||
  fail "Helpdesk view_ticket permission gate is missing"

grep -F -A 3 \
  'socket.on("ticket_get_viewers", async (ticket_id) => {' \
  "$HELPDESK_HANDLER" |
  grep -F \
    'if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;' \
    >/dev/null ||
  fail "Helpdesk ticket_get_viewers permission gate is missing"

grep -F \
  'channel: "helpdesk_ticket"' \
  "$HELPDESK_HANDLER" >/dev/null ||
  fail "Helpdesk ticket authorisation channel is missing"

grep -F \
  'res.body.message === true' \
  "$HELPDESK_HANDLER" >/dev/null ||
  fail "Helpdesk strict authorisation check is missing"

if grep -Fq \
  'socket.on("notify_ticket_update"' \
  "$HELPDESK_HANDLER"
then
  fail "Untrusted client ticket-update handler remains enabled"
fi

if grep -Fq \
  '.emit("ticket_update"' \
  "$HELPDESK_HANDLER"
then
  fail "Untrusted ticket field broadcast remains enabled"
fi

grep -F -A 5 \
  'socket.on("stop_view_ticket", (ticket_id) => {' \
  "$HELPDESK_HANDLER" |
  grep -F \
    'if (!members || !members.has(socket.id)) return;' \
    >/dev/null ||
  fail "Helpdesk stop_view_ticket membership gate is missing"

for EVENT in \
  helpdesk_ticket_typing \
  helpdesk_ticket_typing_stopped
do
  grep -F -A 6 \
    "socket.on(\"${EVENT}\", async (ticket_id) => {" \
    "$HELPDESK_HANDLER" |
    grep -F \
      'if (!members || !members.has(socket.id)) return;' \
      >/dev/null ||
    fail "${EVENT}: room membership gate missing"

  grep -F -A 6 \
    "socket.on(\"${EVENT}\", async (ticket_id) => {" \
    "$HELPDESK_HANDLER" |
    grep -F \
      'if (!(await can_view_helpdesk_ticket(socket, ticket_id))) return;' \
      >/dev/null ||
    fail "${EVENT}: current authorisation gate missing"
done

for EVENT in \
  helpdesk_ticket_typing \
  helpdesk_ticket_typing_stopped
do
  grep -F -A 7 \
    "socket.on(\"${EVENT}\", async (ticket_id) => {" \
    "$HELPDESK_HANDLER" |
    grep -F \
      'if (!socket.nsp.adapter.rooms.get(ticket_room)?.has(socket.id)) return;' \
      >/dev/null ||
    fail "${EVENT}: post-authorisation membership recheck missing"
done

grep -Fq \
  'socket.on("disconnect", () => pendingTicketViews.clear());' \
  "$HELPDESK_HANDLER" ||
  fail "Helpdesk pending-view disconnect cleanup missing"

grep -F -A 12 \
  'socket.on("view_ticket", async (ticket_id) => {' \
  "$HELPDESK_HANDLER" |
  grep -F \
    'if (!allowed || socket.connected !== true) return;' \
    >/dev/null ||
  fail "Helpdesk pending-view connection gate missing"

grep -F -A 5 \
  'socket.on("stop_view_ticket", (ticket_id) => {' \
  "$HELPDESK_HANDLER" |
  grep -F \
    'pendingTicketViews.delete(ticket_id);' \
    >/dev/null ||
  fail "Helpdesk pending-view cancellation missing"

printf '%s\n' \
  'HELPDESK_PENDING_VIEW_LIFECYCLE_CONTRACT=PASS'
printf '%s\n' \
  'HELPDESK_TYPING_POST_AUTH_MEMBERSHIP=PASS'
printf '%s\n' \
  'HELPDESK_TYPING_EVENT_SOURCE_GATES=PASS'
printf '%s\n' \
  'HELPDESK_STOP_VIEW_MEMBERSHIP_GATE=PASS'

printf '%s\n' \
  'HELPDESK_UNTRUSTED_TICKET_UPDATE_DISABLED=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_RUNTIME_CONTRACTS=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_OPEN_IN_EDITOR_PRESERVED=PASS'

printf '\n%s\n' \
  '=== Altered upstream source rejection ==='

printf '\n// realtime compatibility guard regression\n' >> \
  "${NEGATIVE_ROOT}/apps/frappe/realtime/utils.js"

NEGATIVE_PATHS=(
  "apps/frappe/realtime/utils.js"
  "apps/frappe/realtime/middlewares/authenticate.js"
  "apps/frappe/realtime/index.js"
  "apps/frappe/realtime/handlers/frappe_handlers.js"
  "apps/helpdesk/realtime/handlers.js"
)

NEGATIVE_BEFORE=()

for RELATIVE_PATH in "${NEGATIVE_PATHS[@]}"; do
  NEGATIVE_BEFORE+=(
    "$(sha256_file "${NEGATIVE_ROOT}/${RELATIVE_PATH}")"
  )
done

if NEGATIVE_OUTPUT="$(
  FRAPPE_BENCH_ROOT="$NEGATIVE_ROOT" \
    python3 "$HELPER" \
    2>&1
)"; then
  NEGATIVE_STATUS=0
else
  NEGATIVE_STATUS=$?
fi

printf '%s\n' "$NEGATIVE_OUTPUT"
printf 'NEGATIVE_STATUS=%s\n' "$NEGATIVE_STATUS"

[ "$NEGATIVE_STATUS" -ne 0 ] ||
  fail "compatibility helper accepted altered upstream source"

grep -F \
  'SHA256_MISMATCH' \
  <<<"$NEGATIVE_OUTPUT" \
  >/dev/null ||
  fail "altered-source rejection reason was not reported"

grep -F \
  "'frappe_realtime_compat': 'REFUSED'" \
  <<<"$NEGATIVE_OUTPUT" \
  >/dev/null ||
  fail "fail-closed marker was not reported"

for INDEX in "${!NEGATIVE_PATHS[@]}"; do
  RELATIVE_PATH="${NEGATIVE_PATHS[$INDEX]}"

  ACTUAL_SHA256="$(
    sha256_file "${NEGATIVE_ROOT}/${RELATIVE_PATH}"
  )"

  [ "$ACTUAL_SHA256" = "${NEGATIVE_BEFORE[$INDEX]}" ] ||
    fail "rejected transformation modified ${RELATIVE_PATH}"
done

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_REFUSAL_UNCHANGED=PASS'

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_SOURCE_GUARD=PASS'

printf '\n%s\n' \
  '=== Runtime Dockerfile integration ==='

grep -F \
  'COPY docker/apply-frappe-realtime-compat.py /tmp/apply-frappe-realtime-compat.py' \
  "$DOCKERFILE" \
  >/dev/null ||
  fail "runtime Dockerfile does not copy compatibility helper"

grep -F \
  'python /tmp/apply-frappe-realtime-compat.py;' \
  "$DOCKERFILE" \
  >/dev/null ||
  fail "runtime Dockerfile does not execute compatibility helper"

grep -F \
  'node --check apps/frappe/realtime/utils.js;' \
  "$DOCKERFILE" \
  >/dev/null ||
  fail "runtime Dockerfile does not validate patched utils.js"

grep -F \
  'node --check apps/frappe/realtime/middlewares/authenticate.js;' \
  "$DOCKERFILE" \
  >/dev/null ||
  fail "runtime Dockerfile does not validate patched authenticate.js"

grep -F \
  'node --check apps/frappe/realtime/index.js;' \
  "$DOCKERFILE" \
  >/dev/null ||
  fail "runtime Dockerfile does not validate patched index.js"

grep -F \
  'node --check apps/frappe/realtime/handlers/frappe_handlers.js;' \
  "$DOCKERFILE" >/dev/null ||
  fail "runtime Dockerfile does not validate native Frappe handler"

grep -F \
  'node --check apps/helpdesk/realtime/handlers.js;' \
  "$DOCKERFILE" >/dev/null ||
  fail "runtime Dockerfile does not validate Helpdesk handler"

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_DOCKERFILE_INTEGRATION=PASS'

printf '\n%s\n' \
  '=== Obsolete HD Team image guard ==='

if grep -E \
  'hd_team\.json|production_fixture_safety|@local\.test HD Team' \
  "$DOCKERFILE" \
  >/dev/null
then
  fail "obsolete HD Team fixture image guard is present"
fi

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_STALE_HD_TEAM_GUARD_ABSENT=PASS'

printf '\n%s\n' \
  '=== Compose realtime callback configuration ==='

docker compose \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_PRODUCTION" \
  config \
  --no-interpolate \
  >"$COMPOSE_RENDER" ||
  fail "DEV/PROD Compose configuration does not render"

grep -F \
  'bench set-config -g webserver_host $$WEBSERVER_HOST;' \
  "$COMPOSE_RENDER" \
  >/dev/null ||
  fail "effective configurator does not set webserver_host"

grep -F \
  'bench set-config -gp webserver_port $$WEBSERVER_PORT;' \
  "$COMPOSE_RENDER" \
  >/dev/null ||
  fail "effective configurator does not set webserver_port"

grep -F \
  'WEBSERVER_HOST: backend' \
  "$COMPOSE_RENDER" \
  >/dev/null ||
  fail "effective configurator does not use backend as webserver host"

grep -F \
  'WEBSERVER_PORT: "8000"' \
  "$COMPOSE_RENDER" \
  >/dev/null ||
  fail "effective configurator does not use port 8000"

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_COMPOSE_CONFIG=PASS'

printf '\n%s\n' \
  '=== Final result ==='

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_HELPER_SYNTAX=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_POSITIVE_PATH=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_POST_HASHES=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_JS_SYNTAX=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_RUNTIME_CONTRACTS=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_OPEN_IN_EDITOR_PRESERVED=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_SOURCE_GUARD=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_DOCKERFILE_INTEGRATION=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_STALE_HD_TEAM_GUARD_ABSENT=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_COMPOSE_CONFIG=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_REGRESSION=PASS'
