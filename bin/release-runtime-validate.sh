#!/usr/bin/env bash

set -euo pipefail

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

RELEASE_ID="${RELEASE_ID:-}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
EXPECTED_FRAPPE_VERSION="${EXPECTED_FRAPPE_VERSION:-}"
EXPECTED_ERPNEXT_VERSION="${EXPECTED_ERPNEXT_VERSION:-}"
EXPECTED_HELPDESK_VERSION="${EXPECTED_HELPDESK_VERSION:-}"
EXPECTED_TELEPHONY_VERSION="${EXPECTED_TELEPHONY_VERSION:-}"
EMBEDDED_CHANGE_PATH="${EMBEDDED_CHANGE_PATH:-}"
EXPECTED_EMBEDDED_SHA256="${EXPECTED_EMBEDDED_SHA256:-}"
SEMANTIC_VALIDATOR="${SEMANTIC_VALIDATOR:-}"

[ -n "$RELEASE_ID" ] ||
  fail "RELEASE_ID is required"

[ -n "$EXPECTED_FRAPPE_VERSION" ] ||
  fail "EXPECTED_FRAPPE_VERSION is required"

[ -n "$EXPECTED_ERPNEXT_VERSION" ] ||
  fail "EXPECTED_ERPNEXT_VERSION is required"

[ -n "$EXPECTED_HELPDESK_VERSION" ] ||
  fail "EXPECTED_HELPDESK_VERSION is required"

[ -n "$EXPECTED_TELEPHONY_VERSION" ] ||
  fail "EXPECTED_TELEPHONY_VERSION is required"

[ -n "$EMBEDDED_CHANGE_PATH" ] ||
  fail "EMBEDDED_CHANGE_PATH is required"

[ -n "$EXPECTED_EMBEDDED_SHA256" ] ||
  fail "EXPECTED_EMBEDDED_SHA256 is required"

case "$EMBEDDED_CHANGE_PATH" in
  apps/*)
    ;;
  *)
    fail "EMBEDDED_CHANGE_PATH must be a relative path beneath apps/"
    ;;
esac

case "/${EMBEDDED_CHANGE_PATH}/" in
  *//*|*/./*|*/../*)
    fail "EMBEDDED_CHANGE_PATH contains an unsafe path component"
    ;;
esac

[ "$EMBEDDED_CHANGE_PATH" != "apps/" ] ||
  fail "EMBEDDED_CHANGE_PATH must identify a file"

[ "${#EXPECTED_EMBEDDED_SHA256}" -eq 64 ] ||
  fail "EXPECTED_EMBEDDED_SHA256 must be 64 lowercase hexadecimal characters"

case "$EXPECTED_EMBEDDED_SHA256" in
  *[!0-9a-f]*)
    fail "EXPECTED_EMBEDDED_SHA256 must be 64 lowercase hexadecimal characters"
    ;;
esac

[ -n "$SEMANTIC_VALIDATOR" ] ||
  fail "SEMANTIC_VALIDATOR is required"

[ -f "$SEMANTIC_VALIDATOR" ] ||
  fail "SEMANTIC_VALIDATOR does not exist: $SEMANTIC_VALIDATOR"

[ -r "$SEMANTIC_VALIDATOR" ] ||
  fail "SEMANTIC_VALIDATOR is not readable: $SEMANTIC_VALIDATOR"

if bash -n "$SEMANTIC_VALIDATOR"
then
  :
else
  fail "SEMANTIC_VALIDATOR is not valid Bash: $SEMANTIC_VALIDATOR"
fi

SEMANTIC_VALIDATOR_DIR="$(
  cd "$(dirname "$SEMANTIC_VALIDATOR")" &&
    pwd -P
)"

SEMANTIC_VALIDATOR_ABS="${SEMANTIC_VALIDATOR_DIR}/$(basename "$SEMANTIC_VALIDATOR")"
SEMANTIC_VALIDATOR_CONTAINER='/tmp/telectro-semantic-validator.sh'

case "$RELEASE_ID" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f])
    ;;
  *)
    fail "RELEASE_ID must use YYYYMMDD-<7 lowercase hex> format"
    ;;
esac

if [ -x "$DOCKER_BIN" ]; then
  :
elif command -v "$DOCKER_BIN" >/dev/null 2>&1; then
  :
else
  fail "Docker command is not available: $DOCKER_BIN"
fi

IMAGE_TAG="telectro/erpnext-runtime:prod-${RELEASE_ID}"
VALIDATION_LOG="${VALIDATION_LOG:-/tmp/telectro-runtime-validation-${RELEASE_ID}.log}"

printf '%s\n' '=== Phase 5 — candidate image identity ==='

if ! IMAGE_INSPECT="$(
  "$DOCKER_BIN" image inspect \
    --format '{{.Id}}|{{.Created}}|{{.Os}}|{{.Architecture}}|{{.Size}}' \
    "$IMAGE_TAG" \
    2>&1
)"; then
  printf '%s\n' "$IMAGE_INSPECT" >&2
  fail "candidate image is unavailable: $IMAGE_TAG"
fi

IFS='|' read -r \
  IMAGE_ID \
  IMAGE_CREATED \
  IMAGE_OS \
  IMAGE_ARCHITECTURE \
  IMAGE_SIZE \
  <<<"$IMAGE_INSPECT"

[ -n "$IMAGE_ID" ] ||
  fail "candidate image ID is missing"

[ -n "$IMAGE_CREATED" ] ||
  fail "candidate image creation timestamp is missing"

[ -n "$IMAGE_SIZE" ] ||
  fail "candidate image size is missing"

[ "$IMAGE_OS" = "linux" ] ||
  fail "candidate image OS must be linux; observed: $IMAGE_OS"

[ "$IMAGE_ARCHITECTURE" = "amd64" ] ||
  fail "candidate image architecture must be amd64; observed: $IMAGE_ARCHITECTURE"

printf 'IMAGE_TAG=%s\n' "$IMAGE_TAG"
printf 'IMAGE_ID=%s\n' "$IMAGE_ID"
printf 'IMAGE_CREATED=%s\n' "$IMAGE_CREATED"
printf 'IMAGE_SIZE=%s\n' "$IMAGE_SIZE"
printf 'IMAGE_OS=%s\n' "$IMAGE_OS"
printf 'IMAGE_ARCHITECTURE=%s\n' "$IMAGE_ARCHITECTURE"
printf 'VALIDATION_LOG=%s\n' "$VALIDATION_LOG"

printf '%s\n' 'CANDIDATE_RUNTIME_PLATFORM_OK=YES'

VALIDATION_LOG_DIR="$(dirname "$VALIDATION_LOG")"

[ -d "$VALIDATION_LOG_DIR" ] ||
  fail "VALIDATION_LOG parent does not exist: $VALIDATION_LOG_DIR"

[ ! -e "$VALIDATION_LOG" ] ||
  fail "VALIDATION_LOG already exists: $VALIDATION_LOG"

run_candidate_runtime_validation() {
  "$DOCKER_BIN" run \
    --rm \
    --platform linux/amd64 \
    --entrypoint bash \
    --interactive \
    --env "EMBEDDED_CHANGE_PATH=$EMBEDDED_CHANGE_PATH" \
    --volume "${SEMANTIC_VALIDATOR_ABS}:${SEMANTIC_VALIDATOR_CONTAINER}:ro" \
    "$IMAGE_TAG" \
    -s <<'COMMAND'
set -euo pipefail

cd /home/frappe/frappe-bench

printf '%s\n' '=== Required app directories ==='

for app in frappe erpnext helpdesk telephony
do
  case "$app" in
    frappe) marker='FRAPPE_APP_PRESENT' ;;
    erpnext) marker='ERPNEXT_APP_PRESENT' ;;
    helpdesk) marker='HELPDESK_APP_PRESENT' ;;
    telephony) marker='TELEPHONY_APP_PRESENT' ;;
  esac

  if [ -d "apps/${app}" ]
  then
    printf '%s=YES\n' "$marker"
  else
    printf '%s=NO\n' "$marker"
    exit 20
  fi
done

printf '\n%s\n' '=== Python imports ==='

./env/bin/python -c 'import frappe; print("FRAPPE_IMPORT=PASS")'
./env/bin/python -c 'import erpnext; print("ERPNEXT_IMPORT=PASS")'
./env/bin/python -c 'import helpdesk; print("HELPDESK_IMPORT=PASS")'
./env/bin/python -c 'import telephony; print("TELEPHONY_IMPORT=PASS")'

printf '\n%s\n' '=== Bench versions ==='

bench version
printf '\n%s\n' '=== Embedded changed-source SHA-256 ==='

if [ ! -f "$EMBEDDED_CHANGE_PATH" ]
then
  printf 'EMBEDDED_CHANGE_FILE_PRESENT=NO\n'
  exit 21
fi

printf 'EMBEDDED_CHANGE_FILE_PRESENT=YES\n'

EMBEDDED_SOURCE_SHA256="$(
  ./env/bin/python -c \
    'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' \
    "$EMBEDDED_CHANGE_PATH"
)"

printf 'EMBEDDED_SOURCE_SHA256=%s\n' "$EMBEDDED_SOURCE_SHA256"

printf '\n%s\n' '=== Release-specific semantic validation ==='

bash /tmp/telectro-semantic-validator.sh
COMMAND
}

printf '\n%s\n' '=== Phase 5 — candidate runtime validation ==='

if run_candidate_runtime_validation \
  >"$VALIDATION_LOG" \
  2>&1
then
  VALIDATION_STATUS=0
else
  VALIDATION_STATUS=$?
fi

printf '%s\n' '=== Candidate runtime validation output ==='

if [ -f "$VALIDATION_LOG" ]
then
  cat "$VALIDATION_LOG"
else
  fail "candidate runtime validation log was not created"
fi

printf '\nVALIDATION_STATUS=%s\n' "$VALIDATION_STATUS"
printf 'VALIDATION_LOG=%s\n' "$VALIDATION_LOG"

[ "$VALIDATION_STATUS" -eq 0 ] ||
  fail "candidate runtime validation failed with status $VALIDATION_STATUS"

for marker in \
  'FRAPPE_APP_PRESENT=YES' \
  'ERPNEXT_APP_PRESENT=YES' \
  'HELPDESK_APP_PRESENT=YES' \
  'TELEPHONY_APP_PRESENT=YES' \
  'FRAPPE_IMPORT=PASS' \
  'ERPNEXT_IMPORT=PASS' \
  'HELPDESK_IMPORT=PASS' \
  'TELEPHONY_IMPORT=PASS'
do
  grep -Fqx "$marker" "$VALIDATION_LOG" ||
    fail "required runtime validation marker is missing: $marker"
done

printf '%s\n' 'CANDIDATE_RUNTIME_IMPORTS_OK=YES'

grep -Fqx \
  "frappe ${EXPECTED_FRAPPE_VERSION}" \
  "$VALIDATION_LOG" ||
  fail "frappe version mismatch; expected: ${EXPECTED_FRAPPE_VERSION}"

grep -Fqx \
  "erpnext ${EXPECTED_ERPNEXT_VERSION}" \
  "$VALIDATION_LOG" ||
  fail "erpnext version mismatch; expected: ${EXPECTED_ERPNEXT_VERSION}"

grep -Fqx \
  "helpdesk ${EXPECTED_HELPDESK_VERSION}" \
  "$VALIDATION_LOG" ||
  fail "helpdesk version mismatch; expected: ${EXPECTED_HELPDESK_VERSION}"

grep -Fqx \
  "telephony ${EXPECTED_TELEPHONY_VERSION}" \
  "$VALIDATION_LOG" ||
  fail "telephony version mismatch; expected: ${EXPECTED_TELEPHONY_VERSION}"

printf '%s\n' 'CANDIDATE_RUNTIME_VERSIONS_OK=YES'

EMBEDDED_SHA_LINE_COUNT="$(
  grep -c '^EMBEDDED_SOURCE_SHA256=' "$VALIDATION_LOG" ||
    true
)"

[ "$EMBEDDED_SHA_LINE_COUNT" -eq 1 ] ||
  fail "expected exactly one embedded source SHA-256 result"

EMBEDDED_SOURCE_SHA256="$(
  grep '^EMBEDDED_SOURCE_SHA256=' "$VALIDATION_LOG" |
    cut -d= -f2-
)"

[ "${#EMBEDDED_SOURCE_SHA256}" -eq 64 ] ||
  fail "embedded source SHA-256 is malformed"

case "$EMBEDDED_SOURCE_SHA256" in
  *[!0-9a-f]*)
    fail "embedded source SHA-256 is malformed"
    ;;
esac

printf 'EXPECTED_EMBEDDED_SHA256=%s\n' "$EXPECTED_EMBEDDED_SHA256"
printf 'EMBEDDED_SOURCE_SHA256=%s\n' "$EMBEDDED_SOURCE_SHA256"

[ "$EMBEDDED_SOURCE_SHA256" = "$EXPECTED_EMBEDDED_SHA256" ] ||
  fail "embedded source SHA-256 mismatch"

printf '%s\n' 'CANDIDATE_EMBEDDED_CHANGE_OK=YES'
printf '%s\n' 'CANDIDATE_SEMANTIC_VALIDATION_OK=YES'
printf '%s\n' 'CANDIDATE_RUNTIME_VALIDATION_OK=YES'
