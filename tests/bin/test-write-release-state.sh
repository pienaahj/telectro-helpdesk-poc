#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WRITER="${ROOT_DIR}/bin/write-release-state.py"
PYTHON_BIN="$(command -v python3)"

TEST_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TEST_DIR"
}

trap cleanup EXIT

OUTPUT="$TEST_DIR/release-state.env"
SENTINEL="$TEST_DIR/should-not-exist"
EMPTY_PATH="$TEST_DIR/empty-path"

mkdir -p "$EMPTY_PATH"

SPACE_VALUE='TELECTRO Assignment Handoff Log.png'
QUOTE_VALUE="Christo's production release"
SHELL_VALUE="\$(touch '$SENTINEL'); \$HOME; \`uname\`; a&b"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

sha256_file() {
  "$PYTHON_BIN" - "$1" <<'PY'
from hashlib import sha256
from pathlib import Path
import sys

print(sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
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

assert_file_unchanged() {
  local expected_sha256="$1"
  local actual_sha256

  actual_sha256="$(sha256_file "$OUTPUT")"

  [[ "$actual_sha256" == "$expected_sha256" ]] || {
    fail "previous valid state file was modified after a failed write"
  }
}

expect_failure() {
  local expected_message="$1"
  shift

  local failure_output
  local failure_status

  set +e

  failure_output="$("$@" 2>&1)"
  failure_status=$?

  set -e

  printf '%s\n' "$failure_output"
  printf 'EXPECTED_FAILURE_STATUS=%s\n' "$failure_status"

  [[ "$failure_status" -ne 0 ]] || {
    fail "command unexpectedly succeeded"
  }

  grep -Fq "$expected_message" <<<"$failure_output" || {
    fail "expected failure message was not found: $expected_message"
  }
}

cd "$ROOT_DIR"

[[ -x "$WRITER" ]] || {
  fail "release-state writer is missing or not executable: $WRITER"
}

printf '%s\n' \
  '=== Python syntax ==='

"$PYTHON_BIN" - "$WRITER" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
compile(path.read_text(encoding="utf-8"), str(path), "exec")

print("PYTHON_SYNTAX_OK=YES")
PY

printf '\n%s\n' \
  '=== No fallible permission operation after atomic replacement ==='

"$PYTHON_BIN" - "$WRITER" "$TEST_DIR/post-replace-state.env" <<'PY'
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


writer_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])

spec = importlib.util.spec_from_file_location(
    "write_release_state",
    writer_path,
)

if spec is None or spec.loader is None:
    raise RuntimeError("could not load release-state writer module")

writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)

original_chmod = writer.os.chmod
original_replace = writer.os.replace
replacement_completed = False


def tracked_replace(source: os.PathLike[str], destination: os.PathLike[str]) -> None:
    global replacement_completed

    original_replace(source, destination)
    replacement_completed = True


def guarded_chmod(path: os.PathLike[str], mode: int) -> None:
    if replacement_completed:
        raise RuntimeError(
            "permission operation attempted after atomic replacement"
        )

    original_chmod(path, mode)


writer.os.replace = tracked_replace
writer.os.chmod = guarded_chmod

writer.write_atomic(
    output_path,
    "RELEASE_ID=post-replace-regression\n",
)

if not replacement_completed:
    raise RuntimeError("atomic replacement was not reached")

if output_path.read_text(encoding="utf-8") != (
    "RELEASE_ID=post-replace-regression\n"
):
    raise RuntimeError("replacement output content is incorrect")

mode = output_path.stat().st_mode & 0o777

if mode != 0o600:
    raise RuntimeError(
        f"replacement output mode is {mode:03o}, expected 600"
    )

print("NO_POST_REPLACE_PERMISSION_OPERATION=YES")
print("POST_REPLACE_OUTPUT_MODE=600")
PY

printf '\n%s\n' \
  '=== Successful state write ==='

"$WRITER" \
  --output "$OUTPUT" \
  --allowed-key RELEASE_ID \
  --allowed-key SCREENSHOT \
  --allowed-key NOTE \
  --allowed-key SHELL_TEXT \
  --allowed-key OPTIONAL \
  --required-key RELEASE_ID \
  --required-key SCREENSHOT \
  --required-key NOTE \
  --required-key SHELL_TEXT \
  --field 'RELEASE_ID=20260727-test' \
  --field "SCREENSHOT=$SPACE_VALUE" \
  --field "NOTE=$QUOTE_VALUE" \
  --field "SHELL_TEXT=$SHELL_VALUE" \
  --field 'OPTIONAL='

printf '\n%s\n' \
  '=== Generated state file ==='

cat "$OUTPUT"

bash -n "$OUTPUT"

OUTPUT_MODE="$(file_mode "$OUTPUT")"

printf 'OUTPUT_MODE=%s\n' "$OUTPUT_MODE"

[[ "$OUTPUT_MODE" == "600" ]] || {
  fail "expected output mode 600, received $OUTPUT_MODE"
}

printf '\n%s\n' \
  '=== Source and value verification ==='

source "$OUTPUT"

[[ "$RELEASE_ID" == "20260727-test" ]] || {
  fail "RELEASE_ID was not preserved"
}

[[ "$SCREENSHOT" == "$SPACE_VALUE" ]] || {
  fail "value containing spaces was not preserved"
}

[[ "$NOTE" == "$QUOTE_VALUE" ]] || {
  fail "value containing quotes was not preserved"
}

[[ "$SHELL_TEXT" == "$SHELL_VALUE" ]] || {
  fail "value containing shell characters was not preserved"
}

[[ "$OPTIONAL" == "" ]] || {
  fail "empty optional value was not preserved"
}

[[ ! -e "$SENTINEL" ]] || {
  fail "shell content from a state value was executed"
}

printf '%s\n' \
  'VALUE_WITH_SPACES_PRESERVED=YES' \
  'VALUE_WITH_QUOTES_PRESERVED=YES' \
  'VALUE_WITH_SHELL_CHARACTERS_PRESERVED=YES' \
  'EMPTY_OPTIONAL_VALUE_PRESERVED=YES' \
  'SHELL_CONTENT_EXECUTED=NO' \
  'OUTPUT_PASSES_BASH_N=YES'

VALID_SHA256="$(sha256_file "$OUTPUT")"

printf 'VALID_STATE_SHA256=%s\n' "$VALID_SHA256"

printf '\n%s\n' \
  '=== Unknown field rejection ==='

expect_failure \
  'unknown fields supplied: UNKNOWN' \
  "$WRITER" \
  --output "$OUTPUT" \
  --allowed-key RELEASE_ID \
  --required-key RELEASE_ID \
  --field 'RELEASE_ID=replaced' \
  --field 'UNKNOWN=value'

assert_file_unchanged "$VALID_SHA256"

printf '\n%s\n' \
  '=== Missing required field rejection ==='

expect_failure \
  'required fields are missing: RELEASE_ID' \
  "$WRITER" \
  --output "$OUTPUT" \
  --allowed-key RELEASE_ID \
  --required-key RELEASE_ID

assert_file_unchanged "$VALID_SHA256"

printf '\n%s\n' \
  '=== Empty required field rejection ==='

expect_failure \
  'required fields are empty: RELEASE_ID' \
  "$WRITER" \
  --output "$OUTPUT" \
  --allowed-key RELEASE_ID \
  --required-key RELEASE_ID \
  --field 'RELEASE_ID='

assert_file_unchanged "$VALID_SHA256"

printf '\n%s\n' \
  '=== Duplicate field rejection ==='

expect_failure \
  "duplicate field 'RELEASE_ID'" \
  "$WRITER" \
  --output "$OUTPUT" \
  --allowed-key RELEASE_ID \
  --required-key RELEASE_ID \
  --field 'RELEASE_ID=first' \
  --field 'RELEASE_ID=second'

assert_file_unchanged "$VALID_SHA256"

printf '\n%s\n' \
  '=== Duplicate schema-key rejection ==='

expect_failure \
  "allowed schema contains duplicate key 'RELEASE_ID'" \
  "$WRITER" \
  --output "$OUTPUT" \
  --allowed-key RELEASE_ID \
  --allowed-key RELEASE_ID \
  --required-key RELEASE_ID \
  --field 'RELEASE_ID=value'

assert_file_unchanged "$VALID_SHA256"

printf '\n%s\n' \
  '=== Invalid key rejection ==='

expect_failure \
  "field contains an invalid key 'invalid-key'" \
  "$WRITER" \
  --output "$OUTPUT" \
  --allowed-key RELEASE_ID \
  --field 'invalid-key=value'

assert_file_unchanged "$VALID_SHA256"

printf '\n%s\n' \
  '=== Multiline value rejection ==='

expect_failure \
  "field 'NOTE' contains a line break" \
  "$WRITER" \
  --output "$OUTPUT" \
  --allowed-key NOTE \
  --field $'NOTE=first line\nsecond line'

assert_file_unchanged "$VALID_SHA256"

printf '\n%s\n' \
  '=== Missing parent-directory rejection ==='

expect_failure \
  'output parent directory does not exist' \
  "$WRITER" \
  --output "$TEST_DIR/missing/release-state.env" \
  --allowed-key RELEASE_ID \
  --required-key RELEASE_ID \
  --field 'RELEASE_ID=value'

assert_file_unchanged "$VALID_SHA256"

printf '\n%s\n' \
  '=== Post-write validation failure preserves previous file ==='

expect_failure \
  'bash was not found; cannot validate the state file' \
  env \
  PATH="$EMPTY_PATH" \
  "$PYTHON_BIN" \
  "$WRITER" \
  --output "$OUTPUT" \
  --allowed-key RELEASE_ID \
  --required-key RELEASE_ID \
  --field 'RELEASE_ID=replacement-attempt'

assert_file_unchanged "$VALID_SHA256"

TEMPORARY_FILE_COUNT="$(
  find "$TEST_DIR" \
    -maxdepth 1 \
    -name '.release-state.env.*.tmp' |
    wc -l |
    tr -d ' '
)"

printf 'TEMPORARY_FILE_COUNT=%s\n' "$TEMPORARY_FILE_COUNT"

[[ "$TEMPORARY_FILE_COUNT" == "0" ]] || {
  fail "temporary release-state files remain after testing"
}

printf '\n%s\n' \
  'UNKNOWN_FIELD_REJECTED=YES' \
  'MISSING_REQUIRED_FIELD_REJECTED=YES' \
  'EMPTY_REQUIRED_FIELD_REJECTED=YES' \
  'DUPLICATE_FIELD_REJECTED=YES' \
  'DUPLICATE_SCHEMA_KEY_REJECTED=YES' \
  'INVALID_KEY_REJECTED=YES' \
  'MULTILINE_VALUE_REJECTED=YES' \
  'MISSING_PARENT_REJECTED=YES' \
  'POST_WRITE_VALIDATION_FAILURE_REJECTED=YES' \
  'PREVIOUS_VALID_FILE_PRESERVED=YES' \
  'TEMPORARY_FILES_CLEANED=YES' \
  'ATOMIC_RELEASE_STATE_WRITER_REGRESSION=PASS'
