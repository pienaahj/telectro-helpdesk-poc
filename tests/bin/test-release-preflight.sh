#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PREFLIGHT="${ROOT_DIR}/bin/release-preflight.sh"

KNOWN_GOOD_SHA="b946cbf7ae23b628a261ac0702577b5f7323c222"
KNOWN_GOOD_SHORT_SHA="b946cbf"
KNOWN_RELEASE_DATE="20260814"
KNOWN_RELEASE_ID="20260814-b946cbf"
KNOWN_SOURCE_ARTIFACT="/tmp/telectro-app-20260814-b946cbf.tar.gz"

TEST_DIR="$(mktemp -d)"
BASE_REMOTE="${TEST_DIR}/base-origin.git"

cleanup() {
  rm -rf "$TEST_DIR"
}

trap cleanup EXIT

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
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

  assert_not_contains "RELEASE_IDENTITY_DEFINED" "$content"
  assert_not_contains "LOCAL_GIT_RELEASE_PREFLIGHT_OK" "$content"
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
    fail "expected status $expected_status, received $status"
  }

  RUN_OUTPUT="$output"
}

configure_identity() {
  local repo="$1"

  git -C "$repo" config user.name "Release Preflight Regression"
  git -C "$repo" config user.email "release-preflight@example.invalid"
}

prepare_case() {
  local name="$1"

  CASE_REMOTE="${TEST_DIR}/${name}-origin.git"
  CASE_REPO="${TEST_DIR}/${name}-work"

  git clone \
    --quiet \
    --bare \
    "$BASE_REMOTE" \
    "$CASE_REMOTE"

  git clone \
    --quiet \
    --branch main \
    "$CASE_REMOTE" \
    "$CASE_REPO"

  configure_identity "$CASE_REPO"
}

printf '%s\n' '=== Release preflight regression setup ==='

[[ -f "$PREFLIGHT" ]] || {
  fail "release preflight helper does not exist yet: $PREFLIGHT"
}

git cat-file -e "${KNOWN_GOOD_SHA}^{commit}" || {
  fail "known-good release commit is unavailable: $KNOWN_GOOD_SHA"
}

git clone \
  --quiet \
  --bare \
  "$ROOT_DIR" \
  "$BASE_REMOTE"

git \
  --git-dir="$BASE_REMOTE" \
  update-ref \
  refs/heads/main \
  "$KNOWN_GOOD_SHA"

git \
  --git-dir="$BASE_REMOTE" \
  symbolic-ref \
  HEAD \
  refs/heads/main

BASE_MAIN_SHA="$(
  git \
    --git-dir="$BASE_REMOTE" \
    rev-parse \
    refs/heads/main
)"

[[ "$BASE_MAIN_SHA" == "$KNOWN_GOOD_SHA" ]] || {
  fail \
    "base fixture main mismatch: expected $KNOWN_GOOD_SHA, observed $BASE_MAIN_SHA"
}

printf '%s\n' \
  'KNOWN_GOOD_GIT_FIXTURE=PASS'

printf '\n%s\n' \
  '=== Known-good 2026-08-14 release ==='

prepare_case "known-good"

run_expect_status \
  0 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE="$KNOWN_RELEASE_DATE" \
    bash "$PREFLIGHT"

assert_line \
  "RELEASE_DATE=$KNOWN_RELEASE_DATE" \
  "$RUN_OUTPUT"

assert_line \
  "SOURCE_BRANCH=main" \
  "$RUN_OUTPUT"

assert_line \
  "FULL_COMMIT_SHA=$KNOWN_GOOD_SHA" \
  "$RUN_OUTPUT"

assert_line \
  "SHORT_COMMIT_SHA=$KNOWN_GOOD_SHORT_SHA" \
  "$RUN_OUTPUT"

assert_line \
  "RELEASE_ID=$KNOWN_RELEASE_ID" \
  "$RUN_OUTPUT"

assert_line \
  "SOURCE_ARTIFACT=$KNOWN_SOURCE_ARTIFACT" \
  "$RUN_OUTPUT"

assert_line \
  "RELEASE_IDENTITY_DEFINED" \
  "$RUN_OUTPUT"

assert_line \
  "LOCAL_GIT_RELEASE_PREFLIGHT_OK" \
  "$RUN_OUTPUT"

[[ -z "$(git -C "$CASE_REPO" status --short)" ]] || {
  fail "known-good preflight modified the working tree"
}

printf '%s\n' \
  'KNOWN_GOOD_RELEASE_PREFLIGHT=PASS'

printf '\n%s\n' \
  '=== Dirty working tree rejection ==='

prepare_case "dirty"

printf '%s\n' \
  'untracked release contamination' \
  > "$CASE_REPO/untracked-release-file.txt"

git \
  -C "$CASE_REPO" \
  remote \
  set-url \
  origin \
  "$TEST_DIR/dirty-must-not-fetch.git"

run_expect_status \
  1 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE="$KNOWN_RELEASE_DATE" \
    bash "$PREFLIGHT"

assert_line \
  "ERROR: working tree must be clean for release preflight" \
  "$RUN_OUTPUT"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'DIRTY_WORKTREE_REJECTED=PASS'

printf '\n%s\n' \
  '=== Feature branch rejection ==='

prepare_case "feature-branch"

git \
  -C "$CASE_REPO" \
  checkout \
  --quiet \
  -b feature/test-release-preflight

git \
  -C "$CASE_REPO" \
  remote \
  set-url \
  origin \
  "$TEST_DIR/feature-branch-must-not-fetch.git"

run_expect_status \
  1 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE="$KNOWN_RELEASE_DATE" \
    bash "$PREFLIGHT"

assert_line \
  "ERROR: release source branch must be main; observed: feature/test-release-preflight" \
  "$RUN_OUTPUT"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'FEATURE_BRANCH_REJECTED=PASS'

printf '\n%s\n' \
  '=== Detached HEAD rejection ==='

prepare_case "detached-head"

git \
  -C "$CASE_REPO" \
  checkout \
  --quiet \
  --detach

git \
  -C "$CASE_REPO" \
  remote \
  set-url \
  origin \
  "$TEST_DIR/detached-head-must-not-fetch.git"

run_expect_status \
  1 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE="$KNOWN_RELEASE_DATE" \
    bash "$PREFLIGHT"

assert_line \
  "ERROR: detached HEAD is not a valid release source" \
  "$RUN_OUTPUT"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'DETACHED_HEAD_REJECTED=PASS'

printf '\n%s\n' \
  '=== Local main ahead rejection ==='

prepare_case "ahead"

printf '%s\n' \
  'local-only release commit' \
  > "$CASE_REPO/local-ahead.txt"

git \
  -C "$CASE_REPO" \
  add \
  local-ahead.txt

git \
  -C "$CASE_REPO" \
  commit \
  --quiet \
  -m "Create local-only release commit"

run_expect_status \
  1 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE="$KNOWN_RELEASE_DATE" \
    bash "$PREFLIGHT"

assert_line \
  "ERROR: local main must exactly match origin/main; ahead=1 behind=0" \
  "$RUN_OUTPUT"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'LOCAL_MAIN_AHEAD_REJECTED=PASS'

printf '\n%s\n' \
  '=== Local main behind rejection ==='

prepare_case "behind"

PUSH_REPO="${TEST_DIR}/behind-push"

git clone \
  --quiet \
  --branch main \
  "$CASE_REMOTE" \
  "$PUSH_REPO"

configure_identity "$PUSH_REPO"

printf '%s\n' \
  'remote-only release commit' \
  > "$PUSH_REPO/remote-ahead.txt"

git \
  -C "$PUSH_REPO" \
  add \
  remote-ahead.txt

git \
  -C "$PUSH_REPO" \
  commit \
  --quiet \
  -m "Create remote-only release commit"

git \
  -C "$PUSH_REPO" \
  push \
  --quiet \
  origin \
  main

run_expect_status \
  1 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE="$KNOWN_RELEASE_DATE" \
    bash "$PREFLIGHT"

assert_line \
  "ERROR: local main must exactly match origin/main; ahead=0 behind=1" \
  "$RUN_OUTPUT"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'LOCAL_MAIN_BEHIND_REJECTED=PASS'

printf '\n%s\n' \
  '=== Origin fetch failure rejection ==='

prepare_case "fetch-failure"

git \
  -C "$CASE_REPO" \
  remote \
  set-url \
  origin \
  "$TEST_DIR/nonexistent-origin.git"

run_expect_status \
  1 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE="$KNOWN_RELEASE_DATE" \
    bash "$PREFLIGHT"

assert_line \
  "ERROR: failed to fetch origin" \
  "$RUN_OUTPUT"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'ORIGIN_FETCH_FAILURE_REJECTED=PASS'

printf '\n%s\n' \
  '=== Missing release date rejection ==='

prepare_case "missing-release-date"

run_expect_status \
  1 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE= \
    bash "$PREFLIGHT"

assert_line \
  "ERROR: RELEASE_DATE is required" \
  "$RUN_OUTPUT"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'MISSING_RELEASE_DATE_REJECTED=PASS'

printf '\n%s\n' \
  '=== Invalid release date format rejection ==='

prepare_case "invalid-release-date"

run_expect_status \
  1 \
  env \
    REPO_DIR="$CASE_REPO" \
    RELEASE_DATE="2026-08-14" \
    bash "$PREFLIGHT"

assert_line \
  "ERROR: RELEASE_DATE must use YYYYMMDD format; observed: 2026-08-14" \
  "$RUN_OUTPUT"

assert_no_success_markers "$RUN_OUTPUT"

printf '%s\n' \
  'INVALID_RELEASE_DATE_REJECTED=PASS'

printf '\n%s\n' \
  '=== Final result ==='

printf '%s\n' \
  'RELEASE_PREFLIGHT_REGRESSION=PASS'
