#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

HELPER="${ROOT_DIR}/bin/release-runtime-build.sh"
SOURCE_ARTIFACT_HELPER="${ROOT_DIR}/bin/release-source-artifact.sh"

KNOWN_RELEASE_ID="20260814-b946cbf"
KNOWN_FULL_COMMIT_SHA="b946cbf7ae23b628a261ac0702577b5f7323c222"
KNOWN_SOURCE_TAR_SHA256="5d95fbc2ba1f1e9a4da7f3bb49e13b9620b1e6b4aeaa65aeb8afb07b817815d8"
KNOWN_IMAGE_TAG="telectro/erpnext-runtime:prod-${KNOWN_RELEASE_ID}"
KNOWN_BUILDER="recordingdepov2-builder"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

SOURCE_ARTIFACT="${TMP_ROOT}/telectro-app-${KNOWN_RELEASE_ID}.tar.gz"
BUILD_LOG="${TMP_ROOT}/telectro-runtime-build-${KNOWN_RELEASE_ID}.log"
MOCK_DOCKER="${TMP_ROOT}/docker"
MOCK_BUILD_ARGS="${TMP_ROOT}/build-args.txt"

printf '%s\n' '=== Phase 4 runtime-build regression ==='

test -x "$SOURCE_ARTIFACT_HELPER" ||
  fail "source-artifact helper is missing or not executable"

if [ ! -x "$HELPER" ]; then
  printf '%s\n' 'RELEASE_RUNTIME_BUILD_HELPER_PRESENT=FAIL'
  printf 'EXPECTED_HELPER=%s\n' "$HELPER"
  exit 1
fi

printf '%s\n' 'RELEASE_RUNTIME_BUILD_HELPER_PRESENT=PASS'

printf '\n%s\n' '=== Prepare known-good 2026-08-14 source artifact ==='

RELEASE_ID="$KNOWN_RELEASE_ID" \
FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
  "$SOURCE_ARTIFACT_HELPER" \
  >"${TMP_ROOT}/source-artifact.out"

test -f "$SOURCE_ARTIFACT" ||
  fail "known-good source artifact was not created"

grep -F \
  "SOURCE_TAR_SHA256=${KNOWN_SOURCE_TAR_SHA256}" \
  "${TMP_ROOT}/source-artifact.out" \
  >/dev/null ||
  fail "known-good source tar SHA-256 was not reproduced"

printf '%s\n' 'KNOWN_GOOD_SOURCE_ARTIFACT=PASS'

printf '\n%s\n' '=== Install isolated Docker mock ==='

cat >"$MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ge 2 ] &&
   [ "$1" = "buildx" ] &&
   [ "$2" = "inspect" ]; then
  if [ "${3:-}" != "${EXPECTED_BUILDER:?}" ]; then
    printf 'unexpected builder: %s\n' "${3:-}" >&2
    exit 91
  fi

  printf 'Name: %s\n' "$3"
  printf '%s\n' 'Driver: docker-container'
  printf '%s\n' 'Status: running'
  printf '%s\n' 'Platforms: linux/amd64, linux/arm64'
  exit 0
fi

if [ "$#" -ge 2 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ]; then
  if [ "${MOCK_TAG_EXISTS:-NO}" = "YES" ]; then
    printf '%s\n' 'mock-existing-image'
    exit 0
  fi

  exit 1
fi

if [ "$#" -ge 2 ] &&
   [ "$1" = "buildx" ] &&
   [ "$2" = "build" ]; then
  printf '%s\n' "$*" >"${MOCK_BUILD_ARGS:?}"
  printf '%s\n' 'MOCK_RUNTIME_BUILD_OUTPUT'
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$MOCK_DOCKER"

export EXPECTED_BUILDER="$KNOWN_BUILDER"
export MOCK_BUILD_ARGS

printf '%s\n' 'DOCKER_MOCK_READY=PASS'

printf '\n%s\n' '=== Known-good Phase 4 build ==='

if OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
  SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
  SOURCE_TAR_SHA256="$KNOWN_SOURCE_TAR_SHA256" \
  BUILDX_BUILDER="$KNOWN_BUILDER" \
  BUILD_LOG="$BUILD_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
  TMPDIR="$TMP_ROOT" \
    "$HELPER" \
    2>&1
)"; then
  STATUS=0
else
  STATUS=$?
fi

printf '%s\n' "$OUTPUT"
printf 'KNOWN_GOOD_BUILD_STATUS=%s\n' "$STATUS"

[ "$STATUS" -eq 0 ] ||
  fail "known-good runtime build returned ${STATUS}"

grep -F \
  "IMAGE_TAG=${KNOWN_IMAGE_TAG}" \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "expected immutable image tag was not emitted"

grep -F \
  "BUILD_PLATFORM=linux/amd64" \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "expected build platform was not emitted"

grep -F \
  "BUILDX_BUILDER=${KNOWN_BUILDER}" \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "expected builder was not emitted"

grep -F \
  "BUILD_LOG=${BUILD_LOG}" \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "expected build log path was not emitted"

grep -F \
  'CANDIDATE_RUNTIME_IMAGE_BUILD_OK=YES' \
  <<<"$OUTPUT" \
  >/dev/null ||
  fail "successful build marker was not emitted"

test -f "$BUILD_LOG" ||
  fail "build log was not retained"

grep -F \
  'MOCK_RUNTIME_BUILD_OUTPUT' \
  "$BUILD_LOG" \
  >/dev/null ||
  fail "complete build output was not retained"

test -f "$MOCK_BUILD_ARGS" ||
  fail "mock Docker build was not invoked"

grep -F \
  "buildx build --builder ${KNOWN_BUILDER}" \
  "$MOCK_BUILD_ARGS" \
  >/dev/null ||
  fail "expected explicit Buildx builder was not used"

grep -F \
  -- '--platform linux/amd64' \
  "$MOCK_BUILD_ARGS" \
  >/dev/null ||
  fail "linux/amd64 was not requested"

grep -F \
  -- '--progress plain' \
  "$MOCK_BUILD_ARGS" \
  >/dev/null ||
  fail "plain build progress was not requested"

grep -F \
  -- '--load' \
  "$MOCK_BUILD_ARGS" \
  >/dev/null ||
  fail "candidate image was not requested for local load"

grep -F \
  -- "--tag ${KNOWN_IMAGE_TAG}" \
  "$MOCK_BUILD_ARGS" \
  >/dev/null ||
  fail "expected immutable candidate tag was not used"

grep -F \
  'docker/telectro-runtime.Dockerfile' \
  "$MOCK_BUILD_ARGS" \
  >/dev/null ||
  fail "runtime Dockerfile was not used"

printf '%s\n' 'KNOWN_GOOD_RUNTIME_BUILD=PASS'
printf '\n%s\n' '=== Existing candidate tag rejection ==='

EXISTING_TAG_BUILD_LOG="${TMP_ROOT}/existing-tag-build.log"
EXISTING_TAG_BUILD_ARGS="${TMP_ROOT}/existing-tag-build-args.txt"

rm -f "$MOCK_BUILD_ARGS"

if EXISTING_TAG_OUTPUT="$(
  MOCK_TAG_EXISTS=YES \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
  SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
  SOURCE_TAR_SHA256="$KNOWN_SOURCE_TAR_SHA256" \
  BUILDX_BUILDER="$KNOWN_BUILDER" \
  BUILD_LOG="$EXISTING_TAG_BUILD_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
  MOCK_BUILD_ARGS="$EXISTING_TAG_BUILD_ARGS" \
  TMPDIR="$TMP_ROOT" \
    "$HELPER" \
    2>&1
)"; then
  EXISTING_TAG_STATUS=0
else
  EXISTING_TAG_STATUS=$?
fi

printf '%s\n' "$EXISTING_TAG_OUTPUT"
printf 'EXISTING_TAG_STATUS=%s\n' "$EXISTING_TAG_STATUS"

[ "$EXISTING_TAG_STATUS" -ne 0 ] ||
  fail "existing candidate tag was not rejected"

grep -F \
  "candidate image tag already exists locally: ${KNOWN_IMAGE_TAG}" \
  <<<"$EXISTING_TAG_OUTPUT" \
  >/dev/null ||
  fail "existing-tag rejection reason was not reported"

[ ! -e "$EXISTING_TAG_BUILD_LOG" ] ||
  fail "existing-tag rejection created a build log"

[ ! -e "$EXISTING_TAG_BUILD_ARGS" ] ||
  fail "Docker build was invoked despite existing candidate tag"

printf '%s\n' 'EXISTING_CANDIDATE_TAG_REJECTED=PASS'
printf '\n%s\n' '=== Source tar SHA mismatch rejection ==='

BAD_SOURCE_TAR_SHA256="0000000000000000000000000000000000000000000000000000000000000000"
BAD_HASH_BUILD_LOG="${TMP_ROOT}/bad-hash-build.log"
NO_DOCKER="${TMP_ROOT}/docker-must-not-run"
NO_DOCKER_MARKER="${TMP_ROOT}/docker-was-called"

cat >"$NO_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

: >"${NO_DOCKER_MARKER:?}"

printf '%s\n' \
  'Docker must not be invoked when source artifact identity is invalid' \
  >&2

exit 99
MOCK

chmod +x "$NO_DOCKER"
export NO_DOCKER_MARKER

if BAD_HASH_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
  SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
  SOURCE_TAR_SHA256="$BAD_SOURCE_TAR_SHA256" \
  BUILDX_BUILDER="$KNOWN_BUILDER" \
  BUILD_LOG="$BAD_HASH_BUILD_LOG" \
  DOCKER_BIN="$NO_DOCKER" \
  TMPDIR="$TMP_ROOT" \
    "$HELPER" \
    2>&1
)"; then
  BAD_HASH_STATUS=0
else
  BAD_HASH_STATUS=$?
fi

printf '%s\n' "$BAD_HASH_OUTPUT"
printf 'BAD_SOURCE_TAR_SHA_STATUS=%s\n' "$BAD_HASH_STATUS"

[ "$BAD_HASH_STATUS" -ne 0 ] ||
  fail "incorrect source tar SHA-256 was not rejected"

grep -F \
  'source tar SHA-256 does not match expected value' \
  <<<"$BAD_HASH_OUTPUT" \
  >/dev/null ||
  fail "source tar SHA mismatch reason was not reported"

[ ! -e "$NO_DOCKER_MARKER" ] ||
  fail "Docker was invoked despite invalid source artifact identity"

[ ! -e "$BAD_HASH_BUILD_LOG" ] ||
  fail "source SHA rejection created a build log"

if find "$TMP_ROOT" \
  -maxdepth 1 \
  -type d \
  -name "telectro-runtime-build.${KNOWN_RELEASE_ID}.*" \
  -print |
  grep -q .
then
  fail "temporary build root remained after rejected source artifact"
fi

printf '%s\n' 'SOURCE_TAR_SHA_MISMATCH_REJECTED=PASS'
printf '%s\n' 'INVALID_SOURCE_DOCKER_NOT_INVOKED=PASS'
printf '%s\n' 'REJECTED_BUILD_CONTEXT_CLEANED=PASS'
printf '\n%s\n' '=== Unavailable Buildx builder rejection ==='

UNAVAILABLE_BUILDER_DOCKER="${TMP_ROOT}/docker-builder-unavailable"
UNAVAILABLE_BUILDER_LOG="${TMP_ROOT}/builder-unavailable-build.log"
UNEXPECTED_DOCKER_MARKER="${TMP_ROOT}/docker-called-after-builder-failure"

cat >"$UNAVAILABLE_BUILDER_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ge 2 ] &&
   [ "$1" = "buildx" ] &&
   [ "$2" = "inspect" ]; then
  printf '%s\n' 'mock: builder unavailable' >&2
  exit 44
fi

: >"${UNEXPECTED_DOCKER_MARKER:?}"

printf 'unexpected Docker call after builder failure:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2

exit 98
MOCK

chmod +x "$UNAVAILABLE_BUILDER_DOCKER"
export UNEXPECTED_DOCKER_MARKER

if UNAVAILABLE_BUILDER_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
  SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
  SOURCE_TAR_SHA256="$KNOWN_SOURCE_TAR_SHA256" \
  BUILDX_BUILDER="$KNOWN_BUILDER" \
  BUILD_LOG="$UNAVAILABLE_BUILDER_LOG" \
  DOCKER_BIN="$UNAVAILABLE_BUILDER_DOCKER" \
  TMPDIR="$TMP_ROOT" \
    "$HELPER" \
    2>&1
)"; then
  UNAVAILABLE_BUILDER_STATUS=0
else
  UNAVAILABLE_BUILDER_STATUS=$?
fi

printf '%s\n' "$UNAVAILABLE_BUILDER_OUTPUT"
printf 'UNAVAILABLE_BUILDER_STATUS=%s\n' "$UNAVAILABLE_BUILDER_STATUS"

[ "$UNAVAILABLE_BUILDER_STATUS" -ne 0 ] ||
  fail "unavailable Buildx builder was not rejected"

grep -F \
  'mock: builder unavailable' \
  <<<"$UNAVAILABLE_BUILDER_OUTPUT" \
  >/dev/null ||
  fail "builder inspection failure output was not preserved"

grep -F \
  "Buildx builder is unavailable: ${KNOWN_BUILDER}" \
  <<<"$UNAVAILABLE_BUILDER_OUTPUT" \
  >/dev/null ||
  fail "builder-unavailable rejection reason was not reported"

[ ! -e "$UNEXPECTED_DOCKER_MARKER" ] ||
  fail "Docker continued after Buildx builder inspection failed"

[ ! -e "$UNAVAILABLE_BUILDER_LOG" ] ||
  fail "builder rejection created a build log"

if find "$TMP_ROOT" \
  -maxdepth 1 \
  -type d \
  -name "telectro-runtime-build.${KNOWN_RELEASE_ID}.*" \
  -print |
  grep -q .
then
  fail "temporary build root remained after builder rejection"
fi

printf '%s\n' 'UNAVAILABLE_BUILDX_BUILDER_REJECTED=PASS'
printf '%s\n' 'BUILDER_FAILURE_STOPPED_DOCKER_FLOW=PASS'
printf '%s\n' 'BUILDER_FAILURE_CONTEXT_CLEANED=PASS'
printf '\n%s\n' '=== Buildx builder without linux/amd64 rejection ==='

WRONG_PLATFORM_DOCKER="${TMP_ROOT}/docker-wrong-platform"
WRONG_PLATFORM_BUILD_LOG="${TMP_ROOT}/wrong-platform-build.log"
WRONG_PLATFORM_DOCKER_MARKER="${TMP_ROOT}/docker-called-after-platform-rejection"

cat >"$WRONG_PLATFORM_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ge 2 ] &&
   [ "$1" = "buildx" ] &&
   [ "$2" = "inspect" ]; then
  printf '%s\n' 'Name: arm-only-builder'
  printf '%s\n' 'Driver: docker-container'
  printf '%s\n' 'Status: running'
  printf '%s\n' 'Platforms: linux/amd64/v2, linux/arm64'
  exit 0
fi

: >"${WRONG_PLATFORM_DOCKER_MARKER:?}"

printf 'unexpected Docker call after platform rejection:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2

exit 97
MOCK

chmod +x "$WRONG_PLATFORM_DOCKER"
export WRONG_PLATFORM_DOCKER_MARKER

if WRONG_PLATFORM_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
  SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
  SOURCE_TAR_SHA256="$KNOWN_SOURCE_TAR_SHA256" \
  BUILDX_BUILDER="arm-only-builder" \
  BUILD_LOG="$WRONG_PLATFORM_BUILD_LOG" \
  DOCKER_BIN="$WRONG_PLATFORM_DOCKER" \
  TMPDIR="$TMP_ROOT" \
    "$HELPER" \
    2>&1
)"; then
  WRONG_PLATFORM_STATUS=0
else
  WRONG_PLATFORM_STATUS=$?
fi

printf '%s\n' "$WRONG_PLATFORM_OUTPUT"
printf 'WRONG_PLATFORM_STATUS=%s\n' "$WRONG_PLATFORM_STATUS"

[ "$WRONG_PLATFORM_STATUS" -ne 0 ] ||
  fail "Buildx builder without linux/amd64 was not rejected"

grep -F \
  'Platforms: linux/amd64/v2, linux/arm64' \
  <<<"$WRONG_PLATFORM_OUTPUT" \
  >/dev/null ||
  fail "builder platform inspection output was not preserved"

grep -F \
  'Buildx builder does not advertise linux/amd64' \
  <<<"$WRONG_PLATFORM_OUTPUT" \
  >/dev/null ||
  fail "missing-linux/amd64 rejection reason was not reported"

[ ! -e "$WRONG_PLATFORM_DOCKER_MARKER" ] ||
  fail "Docker continued after builder platform rejection"

[ ! -e "$WRONG_PLATFORM_BUILD_LOG" ] ||
  fail "builder platform rejection created a build log"

if find "$TMP_ROOT" \
  -maxdepth 1 \
  -type d \
  -name "telectro-runtime-build.${KNOWN_RELEASE_ID}.*" \
  -print |
  grep -q .
then
  fail "temporary build root remained after builder platform rejection"
fi

printf '%s\n' 'BUILDX_AMD64_CAPABILITY_REQUIRED=PASS'
printf '%s\n' 'WRONG_PLATFORM_STOPPED_DOCKER_FLOW=PASS'
printf '%s\n' 'WRONG_PLATFORM_CONTEXT_CLEANED=PASS'
printf '\n%s\n' '=== Runtime build failure propagation ==='

FAILED_BUILD_DOCKER="${TMP_ROOT}/docker-build-fails"
FAILED_BUILD_LOG="${TMP_ROOT}/failed-runtime-build.log"

cat >"$FAILED_BUILD_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ge 2 ] &&
   [ "$1" = "buildx" ] &&
   [ "$2" = "inspect" ]; then
  printf '%s\n' 'Name: recordingdepov2-builder'
  printf '%s\n' 'Driver: docker-container'
  printf '%s\n' 'Status: running'
  printf '%s\n' 'Platforms: linux/amd64, linux/arm64'
  exit 0
fi

if [ "$#" -ge 2 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ]; then
  exit 1
fi

if [ "$#" -ge 2 ] &&
   [ "$1" = "buildx" ] &&
   [ "$2" = "build" ]; then
  printf '%s\n' 'MOCK_BUILD_STARTED'
  printf '%s\n' 'MOCK_BUILD_FAILURE_DETAIL' >&2
  exit 73
fi

printf 'unexpected Docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2

exit 96
MOCK

chmod +x "$FAILED_BUILD_DOCKER"

if FAILED_BUILD_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
  SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
  SOURCE_TAR_SHA256="$KNOWN_SOURCE_TAR_SHA256" \
  BUILDX_BUILDER="$KNOWN_BUILDER" \
  BUILD_LOG="$FAILED_BUILD_LOG" \
  DOCKER_BIN="$FAILED_BUILD_DOCKER" \
  TMPDIR="$TMP_ROOT" \
    "$HELPER" \
    2>&1
)"; then
  FAILED_BUILD_STATUS=0
else
  FAILED_BUILD_STATUS=$?
fi

printf '%s\n' "$FAILED_BUILD_OUTPUT"
printf 'FAILED_BUILD_HELPER_STATUS=%s\n' "$FAILED_BUILD_STATUS"

[ "$FAILED_BUILD_STATUS" -ne 0 ] ||
  fail "failed runtime build was reported as successful"

grep -F \
  'BUILD_STATUS=73' \
  <<<"$FAILED_BUILD_OUTPUT" \
  >/dev/null ||
  fail "Docker build failure status was not preserved"

grep -F \
  'BUILD_LOG_STATUS=0' \
  <<<"$FAILED_BUILD_OUTPUT" \
  >/dev/null ||
  fail "successful build-log capture status was not reported"

grep -F \
  'runtime image build failed with status 73' \
  <<<"$FAILED_BUILD_OUTPUT" \
  >/dev/null ||
  fail "runtime build failure reason was not reported"

if grep -F \
  'CANDIDATE_RUNTIME_IMAGE_BUILD_OK=YES' \
  <<<"$FAILED_BUILD_OUTPUT" \
  >/dev/null
then
  fail "successful runtime-build marker was emitted after build failure"
fi

test -f "$FAILED_BUILD_LOG" ||
  fail "failed runtime build did not retain its build log"

grep -F \
  'MOCK_BUILD_STARTED' \
  "$FAILED_BUILD_LOG" \
  >/dev/null ||
  fail "failed build stdout was not retained"

grep -F \
  'MOCK_BUILD_FAILURE_DETAIL' \
  "$FAILED_BUILD_LOG" \
  >/dev/null ||
  fail "failed build stderr was not retained"

if find "$TMP_ROOT" \
  -maxdepth 1 \
  -type d \
  -name "telectro-runtime-build.${KNOWN_RELEASE_ID}.*" \
  -print |
  grep -q .
then
  fail "temporary build root remained after failed runtime build"
fi

printf '%s\n' 'FAILED_RUNTIME_BUILD_REJECTED=PASS'
printf '%s\n' 'BUILD_PIPESTATUS_PRESERVED=PASS'
printf '%s\n' 'FAILED_BUILD_LOG_RETAINED=PASS'
printf '%s\n' 'FAILED_BUILD_CONTEXT_CLEANED=PASS'
printf '\n%s\n' '=== Build-log capture failure propagation ==='

TEE_FAILURE_BIN_DIR="${TMP_ROOT}/tee-failure-bin"
TEE_FAILURE_LOG="${TMP_ROOT}/tee-failure-build.log"

mkdir -p "$TEE_FAILURE_BIN_DIR"

cat >"${TEE_FAILURE_BIN_DIR}/tee" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

# Consume the complete build stream so the successful producer does not
# receive SIGPIPE, then fail as though the build log could not be retained.
cat >/dev/null

exit 74
MOCK

chmod +x "${TEE_FAILURE_BIN_DIR}/tee"

if TEE_FAILURE_OUTPUT="$(
  PATH="${TEE_FAILURE_BIN_DIR}:${PATH}" \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
  SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
  SOURCE_TAR_SHA256="$KNOWN_SOURCE_TAR_SHA256" \
  BUILDX_BUILDER="$KNOWN_BUILDER" \
  BUILD_LOG="$TEE_FAILURE_LOG" \
  DOCKER_BIN="$MOCK_DOCKER" \
  MOCK_TAG_EXISTS=NO \
  TMPDIR="$TMP_ROOT" \
    "$HELPER" \
    2>&1
)"; then
  TEE_FAILURE_STATUS=0
else
  TEE_FAILURE_STATUS=$?
fi

printf '%s\n' "$TEE_FAILURE_OUTPUT"
printf 'TEE_FAILURE_HELPER_STATUS=%s\n' "$TEE_FAILURE_STATUS"

[ "$TEE_FAILURE_STATUS" -ne 0 ] ||
  fail "build-log capture failure was reported as successful"

grep -F \
  'BUILD_STATUS=0' \
  <<<"$TEE_FAILURE_OUTPUT" \
  >/dev/null ||
  fail "successful Docker build status was not preserved"

grep -F \
  'BUILD_LOG_STATUS=74' \
  <<<"$TEE_FAILURE_OUTPUT" \
  >/dev/null ||
  fail "build-log failure status was not preserved"

grep -F \
  'failed to retain complete build log' \
  <<<"$TEE_FAILURE_OUTPUT" \
  >/dev/null ||
  fail "build-log capture failure reason was not reported"

if grep -F \
  'CANDIDATE_RUNTIME_IMAGE_BUILD_OK=YES' \
  <<<"$TEE_FAILURE_OUTPUT" \
  >/dev/null
then
  fail "successful runtime-build marker was emitted after log failure"
fi

[ ! -e "$TEE_FAILURE_LOG" ] ||
  fail "failed tee unexpectedly produced the requested build log"

if find "$TMP_ROOT" \
  -maxdepth 1 \
  -type d \
  -name "telectro-runtime-build.${KNOWN_RELEASE_ID}.*" \
  -print |
  grep -q .
then
  fail "temporary build root remained after build-log capture failure"
fi

printf '%s\n' 'BUILD_LOG_FAILURE_REJECTED=PASS'
printf '%s\n' 'TEE_PIPESTATUS_PRESERVED=PASS'
printf '%s\n' 'LOG_FAILURE_SUCCESS_MARKER_SUPPRESSED=PASS'
printf '%s\n' 'LOG_FAILURE_CONTEXT_CLEANED=PASS'
printf '\n%s\n' '=== Malformed identity input rejection ==='

INVALID_INPUT_DOCKER="${TMP_ROOT}/docker-invalid-input"
INVALID_INPUT_DOCKER_MARKER="${TMP_ROOT}/invalid-input-docker-called"

cat >"$INVALID_INPUT_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

: >"${INVALID_INPUT_DOCKER_MARKER:?}"

printf '%s\n' \
  'Docker must not run for malformed release identity input' \
  >&2

exit 95
MOCK

chmod +x "$INVALID_INPUT_DOCKER"
export INVALID_INPUT_DOCKER_MARKER

printf '\n%s\n' '=== Malformed release ID rejection ==='

INVALID_RELEASE_IDS=(
  "20260814"
  "2026-08-14-b946cbf"
  "20260814-B946CBF"
  "20260814-b946cbf-extra"
  "../20260814-b946cbf"
)

for INVALID_RELEASE_ID in "${INVALID_RELEASE_IDS[@]}"; do
  rm -f "$INVALID_INPUT_DOCKER_MARKER"

  if INVALID_RELEASE_OUTPUT="$(
    RELEASE_ID="$INVALID_RELEASE_ID" \
    FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
    SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
    SOURCE_TAR_SHA256="$KNOWN_SOURCE_TAR_SHA256" \
    BUILDX_BUILDER="$KNOWN_BUILDER" \
    DOCKER_BIN="$INVALID_INPUT_DOCKER" \
    TMPDIR="$TMP_ROOT" \
      "$HELPER" \
      2>&1
  )"; then
    INVALID_RELEASE_STATUS=0
  else
    INVALID_RELEASE_STATUS=$?
  fi

  [ "$INVALID_RELEASE_STATUS" -ne 0 ] ||
    fail "malformed RELEASE_ID was accepted: $INVALID_RELEASE_ID"

  grep -F \
    'RELEASE_ID must use YYYYMMDD-<7 lowercase hex> format' \
    <<<"$INVALID_RELEASE_OUTPUT" \
    >/dev/null ||
    fail "malformed RELEASE_ID rejection reason was not reported"

  [ ! -e "$INVALID_INPUT_DOCKER_MARKER" ] ||
    fail "Docker was invoked for malformed RELEASE_ID"
done

printf '%s\n' 'MALFORMED_RELEASE_ID_REJECTED=PASS'

INVALID_FULL_SHAS=(
  "b946cbf"
  "b946cbf7ae23b628a261ac0702577b5f7323c2220"
  "B946cbf7ae23b628a261ac0702577b5f7323c222"
)

for INVALID_FULL_SHA in "${INVALID_FULL_SHAS[@]}"; do
  rm -f "$INVALID_INPUT_DOCKER_MARKER"

  if INVALID_SHA_OUTPUT="$(
    RELEASE_ID="$KNOWN_RELEASE_ID" \
    FULL_COMMIT_SHA="$INVALID_FULL_SHA" \
    SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
    SOURCE_TAR_SHA256="$KNOWN_SOURCE_TAR_SHA256" \
    BUILDX_BUILDER="$KNOWN_BUILDER" \
    DOCKER_BIN="$INVALID_INPUT_DOCKER" \
    TMPDIR="$TMP_ROOT" \
      "$HELPER" \
      2>&1
  )"; then
    INVALID_SHA_STATUS=0
  else
    INVALID_SHA_STATUS=$?
  fi

  [ "$INVALID_SHA_STATUS" -ne 0 ] ||
    fail "malformed FULL_COMMIT_SHA was accepted: $INVALID_FULL_SHA"

  grep -F \
    'FULL_COMMIT_SHA must be exactly 40 lowercase hexadecimal characters' \
    <<<"$INVALID_SHA_OUTPUT" \
    >/dev/null ||
    fail "malformed FULL_COMMIT_SHA rejection reason was not reported"

  [ ! -e "$INVALID_INPUT_DOCKER_MARKER" ] ||
    fail "Docker was invoked for malformed FULL_COMMIT_SHA"
done

INVALID_SOURCE_SHAS=(
  "1234"
  "00000000000000000000000000000000000000000000000000000000000000000"
  "5D95fbc2ba1f1e9a4da7f3bb49e13b9620b1e6b4aeaa65aeb8afb07b817815d8"
)

for INVALID_SOURCE_SHA in "${INVALID_SOURCE_SHAS[@]}"; do
  rm -f "$INVALID_INPUT_DOCKER_MARKER"

  if INVALID_SOURCE_SHA_OUTPUT="$(
    RELEASE_ID="$KNOWN_RELEASE_ID" \
    FULL_COMMIT_SHA="$KNOWN_FULL_COMMIT_SHA" \
    SOURCE_ARTIFACT="$SOURCE_ARTIFACT" \
    SOURCE_TAR_SHA256="$INVALID_SOURCE_SHA" \
    BUILDX_BUILDER="$KNOWN_BUILDER" \
    DOCKER_BIN="$INVALID_INPUT_DOCKER" \
    TMPDIR="$TMP_ROOT" \
      "$HELPER" \
      2>&1
  )"; then
    INVALID_SOURCE_SHA_STATUS=0
  else
    INVALID_SOURCE_SHA_STATUS=$?
  fi

  [ "$INVALID_SOURCE_SHA_STATUS" -ne 0 ] ||
    fail "malformed SOURCE_TAR_SHA256 was accepted: $INVALID_SOURCE_SHA"

  grep -F \
    'SOURCE_TAR_SHA256 must be exactly 64 lowercase hexadecimal characters' \
    <<<"$INVALID_SOURCE_SHA_OUTPUT" \
    >/dev/null ||
    fail "malformed SOURCE_TAR_SHA256 rejection reason was not reported"

  [ ! -e "$INVALID_INPUT_DOCKER_MARKER" ] ||
    fail "Docker was invoked for malformed SOURCE_TAR_SHA256"
done

printf '%s\n' 'MALFORMED_FULL_COMMIT_SHA_REJECTED=PASS'
printf '%s\n' 'MALFORMED_SOURCE_TAR_SHA_REJECTED=PASS'
printf '%s\n' 'MALFORMED_IDENTITY_DOCKER_NOT_INVOKED=PASS'
printf '%s\n' 'RELEASE_RUNTIME_BUILD_REGRESSION=PASS'
