#!/usr/bin/env bash

set -euo pipefail

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

RELEASE_ID="${RELEASE_ID:-}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
IMAGE_ARCHIVE="${IMAGE_ARCHIVE:-/tmp/telectro-erpnext-runtime-prod-${RELEASE_ID}.tar.gz}"

[ -n "$RELEASE_ID" ] ||
  fail "RELEASE_ID is required"

case "$RELEASE_ID" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f])
    ;;
  *)
    fail "RELEASE_ID must use YYYYMMDD-<7 lowercase hex> format"
    ;;
esac

if [ -x "$DOCKER_BIN" ]
then
  :
elif command -v "$DOCKER_BIN" >/dev/null 2>&1
then
  :
else
  fail "Docker command is not available: $DOCKER_BIN"
fi

IMAGE_TAG="telectro/erpnext-runtime:prod-${RELEASE_ID}"

if ! IMAGE_ID="$(
  "$DOCKER_BIN" image inspect \
    --format '{{.Id}}' \
    "$IMAGE_TAG" \
    2>/dev/null
)"
then
  fail "candidate image is unavailable: $IMAGE_TAG"
fi

[ -n "$IMAGE_ID" ] ||
  fail "candidate image ID is missing"

[ ! -e "$IMAGE_ARCHIVE" ] ||
  fail "image archive already exists: $IMAGE_ARCHIVE"

[ ! -e "${IMAGE_ARCHIVE}.sha256" ] ||
  fail "image archive SHA-256 sidecar already exists: ${IMAGE_ARCHIVE}.sha256"

ARTIFACT_PAIR_PUBLISHED=NO

cleanup_release_artifact_pair() {
  cleanup_status=$?

  if [ "${ARTIFACT_PAIR_PUBLISHED:-NO}" != "YES" ]
  then
    if ! rm -f \
      "$IMAGE_ARCHIVE" \
      "${IMAGE_ARCHIVE}.sha256"
    then
      printf '%s\n' \
        'ERROR: failed to clean image archive artifact pair' \
        >&2
    fi
  fi

  return "$cleanup_status"
}

trap cleanup_release_artifact_pair EXIT

printf '%s\n' '=== Phase 6 — image archive identity ==='
printf 'RELEASE_ID=%s\n' "$RELEASE_ID"
printf 'IMAGE_TAG=%s\n' "$IMAGE_TAG"
printf 'IMAGE_ID=%s\n' "$IMAGE_ID"
printf 'IMAGE_ARCHIVE=%s\n' "$IMAGE_ARCHIVE"

printf '\n%s\n' '=== Phase 6 — create image archive ==='

if "$DOCKER_BIN" save "$IMAGE_TAG" |
   gzip -1 \
     >"$IMAGE_ARCHIVE"
then
  ARCHIVE_CREATE_STATUS=0
else
  ARCHIVE_CREATE_STATUS=$?
fi

printf 'ARCHIVE_CREATE_STATUS=%s\n' "$ARCHIVE_CREATE_STATUS"

if [ "$ARCHIVE_CREATE_STATUS" -ne 0 ]
then
  rm -f "$IMAGE_ARCHIVE"
  fail "image archive creation failed with status $ARCHIVE_CREATE_STATUS"
fi

if [ ! -s "$IMAGE_ARCHIVE" ]
then
  rm -f "$IMAGE_ARCHIVE"
  fail "image archive was not created or is empty"
fi

printf '\n%s\n' '=== Phase 6 — gzip integrity ==='

if gzip -t "$IMAGE_ARCHIVE"
then
  GZIP_STATUS=0
else
  GZIP_STATUS=$?
fi

printf 'GZIP_STATUS=%s\n' "$GZIP_STATUS"

if [ "$GZIP_STATUS" -ne 0 ]
then
  rm -f "$IMAGE_ARCHIVE"
  fail "image archive gzip validation failed with status $GZIP_STATUS"
fi

printf '%s\n' 'IMAGE_ARCHIVE_GZIP_OK=YES'

printf '\n%s\n' '=== Phase 6 — archive size and SHA-256 ==='

if IMAGE_ARCHIVE_SIZE="$(
  stat -f '%z' "$IMAGE_ARCHIVE"
)"
then
  :
else
  fail "image archive size could not be recorded"
fi

[ -n "$IMAGE_ARCHIVE_SIZE" ] ||
  fail "image archive size is empty"

if IMAGE_ARCHIVE_SHA256="$(
  shasum -a 256 "$IMAGE_ARCHIVE" |
    awk '{print $1}'
)"
then
  :
else
  fail "image archive SHA-256 could not be recorded"
fi

[ -n "$IMAGE_ARCHIVE_SHA256" ] ||
  fail "image archive SHA-256 is empty"

printf 'IMAGE_ARCHIVE_SIZE=%s\n' "$IMAGE_ARCHIVE_SIZE"
printf 'IMAGE_ARCHIVE_SHA256=%s\n' "$IMAGE_ARCHIVE_SHA256"
printf '%s\n' 'IMAGE_ARCHIVE_SHA256_RECORDED=YES'

printf '\n%s\n' '=== Phase 6 — Docker archive manifest ==='

MANIFEST_FILE="$(mktemp)"

if tar -xOzf "$IMAGE_ARCHIVE" manifest.json \
  >"$MANIFEST_FILE"
then
  MANIFEST_STATUS=0
else
  MANIFEST_STATUS=$?
fi

printf 'MANIFEST_STATUS=%s\n' "$MANIFEST_STATUS"

if [ "$MANIFEST_STATUS" -ne 0 ]
then
  rm -f "$MANIFEST_FILE"
  fail "image archive manifest extraction failed with status $MANIFEST_STATUS"
fi

if CONFIG_PATH="$(
  python3 - \
    "$IMAGE_TAG" \
    "$MANIFEST_FILE" <<'PYTHON'
import json
import sys

image_tag = sys.argv[1]
manifest_path = sys.argv[2]

with open(manifest_path, encoding="utf-8") as handle:
    rows = json.load(handle)

matches = [
    row
    for row in rows
    if image_tag in (row.get("RepoTags") or [])
]

if len(matches) != 1:
    raise SystemExit(
        f"expected exactly one manifest entry for {image_tag!r}; "
        f"found {len(matches)}"
    )

config_path = matches[0].get("Config")

if not config_path:
    raise SystemExit(
        f"manifest entry for {image_tag!r} has no Config path"
    )

print(config_path)
PYTHON
)"
then
  CONFIG_PATH_STATUS=0
else
  CONFIG_PATH_STATUS=$?
fi

rm -f "$MANIFEST_FILE"

printf 'EXPECTED_IMAGE_TAG=%s\n' "$IMAGE_TAG"
printf 'CONFIG_PATH=%s\n' "$CONFIG_PATH"
printf 'CONFIG_PATH_STATUS=%s\n' "$CONFIG_PATH_STATUS"

if [ "$CONFIG_PATH_STATUS" -ne 0 ]
then
  rm -f "$IMAGE_ARCHIVE"
  fail "expected image tag was not resolved uniquely in archive manifest"
fi

[ -n "$CONFIG_PATH" ] ||
  fail "archive manifest config path is empty"

printf '%s\n' 'IMAGE_ARCHIVE_TAG_OK=YES'

printf '\n%s\n' '=== Phase 6 — config digest proof ==='

CONFIG_BLOB="$(mktemp)"

case "$CONFIG_PATH" in
  blobs/sha256/*)
    DECLARED_CONFIG_SHA256="${CONFIG_PATH##*/}"
    ;;
  *.json)
    DECLARED_CONFIG_SHA256="${CONFIG_PATH%.json}"
    ;;
  *)
    rm -f \
      "$CONFIG_BLOB" \
      "$IMAGE_ARCHIVE"
    fail "unsupported config path layout: $CONFIG_PATH"
    ;;
esac

if printf '%s\n' "$DECLARED_CONFIG_SHA256" |
   grep -Eq '^[0-9a-f]{64}$'
then
  :
else
  rm -f \
    "$CONFIG_BLOB" \
    "$IMAGE_ARCHIVE"
  fail "declared config digest is invalid: $DECLARED_CONFIG_SHA256"
fi

if tar -xOzf \
  "$IMAGE_ARCHIVE" \
  "$CONFIG_PATH" \
  >"$CONFIG_BLOB"
then
  CONFIG_EXTRACT_STATUS=0
else
  CONFIG_EXTRACT_STATUS=$?
fi

printf 'CONFIG_EXTRACT_STATUS=%s\n' "$CONFIG_EXTRACT_STATUS"

if [ "$CONFIG_EXTRACT_STATUS" -ne 0 ]
then
  rm -f \
    "$CONFIG_BLOB" \
    "$IMAGE_ARCHIVE"
  fail "config blob extraction failed with status $CONFIG_EXTRACT_STATUS"
fi

if ACTUAL_CONFIG_SHA256="$(
  shasum -a 256 "$CONFIG_BLOB" |
    awk '{print $1}'
)"
then
  :
else
  rm -f \
    "$CONFIG_BLOB" \
    "$IMAGE_ARCHIVE"
  fail "config blob SHA-256 could not be recorded"
fi

rm -f "$CONFIG_BLOB"

DECLARED_CONFIG_DIGEST="sha256:${DECLARED_CONFIG_SHA256}"
IMAGE_CONFIG_DIGEST="$DECLARED_CONFIG_DIGEST"

printf 'DECLARED_CONFIG_DIGEST=%s\n' "$DECLARED_CONFIG_DIGEST"
printf 'IMAGE_CONFIG_DIGEST=%s\n' "$IMAGE_CONFIG_DIGEST"
printf 'ACTUAL_CONFIG_SHA256=%s\n' "$ACTUAL_CONFIG_SHA256"

if [ "$DECLARED_CONFIG_SHA256" != "$ACTUAL_CONFIG_SHA256" ]
then
  rm -f "$IMAGE_ARCHIVE"
  fail "config blob SHA-256 does not match declared config digest"
fi

printf '%s\n' 'IMAGE_ARCHIVE_CONFIG_DIGEST_OK=YES'

printf '\n%s\n' '=== Phase 6 — aggregate archive validation ==='

if [ "$ARCHIVE_CREATE_STATUS" -eq 0 ] &&
   [ "$GZIP_STATUS" -eq 0 ] &&
   [ -s "$IMAGE_ARCHIVE" ] &&
   [ -n "$IMAGE_ARCHIVE_SIZE" ] &&
   [ -n "$IMAGE_ARCHIVE_SHA256" ] &&
   [ "$MANIFEST_STATUS" -eq 0 ] &&
   [ "$CONFIG_PATH_STATUS" -eq 0 ] &&
   [ -n "$CONFIG_PATH" ] &&
   [ "$CONFIG_EXTRACT_STATUS" -eq 0 ] &&
   [ "$DECLARED_CONFIG_SHA256" = "$ACTUAL_CONFIG_SHA256" ]
then
  :
else
  rm -f "$IMAGE_ARCHIVE"
  fail "aggregate image archive validation failed"
fi

printf '%s\n' 'IMAGE_ARCHIVE_VALIDATION_OK=YES'

printf '\n%s\n' '=== Phase 6 — archive SHA-256 sidecar ==='

IMAGE_ARCHIVE_SHA256_FILE="${IMAGE_ARCHIVE}.sha256"
IMAGE_ARCHIVE_BASENAME="$(basename "$IMAGE_ARCHIVE")"

if printf '%s  %s\n' \
  "$IMAGE_ARCHIVE_SHA256" \
  "$IMAGE_ARCHIVE_BASENAME" \
  >"$IMAGE_ARCHIVE_SHA256_FILE"
then
  SHA256_SIDECAR_STATUS=0
else
  SHA256_SIDECAR_STATUS=$?
fi

printf 'SHA256_SIDECAR_STATUS=%s\n' "$SHA256_SIDECAR_STATUS"

if [ "$SHA256_SIDECAR_STATUS" -ne 0 ]
then
  rm -f \
    "$IMAGE_ARCHIVE_SHA256_FILE" \
    "$IMAGE_ARCHIVE"
  fail "archive SHA-256 sidecar creation failed with status $SHA256_SIDECAR_STATUS"
fi

printf 'IMAGE_ARCHIVE_SHA256_FILE=%s\n' "$IMAGE_ARCHIVE_SHA256_FILE"
ARTIFACT_PAIR_PUBLISHED=YES
trap - EXIT
