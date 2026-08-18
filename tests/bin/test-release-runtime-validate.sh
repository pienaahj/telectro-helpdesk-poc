#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

HELPER="${ROOT_DIR}/bin/release-runtime-validate.sh"

KNOWN_RELEASE_ID="20260814-b946cbf"
KNOWN_IMAGE_TAG="telectro/erpnext-runtime:prod-${KNOWN_RELEASE_ID}"

KNOWN_EMBEDDED_PATH="apps/telephony/telephony/telectro_assign_sync.py"
KNOWN_EMBEDDED_SHA256="146ebd7b061d5a2b6436c31deb9283048b28128857cf7288bbb23d7d9b5300d6"

KNOWN_FRAPPE_VERSION="15.96.0"
KNOWN_ERPNEXT_VERSION="15.94.1"
KNOWN_HELPDESK_VERSION="1.18.1"
KNOWN_TELEPHONY_VERSION="0.0.1"

KNOWN_SEMANTIC_VALIDATOR="${ROOT_DIR}/bin/release-validators/validate-terminal-assignment.sh"

printf '%s\n' '=== Phase 5 runtime-validation regression ==='

if [ ! -x "$HELPER" ]; then
  printf '%s\n' 'RELEASE_RUNTIME_VALIDATE_HELPER_PRESENT=FAIL'
  printf 'EXPECTED_HELPER=%s\n' "$HELPER"
  exit 1
fi

printf '%s\n' 'RELEASE_RUNTIME_VALIDATE_HELPER_PRESENT=PASS'

printf 'KNOWN_RELEASE_ID=%s\n' "$KNOWN_RELEASE_ID"
printf 'KNOWN_IMAGE_TAG=%s\n' "$KNOWN_IMAGE_TAG"
printf 'KNOWN_EMBEDDED_PATH=%s\n' "$KNOWN_EMBEDDED_PATH"
printf 'KNOWN_EMBEDDED_SHA256=%s\n' "$KNOWN_EMBEDDED_SHA256"
printf 'KNOWN_SEMANTIC_VALIDATOR=%s\n' "$KNOWN_SEMANTIC_VALIDATOR"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

MOCK_DOCKER="${TMP_ROOT}/docker"
VALIDATION_LOG="${TMP_ROOT}/telectro-runtime-validation-${KNOWN_RELEASE_ID}.log"

MOCK_RUN_ARGS="${TMP_ROOT}/runtime-run-args.txt"
export MOCK_RUN_ARGS

cat >"$MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]; then
  if [ "$5" != "${EXPECTED_IMAGE_TAG:?}" ]; then
    printf 'unexpected image tag: %s\n' "$5" >&2
    exit 91
  fi

  printf '%s|%s|%s|%s|%s\n' \
  'sha256:c405f1267b71728891810722d627c7e6cf14126609b44f5285fb729161f1c3aa' \
  '2026-08-14T13:35:10.937000085Z' \
  "${MOCK_IMAGE_OS:-linux}" \
  "${MOCK_IMAGE_ARCHITECTURE:-amd64}" \
  '2484643782'
  exit 0
fi

if [ "$#" -ge 1 ] &&
   [ "$1" = "run" ]; then
  printf '%s\n' "$*" >"${MOCK_RUN_ARGS:?}"

  printf '%s\n' '=== Required app directories ==='
  printf '%s\n' 'FRAPPE_APP_PRESENT=YES'
  printf '%s\n' 'ERPNEXT_APP_PRESENT=YES'
  printf '%s\n' 'HELPDESK_APP_PRESENT=YES'
  printf '%s\n' 'TELEPHONY_APP_PRESENT=YES'

  printf '\n%s\n' '=== Python imports ==='
  printf '%s\n' 'FRAPPE_IMPORT=PASS'
  printf '%s\n' 'ERPNEXT_IMPORT=PASS'
  printf '%s\n' 'HELPDESK_IMPORT=PASS'
  printf '%s\n' 'TELEPHONY_IMPORT=PASS'

  printf '\n%s\n' '=== Bench versions ==='
  printf '%s\n' 'erpnext 15.94.1'
  printf 'frappe %s\n' "${MOCK_FRAPPE_VERSION:-15.96.0}"
  printf '%s\n' 'helpdesk 1.18.1'
  printf '%s\n' 'telephony 0.0.1'

  printf '\n%s\n' '=== Embedded changed-source SHA-256 ==='
  printf '%s\n' 'EMBEDDED_CHANGE_FILE_PRESENT=YES'
  printf 'EMBEDDED_SOURCE_SHA256=%s\n' \
    "${MOCK_EMBEDDED_SHA256:-146ebd7b061d5a2b6436c31deb9283048b28128857cf7288bbb23d7d9b5300d6}"

  printf '\n%s\n' '=== Release-specific semantic validation ==='

  if [ "${MOCK_SEMANTIC_FAILURE:-NO}" = "YES" ]
  then
    printf '%s\n' "TERMINAL_TICKET_STATUSES= ['Closed', 'Resolved']"
    printf '%s\n' 'TERMINAL_ASSIGNMENT_CHANGE=FAIL'
    exit 74
  fi

  printf '%s\n' "TERMINAL_TICKET_STATUSES= ['Archived', 'Closed', 'Resolved']"
  printf '%s\n' 'TERMINAL_ASSIGNMENT_CHANGE=PASS'

  exit "${MOCK_RUN_STATUS:-0}"
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$MOCK_DOCKER"

export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"

printf '\n%s\n' '=== Known-good candidate image identity ==='

if OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  EXPECTED_FRAPPE_VERSION="$KNOWN_FRAPPE_VERSION" \
  EXPECTED_ERPNEXT_VERSION="$KNOWN_ERPNEXT_VERSION" \
  EXPECTED_HELPDESK_VERSION="$KNOWN_HELPDESK_VERSION" \
  EXPECTED_TELEPHONY_VERSION="$KNOWN_TELEPHONY_VERSION" \
  EMBEDDED_CHANGE_PATH="$KNOWN_EMBEDDED_PATH" \
  EXPECTED_EMBEDDED_SHA256="$KNOWN_EMBEDDED_SHA256" \
  SEMANTIC_VALIDATOR="$KNOWN_SEMANTIC_VALIDATOR" \
  VALIDATION_LOG="$VALIDATION_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"; then
  STATUS=0
else
  STATUS=$?
fi

printf '%s\n' "$OUTPUT"
printf 'KNOWN_GOOD_IDENTITY_STATUS=%s\n' "$STATUS"

[ "$STATUS" -eq 0 ] ||
  fail "known-good candidate identity returned ${STATUS}"

grep -F \
  "IMAGE_TAG=${KNOWN_IMAGE_TAG}" \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "derived immutable image tag was not emitted"

grep -F \
  'IMAGE_ID=sha256:c405f1267b71728891810722d627c7e6cf14126609b44f5285fb729161f1c3aa' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate image ID was not emitted"

grep -F \
  'IMAGE_CREATED=2026-08-14T13:35:10.937000085Z' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate creation timestamp was not emitted"

grep -F \
  'IMAGE_SIZE=2484643782' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate image size was not emitted"

grep -F \
  'IMAGE_OS=linux' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate OS was not emitted"

grep -F \
  'IMAGE_ARCHITECTURE=amd64' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate architecture was not emitted"

grep -F \
  "VALIDATION_LOG=${VALIDATION_LOG}" \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "validation-log path was not emitted"

printf '\n%s\n' '=== Candidate runtime failure rejection ==='

RUNTIME_FAILURE_LOG="${TMP_ROOT}/runtime-failure-validation.log"

if RUNTIME_FAILURE_OUTPUT="$(
  MOCK_RUN_STATUS=73 \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  EXPECTED_FRAPPE_VERSION="$KNOWN_FRAPPE_VERSION" \
  EXPECTED_ERPNEXT_VERSION="$KNOWN_ERPNEXT_VERSION" \
  EXPECTED_HELPDESK_VERSION="$KNOWN_HELPDESK_VERSION" \
  EXPECTED_TELEPHONY_VERSION="$KNOWN_TELEPHONY_VERSION" \
  EMBEDDED_CHANGE_PATH="$KNOWN_EMBEDDED_PATH" \
  EXPECTED_EMBEDDED_SHA256="$KNOWN_EMBEDDED_SHA256" \
  SEMANTIC_VALIDATOR="$KNOWN_SEMANTIC_VALIDATOR" \
  VALIDATION_LOG="$RUNTIME_FAILURE_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"; then
  RUNTIME_FAILURE_STATUS=0
else
  RUNTIME_FAILURE_STATUS=$?
fi

printf '%s\n' "$RUNTIME_FAILURE_OUTPUT"
printf 'RUNTIME_FAILURE_STATUS=%s\n' "$RUNTIME_FAILURE_STATUS"

[ "$RUNTIME_FAILURE_STATUS" -ne 0 ] ||
  fail "failed candidate runtime validation was accepted"

test -f "$RUNTIME_FAILURE_LOG" ||
  fail "failed candidate runtime validation log was not retained"

grep -F \
  'VALIDATION_STATUS=73' \
  <<<"$RUNTIME_FAILURE_OUTPUT" \
  >/dev/null ||
  fail "candidate runtime failure status was not reported"

grep -F \
  'candidate runtime validation failed with status 73' \
  <<<"$RUNTIME_FAILURE_OUTPUT" \
  >/dev/null ||
  fail "candidate runtime failure reason was not reported"

if grep -F \
  'CANDIDATE_RUNTIME_IMPORTS_OK=YES' \
  <<<"$RUNTIME_FAILURE_OUTPUT" \
  >/dev/null
then
  fail "runtime-import success marker was emitted after candidate runtime failure"
fi

printf '%s\n' 'FAILED_CANDIDATE_RUNTIME_REJECTED=PASS'
printf '%s\n' 'FAILED_RUNTIME_LOG_RETAINED=PASS'
printf '%s\n' 'FAILED_RUNTIME_IMPORT_MARKER_SUPPRESSED=PASS'

printf '\n%s\n' '=== Wrong candidate application version rejection ==='

WRONG_VERSION_LOG="${TMP_ROOT}/wrong-version-validation.log"

if WRONG_VERSION_OUTPUT="$(
  MOCK_FRAPPE_VERSION=15.95.0 \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  EXPECTED_FRAPPE_VERSION="$KNOWN_FRAPPE_VERSION" \
  EXPECTED_ERPNEXT_VERSION="$KNOWN_ERPNEXT_VERSION" \
  EXPECTED_HELPDESK_VERSION="$KNOWN_HELPDESK_VERSION" \
  EXPECTED_TELEPHONY_VERSION="$KNOWN_TELEPHONY_VERSION" \
  EMBEDDED_CHANGE_PATH="$KNOWN_EMBEDDED_PATH" \
  EXPECTED_EMBEDDED_SHA256="$KNOWN_EMBEDDED_SHA256" \
  SEMANTIC_VALIDATOR="$KNOWN_SEMANTIC_VALIDATOR" \
  VALIDATION_LOG="$WRONG_VERSION_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"; then
  WRONG_VERSION_STATUS=0
else
  WRONG_VERSION_STATUS=$?
fi

printf '%s\n' "$WRONG_VERSION_OUTPUT"
printf 'WRONG_VERSION_STATUS=%s\n' "$WRONG_VERSION_STATUS"

[ "$WRONG_VERSION_STATUS" -ne 0 ] ||
  fail "candidate with wrong frappe version was accepted"

test -f "$WRONG_VERSION_LOG" ||
  fail "wrong-version validation log was not retained"

grep -Fqx \
  'frappe 15.95.0' \
  "$WRONG_VERSION_LOG" \
  >/dev/null ||
  fail "wrong observed frappe version was not retained"

grep -F \
  'frappe version mismatch; expected: 15.96.0' \
  <<<"$WRONG_VERSION_OUTPUT" \
  >/dev/null ||
  fail "frappe version mismatch reason was not reported"

grep -F \
  'CANDIDATE_RUNTIME_IMPORTS_OK=YES' \
  <<<"$WRONG_VERSION_OUTPUT" \
  >/dev/null ||
  fail "successful import proof was lost during version rejection"

if grep -F \
  'CANDIDATE_RUNTIME_VERSIONS_OK=YES' \
  <<<"$WRONG_VERSION_OUTPUT" \
  >/dev/null
then
  fail "runtime-version success marker was emitted for wrong frappe version"
fi

printf '%s\n' 'WRONG_CANDIDATE_VERSION_REJECTED=PASS'
printf '%s\n' 'WRONG_VERSION_LOG_RETAINED=PASS'
printf '%s\n' 'WRONG_VERSION_IMPORT_PROOF_PRESERVED=PASS'
printf '%s\n' 'WRONG_VERSION_MARKER_SUPPRESSED=PASS'

grep -F \
  'CANDIDATE_RUNTIME_PLATFORM_OK=YES' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate platform marker was not emitted"

test -f "$VALIDATION_LOG" ||
  fail "candidate runtime validation log was not created"

for APP_MARKER in \
  'FRAPPE_APP_PRESENT=YES' \
  'ERPNEXT_APP_PRESENT=YES' \
  'HELPDESK_APP_PRESENT=YES' \
  'TELEPHONY_APP_PRESENT=YES'
do
  grep -F \
    "$APP_MARKER" \
    "$VALIDATION_LOG" \
    >/dev/null ||
    fail "required app-directory marker is missing: $APP_MARKER"
done

for IMPORT_MARKER in \
  'FRAPPE_IMPORT=PASS' \
  'ERPNEXT_IMPORT=PASS' \
  'HELPDESK_IMPORT=PASS' \
  'TELEPHONY_IMPORT=PASS'
do
  grep -F \
    "$IMPORT_MARKER" \
    "$VALIDATION_LOG" \
    >/dev/null ||
    fail "required Python-import marker is missing: $IMPORT_MARKER"
done

grep -F \
  'CANDIDATE_RUNTIME_IMPORTS_OK=YES' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate runtime-import marker was not emitted"

for VERSION_LINE in \
  "frappe ${KNOWN_FRAPPE_VERSION}" \
  "erpnext ${KNOWN_ERPNEXT_VERSION}" \
  "helpdesk ${KNOWN_HELPDESK_VERSION}" \
  "telephony ${KNOWN_TELEPHONY_VERSION}"
do
  grep -Fqx \
    "$VERSION_LINE" \
    "$VALIDATION_LOG" \
    >/dev/null ||
    fail "expected application version is missing: $VERSION_LINE"
done

grep -F \
  'CANDIDATE_RUNTIME_VERSIONS_OK=YES' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate runtime-version marker was not emitted"

grep -Fqx \
  "EMBEDDED_SOURCE_SHA256=${KNOWN_EMBEDDED_SHA256}" \
  "$VALIDATION_LOG" \
  >/dev/null ||
  fail "expected embedded changed-source SHA-256 is missing"

grep -F \
  'CANDIDATE_EMBEDDED_CHANGE_OK=YES' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate embedded-change marker was not emitted"

grep -Fqx \
  "TERMINAL_TICKET_STATUSES= ['Archived', 'Closed', 'Resolved']" \
  "$VALIDATION_LOG" \
  >/dev/null ||
  fail "terminal-assignment status semantic proof is missing"

grep -Fqx \
  'TERMINAL_ASSIGNMENT_CHANGE=PASS' \
  "$VALIDATION_LOG" \
  >/dev/null ||
  fail "terminal-assignment semantic PASS proof is missing"

grep -F \
  'CANDIDATE_SEMANTIC_VALIDATION_OK=YES' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "candidate semantic-validation marker was not emitted"

grep -F \
  'CANDIDATE_RUNTIME_VALIDATION_OK=YES' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "final candidate runtime-validation marker was not emitted"

printf '%s\n' 'KNOWN_GOOD_CANDIDATE_IDENTITY=PASS'
printf '%s\n' 'KNOWN_GOOD_RUNTIME_CONTAINER=PASS'

printf '\n%s\n' '=== Wrong embedded changed-source SHA rejection ==='

WRONG_EMBEDDED_SHA_LOG="${TMP_ROOT}/wrong-embedded-sha-validation.log"
WRONG_EXPECTED_EMBEDDED_SHA256="046ebd7b061d5a2b6436c31deb9283048b28128857cf7288bbb23d7d9b5300d6"

if WRONG_EMBEDDED_SHA_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  EXPECTED_FRAPPE_VERSION="$KNOWN_FRAPPE_VERSION" \
  EXPECTED_ERPNEXT_VERSION="$KNOWN_ERPNEXT_VERSION" \
  EXPECTED_HELPDESK_VERSION="$KNOWN_HELPDESK_VERSION" \
  EXPECTED_TELEPHONY_VERSION="$KNOWN_TELEPHONY_VERSION" \
  EMBEDDED_CHANGE_PATH="$KNOWN_EMBEDDED_PATH" \
  EXPECTED_EMBEDDED_SHA256="$WRONG_EXPECTED_EMBEDDED_SHA256" \
  SEMANTIC_VALIDATOR="$KNOWN_SEMANTIC_VALIDATOR" \
  VALIDATION_LOG="$WRONG_EMBEDDED_SHA_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"; then
  WRONG_EMBEDDED_SHA_STATUS=0
else
  WRONG_EMBEDDED_SHA_STATUS=$?
fi

printf '%s\n' "$WRONG_EMBEDDED_SHA_OUTPUT"
printf 'WRONG_EMBEDDED_SHA_STATUS=%s\n' "$WRONG_EMBEDDED_SHA_STATUS"

[ "$WRONG_EMBEDDED_SHA_STATUS" -ne 0 ] ||
  fail "candidate with wrong expected embedded SHA-256 was accepted"

test -f "$WRONG_EMBEDDED_SHA_LOG" ||
  fail "wrong embedded-SHA validation log was not retained"

grep -Fqx \
  "EMBEDDED_SOURCE_SHA256=${KNOWN_EMBEDDED_SHA256}" \
  "$WRONG_EMBEDDED_SHA_LOG" \
  >/dev/null ||
  fail "actual embedded SHA-256 was not retained"

grep -F \
  'embedded source SHA-256 mismatch' \
  <<<"$WRONG_EMBEDDED_SHA_OUTPUT" \
  >/dev/null ||
  fail "embedded SHA-256 mismatch reason was not reported"

grep -F \
  'CANDIDATE_RUNTIME_IMPORTS_OK=YES' \
  <<<"$WRONG_EMBEDDED_SHA_OUTPUT" \
  >/dev/null ||
  fail "import proof was lost during embedded SHA rejection"

grep -F \
  'CANDIDATE_RUNTIME_VERSIONS_OK=YES' \
  <<<"$WRONG_EMBEDDED_SHA_OUTPUT" \
  >/dev/null ||
  fail "version proof was lost during embedded SHA rejection"

if grep -F \
  'CANDIDATE_EMBEDDED_CHANGE_OK=YES' \
  <<<"$WRONG_EMBEDDED_SHA_OUTPUT" \
  >/dev/null
then
  fail "embedded-change success marker was emitted for wrong expected SHA-256"
fi

printf '%s\n' 'WRONG_EMBEDDED_SHA_REJECTED=PASS'
printf '%s\n' 'WRONG_EMBEDDED_SHA_LOG_RETAINED=PASS'
printf '%s\n' 'WRONG_EMBEDDED_SHA_PRIOR_PROOFS_PRESERVED=PASS'
printf '%s\n' 'WRONG_EMBEDDED_SHA_MARKER_SUPPRESSED=PASS'

printf '\n%s\n' '=== Semantic validator failure rejection ==='

SEMANTIC_FAILURE_LOG="${TMP_ROOT}/semantic-failure-validation.log"

if SEMANTIC_FAILURE_OUTPUT="$(
  MOCK_SEMANTIC_FAILURE=YES \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  EXPECTED_FRAPPE_VERSION="$KNOWN_FRAPPE_VERSION" \
  EXPECTED_ERPNEXT_VERSION="$KNOWN_ERPNEXT_VERSION" \
  EXPECTED_HELPDESK_VERSION="$KNOWN_HELPDESK_VERSION" \
  EXPECTED_TELEPHONY_VERSION="$KNOWN_TELEPHONY_VERSION" \
  EMBEDDED_CHANGE_PATH="$KNOWN_EMBEDDED_PATH" \
  EXPECTED_EMBEDDED_SHA256="$KNOWN_EMBEDDED_SHA256" \
  SEMANTIC_VALIDATOR="$KNOWN_SEMANTIC_VALIDATOR" \
  VALIDATION_LOG="$SEMANTIC_FAILURE_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"; then
  SEMANTIC_FAILURE_STATUS=0
else
  SEMANTIC_FAILURE_STATUS=$?
fi

printf '%s\n' "$SEMANTIC_FAILURE_OUTPUT"
printf 'SEMANTIC_FAILURE_STATUS=%s\n' "$SEMANTIC_FAILURE_STATUS"

[ "$SEMANTIC_FAILURE_STATUS" -ne 0 ] ||
  fail "failed semantic validation was accepted"

test -f "$SEMANTIC_FAILURE_LOG" ||
  fail "failed semantic-validation log was not retained"

grep -Fqx \
  'TERMINAL_ASSIGNMENT_CHANGE=FAIL' \
  "$SEMANTIC_FAILURE_LOG" \
  >/dev/null ||
  fail "semantic failure evidence was not retained"

grep -F \
  'VALIDATION_STATUS=74' \
  <<<"$SEMANTIC_FAILURE_OUTPUT" \
  >/dev/null ||
  fail "semantic validator failure status was not reported"

grep -F \
  'candidate runtime validation failed with status 74' \
  <<<"$SEMANTIC_FAILURE_OUTPUT" \
  >/dev/null ||
  fail "semantic validator failure reason was not reported"

if grep -F \
  'CANDIDATE_SEMANTIC_VALIDATION_OK=YES' \
  <<<"$SEMANTIC_FAILURE_OUTPUT" \
  >/dev/null
then
  fail "semantic success marker was emitted after semantic failure"
fi

printf '%s\n' 'FAILED_SEMANTIC_VALIDATION_REJECTED=PASS'
printf '%s\n' 'FAILED_SEMANTIC_LOG_RETAINED=PASS'
printf '%s\n' 'FAILED_SEMANTIC_MARKER_SUPPRESSED=PASS'

printf '\n%s\n' '=== Wrong candidate architecture rejection ==='

WRONG_ARCH_LOG="${TMP_ROOT}/wrong-architecture-validation.log"

if WRONG_ARCH_OUTPUT="$(
  MOCK_IMAGE_ARCHITECTURE=arm64 \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  EXPECTED_FRAPPE_VERSION="$KNOWN_FRAPPE_VERSION" \
  EXPECTED_ERPNEXT_VERSION="$KNOWN_ERPNEXT_VERSION" \
  EXPECTED_HELPDESK_VERSION="$KNOWN_HELPDESK_VERSION" \
  EXPECTED_TELEPHONY_VERSION="$KNOWN_TELEPHONY_VERSION" \
  EMBEDDED_CHANGE_PATH="$KNOWN_EMBEDDED_PATH" \
  EXPECTED_EMBEDDED_SHA256="$KNOWN_EMBEDDED_SHA256" \
  SEMANTIC_VALIDATOR="$KNOWN_SEMANTIC_VALIDATOR" \
  VALIDATION_LOG="$WRONG_ARCH_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"; then
  WRONG_ARCH_STATUS=0
else
  WRONG_ARCH_STATUS=$?
fi

printf '%s\n' "$WRONG_ARCH_OUTPUT"
printf 'WRONG_ARCH_STATUS=%s\n' "$WRONG_ARCH_STATUS"

[ "$WRONG_ARCH_STATUS" -ne 0 ] ||
  fail "arm64 candidate image was not rejected"

grep -F \
  'candidate image architecture must be amd64; observed: arm64' \
  <<<"$WRONG_ARCH_OUTPUT" \
  >/dev/null ||
  fail "wrong-architecture rejection reason was not reported"

if grep -F \
  'CANDIDATE_RUNTIME_PLATFORM_OK=YES' \
  <<<"$WRONG_ARCH_OUTPUT" \
  >/dev/null
then
  fail "platform success marker was emitted for arm64 candidate"
fi

[ ! -e "$WRONG_ARCH_LOG" ] ||
  fail "architecture rejection unexpectedly created validation log"

printf '%s\n' 'WRONG_CANDIDATE_ARCHITECTURE_REJECTED=PASS'
printf '%s\n' 'WRONG_ARCH_PLATFORM_MARKER_SUPPRESSED=PASS'
printf '\n%s\n' '=== Wrong candidate OS rejection ==='

WRONG_OS_LOG="${TMP_ROOT}/wrong-os-validation.log"

if WRONG_OS_OUTPUT="$(
  MOCK_IMAGE_OS=windows \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  EXPECTED_FRAPPE_VERSION="$KNOWN_FRAPPE_VERSION" \
  EXPECTED_ERPNEXT_VERSION="$KNOWN_ERPNEXT_VERSION" \
  EXPECTED_HELPDESK_VERSION="$KNOWN_HELPDESK_VERSION" \
  EXPECTED_TELEPHONY_VERSION="$KNOWN_TELEPHONY_VERSION" \
  EMBEDDED_CHANGE_PATH="$KNOWN_EMBEDDED_PATH" \
  EXPECTED_EMBEDDED_SHA256="$KNOWN_EMBEDDED_SHA256" \
  SEMANTIC_VALIDATOR="$KNOWN_SEMANTIC_VALIDATOR" \
  VALIDATION_LOG="$WRONG_OS_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"; then
  WRONG_OS_STATUS=0
else
  WRONG_OS_STATUS=$?
fi

printf '%s\n' "$WRONG_OS_OUTPUT"
printf 'WRONG_OS_STATUS=%s\n' "$WRONG_OS_STATUS"

[ "$WRONG_OS_STATUS" -ne 0 ] ||
  fail "non-linux candidate image was not rejected"

grep -F \
  'candidate image OS must be linux; observed: windows' \
  <<<"$WRONG_OS_OUTPUT" \
  >/dev/null ||
  fail "wrong-OS rejection reason was not reported"

if grep -F \
  'CANDIDATE_RUNTIME_PLATFORM_OK=YES' \
  <<<"$WRONG_OS_OUTPUT" \
  >/dev/null
then
  fail "platform success marker was emitted for non-linux candidate"
fi

[ ! -e "$WRONG_OS_LOG" ] ||
  fail "OS rejection unexpectedly created validation log"

test -f "$MOCK_RUN_ARGS" ||
  fail "isolated candidate container was not invoked"

grep -F \
  'run --rm --platform linux/amd64 --entrypoint bash' \
  "$MOCK_RUN_ARGS" \
  >/dev/null ||
  fail "candidate validation did not use isolated linux/amd64 container"

grep -F \
  "$KNOWN_IMAGE_TAG" \
  "$MOCK_RUN_ARGS" \
  >/dev/null ||
  fail "candidate validation container did not use expected image"

printf '%s\n' 'WRONG_CANDIDATE_OS_REJECTED=PASS'
printf '%s\n' 'WRONG_OS_PLATFORM_MARKER_SUPPRESSED=PASS'
printf '%s\n' 'RELEASE_RUNTIME_VALIDATE_REGRESSION=PASS'
