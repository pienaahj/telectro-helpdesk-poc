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

EXPECTED_UTILS_SHA256="22f4eaafc945a153d89f5cece7532ad1803309150752061d8bb56b14cd9a5df0"
EXPECTED_AUTHENTICATE_SHA256="e05f517c353d300833fcf9376038718ca76a248098ffa74b5c0cd1f4d57c271f"
EXPECTED_INDEX_SHA256="524c30923fa153f8f71ca1ece1b654dc1392bc466c7f16a73a7a005b61ab2527"

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

[ "$ACTUAL_UTILS_SHA256" = "$EXPECTED_UTILS_SHA256" ] ||
  fail "patched utils.js SHA-256 changed"

[ "$ACTUAL_AUTHENTICATE_SHA256" = "$EXPECTED_AUTHENTICATE_SHA256" ] ||
  fail "patched authenticate.js SHA-256 changed"

[ "$ACTUAL_INDEX_SHA256" = "$EXPECTED_INDEX_SHA256" ] ||
  fail "patched index.js SHA-256 changed"

printf 'UTILS_SHA256=%s\n' "$ACTUAL_UTILS_SHA256"
printf 'AUTHENTICATE_SHA256=%s\n' "$ACTUAL_AUTHENTICATE_SHA256"
printf 'INDEX_SHA256=%s\n' "$ACTUAL_INDEX_SHA256"

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_POST_HASHES=PASS'

printf '\n%s\n' \
  '=== Patched JavaScript syntax ==='

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

printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_RUNTIME_CONTRACTS=PASS'
printf '%s\n' \
  'FRAPPE_REALTIME_COMPAT_OPEN_IN_EDITOR_PRESERVED=PASS'

printf '\n%s\n' \
  '=== Altered upstream source rejection ==='

printf '\n// realtime compatibility guard regression\n' >> \
  "${NEGATIVE_ROOT}/apps/frappe/realtime/utils.js"

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
