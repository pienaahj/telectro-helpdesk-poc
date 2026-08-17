#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_HELPER="${ROOT_DIR}/bin/release-source-artifact.sh"

KNOWN_GOOD_SHA="b946cbf7ae23b628a261ac0702577b5f7323c222"
KNOWN_GOOD_SHORT_SHA="b946cbf"
KNOWN_RELEASE_ID="20260814-b946cbf"
KNOWN_SOURCE_TAR_SHA256="5d95fbc2ba1f1e9a4da7f3bb49e13b9620b1e6b4aeaa65aeb8afb07b817815d8"
EXPECTED_PREFIX="telectro-helpdesk-poc-${KNOWN_RELEASE_ID}/"

TEST_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TEST_DIR"
}

trap cleanup EXIT

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

assert_exists() {
  [[ -e "$1" ]] || {
    fail "expected path does not exist: $1"
  }
}

assert_not_exists() {
  [[ ! -e "$1" ]] || {
    fail "unexpected path exists: $1"
  }
}

assert_equal() {
  local expected="$1"
  local observed="$2"
  local label="$3"

  [[ "$observed" == "$expected" ]] || {
    fail \
      "$label mismatch: expected '$expected', observed '$observed'"
  }
}

assert_line() {
  local expected="$1"
  local content="$2"

  grep -Fqx -- "$expected" <<<"$content" || {
    fail "expected line was not found: $expected"
  }
}

assert_not_contains() {
  local unexpected="$1"
  local content="$2"

  if grep -Fq -- "$unexpected" <<<"$content"; then
    fail "unexpected text was found: $unexpected"
  fi
}

assert_no_success_markers() {
  local content="$1"

  assert_not_contains \
    "SOURCE_ARTIFACT_CREATED" \
    "$content"

  assert_not_contains \
    "SOURCE_ARTIFACT_APPLEDOUBLE_FREE" \
    "$content"

  assert_not_contains \
    "SOURCE_ARTIFACT_SHA256_RECORDED" \
    "$content"
}

extract_value() {
  local key="$1"
  local content="$2"
  local value

  value="$(
    awk \
      -v key="$key" \
      'index($0, key "=") == 1 {
        print substr($0, length(key) + 2)
        exit
      }' \
      <<<"$content"
  )"

  [[ -n "$value" ]] || {
    fail "expected evidence value was not found: $key"
  }

  printf '%s\n' "$value"
}

run_expect_status() {
  local expected_status="$1"
  shift

  local output
  local status

  set +e

  output="$("$@" 2>&1)"
  status=$?

  set -e

  printf '%s\n' "$output"
  printf 'OBSERVED_STATUS=%s\n' "$status"

  [[ "$status" -eq "$expected_status" ]] || {
    fail \
      "expected status $expected_status, received $status"
  }

  RUN_OUTPUT="$output"
}

printf '%s\n' \
  '=== Release source artifact regression setup ==='

[[ -x "$ARTIFACT_HELPER" ]] || {
  fail \
    "release source artifact helper does not exist or is not executable: $ARTIFACT_HELPER"
}

git \
  -C "$ROOT_DIR" \
  cat-file \
  -e \
  "${KNOWN_GOOD_SHA}^{commit}" || {
    fail \
      "known-good release commit is unavailable: $KNOWN_GOOD_SHA"
  }

printf '%s\n' \
  'KNOWN_GOOD_SOURCE_COMMIT_AVAILABLE=PASS'

printf '\n%s\n' \
  '=== Known-good 2026-08-14 source artifact ==='

KNOWN_ONE_DIR="${TEST_DIR}/known-good-one"
KNOWN_ONE_ARTIFACT="${KNOWN_ONE_DIR}/telectro-app-${KNOWN_RELEASE_ID}.tar.gz"
KNOWN_ONE_TAR="${KNOWN_ONE_DIR}/source.tar"
KNOWN_ONE_LIST="${KNOWN_ONE_DIR}/archive-list.txt"

mkdir -p "$KNOWN_ONE_DIR"

run_expect_status \
  0 \
  env \
    REPO_DIR="$ROOT_DIR" \
    RELEASE_ID="$KNOWN_RELEASE_ID" \
    FULL_COMMIT_SHA="$KNOWN_GOOD_SHA" \
    SOURCE_ARTIFACT="$KNOWN_ONE_ARTIFACT" \
    "$ARTIFACT_HELPER"

assert_exists "$KNOWN_ONE_ARTIFACT"

assert_line \
  "RELEASE_ID=$KNOWN_RELEASE_ID" \
  "$RUN_OUTPUT"

assert_line \
  "FULL_COMMIT_SHA=$KNOWN_GOOD_SHA" \
  "$RUN_OUTPUT"

assert_line \
  "SOURCE_ARTIFACT=$KNOWN_ONE_ARTIFACT" \
  "$RUN_OUTPUT"

assert_line \
  "ARCHIVE_PREFIX=$EXPECTED_PREFIX" \
  "$RUN_OUTPUT"

assert_line \
  "ARCHIVE_COMMIT_SHA=$KNOWN_GOOD_SHA" \
  "$RUN_OUTPUT"

assert_line \
  "APPLEDOUBLE_COUNT=0" \
  "$RUN_OUTPUT"

assert_line \
  "SOURCE_TAR_SHA256=$KNOWN_SOURCE_TAR_SHA256" \
  "$RUN_OUTPUT"

assert_line \
  "SOURCE_ARTIFACT_CREATED" \
  "$RUN_OUTPUT"

assert_line \
  "SOURCE_ARTIFACT_APPLEDOUBLE_FREE" \
  "$RUN_OUTPUT"

assert_line \
  "SOURCE_ARTIFACT_SHA256_RECORDED" \
  "$RUN_OUTPUT"

REPORTED_ARTIFACT_SHA="$(
  extract_value \
    "SOURCE_ARTIFACT_SHA256" \
    "$RUN_OUTPUT"
)"

ACTUAL_ARTIFACT_SHA="$(
  shasum \
    -a 256 \
    "$KNOWN_ONE_ARTIFACT" |
    awk '{print $1}'
)"

assert_equal \
  "$ACTUAL_ARTIFACT_SHA" \
  "$REPORTED_ARTIFACT_SHA" \
  "source artifact SHA-256"

gzip \
  -dc \
  "$KNOWN_ONE_ARTIFACT" \
  > "$KNOWN_ONE_TAR"

ACTUAL_TAR_SHA="$(
  shasum \
    -a 256 \
    "$KNOWN_ONE_TAR" |
    awk '{print $1}'
)"

assert_equal \
  "$KNOWN_SOURCE_TAR_SHA256" \
  "$ACTUAL_TAR_SHA" \
  "known-good source tar SHA-256"

ARCHIVE_COMMIT="$(
  git \
    get-tar-commit-id \
    < "$KNOWN_ONE_TAR"
)"

assert_equal \
  "$KNOWN_GOOD_SHA" \
  "$ARCHIVE_COMMIT" \
  "embedded archive commit"

tar \
  -tzf \
  "$KNOWN_ONE_ARTIFACT" \
  > "$KNOWN_ONE_LIST"

FIRST_ENTRY="$(
  sed \
    -n \
    '1p' \
    "$KNOWN_ONE_LIST"
)"

assert_equal \
  "$EXPECTED_PREFIX" \
  "$FIRST_ENTRY" \
  "archive root prefix"

BAD_PREFIX_COUNT="$(
  awk \
    -v prefix="$EXPECTED_PREFIX" \
    'index($0, prefix) != 1 {
      count++
    }
    END {
      print count + 0
    }' \
    "$KNOWN_ONE_LIST"
)"

assert_equal \
  "0" \
  "$BAD_PREFIX_COUNT" \
  "archive entries outside expected prefix"

APPLEDOUBLE_COUNT="$(
  awk \
    -F/ \
    '$NF ~ /^\._/ {
      count++
    }
    END {
      print count + 0
    }' \
    "$KNOWN_ONE_LIST"
)"

assert_equal \
  "0" \
  "$APPLEDOUBLE_COUNT" \
  "AppleDouble entry count"

printf '%s\n' \
  'KNOWN_GOOD_SOURCE_ARTIFACT=PASS'

printf '\n%s\n' \
  '=== Deterministic rebuild ==='

KNOWN_TWO_DIR="${TEST_DIR}/known-good-two"
KNOWN_TWO_ARTIFACT="${KNOWN_TWO_DIR}/telectro-app-${KNOWN_RELEASE_ID}.tar.gz"
KNOWN_TWO_TAR="${KNOWN_TWO_DIR}/source.tar"

mkdir -p "$KNOWN_TWO_DIR"

sleep 2

run_expect_status \
  0 \
  env \
    REPO_DIR="$ROOT_DIR" \
    RELEASE_ID="$KNOWN_RELEASE_ID" \
    FULL_COMMIT_SHA="$KNOWN_GOOD_SHA" \
    SOURCE_ARTIFACT="$KNOWN_TWO_ARTIFACT" \
    "$ARTIFACT_HELPER"

assert_exists "$KNOWN_TWO_ARTIFACT"

SECOND_ARTIFACT_SHA="$(
  shasum \
    -a 256 \
    "$KNOWN_TWO_ARTIFACT" |
    awk '{print $1}'
)"

assert_equal \
  "$ACTUAL_ARTIFACT_SHA" \
  "$SECOND_ARTIFACT_SHA" \
  "deterministic compressed artifact SHA-256"

cmp \
  -s \
  "$KNOWN_ONE_ARTIFACT" \
  "$KNOWN_TWO_ARTIFACT" || {
    fail \
      "repeated source artifact builds were not byte-identical"
  }

gzip \
  -dc \
  "$KNOWN_TWO_ARTIFACT" \
  > "$KNOWN_TWO_TAR"

SECOND_TAR_SHA="$(
  shasum \
    -a 256 \
    "$KNOWN_TWO_TAR" |
    awk '{print $1}'
)"

assert_equal \
  "$KNOWN_SOURCE_TAR_SHA256" \
  "$SECOND_TAR_SHA" \
  "deterministic source tar SHA-256"

printf '%s\n' \
  'DETERMINISTIC_SOURCE_ARTIFACT_REBUILD=PASS'

printf '\n%s\n' \
  '=== Release ID and commit mismatch rejection ==='

MISMATCH_DIR="${TEST_DIR}/mismatch"
MISMATCH_ARTIFACT="${MISMATCH_DIR}/mismatch.tar.gz"

mkdir -p "$MISMATCH_DIR"

run_expect_status \
  1 \
  env \
    REPO_DIR="$ROOT_DIR" \
    RELEASE_ID="20260814-81564cb" \
    FULL_COMMIT_SHA="$KNOWN_GOOD_SHA" \
    SOURCE_ARTIFACT="$MISMATCH_ARTIFACT" \
    "$ARTIFACT_HELPER"

assert_line \
  "ERROR: RELEASE_ID must end with -$KNOWN_GOOD_SHORT_SHA; observed: 20260814-81564cb" \
  "$RUN_OUTPUT"

assert_not_exists "$MISMATCH_ARTIFACT"
assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'RELEASE_ID_COMMIT_MISMATCH_REJECTED=PASS'

printf '\n%s\n' \
  '=== Unknown commit rejection ==='

UNKNOWN_SHA="0000000000000000000000000000000000000000"
UNKNOWN_DIR="${TEST_DIR}/unknown-commit"
UNKNOWN_ARTIFACT="${UNKNOWN_DIR}/unknown.tar.gz"

mkdir -p "$UNKNOWN_DIR"

run_expect_status \
  1 \
  env \
    REPO_DIR="$ROOT_DIR" \
    RELEASE_ID="20260814-0000000" \
    FULL_COMMIT_SHA="$UNKNOWN_SHA" \
    SOURCE_ARTIFACT="$UNKNOWN_ARTIFACT" \
    "$ARTIFACT_HELPER"

assert_line \
  "ERROR: FULL_COMMIT_SHA is not an existing commit: $UNKNOWN_SHA" \
  "$RUN_OUTPUT"

assert_not_exists "$UNKNOWN_ARTIFACT"
assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'UNKNOWN_COMMIT_REJECTED=PASS'

printf '\n%s\n' \
  '=== Existing destination rejection ==='

EXISTING_DIR="${TEST_DIR}/existing-destination"
EXISTING_ARTIFACT="${EXISTING_DIR}/existing.tar.gz"

mkdir -p "$EXISTING_DIR"

printf '%s\n' \
  'do not overwrite this file' \
  > "$EXISTING_ARTIFACT"

run_expect_status \
  1 \
  env \
    REPO_DIR="$ROOT_DIR" \
    RELEASE_ID="$KNOWN_RELEASE_ID" \
    FULL_COMMIT_SHA="$KNOWN_GOOD_SHA" \
    SOURCE_ARTIFACT="$EXISTING_ARTIFACT" \
    "$ARTIFACT_HELPER"

assert_line \
  "ERROR: source artifact already exists: $EXISTING_ARTIFACT" \
  "$RUN_OUTPUT"

EXISTING_CONTENT="$(
  cat "$EXISTING_ARTIFACT"
)"

assert_equal \
  "do not overwrite this file" \
  "$EXISTING_CONTENT" \
  "existing destination content"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'EXISTING_SOURCE_ARTIFACT_REJECTED=PASS'

printf '\n%s\n' \
  '=== Failed creation leaves no official artifact ==='

FAILURE_DIR="${TEST_DIR}/creation-failure"
FAILURE_ARTIFACT="${FAILURE_DIR}/failed.tar.gz"
MOCK_GZIP="${TEST_DIR}/mock-gzip-failure"

mkdir -p "$FAILURE_DIR"

cat > "$MOCK_GZIP" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

cat >/dev/null

printf '%s\n' \
  'partial invalid gzip content'

exit 73
MOCK

chmod +x "$MOCK_GZIP"

run_expect_status \
  1 \
  env \
    REPO_DIR="$ROOT_DIR" \
    RELEASE_ID="$KNOWN_RELEASE_ID" \
    FULL_COMMIT_SHA="$KNOWN_GOOD_SHA" \
    SOURCE_ARTIFACT="$FAILURE_ARTIFACT" \
    GZIP_BIN="$MOCK_GZIP" \
    "$ARTIFACT_HELPER"

assert_line \
  "ERROR: failed to create source artifact" \
  "$RUN_OUTPUT"

assert_not_exists "$FAILURE_ARTIFACT"
assert_no_success_markers "$RUN_OUTPUT"

FAILURE_REMAINS="$(
  ls -A "$FAILURE_DIR"
)"

assert_equal \
  "" \
  "$FAILURE_REMAINS" \
  "temporary artifact cleanup"

printf '%s\n' \
  'FAILED_CREATION_CLEANUP=PASS'

printf '\n%s\n' \
  '=== Final result ==='

printf '%s\n' \
  'RELEASE_SOURCE_ARTIFACT_REGRESSION=PASS'
