#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

REPO_DIR="${REPO_DIR:-$DEFAULT_REPO_DIR}"
RELEASE_ID="${RELEASE_ID:-}"
FULL_COMMIT_SHA="${FULL_COMMIT_SHA:-}"
GZIP_BIN="${GZIP_BIN:-gzip}"

TEMP_ARTIFACT=""

cleanup() {
  if [[ -n "$TEMP_ARTIFACT" && -e "$TEMP_ARTIFACT" ]]; then
    rm -f "$TEMP_ARTIFACT"
  fi
}

trap cleanup EXIT

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ -z "$RELEASE_ID" ]]; then
  fail "RELEASE_ID is required"
fi

if [[ -z "$FULL_COMMIT_SHA" ]]; then
  fail "FULL_COMMIT_SHA is required"
fi

if [[ ${#FULL_COMMIT_SHA} -ne 40 || "$FULL_COMMIT_SHA" == *[!0-9a-f]* ]]; then
  fail "FULL_COMMIT_SHA must be a 40-character lowercase hexadecimal SHA"
fi

if ! REPO_DIR="$(
  cd "$REPO_DIR" 2>/dev/null &&
    pwd
)"; then
  fail "repository directory does not exist: $REPO_DIR"
fi

if ! GIT_TOPLEVEL="$(
  git \
    -C "$REPO_DIR" \
    rev-parse \
    --show-toplevel \
    2>/dev/null
)"; then
  fail "REPO_DIR must be a Git working tree: $REPO_DIR"
fi

REPO_DIR="$GIT_TOPLEVEL"

if ! RESOLVED_COMMIT_SHA="$(
  git \
    -C "$REPO_DIR" \
    rev-parse \
    --verify \
    "${FULL_COMMIT_SHA}^{commit}" \
    2>/dev/null
)"; then
  fail "FULL_COMMIT_SHA is not an existing commit: $FULL_COMMIT_SHA"
fi

if [[ "$RESOLVED_COMMIT_SHA" != "$FULL_COMMIT_SHA" ]]; then
  fail \
    "FULL_COMMIT_SHA resolved unexpectedly: expected $FULL_COMMIT_SHA, observed $RESOLVED_COMMIT_SHA"
fi

SHORT_COMMIT_SHA="${FULL_COMMIT_SHA:0:7}"

if [[ "$RELEASE_ID" != *-"$SHORT_COMMIT_SHA" ]]; then
  fail \
    "RELEASE_ID must end with -$SHORT_COMMIT_SHA; observed: $RELEASE_ID"
fi

SOURCE_ARTIFACT="${SOURCE_ARTIFACT:-/tmp/telectro-app-${RELEASE_ID}.tar.gz}"

if [[ -e "$SOURCE_ARTIFACT" ]]; then
  fail "source artifact already exists: $SOURCE_ARTIFACT"
fi

SOURCE_ARTIFACT_DIR="$(dirname "$SOURCE_ARTIFACT")"

if [[ ! -d "$SOURCE_ARTIFACT_DIR" ]]; then
  fail \
    "source artifact parent directory does not exist: $SOURCE_ARTIFACT_DIR"
fi

if ! command -v "$GZIP_BIN" >/dev/null 2>&1; then
  fail "gzip command is unavailable: $GZIP_BIN"
fi

ARCHIVE_PREFIX="telectro-helpdesk-poc-${RELEASE_ID}/"

if ! TEMP_ARTIFACT="$(
  mktemp "${SOURCE_ARTIFACT}.tmp.XXXXXX"
)"; then
  fail "failed to create temporary source artifact path"
fi

if ! git \
  -C "$REPO_DIR" \
  archive \
  --format=tar \
  --prefix="$ARCHIVE_PREFIX" \
  "$FULL_COMMIT_SHA" |
  "$GZIP_BIN" -n -9 > "$TEMP_ARTIFACT"
then
  fail "failed to create source artifact"
fi

# git get-tar-commit-id reads only the tar metadata it needs and may
# close the pipe before gzip finishes writing. Disable pipefail only
# for this pipeline so the expected upstream SIGPIPE is not treated
# as archive corruption. Later validations consume the full archive.
if ! ARCHIVE_COMMIT_SHA="$(
  (
    set +o pipefail

    "$GZIP_BIN" \
      -dc \
      "$TEMP_ARTIFACT" |
      git get-tar-commit-id
  )
)"; then
  fail "failed to read embedded Git commit from source artifact"
fi

if [[ "$ARCHIVE_COMMIT_SHA" != "$FULL_COMMIT_SHA" ]]; then
  fail \
    "embedded archive commit mismatch: expected $FULL_COMMIT_SHA, observed $ARCHIVE_COMMIT_SHA"
fi

if ! FIRST_ARCHIVE_ENTRY="$(
  tar \
    -tzf \
    "$TEMP_ARTIFACT" |
    sed -n '1p'
)"; then
  fail "failed to inspect source artifact prefix"
fi

if [[ "$FIRST_ARCHIVE_ENTRY" != "$ARCHIVE_PREFIX" ]]; then
  fail \
    "archive root prefix mismatch: expected $ARCHIVE_PREFIX, observed $FIRST_ARCHIVE_ENTRY"
fi

if ! BAD_PREFIX_COUNT="$(
  tar \
    -tzf \
    "$TEMP_ARTIFACT" |
    awk \
      -v prefix="$ARCHIVE_PREFIX" \
      'index($0, prefix) != 1 {
        count++
      }
      END {
        print count + 0
      }'
)"; then
  fail "failed to validate source artifact entry prefixes"
fi

if [[ "$BAD_PREFIX_COUNT" -ne 0 ]]; then
  fail \
    "source artifact contains entries outside expected prefix: count=$BAD_PREFIX_COUNT"
fi

if ! APPLEDOUBLE_COUNT="$(
  tar \
    -tzf \
    "$TEMP_ARTIFACT" |
    awk \
      -F/ \
      '$NF ~ /^\._/ {
        count++
      }
      END {
        print count + 0
      }'
)"; then
  fail "failed to inspect source artifact for AppleDouble entries"
fi

if [[ "$APPLEDOUBLE_COUNT" -ne 0 ]]; then
  fail \
    "source artifact contains AppleDouble entries: count=$APPLEDOUBLE_COUNT"
fi

if ! SOURCE_TAR_SHA256="$(
  "$GZIP_BIN" \
    -dc \
    "$TEMP_ARTIFACT" |
    shasum -a 256 |
    awk '{print $1}'
)"; then
  fail "failed to calculate source tar SHA-256"
fi

if ! SOURCE_ARTIFACT_SHA256="$(
  shasum \
    -a 256 \
    "$TEMP_ARTIFACT" |
    awk '{print $1}'
)"; then
  fail "failed to calculate source artifact SHA-256"
fi

if ! mv \
  "$TEMP_ARTIFACT" \
  "$SOURCE_ARTIFACT"
then
  fail "failed to publish validated source artifact"
fi

TEMP_ARTIFACT=""

printf '%s\n' \
  "RELEASE_ID=$RELEASE_ID" \
  "FULL_COMMIT_SHA=$FULL_COMMIT_SHA" \
  "SOURCE_ARTIFACT=$SOURCE_ARTIFACT" \
  "ARCHIVE_PREFIX=$ARCHIVE_PREFIX" \
  "ARCHIVE_COMMIT_SHA=$ARCHIVE_COMMIT_SHA" \
  "APPLEDOUBLE_COUNT=$APPLEDOUBLE_COUNT" \
  "SOURCE_TAR_SHA256=$SOURCE_TAR_SHA256" \
  "SOURCE_ARTIFACT_SHA256=$SOURCE_ARTIFACT_SHA256"

printf '\n%s\n' \
  'SOURCE_ARTIFACT_CREATED' \
  'SOURCE_ARTIFACT_APPLEDOUBLE_FREE' \
  'SOURCE_ARTIFACT_SHA256_RECORDED'
