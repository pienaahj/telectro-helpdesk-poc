#!/usr/bin/env bash

set -euo pipefail

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

sha256_stdin() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 |
      awk '{print $1}'
    return
  fi

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum |
      awk '{print $1}'
    return
  fi

  fail "no SHA-256 command available"
}

RELEASE_ID="${RELEASE_ID:-}"
FULL_COMMIT_SHA="${FULL_COMMIT_SHA:-}"
SOURCE_ARTIFACT="${SOURCE_ARTIFACT:-}"
SOURCE_TAR_SHA256="${SOURCE_TAR_SHA256:-}"
BUILDX_BUILDER="${BUILDX_BUILDER:-}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
TMPDIR="${TMPDIR:-/tmp}"

[ -n "$RELEASE_ID" ] ||
  fail "RELEASE_ID is required"

case "$RELEASE_ID" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f])
    ;;
  *)
    fail "RELEASE_ID must use YYYYMMDD-<7 lowercase hex> format"
    ;;
esac

[ -n "$FULL_COMMIT_SHA" ] ||
  fail "FULL_COMMIT_SHA is required"

[ -n "$SOURCE_ARTIFACT" ] ||
  fail "SOURCE_ARTIFACT is required"

[ -n "$SOURCE_TAR_SHA256" ] ||
  fail "SOURCE_TAR_SHA256 is required"

[ -n "$BUILDX_BUILDER" ] ||
  fail "BUILDX_BUILDER is required"

[ "${#FULL_COMMIT_SHA}" -eq 40 ] ||
  fail "FULL_COMMIT_SHA must be exactly 40 lowercase hexadecimal characters"

case "$FULL_COMMIT_SHA" in
  *[!0-9a-f]*)
    fail "FULL_COMMIT_SHA must be exactly 40 lowercase hexadecimal characters"
    ;;
esac

SHORT_COMMIT_SHA="${FULL_COMMIT_SHA:0:7}"

case "$RELEASE_ID" in
  *-"$SHORT_COMMIT_SHA")
    ;;
  *)
    fail "RELEASE_ID does not match FULL_COMMIT_SHA"
    ;;
esac

[ "${#SOURCE_TAR_SHA256}" -eq 64 ] ||
  fail "SOURCE_TAR_SHA256 must be exactly 64 lowercase hexadecimal characters"

case "$SOURCE_TAR_SHA256" in
  *[!0-9a-f]*)
    fail "SOURCE_TAR_SHA256 must be exactly 64 lowercase hexadecimal characters"
    ;;
esac

[ -f "$SOURCE_ARTIFACT" ] ||
  fail "source artifact does not exist: $SOURCE_ARTIFACT"

[ -d "$TMPDIR" ] ||
  fail "TMPDIR does not exist: $TMPDIR"

if [ -x "$DOCKER_BIN" ]; then
  :
elif command -v "$DOCKER_BIN" >/dev/null 2>&1; then
  :
else
  fail "Docker command is not available: $DOCKER_BIN"
fi

IMAGE_TAG="telectro/erpnext-runtime:prod-${RELEASE_ID}"
BUILD_PLATFORM="linux/amd64"
ARCHIVE_PREFIX="telectro-helpdesk-poc-${RELEASE_ID}/"
BUILD_LOG="${BUILD_LOG:-/tmp/telectro-runtime-build-${RELEASE_ID}.log}"

BUILD_LOG_DIR="$(dirname "$BUILD_LOG")"

[ -d "$BUILD_LOG_DIR" ] ||
  fail "BUILD_LOG parent does not exist: $BUILD_LOG_DIR"

[ ! -e "$BUILD_LOG" ] ||
  fail "BUILD_LOG already exists: $BUILD_LOG"

BUILD_ROOT="$(
  mktemp -d \
    "${TMPDIR%/}/telectro-runtime-build.${RELEASE_ID}.XXXXXX"
)"

cleanup() {
  if [ -n "${BUILD_ROOT:-}" ] &&
     [ -d "$BUILD_ROOT" ]; then
    rm -rf "$BUILD_ROOT"
  fi
}

trap cleanup EXIT

ARCHIVE_LIST="${BUILD_ROOT}/archive-list.txt"
BUILD_CONTEXT="${BUILD_ROOT}/${ARCHIVE_PREFIX%/}"

printf '%s\n' '=== Phase 4 — source artifact proof ==='

gzip -t "$SOURCE_ARTIFACT" ||
  fail "source artifact gzip integrity failed"

ACTUAL_SOURCE_TAR_SHA256="$(
  gzip -dc "$SOURCE_ARTIFACT" |
    sha256_stdin
)"

[ "$ACTUAL_SOURCE_TAR_SHA256" = "$SOURCE_TAR_SHA256" ] ||
  fail "source tar SHA-256 does not match expected value"

if ! ARCHIVE_COMMIT_SHA="$(
  (
    # git get-tar-commit-id exits after reading the Git archive metadata it
    # needs. gzip may therefore receive the expected SIGPIPE. Disable
    # pipefail only for this metadata-reading pipeline.
    set +o pipefail

    gzip -dc "$SOURCE_ARTIFACT" |
      git get-tar-commit-id
  )
)"; then
  fail "failed to read embedded Git commit from source artifact"
fi

[ "$ARCHIVE_COMMIT_SHA" = "$FULL_COMMIT_SHA" ] ||
  fail "embedded Git commit does not match FULL_COMMIT_SHA"

tar -tzf "$SOURCE_ARTIFACT" >"$ARCHIVE_LIST" ||
  fail "failed to list source artifact"

IFS= read -r FIRST_ARCHIVE_ENTRY <"$ARCHIVE_LIST" ||
  fail "source artifact is empty"

[ "$FIRST_ARCHIVE_ENTRY" = "$ARCHIVE_PREFIX" ] ||
  fail "source artifact root prefix does not match release"

if ! awk \
  -v prefix="$ARCHIVE_PREFIX" \
  'index($0, prefix) != 1 { bad = 1 } END { exit bad }' \
  "$ARCHIVE_LIST"
then
  fail "source artifact contains entries outside expected release prefix"
fi

if grep -E '(^|/)\._' "$ARCHIVE_LIST" >/dev/null 2>&1; then
  fail "source artifact contains macOS AppleDouble entries"
fi

printf 'RELEASE_ID=%s\n' "$RELEASE_ID"
printf 'FULL_COMMIT_SHA=%s\n' "$FULL_COMMIT_SHA"
printf 'SOURCE_ARTIFACT=%s\n' "$SOURCE_ARTIFACT"
printf 'SOURCE_TAR_SHA256=%s\n' "$ACTUAL_SOURCE_TAR_SHA256"
printf 'ARCHIVE_COMMIT_SHA=%s\n' "$ARCHIVE_COMMIT_SHA"
printf 'ARCHIVE_PREFIX=%s\n' "$ARCHIVE_PREFIX"

printf '\n%s\n' '=== Phase 4 — isolated build context ==='

tar -xzf "$SOURCE_ARTIFACT" -C "$BUILD_ROOT" ||
  fail "failed to extract source artifact"

[ -f "$BUILD_CONTEXT/docker/telectro-runtime.Dockerfile" ] ||
  fail "runtime Dockerfile is missing from build context"

[ -d "$BUILD_CONTEXT/apps/helpdesk" ] ||
  fail "Helpdesk application source is missing from build context"

[ -d "$BUILD_CONTEXT/apps/telephony" ] ||
  fail "Telephony application source is missing from build context"

printf 'BUILD_CONTEXT=%s\n' "$BUILD_CONTEXT"
printf '%s\n' 'RUNTIME_DOCKERFILE_PRESENT=YES'
printf '%s\n' 'RUNTIME_APP_CONTEXT_PRESENT=YES'

printf '\n%s\n' '=== Phase 4 — Buildx builder proof ==='

if ! BUILDER_INSPECT="$(
  "$DOCKER_BIN" buildx inspect "$BUILDX_BUILDER" 2>&1
)"; then
  printf '%s\n' "$BUILDER_INSPECT" >&2
  fail "Buildx builder is unavailable: $BUILDX_BUILDER"
fi

printf '%s\n' "$BUILDER_INSPECT"

if ! awk '
  $1 == "Platforms:" {
    for (i = 2; i <= NF; i++) {
      platform = $i
      sub(/,$/, "", platform)

      if (platform == "linux/amd64") {
        found = 1
      }
    }
  }

  END {
    exit(found ? 0 : 1)
  }
' <<<"$BUILDER_INSPECT"
then
  fail "Buildx builder does not advertise linux/amd64"
fi

printf 'BUILDX_BUILDER=%s\n' "$BUILDX_BUILDER"
printf 'BUILD_PLATFORM=%s\n' "$BUILD_PLATFORM"

printf '\n%s\n' '=== Phase 4 — candidate tag preflight ==='

if "$DOCKER_BIN" image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
  fail "candidate image tag already exists locally: $IMAGE_TAG"
fi

printf 'IMAGE_TAG=%s\n' "$IMAGE_TAG"
printf '%s\n' 'CANDIDATE_TAG_ALREADY_EXISTS=NO'

printf '\n%s\n' '=== Phase 4 — immutable runtime build ==='

if "$DOCKER_BIN" buildx build \
  --builder "$BUILDX_BUILDER" \
  --platform "$BUILD_PLATFORM" \
  --progress plain \
  --load \
  --file "$BUILD_CONTEXT/docker/telectro-runtime.Dockerfile" \
  --tag "$IMAGE_TAG" \
  "$BUILD_CONTEXT" \
  2>&1 |
  tee "$BUILD_LOG"
then
  PIPE_STATUSES=("${PIPESTATUS[@]}")
else
  PIPE_STATUSES=("${PIPESTATUS[@]}")
fi

BUILD_STATUS="${PIPE_STATUSES[0]:-1}"
TEE_STATUS="${PIPE_STATUSES[1]:-1}"

printf '\nBUILD_STATUS=%s\n' "$BUILD_STATUS"
printf 'BUILD_LOG_STATUS=%s\n' "$TEE_STATUS"
printf 'BUILD_LOG=%s\n' "$BUILD_LOG"

[ "$TEE_STATUS" -eq 0 ] ||
  fail "failed to retain complete build log"

[ "$BUILD_STATUS" -eq 0 ] ||
  fail "runtime image build failed with status $BUILD_STATUS"

printf '%s\n' 'CANDIDATE_RUNTIME_IMAGE_BUILD_OK=YES'
