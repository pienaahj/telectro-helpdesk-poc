#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATE="${ROOT_DIR}/bin/prod-migrate.sh"
REAL_STATE_WRITER="${ROOT_DIR}/bin/write-release-state.py"
PYTHON_BIN="$(command -v python3)"

TEST_DIR="$(mktemp -d)"
MOCK_BIN="$TEST_DIR/bin"
EVIDENCE_DIR="$TEST_DIR/deploy-evidence"
BENCH_INVOCATIONS="$TEST_DIR/bench-invocations.txt"
DATE_COUNTER="$TEST_DIR/date-counter.txt"

cleanup() {
  rm -rf "$TEST_DIR"
}

trap cleanup EXIT

mkdir -p "$MOCK_BIN" "$EVIDENCE_DIR"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

file_mode() {
  "$PYTHON_BIN" - "$1" <<'PY'
import os
import stat
import sys

mode = stat.S_IMODE(os.stat(sys.argv[1]).st_mode)
print(f"{mode:03o}")
PY
}

assert_exists() {
  [[ -e "$1" ]] || fail "expected path does not exist: $1"
}

assert_not_exists() {
  [[ ! -e "$1" ]] || fail "unexpected path exists: $1"
}

assert_contains() {
  local expected="$1"
  local content="$2"

  grep -Fq "$expected" <<<"$content" || {
    fail "expected text was not found: $expected"
  }
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

cat > "$MOCK_BIN/mock-date" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

counter_file="${MOCK_DATE_COUNTER:?}"

count=0

if [[ -f "$counter_file" ]]; then
  count="$(cat "$counter_file")"
fi

count=$((count + 1))
printf '%s\n' "$count" > "$counter_file"

fail_call="${MOCK_DATE_FAIL_CALL:-0}"
fail_status="${MOCK_DATE_FAIL_STATUS:-75}"

if [[ "$count" -eq "$fail_call" ]]; then
  printf \
    'ERROR: simulated UTC timestamp failure on call %s\n' \
    "$count" \
    >&2

  exit "$fail_status"
fi

case "$count" in
  1)
    printf '2026-07-28T06:00:00Z\n'
    ;;
  2)
    printf '2026-07-28T06:00:10Z\n'
    ;;
  3)
    printf '2026-07-28T07:00:00Z\n'
    ;;
  4)
    printf '2026-07-28T07:00:15Z\n'
    ;;
  5)
    printf '2026-07-28T08:00:00Z\n'
    ;;
  6)
    printf '2026-07-28T08:00:20Z\n'
    ;;
  7)
    printf '2026-07-28T09:00:00Z\n'
    ;;
  8)
    printf '2026-07-28T09:00:25Z\n'
    ;;
  *)
    printf '2026-07-28T10:00:00Z\n'
    ;;
esac
MOCK

cat > "$MOCK_BIN/mock-bench" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

invocations="${MOCK_BENCH_INVOCATIONS:?}"
exit_status="${MOCK_BENCH_EXIT_STATUS:-0}"
message="${MOCK_BENCH_MESSAGE:-mock migration output}"

printf '%q ' "$@" >> "$invocations"
printf '\n' >> "$invocations"

[[ "${1:-}" == "--site" ]]
[[ -n "${2:-}" ]]
[[ "${3:-}" == "migrate" ]]
[[ "$#" -eq 3 ]]

printf '%s\n' "$message"
exit "$exit_status"
MOCK

cat > "$MOCK_BIN/fail-completed-writer" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

real_writer="${REAL_STATE_WRITER:?}"
fail_status="${MOCK_WRITER_FAIL_STATUS:-71}"
output=""

args=("$@")

for ((index = 0; index < ${#args[@]}; index++)); do
  if [[ "${args[$index]}" == "--output" ]]; then
    output="${args[$((index + 1))]}"
    break
  fi
done

if [[ "$output" == */migration-completed.env ]]; then
  printf 'ERROR: simulated completed-record write failure\n' >&2
  exit "$fail_status"
fi

exec "$real_writer" "$@"
MOCK

cat > "$MOCK_BIN/fail-failed-writer" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

real_writer="${REAL_STATE_WRITER:?}"
fail_status="${MOCK_WRITER_FAIL_STATUS:-74}"
output=""

args=("$@")

for ((index = 0; index < ${#args[@]}; index++)); do
  if [[ "${args[$index]}" == "--output" ]]; then
    output="${args[$((index + 1))]}"
    break
  fi
done

if [[ "$output" == */migration-failed.env ]]; then
  printf 'ERROR: simulated failed-record write failure\n' >&2
  exit "$fail_status"
fi

exec "$real_writer" "$@"
MOCK

cat > "$MOCK_BIN/fail-started-writer" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

printf 'ERROR: simulated started-record write failure\n' >&2
exit "${MOCK_WRITER_FAIL_STATUS:-72}"
MOCK

cat > "$MOCK_BIN/tee" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

cat >/dev/null
exit "${MOCK_TEE_EXIT_STATUS:-73}"
MOCK

chmod +x \
  "$MOCK_BIN/mock-date" \
  "$MOCK_BIN/mock-bench" \
  "$MOCK_BIN/fail-failed-writer" \
  "$MOCK_BIN/fail-completed-writer" \
  "$MOCK_BIN/fail-started-writer" \
  "$MOCK_BIN/tee"

export MOCK_DATE_COUNTER="$DATE_COUNTER"
export MOCK_BENCH_INVOCATIONS="$BENCH_INVOCATIONS"
export REAL_STATE_WRITER="$REAL_STATE_WRITER"

cd "$ROOT_DIR"

[[ -x "$MIGRATE" ]] || {
  fail "migration wrapper is missing or not executable: $MIGRATE"
}

[[ -x "$REAL_STATE_WRITER" ]] || {
  fail "state writer is missing or not executable: $REAL_STATE_WRITER"
}

printf '%s\n' \
  '=== Successful migration evidence ==='

SUCCESS_RELEASE="20260728-success"
SUCCESS_DIR="$EVIDENCE_DIR/releases/$SUCCESS_RELEASE/production-migration"

run_expect_status 0 \
  env \
  SITE=erp.test \
  RELEASE_ID="$SUCCESS_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$REAL_STATE_WRITER" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  MOCK_BENCH_EXIT_STATUS=0 \
  MOCK_BENCH_MESSAGE='successful migration output' \
  "$MIGRATE"

assert_contains 'PRODUCTION_MIGRATION_COMMAND_OK=YES' "$RUN_OUTPUT"
assert_contains "MIGRATION_OUTPUT_LOG=$SUCCESS_DIR/migration-output.log" "$RUN_OUTPUT"
assert_contains "MIGRATION_COMPLETED_RECORD=$SUCCESS_DIR/migration-completed.env" "$RUN_OUTPUT"

assert_exists "$SUCCESS_DIR/migration-started.env"
assert_exists "$SUCCESS_DIR/migration-completed.env"
assert_exists "$SUCCESS_DIR/migration-output.log"
assert_not_exists "$SUCCESS_DIR/migration-failed.env"
assert_not_exists "$SUCCESS_DIR/migration-review-required.env"

[[ "$(file_mode "$SUCCESS_DIR")" == "700" ]] || {
  fail "successful migration directory mode is not 700"
}

for evidence_file in \
  "$SUCCESS_DIR/migration-started.env" \
  "$SUCCESS_DIR/migration-completed.env" \
  "$SUCCESS_DIR/migration-output.log"
do
  [[ "$(file_mode "$evidence_file")" == "600" ]] || {
    fail "evidence file mode is not 600: $evidence_file"
  }
done

grep -qx 'successful migration output' \
  "$SUCCESS_DIR/migration-output.log"

source "$SUCCESS_DIR/migration-started.env"

[[ "$RELEASE_ID" == "$SUCCESS_RELEASE" ]]
[[ "$SITE" == "erp.test" ]]
[[ "$MIGRATION_STATE" == "STARTED" ]]
[[ "$MIGRATION_STARTED_UTC" == "2026-07-28T06:00:00Z" ]]
[[ "$MIGRATION_OUTPUT_LOG" == "$SUCCESS_DIR/migration-output.log" ]]

unset \
  RELEASE_ID \
  SITE \
  MIGRATION_STATE \
  MIGRATION_STARTED_UTC \
  MIGRATION_OUTPUT_LOG

source "$SUCCESS_DIR/migration-completed.env"

[[ "$RELEASE_ID" == "$SUCCESS_RELEASE" ]]
[[ "$SITE" == "erp.test" ]]
[[ "$MIGRATION_STATE" == "COMPLETED" ]]
[[ "$MIGRATION_STARTED_UTC" == "2026-07-28T06:00:00Z" ]]
[[ "$MIGRATION_FINISHED_UTC" == "2026-07-28T06:00:10Z" ]]
[[ "$MIGRATION_EXIT_STATUS" == "0" ]]
[[ "$MIGRATION_OUTPUT_LOG" == "$SUCCESS_DIR/migration-output.log" ]]

printf '%s\n' \
  'SUCCESS_STARTED_RECORD_OK=YES' \
  'SUCCESS_COMPLETED_RECORD_OK=YES' \
  'SUCCESS_OUTPUT_CAPTURE_OK=YES' \
  'SUCCESS_EVIDENCE_MODES_OK=YES'

printf '\n%s\n' \
  '=== Replay refusal ==='

INVOCATIONS_BEFORE_REPLAY="$(
  wc -l < "$BENCH_INVOCATIONS" |
    tr -d ' '
)"

run_expect_status 1 \
  env \
  SITE=erp.test \
  RELEASE_ID="$SUCCESS_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$REAL_STATE_WRITER" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  "$MIGRATE"

assert_contains \
  'Migration evidence already exists; automatic replay is prohibited' \
  "$RUN_OUTPUT"

INVOCATIONS_AFTER_REPLAY="$(
  wc -l < "$BENCH_INVOCATIONS" |
    tr -d ' '
)"

[[ "$INVOCATIONS_AFTER_REPLAY" == "$INVOCATIONS_BEFORE_REPLAY" ]] || {
  fail "Bench was invoked during replay refusal"
}

printf '%s\n' \
  'AUTOMATIC_REPLAY_REFUSED=YES' \
  'BENCH_NOT_REINVOKED=YES'

printf '\n%s\n' \
  '=== Failed migration evidence ==='

FAILED_RELEASE="20260728-failed"
FAILED_DIR="$EVIDENCE_DIR/releases/$FAILED_RELEASE/production-migration"

run_expect_status 42 \
  env \
  SITE=erp.test \
  RELEASE_ID="$FAILED_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$REAL_STATE_WRITER" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  MOCK_BENCH_EXIT_STATUS=42 \
  MOCK_BENCH_MESSAGE='failed migration output' \
  "$MIGRATE"

assert_contains 'PRODUCTION_MIGRATION_COMMAND_OK=NO' "$RUN_OUTPUT"
assert_contains 'MIGRATION_EXIT_STATUS=42' "$RUN_OUTPUT"

assert_exists "$FAILED_DIR/migration-started.env"
assert_exists "$FAILED_DIR/migration-failed.env"
assert_exists "$FAILED_DIR/migration-output.log"
assert_not_exists "$FAILED_DIR/migration-completed.env"
assert_not_exists "$FAILED_DIR/migration-review-required.env"

grep -qx 'failed migration output' \
  "$FAILED_DIR/migration-output.log"

source "$FAILED_DIR/migration-failed.env"

[[ "$RELEASE_ID" == "$FAILED_RELEASE" ]]
[[ "$SITE" == "erp.test" ]]
[[ "$MIGRATION_STATE" == "FAILED" ]]
[[ "$MIGRATION_STARTED_UTC" == "2026-07-28T07:00:00Z" ]]
[[ "$MIGRATION_FINISHED_UTC" == "2026-07-28T07:00:15Z" ]]
[[ "$MIGRATION_EXIT_STATUS" == "42" ]]
[[ "$MIGRATION_OUTPUT_LOG" == "$FAILED_DIR/migration-output.log" ]]

printf '%s\n' \
  'FAILED_STARTED_RECORD_OK=YES' \
  'FAILED_FINAL_RECORD_OK=YES' \
  'FAILED_EXIT_STATUS_PRESERVED=YES'

printf '\n%s\n' \
  '=== Completed action with final evidence failure ==='

RECORD_FAILURE_RELEASE="20260728-record-failure"
RECORD_FAILURE_DIR="$EVIDENCE_DIR/releases/$RECORD_FAILURE_RELEASE/production-migration"

run_expect_status 71 \
  env \
  SITE=erp.test \
  RELEASE_ID="$RECORD_FAILURE_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$MOCK_BIN/fail-completed-writer" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  MOCK_BENCH_EXIT_STATUS=0 \
  MOCK_BENCH_MESSAGE='migration completed before evidence failure' \
  MOCK_WRITER_FAIL_STATUS=71 \
  "$MIGRATE"

assert_contains 'MIGRATION_ACTION_COMPLETED=YES' "$RUN_OUTPUT"
assert_contains 'MIGRATION_EVIDENCE_COMMIT_FAILED=YES' "$RUN_OUTPUT"
assert_contains 'MIGRATION_REVIEW_REQUIRED=YES' "$RUN_OUTPUT"

assert_contains \
  "MIGRATION_REVIEW_RECORD=$RECORD_FAILURE_DIR/migration-review-required.env" \
  "$RUN_OUTPUT"

assert_exists "$RECORD_FAILURE_DIR/migration-started.env"
assert_exists "$RECORD_FAILURE_DIR/migration-output.log"
assert_exists "$RECORD_FAILURE_DIR/migration-review-required.env"
assert_not_exists "$RECORD_FAILURE_DIR/migration-completed.env"
assert_not_exists "$RECORD_FAILURE_DIR/migration-failed.env"

source "$RECORD_FAILURE_DIR/migration-review-required.env"

[[ "$RELEASE_ID" == "$RECORD_FAILURE_RELEASE" ]]
[[ "$SITE" == "erp.test" ]]
[[ "$MIGRATION_STATE" == "REVIEW_REQUIRED" ]]
[[ "$MIGRATION_STARTED_UTC" == "2026-07-28T08:00:00Z" ]]
[[ "$MIGRATION_REVIEW_UTC" == "2026-07-28T08:00:20Z" ]]
[[ "$MIGRATION_EXIT_STATUS" == "0" ]]
[[ "$MIGRATION_OUTPUT_CAPTURE_STATUS" == "0" ]]
[[ "$MIGRATION_OUTPUT_LOG" == "$RECORD_FAILURE_DIR/migration-output.log" ]]
[[ "$MIGRATION_REVIEW_REASON" == "COMPLETED_ACTION_EVIDENCE_COMMIT_FAILED" ]]

unset \
  RELEASE_ID \
  SITE \
  MIGRATION_STATE \
  MIGRATION_STARTED_UTC \
  MIGRATION_REVIEW_UTC \
  MIGRATION_EXIT_STATUS \
  MIGRATION_OUTPUT_CAPTURE_STATUS \
  MIGRATION_OUTPUT_LOG \
  MIGRATION_REVIEW_REASON

printf '%s\n' \
  'COMPLETED_ACTION_NOT_MISCLASSIFIED_AS_FAILED=YES' \
  'EVIDENCE_COMMIT_FAILURE_CLASSIFIED=YES' \
  'REVIEW_REQUIRED_AFTER_EVIDENCE_FAILURE=YES' \
  'DURABLE_COMPLETION_REVIEW_RECORD=YES'

printf '\n%s\n' \
  '=== Failed action with final evidence failure ==='

FAILED_RECORD_FAILURE_RELEASE="20260728-failed-record-failure"
FAILED_RECORD_FAILURE_DIR="$EVIDENCE_DIR/releases/$FAILED_RECORD_FAILURE_RELEASE/production-migration"

run_expect_status 74 \
  env \
  SITE=erp.test \
  RELEASE_ID="$FAILED_RECORD_FAILURE_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$MOCK_BIN/fail-failed-writer" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  MOCK_BENCH_EXIT_STATUS=43 \
  MOCK_BENCH_MESSAGE='migration failed before evidence failure' \
  MOCK_WRITER_FAIL_STATUS=74 \
  "$MIGRATE"

assert_contains 'MIGRATION_EXIT_STATUS=43' "$RUN_OUTPUT"
assert_contains 'MIGRATION_ACTION_FAILED=YES' "$RUN_OUTPUT"
assert_contains 'MIGRATION_EVIDENCE_COMMIT_FAILED=YES' "$RUN_OUTPUT"
assert_contains 'MIGRATION_REVIEW_REQUIRED=YES' "$RUN_OUTPUT"

assert_contains \
  "MIGRATION_REVIEW_RECORD=$FAILED_RECORD_FAILURE_DIR/migration-review-required.env" \
  "$RUN_OUTPUT"

assert_exists "$FAILED_RECORD_FAILURE_DIR/migration-started.env"
assert_exists "$FAILED_RECORD_FAILURE_DIR/migration-output.log"
assert_exists "$FAILED_RECORD_FAILURE_DIR/migration-review-required.env"
assert_not_exists "$FAILED_RECORD_FAILURE_DIR/migration-completed.env"
assert_not_exists "$FAILED_RECORD_FAILURE_DIR/migration-failed.env"

grep -qx \
  'migration failed before evidence failure' \
  "$FAILED_RECORD_FAILURE_DIR/migration-output.log"

[[ "$(file_mode "$FAILED_RECORD_FAILURE_DIR/migration-review-required.env")" == "600" ]] || {
  fail "failed-action review record mode is not 600"
}

source "$FAILED_RECORD_FAILURE_DIR/migration-review-required.env"

[[ "$RELEASE_ID" == "$FAILED_RECORD_FAILURE_RELEASE" ]]
[[ "$SITE" == "erp.test" ]]
[[ "$MIGRATION_STATE" == "REVIEW_REQUIRED" ]]
[[ "$MIGRATION_EXIT_STATUS" == "43" ]]
[[ "$MIGRATION_OUTPUT_CAPTURE_STATUS" == "0" ]]
[[ "$MIGRATION_OUTPUT_LOG" == "$FAILED_RECORD_FAILURE_DIR/migration-output.log" ]]
[[ "$MIGRATION_REVIEW_REASON" == "FAILED_ACTION_EVIDENCE_COMMIT_FAILED" ]]
[[ -n "$MIGRATION_STARTED_UTC" ]]
[[ -n "$MIGRATION_REVIEW_UTC" ]]

unset \
  RELEASE_ID \
  SITE \
  MIGRATION_STATE \
  MIGRATION_STARTED_UTC \
  MIGRATION_REVIEW_UTC \
  MIGRATION_EXIT_STATUS \
  MIGRATION_OUTPUT_CAPTURE_STATUS \
  MIGRATION_OUTPUT_LOG \
  MIGRATION_REVIEW_REASON

printf '%s\n' \
  'FAILED_ACTION_STATUS_PRESERVED_IN_REVIEW_RECORD=YES' \
  'FAILED_EVIDENCE_COMMIT_FAILURE_CLASSIFIED=YES' \
  'DURABLE_FAILED_ACTION_REVIEW_RECORD=YES'

printf '\n%s\n' \
  '=== Started-record failure prevents migration ==='

START_FAILURE_RELEASE="20260728-start-failure"
START_FAILURE_DIR="$EVIDENCE_DIR/releases/$START_FAILURE_RELEASE/production-migration"

INVOCATIONS_BEFORE_START_FAILURE="$(
  wc -l < "$BENCH_INVOCATIONS" |
    tr -d ' '
)"

run_expect_status 72 \
  env \
  SITE=erp.test \
  RELEASE_ID="$START_FAILURE_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$MOCK_BIN/fail-started-writer" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  MOCK_WRITER_FAIL_STATUS=72 \
  "$MIGRATE"

assert_contains 'simulated started-record write failure' "$RUN_OUTPUT"
assert_contains 'MIGRATION_START_CLAIM_RELEASED=YES' "$RUN_OUTPUT"

INVOCATIONS_AFTER_START_FAILURE="$(
  wc -l < "$BENCH_INVOCATIONS" |
    tr -d ' '
)"

[[ "$INVOCATIONS_AFTER_START_FAILURE" == "$INVOCATIONS_BEFORE_START_FAILURE" ]] || {
  fail "Bench was invoked after started-record failure"
}

assert_not_exists "$START_FAILURE_DIR/migration-started.env"
assert_not_exists "$START_FAILURE_DIR/migration-completed.env"
assert_not_exists "$START_FAILURE_DIR/migration-failed.env"
assert_not_exists "$START_FAILURE_DIR/migration-review-required.env"
assert_not_exists "$START_FAILURE_DIR/migration-output.log"
assert_not_exists "$START_FAILURE_DIR"

printf '%s\n' \
  'STARTED_RECORD_REQUIRED_BEFORE_ACTION=YES' \
  'BENCH_NOT_INVOKED_AFTER_STARTED_RECORD_FAILURE=YES' \
  'START_CLAIM_RELEASED_AFTER_STARTED_RECORD_FAILURE=YES'

printf '\n%s\n' \
  '=== Output-capture failure requires review ==='

OUTPUT_FAILURE_RELEASE="20260728-output-failure"
OUTPUT_FAILURE_DIR="$EVIDENCE_DIR/releases/$OUTPUT_FAILURE_RELEASE/production-migration"

run_expect_status 73 \
  env \
  PATH="$MOCK_BIN:$PATH" \
  SITE=erp.test \
  RELEASE_ID="$OUTPUT_FAILURE_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$REAL_STATE_WRITER" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  MOCK_BENCH_EXIT_STATUS=0 \
  MOCK_BENCH_MESSAGE='migration action output lost by tee' \
  MOCK_TEE_EXIT_STATUS=73 \
  "$MIGRATE"

assert_contains 'MIGRATION_EXIT_STATUS=0' "$RUN_OUTPUT"
assert_contains 'MIGRATION_OUTPUT_CAPTURE_STATUS=73' "$RUN_OUTPUT"
assert_contains 'MIGRATION_OUTPUT_CAPTURE_FAILED=YES' "$RUN_OUTPUT"
assert_contains 'MIGRATION_REVIEW_REQUIRED=YES' "$RUN_OUTPUT"

assert_contains \
  "MIGRATION_REVIEW_RECORD=$OUTPUT_FAILURE_DIR/migration-review-required.env" \
  "$RUN_OUTPUT"

assert_exists "$OUTPUT_FAILURE_DIR/migration-started.env"
assert_exists "$OUTPUT_FAILURE_DIR/migration-review-required.env"
assert_not_exists "$OUTPUT_FAILURE_DIR/migration-completed.env"
assert_not_exists "$OUTPUT_FAILURE_DIR/migration-failed.env"
assert_not_exists "$OUTPUT_FAILURE_DIR/migration-output.log"

source "$OUTPUT_FAILURE_DIR/migration-review-required.env"

[[ "$RELEASE_ID" == "$OUTPUT_FAILURE_RELEASE" ]]
[[ "$SITE" == "erp.test" ]]
[[ "$MIGRATION_STATE" == "REVIEW_REQUIRED" ]]
[[ "$MIGRATION_EXIT_STATUS" == "0" ]]
[[ "$MIGRATION_OUTPUT_CAPTURE_STATUS" == "73" ]]
[[ "$MIGRATION_OUTPUT_LOG" == "$OUTPUT_FAILURE_DIR/migration-output.log" ]]
[[ "$MIGRATION_REVIEW_REASON" == "OUTPUT_CAPTURE_FAILED" ]]
[[ -n "$MIGRATION_STARTED_UTC" ]]
[[ -n "$MIGRATION_REVIEW_UTC" ]]

unset \
  RELEASE_ID \
  SITE \
  MIGRATION_STATE \
  MIGRATION_STARTED_UTC \
  MIGRATION_REVIEW_UTC \
  MIGRATION_EXIT_STATUS \
  MIGRATION_OUTPUT_CAPTURE_STATUS \
  MIGRATION_OUTPUT_LOG \
  MIGRATION_REVIEW_REASON

printf '%s\n' \
  'OUTPUT_CAPTURE_STATUS_PRESERVED=YES' \
  'OUTPUT_CAPTURE_FAILURE_NOT_MISCLASSIFIED=YES' \
  'REPLAY_GUARD_PRESERVED_AFTER_OUTPUT_FAILURE=YES' \
  'DURABLE_OUTPUT_FAILURE_REVIEW_RECORD=YES'

printf '\n%s\n' \
  '=== Post-action timestamp failure requires review ==='

printf '0\n' > "$DATE_COUNTER"

TIMESTAMP_FAILURE_RELEASE="20260728-timestamp-failure"
TIMESTAMP_FAILURE_DIR="$EVIDENCE_DIR/releases/$TIMESTAMP_FAILURE_RELEASE/production-migration"

run_expect_status 75 \
  env \
  SITE=erp.test \
  RELEASE_ID="$TIMESTAMP_FAILURE_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$REAL_STATE_WRITER" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  MOCK_DATE_FAIL_CALL=2 \
  MOCK_DATE_FAIL_STATUS=75 \
  MOCK_BENCH_EXIT_STATUS=0 \
  MOCK_BENCH_MESSAGE='migration completed before timestamp failure' \
  "$MIGRATE"

assert_contains 'MIGRATION_TIMESTAMP_STATUS=75' "$RUN_OUTPUT"
assert_contains 'MIGRATION_FINISHED_TIMESTAMP_FAILED=YES' "$RUN_OUTPUT"
assert_contains 'MIGRATION_REVIEW_REQUIRED=YES' "$RUN_OUTPUT"

assert_contains \
  "MIGRATION_REVIEW_RECORD=$TIMESTAMP_FAILURE_DIR/migration-review-required.env" \
  "$RUN_OUTPUT"

assert_exists "$TIMESTAMP_FAILURE_DIR/migration-started.env"
assert_exists "$TIMESTAMP_FAILURE_DIR/migration-output.log"
assert_exists "$TIMESTAMP_FAILURE_DIR/migration-review-required.env"
assert_not_exists "$TIMESTAMP_FAILURE_DIR/migration-completed.env"
assert_not_exists "$TIMESTAMP_FAILURE_DIR/migration-failed.env"

grep -qx \
  'migration completed before timestamp failure' \
  "$TIMESTAMP_FAILURE_DIR/migration-output.log"

source "$TIMESTAMP_FAILURE_DIR/migration-review-required.env"

[[ "$RELEASE_ID" == "$TIMESTAMP_FAILURE_RELEASE" ]]
[[ "$SITE" == "erp.test" ]]
[[ "$MIGRATION_STATE" == "REVIEW_REQUIRED" ]]
[[ "$MIGRATION_STARTED_UTC" == "2026-07-28T06:00:00Z" ]]
[[ "$MIGRATION_REVIEW_UTC" == "UNAVAILABLE" ]]
[[ "$MIGRATION_EXIT_STATUS" == "0" ]]
[[ "$MIGRATION_OUTPUT_CAPTURE_STATUS" == "0" ]]
[[ "$MIGRATION_TIMESTAMP_STATUS" == "75" ]]
[[ "$MIGRATION_OUTPUT_LOG" == "$TIMESTAMP_FAILURE_DIR/migration-output.log" ]]
[[ "$MIGRATION_REVIEW_REASON" == "FINISHED_TIMESTAMP_FAILED" ]]

unset \
  RELEASE_ID \
  SITE \
  MIGRATION_STATE \
  MIGRATION_STARTED_UTC \
  MIGRATION_REVIEW_UTC \
  MIGRATION_EXIT_STATUS \
  MIGRATION_OUTPUT_CAPTURE_STATUS \
  MIGRATION_TIMESTAMP_STATUS \
  MIGRATION_OUTPUT_LOG \
  MIGRATION_REVIEW_REASON

printf '%s\n' \
  'POST_ACTION_TIMESTAMP_FAILURE_CLASSIFIED=YES' \
  'TIMESTAMP_FAILURE_STATUS_PRESERVED=YES' \
  'DURABLE_TIMESTAMP_FAILURE_REVIEW_RECORD=YES'

printf '\n%s\n' \
  '=== Concurrent start claim refusal ==='

CONCURRENT_RELEASE="20260728-concurrent-claim"
CONCURRENT_DIR="$EVIDENCE_DIR/releases/$CONCURRENT_RELEASE/production-migration"

mkdir -p "$CONCURRENT_DIR"
chmod 700 "$CONCURRENT_DIR"

INVOCATIONS_BEFORE_CONCURRENT_CLAIM="$(
  wc -l < "$BENCH_INVOCATIONS" |
    tr -d ' '
)"

run_expect_status 1 \
  env \
  SITE=erp.test \
  RELEASE_ID="$CONCURRENT_RELEASE" \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$REAL_STATE_WRITER" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  "$MIGRATE"

assert_contains \
  "Migration evidence already exists; automatic replay is prohibited: $CONCURRENT_DIR" \
  "$RUN_OUTPUT"

INVOCATIONS_AFTER_CONCURRENT_CLAIM="$(
  wc -l < "$BENCH_INVOCATIONS" |
    tr -d ' '
)"

[[ "$INVOCATIONS_AFTER_CONCURRENT_CLAIM" == "$INVOCATIONS_BEFORE_CONCURRENT_CLAIM" ]] || {
  fail "Bench was invoked after another process had claimed the migration directory"
}

assert_not_exists "$CONCURRENT_DIR/migration-started.env"
assert_not_exists "$CONCURRENT_DIR/migration-completed.env"
assert_not_exists "$CONCURRENT_DIR/migration-failed.env"
assert_not_exists "$CONCURRENT_DIR/migration-review-required.env"
assert_not_exists "$CONCURRENT_DIR/migration-output.log"

printf '%s\n' \
  'EMPTY_EXISTING_MIGRATION_DIRECTORY_REFUSED=YES' \
  'BENCH_NOT_INVOKED_AFTER_CONCURRENT_CLAIM=YES' \
  'ATOMIC_MIGRATION_START_CLAIM=PASS'

printf '\n%s\n' \
  '=== Unsafe release identity rejection ==='

run_expect_status 1 \
  env \
  SITE=erp.test \
  RELEASE_ID='../unsafe release' \
  EVIDENCE_DIR="$EVIDENCE_DIR" \
  PROD_BENCH="$MOCK_BIN/mock-bench" \
  STATE_WRITER="$REAL_STATE_WRITER" \
  DATE_BIN="$MOCK_BIN/mock-date" \
  "$MIGRATE"

assert_contains 'RELEASE_ID contains unsafe characters' "$RUN_OUTPUT"

printf '%s\n' \
  'UNSAFE_RELEASE_ID_REJECTED=YES'

printf '\n%s\n' \
  '=== Final result ==='

printf '%s\n' \
  'SUCCESS_MIGRATION_EVIDENCE=PASS' \
  'FAILED_MIGRATION_EVIDENCE=PASS' \
  'AUTOMATIC_REPLAY_PROTECTION=PASS' \
  'ATOMIC_MIGRATION_START_CLAIM=PASS' \
  'STARTED_RECORD_GATE=PASS' \
  'OUTPUT_CAPTURE_FAILURE_CLASSIFICATION=PASS' \
  'EVIDENCE_COMMIT_FAILURE_CLASSIFICATION=PASS' \
  'FAILED_ACTION_EVIDENCE_COMMIT_FAILURE=PASS' \
  'POST_ACTION_TIMESTAMP_FAILURE_CLASSIFICATION=PASS' \
  'PROD_MIGRATE_EVIDENCE_REGRESSION=PASS'
