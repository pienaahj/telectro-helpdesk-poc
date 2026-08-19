#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

HELPER="${ROOT_DIR}/bin/release-image-archive.sh"

KNOWN_RELEASE_ID="20260814-b946cbf"
KNOWN_IMAGE_TAG="telectro/erpnext-runtime:prod-${KNOWN_RELEASE_ID}"
KNOWN_IMAGE_ID="sha256:c405f1267b71728891810722d627c7e6cf14126609b44f5285fb729161f1c3aa"
KNOWN_DEFAULT_IMAGE_ARCHIVE="/tmp/telectro-erpnext-runtime-prod-${KNOWN_RELEASE_ID}.tar.gz"

printf '%s\n' '=== Phase 6 image-archive regression ==='

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}


write_mock_docker_archive() {
  local archive_path="$1"
  local image_tag="$2"
  local config_path_file="$3"

  python3 - \
    "$archive_path" \
    "$image_tag" \
    "$config_path_file" <<'PYTHON'
import hashlib
import io
import json
import sys
import tarfile

archive_path = sys.argv[1]
image_tag = sys.argv[2]
config_path_file = sys.argv[3]

config_blob = (
    b'{"architecture":"amd64","os":"linux",'
    b'"fixture":"phase6-manifest-proof"}\n'
)

config_sha256 = hashlib.sha256(config_blob).hexdigest()
config_path = f"blobs/sha256/{config_sha256}"

manifest = [
    {
        "Config": config_path,
        "RepoTags": [image_tag],
        "Layers": [],
    }
]

manifest_blob = json.dumps(
    manifest,
    separators=(",", ":"),
).encode("utf-8")

with tarfile.open(archive_path, mode="w") as archive:
    manifest_info = tarfile.TarInfo("manifest.json")
    manifest_info.size = len(manifest_blob)
    archive.addfile(
        manifest_info,
        io.BytesIO(manifest_blob),
    )

    config_info = tarfile.TarInfo(config_path)
    config_info.size = len(config_blob)
    archive.addfile(
        config_info,
        io.BytesIO(config_blob),
    )

with open(config_path_file, "w", encoding="utf-8") as handle:
    handle.write(config_path + "\n")
PYTHON
}

if [ ! -x "$HELPER" ]
then
  printf '%s\n' 'RELEASE_IMAGE_ARCHIVE_HELPER_PRESENT=FAIL'
  printf 'EXPECTED_HELPER=%s\n' "$HELPER"
  exit 1
fi

printf '%s\n' 'RELEASE_IMAGE_ARCHIVE_HELPER_PRESENT=PASS'

printf '\n%s\n' '=== Missing release ID rejection ==='

if MISSING_RELEASE_OUTPUT="$(
  "$HELPER" \
    2>&1
)"
then
  MISSING_RELEASE_STATUS=0
else
  MISSING_RELEASE_STATUS=$?
fi

printf '%s\n' "$MISSING_RELEASE_OUTPUT"
printf 'MISSING_RELEASE_STATUS=%s\n' "$MISSING_RELEASE_STATUS"

[ "$MISSING_RELEASE_STATUS" -ne 0 ] ||
  fail "missing RELEASE_ID was accepted"

grep -Fqx \
  'ERROR: RELEASE_ID is required' \
  <<<"$MISSING_RELEASE_OUTPUT" ||
  fail "missing RELEASE_ID rejection reason was not reported"

printf '%s\n' 'MISSING_RELEASE_ID_REJECTED=PASS'

printf '\n%s\n' '=== Known-good archive identity ==='

IDENTITY_TMP_ROOT="$(mktemp -d)"
IDENTITY_MOCK_DOCKER="${IDENTITY_TMP_ROOT}/docker"
IDENTITY_MOCK_ARGS="${IDENTITY_TMP_ROOT}/docker-args.txt"
IDENTITY_DOCKER_TAR="${IDENTITY_TMP_ROOT}/docker-save.tar"
IDENTITY_CONFIG_PATH_FILE="${IDENTITY_TMP_ROOT}/config-path.txt"

write_mock_docker_archive \
  "$IDENTITY_DOCKER_TAR" \
  "$KNOWN_IMAGE_TAG" \
  "$IDENTITY_CONFIG_PATH_FILE"

cat >"$IDENTITY_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >>"${IDENTITY_MOCK_ARGS:?}"

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  if [ "$5" != "${EXPECTED_IMAGE_TAG:?}" ]
  then
    printf 'unexpected image tag: %s\n' "$5" >&2
    exit 91
  fi

  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  cat "${IDENTITY_DOCKER_TAR:?}"
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$IDENTITY_MOCK_DOCKER"

export IDENTITY_MOCK_ARGS
export IDENTITY_DOCKER_TAR
export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"
export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"

if IDENTITY_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="${IDENTITY_TMP_ROOT}/candidate.tar.gz" \
  DOCKER_BIN="$IDENTITY_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  IDENTITY_STATUS=0
else
  IDENTITY_STATUS=$?
fi

printf '%s\n' "$IDENTITY_OUTPUT"
printf 'IDENTITY_STATUS=%s\n' "$IDENTITY_STATUS"

[ "$IDENTITY_STATUS" -eq 0 ] ||
  fail "known-good archive identity returned ${IDENTITY_STATUS}"

grep -Fqx \
  "RELEASE_ID=${KNOWN_RELEASE_ID}" \
  <<<"$IDENTITY_OUTPUT" ||
  fail "release ID was not emitted"

grep -Fqx \
  "IMAGE_TAG=${KNOWN_IMAGE_TAG}" \
  <<<"$IDENTITY_OUTPUT" ||
  fail "immutable image tag was not derived correctly"

grep -Fqx \
  "IMAGE_ID=${KNOWN_IMAGE_ID}" \
  <<<"$IDENTITY_OUTPUT" ||
  fail "candidate image ID was not emitted correctly"

test -f "$IDENTITY_MOCK_ARGS" ||
  fail "known-good candidate image inspection was not invoked"

grep -F \
  'image inspect --format' \
  "$IDENTITY_MOCK_ARGS" \
  >/dev/null ||
  fail "known-good candidate image was not inspected"

grep -F \
  "$KNOWN_IMAGE_TAG" \
  "$IDENTITY_MOCK_ARGS" \
  >/dev/null ||
  fail "known-good image inspection did not use immutable tag"

rm -rf "$IDENTITY_TMP_ROOT"

printf '%s\n' 'KNOWN_GOOD_ARCHIVE_IDENTITY=PASS'

printf '\n%s\n' '=== Unavailable Docker command rejection ==='

UNAVAILABLE_DOCKER="$(mktemp -d)/docker"

if DOCKER_UNAVAILABLE_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  DOCKER_BIN="$UNAVAILABLE_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  DOCKER_UNAVAILABLE_STATUS=0
else
  DOCKER_UNAVAILABLE_STATUS=$?
fi

printf '%s\n' "$DOCKER_UNAVAILABLE_OUTPUT"
printf 'DOCKER_UNAVAILABLE_STATUS=%s\n' "$DOCKER_UNAVAILABLE_STATUS"

[ "$DOCKER_UNAVAILABLE_STATUS" -ne 0 ] ||
  fail "unavailable Docker command was accepted"

grep -Fqx \
  "ERROR: Docker command is not available: ${UNAVAILABLE_DOCKER}" \
  <<<"$DOCKER_UNAVAILABLE_OUTPUT" ||
  fail "unavailable Docker rejection reason was not reported"

printf '%s\n' 'UNAVAILABLE_DOCKER_REJECTED=PASS'


printf '\n%s\n' '=== Unavailable candidate image rejection ==='

TMP_ROOT="$(mktemp -d)"
MOCK_DOCKER="${TMP_ROOT}/docker"
MOCK_DOCKER_ARGS="${TMP_ROOT}/docker-args.txt"

cat >"$MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >"${MOCK_DOCKER_ARGS:?}"

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf 'Error: No such image: %s\n' "$5" >&2
  exit 1
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$MOCK_DOCKER"
export MOCK_DOCKER_ARGS

if IMAGE_UNAVAILABLE_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  DOCKER_BIN="$MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  IMAGE_UNAVAILABLE_STATUS=0
else
  IMAGE_UNAVAILABLE_STATUS=$?
fi

printf '%s\n' "$IMAGE_UNAVAILABLE_OUTPUT"
printf 'IMAGE_UNAVAILABLE_STATUS=%s\n' "$IMAGE_UNAVAILABLE_STATUS"

[ "$IMAGE_UNAVAILABLE_STATUS" -ne 0 ] ||
  fail "unavailable candidate image was accepted"

grep -F \
  "candidate image is unavailable: ${KNOWN_IMAGE_TAG}" \
  <<<"$IMAGE_UNAVAILABLE_OUTPUT" \
  >/dev/null ||
  fail "unavailable candidate image rejection reason was not reported"

test -f "$MOCK_DOCKER_ARGS" ||
  fail "Docker image inspection was not invoked"

grep -F \
  'image inspect --format' \
  "$MOCK_DOCKER_ARGS" \
  >/dev/null ||
  fail "candidate image was not inspected"

grep -F \
  "$KNOWN_IMAGE_TAG" \
  "$MOCK_DOCKER_ARGS" \
  >/dev/null ||
  fail "candidate image inspection did not use expected immutable tag"

rm -rf "$TMP_ROOT"

printf '%s\n' 'UNAVAILABLE_CANDIDATE_IMAGE_REJECTED=PASS'

printf '\n%s\n' '=== Empty candidate image ID rejection ==='

EMPTY_ID_TMP_ROOT="$(mktemp -d)"
EMPTY_ID_MOCK_DOCKER="${EMPTY_ID_TMP_ROOT}/docker"
EMPTY_ID_DOCKER_CALLS="${EMPTY_ID_TMP_ROOT}/docker-calls.txt"
EMPTY_ID_IMAGE_ARCHIVE="${EMPTY_ID_TMP_ROOT}/candidate.tar.gz"

cat >"$EMPTY_ID_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >>"${EMPTY_ID_DOCKER_CALLS:?}"

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '\n'
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  printf '%s\n' \
    'docker save must not run for empty image ID' \
    >&2
  exit 93
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$EMPTY_ID_MOCK_DOCKER"
export EMPTY_ID_DOCKER_CALLS

if EMPTY_ID_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$EMPTY_ID_IMAGE_ARCHIVE" \
  DOCKER_BIN="$EMPTY_ID_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  EMPTY_ID_STATUS=0
else
  EMPTY_ID_STATUS=$?
fi

printf '%s\n' "$EMPTY_ID_OUTPUT"
printf 'EMPTY_ID_STATUS=%s\n' "$EMPTY_ID_STATUS"

[ "$EMPTY_ID_STATUS" -ne 0 ] ||
  fail "empty candidate image ID was accepted"

grep -Fqx \
  'ERROR: candidate image ID is missing' \
  <<<"$EMPTY_ID_OUTPUT" ||
  fail "empty candidate image ID rejection reason was not reported"

if grep -F \
  'save ' \
  "$EMPTY_ID_DOCKER_CALLS" \
  >/dev/null
then
  fail "empty candidate image ID did not stop docker save"
fi

[ ! -e "$EMPTY_ID_IMAGE_ARCHIVE" ] ||
  fail "empty candidate image ID created an archive"

rm -rf "$EMPTY_ID_TMP_ROOT"

printf '%s\n' 'EMPTY_CANDIDATE_IMAGE_ID_REJECTED=PASS'
printf '%s\n' 'EMPTY_IMAGE_ID_STOPPED_DOCKER_SAVE=PASS'

printf '\n%s\n' '=== Default archive path derivation ==='

DEFAULT_TMP_ROOT="$(mktemp -d)"
DEFAULT_MOCK_DOCKER="${DEFAULT_TMP_ROOT}/docker"
DEFAULT_TEST_RELEASE_ID="20991231-deadbee"
DEFAULT_TEST_IMAGE_ARCHIVE="/tmp/telectro-erpnext-runtime-prod-${DEFAULT_TEST_RELEASE_ID}.tar.gz"
DEFAULT_DOCKER_TAR="${DEFAULT_TMP_ROOT}/docker-save.tar"
DEFAULT_CONFIG_PATH_FILE="${DEFAULT_TMP_ROOT}/config-path.txt"

write_mock_docker_archive \
  "$DEFAULT_DOCKER_TAR" \
  "telectro/erpnext-runtime:prod-${DEFAULT_TEST_RELEASE_ID}" \
  "$DEFAULT_CONFIG_PATH_FILE"

cat >"$DEFAULT_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  cat "${DEFAULT_DOCKER_TAR:?}"
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$DEFAULT_MOCK_DOCKER"

export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export DEFAULT_DOCKER_TAR

[ ! -e "$DEFAULT_TEST_IMAGE_ARCHIVE" ] ||
  fail "default archive test path already exists before test: $DEFAULT_TEST_IMAGE_ARCHIVE"

if DEFAULT_ARCHIVE_OUTPUT="$(
  RELEASE_ID="$DEFAULT_TEST_RELEASE_ID" \
  DOCKER_BIN="$DEFAULT_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  DEFAULT_ARCHIVE_STATUS=0
else
  DEFAULT_ARCHIVE_STATUS=$?
fi

printf '%s\n' "$DEFAULT_ARCHIVE_OUTPUT"
printf 'DEFAULT_ARCHIVE_STATUS=%s\n' "$DEFAULT_ARCHIVE_STATUS"

[ "$DEFAULT_ARCHIVE_STATUS" -eq 0 ] ||
  fail "default archive-path derivation returned ${DEFAULT_ARCHIVE_STATUS}"

grep -Fqx \
  "IMAGE_ARCHIVE=${DEFAULT_TEST_IMAGE_ARCHIVE}" \
  <<<"$DEFAULT_ARCHIVE_OUTPUT" ||
  fail "default image archive path was not derived"

rm -f \
  "$DEFAULT_TEST_IMAGE_ARCHIVE" \
  "${DEFAULT_TEST_IMAGE_ARCHIVE}.sha256"
rm -rf "$DEFAULT_TMP_ROOT"

printf '%s\n' 'DEFAULT_IMAGE_ARCHIVE_DERIVED=PASS'

printf '\n%s\n' '=== Existing archive destination rejection ==='

DEST_TMP_ROOT="$(mktemp -d)"
DEST_MOCK_DOCKER="${DEST_TMP_ROOT}/docker"
DEST_MOCK_ARGS="${DEST_TMP_ROOT}/docker-args.txt"
EXISTING_IMAGE_ARCHIVE="${DEST_TMP_ROOT}/candidate.tar.gz"

: >"$EXISTING_IMAGE_ARCHIVE"

cat >"$DEST_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >>"${DEST_MOCK_ARGS:?}"

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -ge 1 ] &&
   [ "$1" = "save" ]
then
  printf '%s\n' 'MOCK_DOCKER_SAVE_INVOKED'
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$DEST_MOCK_DOCKER"

export DEST_MOCK_ARGS
export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"

if EXISTING_DEST_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$EXISTING_IMAGE_ARCHIVE" \
  DOCKER_BIN="$DEST_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  EXISTING_DEST_STATUS=0
else
  EXISTING_DEST_STATUS=$?
fi

printf '%s\n' "$EXISTING_DEST_OUTPUT"
printf 'EXISTING_DEST_STATUS=%s\n' "$EXISTING_DEST_STATUS"

[ "$EXISTING_DEST_STATUS" -ne 0 ] ||
  fail "existing image archive destination was accepted"

grep -Fqx \
  "ERROR: image archive already exists: ${EXISTING_IMAGE_ARCHIVE}" \
  <<<"$EXISTING_DEST_OUTPUT" ||
  fail "existing archive rejection reason was not reported"

if grep -F \
  'save ' \
  "$DEST_MOCK_ARGS" \
  >/dev/null
then
  fail "docker save was invoked for existing archive destination"
fi

rm -rf "$DEST_TMP_ROOT"

printf '%s\n' 'EXISTING_IMAGE_ARCHIVE_REJECTED=PASS'
printf '%s\n' 'EXISTING_DESTINATION_STOPPED_DOCKER_SAVE=PASS'

printf '\n%s\n' '=== Known-good archive creation ==='

CREATE_TMP_ROOT="$(mktemp -d)"
CREATE_MOCK_DOCKER="${CREATE_TMP_ROOT}/docker"
CREATE_MOCK_ARGS="${CREATE_TMP_ROOT}/docker-args.txt"
CREATE_MOCK_GZIP="${CREATE_TMP_ROOT}/gzip"
CREATE_GZIP_ARGS="${CREATE_TMP_ROOT}/gzip-args.txt"
CREATE_REAL_GZIP="$(command -v gzip)"
CREATE_IMAGE_ARCHIVE="${CREATE_TMP_ROOT}/candidate.tar.gz"
CREATE_DOCKER_TAR="${CREATE_TMP_ROOT}/docker-save.tar"
CREATE_CONFIG_PATH_FILE="${CREATE_TMP_ROOT}/config-path.txt"

write_mock_docker_archive \
  "$CREATE_DOCKER_TAR" \
  "$KNOWN_IMAGE_TAG" \
  "$CREATE_CONFIG_PATH_FILE"

CREATE_EXPECTED_CONFIG_PATH="$(
  cat "$CREATE_CONFIG_PATH_FILE"
)"

cat >"$CREATE_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >>"${CREATE_MOCK_ARGS:?}"

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  if [ "$2" != "${EXPECTED_IMAGE_TAG:?}" ]
  then
    printf 'unexpected image tag: %s\n' "$2" >&2
    exit 91
  fi

  cat "${CREATE_DOCKER_TAR:?}"
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$CREATE_MOCK_DOCKER"

cat >"$CREATE_MOCK_GZIP" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >>"${CREATE_GZIP_ARGS:?}"

exec "${CREATE_REAL_GZIP:?}" "$@"
MOCK

chmod +x "$CREATE_MOCK_GZIP"

export CREATE_MOCK_ARGS
export CREATE_DOCKER_TAR
export CREATE_GZIP_ARGS
export CREATE_REAL_GZIP
export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"

if CREATE_OUTPUT="$(
  PATH="${CREATE_TMP_ROOT}:$PATH" \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$CREATE_IMAGE_ARCHIVE" \
  DOCKER_BIN="$CREATE_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  CREATE_STATUS=0
else
  CREATE_STATUS=$?
fi

printf '%s\n' "$CREATE_OUTPUT"
printf 'CREATE_STATUS=%s\n' "$CREATE_STATUS"

[ "$CREATE_STATUS" -eq 0 ] ||
  fail "known-good archive creation returned ${CREATE_STATUS}"

test -f "$CREATE_IMAGE_ARCHIVE" ||
  fail "image archive was not created"

[ -s "$CREATE_IMAGE_ARCHIVE" ] ||
  fail "created image archive is empty"

test -f "$CREATE_MOCK_ARGS" ||
  fail "Docker invocations were not recorded"

grep -Fqx \
  "save ${KNOWN_IMAGE_TAG}" \
  "$CREATE_MOCK_ARGS" ||
  fail "docker save did not use the exact immutable image tag"

if gzip -t "$CREATE_IMAGE_ARCHIVE"
then
  :
else
  fail "created image archive is not valid gzip"
fi

test -f "$CREATE_GZIP_ARGS" ||
  fail "gzip invocations were not recorded"

grep -Fqx --   '-1'   "$CREATE_GZIP_ARGS" ||
  fail "archive creation did not use gzip -1"

grep -Fqx --   "-t ${CREATE_IMAGE_ARCHIVE}"   "$CREATE_GZIP_ARGS" ||
  fail "helper did not validate gzip integrity"

grep -Fqx   'GZIP_STATUS=0'   <<<"$CREATE_OUTPUT" ||
  fail "successful gzip validation status was not reported"

grep -Fqx   'IMAGE_ARCHIVE_GZIP_OK=YES'   <<<"$CREATE_OUTPUT" ||
  fail "successful gzip integrity marker was not reported"

EXPECTED_ARCHIVE_SIZE="$(
  stat -f '%z' "$CREATE_IMAGE_ARCHIVE"
)"

EXPECTED_ARCHIVE_SHA256="$(
  shasum -a 256 "$CREATE_IMAGE_ARCHIVE" |
    awk '{print $1}'
)"

grep -Fqx \
  "IMAGE_ARCHIVE_SIZE=${EXPECTED_ARCHIVE_SIZE}" \
  <<<"$CREATE_OUTPUT" ||
  fail "exact image archive size was not reported"

grep -Fqx \
  "IMAGE_ARCHIVE_SHA256=${EXPECTED_ARCHIVE_SHA256}" \
  <<<"$CREATE_OUTPUT" ||
  fail "exact image archive SHA-256 was not reported"

grep -Fqx \
  'IMAGE_ARCHIVE_SHA256_RECORDED=YES' \
  <<<"$CREATE_OUTPUT" ||
  fail "image archive SHA-256 evidence marker was not reported"

grep -Fqx \
  'MANIFEST_STATUS=0' \
  <<<"$CREATE_OUTPUT" ||
  fail "archive manifest extraction status was not reported"

grep -Fqx \
  "EXPECTED_IMAGE_TAG=${KNOWN_IMAGE_TAG}" \
  <<<"$CREATE_OUTPUT" ||
  fail "expected archive image tag was not reported"

grep -Fqx \
  "CONFIG_PATH=${CREATE_EXPECTED_CONFIG_PATH}" \
  <<<"$CREATE_OUTPUT" ||
  fail "manifest config path was not resolved for expected image tag"

grep -Fqx \
  'CONFIG_PATH_STATUS=0' \
  <<<"$CREATE_OUTPUT" ||
  fail "manifest config-path resolution status was not reported"

grep -Fqx \
  'IMAGE_ARCHIVE_TAG_OK=YES' \
  <<<"$CREATE_OUTPUT" ||
  fail "image archive tag validation marker was not reported"

CREATE_EXPECTED_CONFIG_SHA256="${CREATE_EXPECTED_CONFIG_PATH##*/}"
CREATE_EXPECTED_CONFIG_DIGEST="sha256:${CREATE_EXPECTED_CONFIG_SHA256}"

grep -Fqx \
  'CONFIG_EXTRACT_STATUS=0' \
  <<<"$CREATE_OUTPUT" ||
  fail "config blob extraction status was not reported"

grep -Fqx \
  "DECLARED_CONFIG_DIGEST=${CREATE_EXPECTED_CONFIG_DIGEST}" \
  <<<"$CREATE_OUTPUT" ||
  fail "declared config digest was not derived from config path"

grep -Fqx \
  "IMAGE_CONFIG_DIGEST=${CREATE_EXPECTED_CONFIG_DIGEST}" \
  <<<"$CREATE_OUTPUT" ||
  fail "release image config digest was not recorded"

grep -Fqx \
  "ACTUAL_CONFIG_SHA256=${CREATE_EXPECTED_CONFIG_SHA256}" \
  <<<"$CREATE_OUTPUT" ||
  fail "actual config blob SHA-256 was not reported"

grep -Fqx \
  'IMAGE_ARCHIVE_CONFIG_DIGEST_OK=YES' \
  <<<"$CREATE_OUTPUT" ||
  fail "image archive config digest validation marker was not reported"

grep -Fqx \
  'IMAGE_ARCHIVE_VALIDATION_OK=YES' \
  <<<"$CREATE_OUTPUT" ||
  fail "aggregate image archive validation marker was not reported"

CREATE_ARCHIVE_PATH_FROM_OUTPUT="$(
  awk -F= \
    '/^IMAGE_ARCHIVE=/ {
      print substr($0, index($0, "=") + 1)
      exit
    }' \
    <<<"$CREATE_OUTPUT"
)"

[ -n "$CREATE_ARCHIVE_PATH_FROM_OUTPUT" ] ||
  fail "created image archive path was not reported"

CREATE_SHA256_FILE="${CREATE_ARCHIVE_PATH_FROM_OUTPUT}.sha256"

test -f "$CREATE_SHA256_FILE" ||
  fail "archive SHA-256 sidecar was not created"

CREATE_ACTUAL_ARCHIVE_SHA256="$(
  shasum -a 256 "$CREATE_ARCHIVE_PATH_FROM_OUTPUT" |
    awk '{print $1}'
)"

CREATE_EXPECTED_SHA256_FILE="${CREATE_TMP_ROOT}/expected-image-archive.sha256"

printf '%s  %s\n' \
  "$CREATE_ACTUAL_ARCHIVE_SHA256" \
  "$(basename "$CREATE_ARCHIVE_PATH_FROM_OUTPUT")" \
  >"$CREATE_EXPECTED_SHA256_FILE"

cmp -s \
  "$CREATE_EXPECTED_SHA256_FILE" \
  "$CREATE_SHA256_FILE" ||
  fail "archive SHA-256 sidecar content was not portable and exact"

rm -rf "$CREATE_TMP_ROOT"

printf '%s\n' 'KNOWN_GOOD_IMAGE_ARCHIVE_CREATED=PASS'
printf '%s\n' 'DOCKER_SAVE_USED_IMMUTABLE_TAG=PASS'

printf '\n%s\n' '=== Failed docker save cleanup ==='

SAVE_FAIL_TMP_ROOT="$(mktemp -d)"
SAVE_FAIL_MOCK_DOCKER="${SAVE_FAIL_TMP_ROOT}/docker"
SAVE_FAIL_MOCK_ARGS="${SAVE_FAIL_TMP_ROOT}/docker-args.txt"
SAVE_FAIL_IMAGE_ARCHIVE="${SAVE_FAIL_TMP_ROOT}/candidate.tar.gz"

cat >"$SAVE_FAIL_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >>"${SAVE_FAIL_MOCK_ARGS:?}"

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  if [ "$2" != "${EXPECTED_IMAGE_TAG:?}" ]
  then
    printf 'unexpected image tag: %s\n' "$2" >&2
    exit 91
  fi

  printf '%s\n' 'PARTIAL_DOCKER_SAVE_PAYLOAD'
  exit 73
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$SAVE_FAIL_MOCK_DOCKER"

export SAVE_FAIL_MOCK_ARGS
export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"

if SAVE_FAIL_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$SAVE_FAIL_IMAGE_ARCHIVE" \
  DOCKER_BIN="$SAVE_FAIL_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  SAVE_FAIL_STATUS=0
else
  SAVE_FAIL_STATUS=$?
fi

printf '%s\n' "$SAVE_FAIL_OUTPUT"
printf 'SAVE_FAIL_STATUS=%s\n' "$SAVE_FAIL_STATUS"

[ "$SAVE_FAIL_STATUS" -ne 0 ] ||
  fail "failed docker save was accepted"

grep -Fqx \
  'ARCHIVE_CREATE_STATUS=73' \
  <<<"$SAVE_FAIL_OUTPUT" ||
  fail "docker save failure status was not preserved"

grep -Fqx \
  'ERROR: image archive creation failed with status 73' \
  <<<"$SAVE_FAIL_OUTPUT" ||
  fail "docker save failure reason was not reported"

[ ! -e "$SAVE_FAIL_IMAGE_ARCHIVE" ] ||
  fail "partial image archive survived failed docker save"

grep -Fqx \
  "save ${KNOWN_IMAGE_TAG}" \
  "$SAVE_FAIL_MOCK_ARGS" ||
  fail "failed docker save did not use immutable image tag"

rm -rf "$SAVE_FAIL_TMP_ROOT"

printf '%s\n' 'FAILED_DOCKER_SAVE_REJECTED=PASS'
printf '%s\n' 'FAILED_DOCKER_SAVE_STATUS_PRESERVED=PASS'
printf '%s\n' 'FAILED_DOCKER_SAVE_PARTIAL_ARCHIVE_REMOVED=PASS'

printf '\n%s\n' '=== Failed gzip validation cleanup ==='

GZIP_FAIL_TMP_ROOT="$(mktemp -d)"
GZIP_FAIL_MOCK_DOCKER="${GZIP_FAIL_TMP_ROOT}/docker"
GZIP_FAIL_MOCK_GZIP="${GZIP_FAIL_TMP_ROOT}/gzip"
GZIP_FAIL_GZIP_ARGS="${GZIP_FAIL_TMP_ROOT}/gzip-args.txt"
GZIP_FAIL_REAL_GZIP="$(command -v gzip)"
GZIP_FAIL_IMAGE_ARCHIVE="${GZIP_FAIL_TMP_ROOT}/candidate.tar.gz"

cat >"$GZIP_FAIL_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  if [ "$2" != "${EXPECTED_IMAGE_TAG:?}" ]
  then
    printf 'unexpected image tag: %s\n' "$2" >&2
    exit 91
  fi

  printf '%s\n' 'MOCK_DOCKER_ARCHIVE_PAYLOAD'
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

cat >"$GZIP_FAIL_MOCK_GZIP" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >>"${GZIP_FAIL_GZIP_ARGS:?}"

if [ "$#" -eq 2 ] &&
   [ "$1" = "-t" ]
then
  exit 74
fi

exec "${GZIP_FAIL_REAL_GZIP:?}" "$@"
MOCK

chmod +x \
  "$GZIP_FAIL_MOCK_DOCKER" \
  "$GZIP_FAIL_MOCK_GZIP"

export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"
export GZIP_FAIL_GZIP_ARGS
export GZIP_FAIL_REAL_GZIP

if GZIP_FAIL_OUTPUT="$(
  PATH="${GZIP_FAIL_TMP_ROOT}:$PATH" \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$GZIP_FAIL_IMAGE_ARCHIVE" \
  DOCKER_BIN="$GZIP_FAIL_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  GZIP_FAIL_STATUS=0
else
  GZIP_FAIL_STATUS=$?
fi

printf '%s\n' "$GZIP_FAIL_OUTPUT"
printf 'GZIP_FAIL_STATUS=%s\n' "$GZIP_FAIL_STATUS"

[ "$GZIP_FAIL_STATUS" -ne 0 ] ||
  fail "failed gzip validation was accepted"

grep -Fqx \
  'ARCHIVE_CREATE_STATUS=0' \
  <<<"$GZIP_FAIL_OUTPUT" ||
  fail "archive creation did not succeed before gzip validation failure"

grep -Fqx \
  'GZIP_STATUS=74' \
  <<<"$GZIP_FAIL_OUTPUT" ||
  fail "gzip validation failure status was not preserved"

grep -Fqx \
  'ERROR: image archive gzip validation failed with status 74' \
  <<<"$GZIP_FAIL_OUTPUT" ||
  fail "gzip validation failure reason was not reported"

[ ! -e "$GZIP_FAIL_IMAGE_ARCHIVE" ] ||
  fail "invalid gzip archive survived failed validation"

test -f "$GZIP_FAIL_GZIP_ARGS" ||
  fail "gzip validation invocations were not recorded"

grep -Fqx -- \
  '-1' \
  "$GZIP_FAIL_GZIP_ARGS" ||
  fail "failed-gzip regression did not create archive with gzip -1"

grep -Fqx -- \
  "-t ${GZIP_FAIL_IMAGE_ARCHIVE}" \
  "$GZIP_FAIL_GZIP_ARGS" ||
  fail "failed-gzip regression did not invoke gzip integrity validation"

rm -rf "$GZIP_FAIL_TMP_ROOT"

printf '%s\n' 'FAILED_GZIP_VALIDATION_REJECTED=PASS'
printf '%s\n' 'FAILED_GZIP_STATUS_PRESERVED=PASS'
printf '%s\n' 'FAILED_GZIP_ARCHIVE_REMOVED=PASS'

printf '\n%s\n' '=== Manifest extraction failure cleanup ==='

MANIFEST_FAIL_TMP_ROOT="$(mktemp -d)"
MANIFEST_FAIL_MOCK_DOCKER="${MANIFEST_FAIL_TMP_ROOT}/docker"
MANIFEST_FAIL_DOCKER_TAR="${MANIFEST_FAIL_TMP_ROOT}/docker-save.tar"
MANIFEST_FAIL_CONFIG_PATH_FILE="${MANIFEST_FAIL_TMP_ROOT}/config-path.txt"
MANIFEST_FAIL_IMAGE_ARCHIVE="${MANIFEST_FAIL_TMP_ROOT}/candidate.tar.gz"
MANIFEST_FAIL_REAL_TAR="$(command -v tar)"
MANIFEST_FAIL_MOCK_TAR="${MANIFEST_FAIL_TMP_ROOT}/tar"

write_mock_docker_archive \
  "$MANIFEST_FAIL_DOCKER_TAR" \
  "$KNOWN_IMAGE_TAG" \
  "$MANIFEST_FAIL_CONFIG_PATH_FILE"

cat >"$MANIFEST_FAIL_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  cat "${MANIFEST_FAIL_DOCKER_TAR:?}"
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

cat >"$MANIFEST_FAIL_MOCK_TAR" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 3 ] &&
   [ "$1" = "-xOzf" ] &&
   [ "$3" = "manifest.json" ]
then
  exit 75
fi

exec "${MANIFEST_FAIL_REAL_TAR:?}" "$@"
MOCK

chmod +x \
  "$MANIFEST_FAIL_MOCK_DOCKER" \
  "$MANIFEST_FAIL_MOCK_TAR"

export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export MANIFEST_FAIL_DOCKER_TAR
export MANIFEST_FAIL_REAL_TAR

if MANIFEST_FAIL_OUTPUT="$(
  PATH="${MANIFEST_FAIL_TMP_ROOT}:$PATH" \
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$MANIFEST_FAIL_IMAGE_ARCHIVE" \
  DOCKER_BIN="$MANIFEST_FAIL_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  MANIFEST_FAIL_STATUS=0
else
  MANIFEST_FAIL_STATUS=$?
fi

printf '%s\n' "$MANIFEST_FAIL_OUTPUT"
printf 'MANIFEST_FAIL_STATUS=%s\n' "$MANIFEST_FAIL_STATUS"

[ "$MANIFEST_FAIL_STATUS" -ne 0 ] ||
  fail "manifest extraction failure was accepted"

grep -Fqx \
  'MANIFEST_STATUS=75' \
  <<<"$MANIFEST_FAIL_OUTPUT" ||
  fail "manifest extraction failure status was not preserved"

grep -Fqx \
  'ERROR: image archive manifest extraction failed with status 75' \
  <<<"$MANIFEST_FAIL_OUTPUT" ||
  fail "manifest extraction failure reason was not reported"

[ ! -e "$MANIFEST_FAIL_IMAGE_ARCHIVE" ] ||
  fail "manifest extraction failure left rejected archive behind"

rm -rf "$MANIFEST_FAIL_TMP_ROOT"

printf '%s\n' 'FAILED_MANIFEST_EXTRACTION_REJECTED=PASS'
printf '%s\n' 'FAILED_MANIFEST_ARCHIVE_REMOVED=PASS'

printf '\n%s\n' '=== Missing manifest tag cleanup ==='

MISSING_TAG_TMP_ROOT="$(mktemp -d)"
MISSING_TAG_MOCK_DOCKER="${MISSING_TAG_TMP_ROOT}/docker"
MISSING_TAG_DOCKER_TAR="${MISSING_TAG_TMP_ROOT}/docker-save.tar"
MISSING_TAG_CONFIG_PATH_FILE="${MISSING_TAG_TMP_ROOT}/config-path.txt"
MISSING_TAG_IMAGE_ARCHIVE="${MISSING_TAG_TMP_ROOT}/candidate.tar.gz"
MISSING_TAG_WRONG_IMAGE_TAG="telectro/erpnext-runtime:prod-20991231-deadbee"

write_mock_docker_archive \
  "$MISSING_TAG_DOCKER_TAR" \
  "$MISSING_TAG_WRONG_IMAGE_TAG" \
  "$MISSING_TAG_CONFIG_PATH_FILE"

cat >"$MISSING_TAG_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  if [ "$2" != "${EXPECTED_IMAGE_TAG:?}" ]
  then
    printf 'unexpected image tag: %s\n' "$2" >&2
    exit 91
  fi

  cat "${MISSING_TAG_DOCKER_TAR:?}"
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$MISSING_TAG_MOCK_DOCKER"

export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"
export MISSING_TAG_DOCKER_TAR

if MISSING_TAG_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$MISSING_TAG_IMAGE_ARCHIVE" \
  DOCKER_BIN="$MISSING_TAG_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  MISSING_TAG_STATUS=0
else
  MISSING_TAG_STATUS=$?
fi

printf '%s\n' "$MISSING_TAG_OUTPUT"
printf 'MISSING_TAG_STATUS=%s\n' "$MISSING_TAG_STATUS"

[ "$MISSING_TAG_STATUS" -ne 0 ] ||
  fail "archive missing expected manifest tag was accepted"

grep -Fqx \
  'CONFIG_PATH_STATUS=1' \
  <<<"$MISSING_TAG_OUTPUT" ||
  fail "missing manifest tag failure status was not reported"

grep -Fqx \
  'ERROR: expected image tag was not resolved uniquely in archive manifest' \
  <<<"$MISSING_TAG_OUTPUT" ||
  fail "missing manifest tag rejection reason was not reported"

[ ! -e "$MISSING_TAG_IMAGE_ARCHIVE" ] ||
  fail "invalid manifest-tag archive survived failed validation"

rm -rf "$MISSING_TAG_TMP_ROOT"

printf '%s\n' 'MISSING_MANIFEST_TAG_REJECTED=PASS'
printf '%s\n' 'MISSING_MANIFEST_TAG_ARCHIVE_REMOVED=PASS'

printf '\n%s\n' '=== Ambiguous manifest tag cleanup ==='

AMBIGUOUS_TAG_TMP_ROOT="$(mktemp -d)"
AMBIGUOUS_TAG_MOCK_DOCKER="${AMBIGUOUS_TAG_TMP_ROOT}/docker"
AMBIGUOUS_TAG_DOCKER_TAR="${AMBIGUOUS_TAG_TMP_ROOT}/docker-save.tar"
AMBIGUOUS_TAG_IMAGE_ARCHIVE="${AMBIGUOUS_TAG_TMP_ROOT}/candidate.tar.gz"

python3 - \
  "$AMBIGUOUS_TAG_DOCKER_TAR" \
  "$KNOWN_IMAGE_TAG" <<'PYTHON'
import hashlib
import io
import json
import sys
import tarfile

archive_path = sys.argv[1]
image_tag = sys.argv[2]

config_blob = (
    b'{"architecture":"amd64","os":"linux",'
    b'"fixture":"phase6-ambiguous-manifest"}\n'
)

config_sha256 = hashlib.sha256(config_blob).hexdigest()
config_path = f"blobs/sha256/{config_sha256}"

manifest = [
    {
        "Config": config_path,
        "RepoTags": [image_tag],
        "Layers": [],
    },
    {
        "Config": config_path,
        "RepoTags": [image_tag],
        "Layers": [],
    },
]

manifest_blob = json.dumps(
    manifest,
    separators=(",", ":"),
).encode("utf-8")

with tarfile.open(archive_path, mode="w") as archive:
    manifest_info = tarfile.TarInfo("manifest.json")
    manifest_info.size = len(manifest_blob)
    archive.addfile(
        manifest_info,
        io.BytesIO(manifest_blob),
    )

    config_info = tarfile.TarInfo(config_path)
    config_info.size = len(config_blob)
    archive.addfile(
        config_info,
        io.BytesIO(config_blob),
    )
PYTHON

cat >"$AMBIGUOUS_TAG_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  if [ "$2" != "${EXPECTED_IMAGE_TAG:?}" ]
  then
    printf 'unexpected image tag: %s\n' "$2" >&2
    exit 91
  fi

  cat "${AMBIGUOUS_TAG_DOCKER_TAR:?}"
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$AMBIGUOUS_TAG_MOCK_DOCKER"

export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"
export AMBIGUOUS_TAG_DOCKER_TAR

if AMBIGUOUS_TAG_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$AMBIGUOUS_TAG_IMAGE_ARCHIVE" \
  DOCKER_BIN="$AMBIGUOUS_TAG_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  AMBIGUOUS_TAG_STATUS=0
else
  AMBIGUOUS_TAG_STATUS=$?
fi

printf '%s\n' "$AMBIGUOUS_TAG_OUTPUT"
printf 'AMBIGUOUS_TAG_STATUS=%s\n' "$AMBIGUOUS_TAG_STATUS"

[ "$AMBIGUOUS_TAG_STATUS" -ne 0 ] ||
  fail "archive with ambiguous manifest tag was accepted"

grep -F \
  'found 2' \
  <<<"$AMBIGUOUS_TAG_OUTPUT" \
  >/dev/null ||
  fail "ambiguous manifest tag count was not reported"

grep -Fqx \
  'CONFIG_PATH_STATUS=1' \
  <<<"$AMBIGUOUS_TAG_OUTPUT" ||
  fail "ambiguous manifest tag failure status was not reported"

grep -Fqx \
  'ERROR: expected image tag was not resolved uniquely in archive manifest' \
  <<<"$AMBIGUOUS_TAG_OUTPUT" ||
  fail "ambiguous manifest tag rejection reason was not reported"

[ ! -e "$AMBIGUOUS_TAG_IMAGE_ARCHIVE" ] ||
  fail "ambiguous manifest-tag archive survived failed validation"

rm -rf "$AMBIGUOUS_TAG_TMP_ROOT"

printf '%s\n' 'AMBIGUOUS_MANIFEST_TAG_REJECTED=PASS'
printf '%s\n' 'AMBIGUOUS_MANIFEST_TAG_ARCHIVE_REMOVED=PASS'

printf '\n%s\n' '=== Config digest mismatch cleanup ==='

DIGEST_MISMATCH_TMP_ROOT="$(mktemp -d)"
DIGEST_MISMATCH_MOCK_DOCKER="${DIGEST_MISMATCH_TMP_ROOT}/docker"
DIGEST_MISMATCH_DOCKER_TAR="${DIGEST_MISMATCH_TMP_ROOT}/docker-save.tar"
DIGEST_MISMATCH_IMAGE_ARCHIVE="${DIGEST_MISMATCH_TMP_ROOT}/candidate.tar.gz"

python3 - \
  "$DIGEST_MISMATCH_DOCKER_TAR" \
  "$KNOWN_IMAGE_TAG" <<'PYTHON'
import io
import json
import sys
import tarfile

archive_path = sys.argv[1]
image_tag = sys.argv[2]

actual_config_blob = (
    b'{"architecture":"amd64","os":"linux",'
    b'"fixture":"phase6-digest-mismatch"}\n'
)

declared_sha256 = "0" * 64
config_path = f"blobs/sha256/{declared_sha256}"

manifest = [
    {
        "Config": config_path,
        "RepoTags": [image_tag],
        "Layers": [],
    }
]

manifest_blob = json.dumps(
    manifest,
    separators=(",", ":"),
).encode("utf-8")

with tarfile.open(archive_path, mode="w") as archive:
    manifest_info = tarfile.TarInfo("manifest.json")
    manifest_info.size = len(manifest_blob)
    archive.addfile(
        manifest_info,
        io.BytesIO(manifest_blob),
    )

    config_info = tarfile.TarInfo(config_path)
    config_info.size = len(actual_config_blob)
    archive.addfile(
        config_info,
        io.BytesIO(actual_config_blob),
    )
PYTHON

cat >"$DIGEST_MISMATCH_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  if [ "$2" != "${EXPECTED_IMAGE_TAG:?}" ]
  then
    printf 'unexpected image tag: %s\n' "$2" >&2
    exit 91
  fi

  cat "${DIGEST_MISMATCH_DOCKER_TAR:?}"
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$DIGEST_MISMATCH_MOCK_DOCKER"

export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"
export DIGEST_MISMATCH_DOCKER_TAR

if DIGEST_MISMATCH_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$DIGEST_MISMATCH_IMAGE_ARCHIVE" \
  DOCKER_BIN="$DIGEST_MISMATCH_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  DIGEST_MISMATCH_STATUS=0
else
  DIGEST_MISMATCH_STATUS=$?
fi

printf '%s\n' "$DIGEST_MISMATCH_OUTPUT"
printf 'DIGEST_MISMATCH_STATUS=%s\n' "$DIGEST_MISMATCH_STATUS"

[ "$DIGEST_MISMATCH_STATUS" -ne 0 ] ||
  fail "config digest mismatch was accepted"

grep -Fqx \
  'DECLARED_CONFIG_DIGEST=sha256:0000000000000000000000000000000000000000000000000000000000000000' \
  <<<"$DIGEST_MISMATCH_OUTPUT" ||
  fail "mismatched declared config digest was not reported"

grep -Eq \
  '^ACTUAL_CONFIG_SHA256=[0-9a-f]{64}$' \
  <<<"$DIGEST_MISMATCH_OUTPUT" ||
  fail "actual mismatched config SHA-256 was not reported"

grep -Fqx \
  'ERROR: config blob SHA-256 does not match declared config digest' \
  <<<"$DIGEST_MISMATCH_OUTPUT" ||
  fail "config digest mismatch rejection reason was not reported"

[ ! -e "$DIGEST_MISMATCH_IMAGE_ARCHIVE" ] ||
  fail "config-digest mismatch archive survived failed validation"

rm -rf "$DIGEST_MISMATCH_TMP_ROOT"

printf '%s\n' 'CONFIG_DIGEST_MISMATCH_REJECTED=PASS'
printf '%s\n' 'CONFIG_DIGEST_MISMATCH_ARCHIVE_REMOVED=PASS'

printf '\n%s\n' '=== Legacy JSON config path layout ==='

LEGACY_CONFIG_TMP_ROOT="$(mktemp -d)"
LEGACY_CONFIG_MOCK_DOCKER="${LEGACY_CONFIG_TMP_ROOT}/docker"
LEGACY_CONFIG_DOCKER_TAR="${LEGACY_CONFIG_TMP_ROOT}/docker-save.tar"
LEGACY_CONFIG_IMAGE_ARCHIVE="${LEGACY_CONFIG_TMP_ROOT}/candidate.tar.gz"
LEGACY_CONFIG_DIGEST_FILE="${LEGACY_CONFIG_TMP_ROOT}/digest.txt"

python3 - \
  "$LEGACY_CONFIG_DOCKER_TAR" \
  "$KNOWN_IMAGE_TAG" \
  "$LEGACY_CONFIG_DIGEST_FILE" <<'PYTHON'
import hashlib
import io
import json
import sys
import tarfile

archive_path = sys.argv[1]
image_tag = sys.argv[2]
digest_file = sys.argv[3]

config_blob = (
    b'{"architecture":"amd64","os":"linux",'
    b'"fixture":"phase6-legacy-json-config"}\n'
)

config_sha256 = hashlib.sha256(config_blob).hexdigest()
config_path = f"{config_sha256}.json"

manifest = [
    {
        "Config": config_path,
        "RepoTags": [image_tag],
        "Layers": [],
    }
]

manifest_blob = json.dumps(
    manifest,
    separators=(",", ":"),
).encode("utf-8")

with tarfile.open(archive_path, mode="w") as archive:
    manifest_info = tarfile.TarInfo("manifest.json")
    manifest_info.size = len(manifest_blob)
    archive.addfile(
        manifest_info,
        io.BytesIO(manifest_blob),
    )

    config_info = tarfile.TarInfo(config_path)
    config_info.size = len(config_blob)
    archive.addfile(
        config_info,
        io.BytesIO(config_blob),
    )

with open(digest_file, "w", encoding="utf-8") as handle:
    handle.write(config_sha256 + "\n")
PYTHON

LEGACY_CONFIG_EXPECTED_SHA256="$(
  cat "$LEGACY_CONFIG_DIGEST_FILE"
)"

LEGACY_CONFIG_EXPECTED_PATH="${LEGACY_CONFIG_EXPECTED_SHA256}.json"
LEGACY_CONFIG_EXPECTED_DIGEST="sha256:${LEGACY_CONFIG_EXPECTED_SHA256}"

cat >"$LEGACY_CONFIG_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  if [ "$2" != "${EXPECTED_IMAGE_TAG:?}" ]
  then
    printf 'unexpected image tag: %s\n' "$2" >&2
    exit 91
  fi

  cat "${LEGACY_CONFIG_DOCKER_TAR:?}"
  exit 0
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$LEGACY_CONFIG_MOCK_DOCKER"

export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export EXPECTED_IMAGE_TAG="$KNOWN_IMAGE_TAG"
export LEGACY_CONFIG_DOCKER_TAR

if LEGACY_CONFIG_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$LEGACY_CONFIG_IMAGE_ARCHIVE" \
  DOCKER_BIN="$LEGACY_CONFIG_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  LEGACY_CONFIG_STATUS=0
else
  LEGACY_CONFIG_STATUS=$?
fi

printf '%s\n' "$LEGACY_CONFIG_OUTPUT"
printf 'LEGACY_CONFIG_STATUS=%s\n' "$LEGACY_CONFIG_STATUS"

[ "$LEGACY_CONFIG_STATUS" -eq 0 ] ||
  fail "legacy .json config path layout was rejected"

grep -Fqx \
  "CONFIG_PATH=${LEGACY_CONFIG_EXPECTED_PATH}" \
  <<<"$LEGACY_CONFIG_OUTPUT" ||
  fail "legacy .json config path was not resolved"

grep -Fqx \
  "DECLARED_CONFIG_DIGEST=${LEGACY_CONFIG_EXPECTED_DIGEST}" \
  <<<"$LEGACY_CONFIG_OUTPUT" ||
  fail "legacy .json declared config digest was not derived"

grep -Fqx \
  "IMAGE_CONFIG_DIGEST=${LEGACY_CONFIG_EXPECTED_DIGEST}" \
  <<<"$LEGACY_CONFIG_OUTPUT" ||
  fail "legacy .json image config digest was not recorded"

grep -Fqx \
  "ACTUAL_CONFIG_SHA256=${LEGACY_CONFIG_EXPECTED_SHA256}" \
  <<<"$LEGACY_CONFIG_OUTPUT" ||
  fail "legacy .json actual config SHA-256 was not reported"

grep -Fqx \
  'IMAGE_ARCHIVE_CONFIG_DIGEST_OK=YES' \
  <<<"$LEGACY_CONFIG_OUTPUT" ||
  fail "legacy .json config digest validation marker was not reported"

rm -f "$LEGACY_CONFIG_IMAGE_ARCHIVE"
rm -rf "$LEGACY_CONFIG_TMP_ROOT"

printf '%s\n' 'LEGACY_JSON_CONFIG_LAYOUT_SUPPORTED=PASS'

printf '\n%s\n' '=== Existing sidecar destination rejection ==='

EXISTING_SIDECAR_TMP_ROOT="$(mktemp -d)"
EXISTING_SIDECAR_MOCK_DOCKER="${EXISTING_SIDECAR_TMP_ROOT}/docker"
EXISTING_SIDECAR_IMAGE_ARCHIVE="${EXISTING_SIDECAR_TMP_ROOT}/candidate.tar.gz"
EXISTING_SIDECAR_SHA256_FILE="${EXISTING_SIDECAR_IMAGE_ARCHIVE}.sha256"
EXISTING_SIDECAR_DOCKER_CALLS="${EXISTING_SIDECAR_TMP_ROOT}/docker-calls.txt"

printf '%s\n' \
  'PRESERVE_EXISTING_SIDECAR' \
  >"$EXISTING_SIDECAR_SHA256_FILE"

cat >"$EXISTING_SIDECAR_MOCK_DOCKER" <<'MOCK'
#!/usr/bin/env bash

set -euo pipefail

printf '%s\n' "$*" >>"${EXISTING_SIDECAR_DOCKER_CALLS:?}"

if [ "$#" -eq 5 ] &&
   [ "$1" = "image" ] &&
   [ "$2" = "inspect" ] &&
   [ "$3" = "--format" ]
then
  printf '%s\n' "${EXPECTED_IMAGE_ID:?}"
  exit 0
fi

if [ "$#" -eq 2 ] &&
   [ "$1" = "save" ]
then
  printf '%s\n' 'docker save must not run' >&2
  exit 93
fi

printf 'unexpected docker invocation:' >&2
printf ' %q' "$@" >&2
printf '\n' >&2
exit 92
MOCK

chmod +x "$EXISTING_SIDECAR_MOCK_DOCKER"

export EXPECTED_IMAGE_ID="$KNOWN_IMAGE_ID"
export EXISTING_SIDECAR_DOCKER_CALLS

if EXISTING_SIDECAR_OUTPUT="$(
  RELEASE_ID="$KNOWN_RELEASE_ID" \
  IMAGE_ARCHIVE="$EXISTING_SIDECAR_IMAGE_ARCHIVE" \
  DOCKER_BIN="$EXISTING_SIDECAR_MOCK_DOCKER" \
    "$HELPER" \
    2>&1
)"
then
  EXISTING_SIDECAR_STATUS=0
else
  EXISTING_SIDECAR_STATUS=$?
fi

printf '%s\n' "$EXISTING_SIDECAR_OUTPUT"
printf 'EXISTING_SIDECAR_STATUS=%s\n' "$EXISTING_SIDECAR_STATUS"

[ "$EXISTING_SIDECAR_STATUS" -ne 0 ] ||
  fail "existing archive SHA-256 sidecar was overwritten"

grep -Fqx \
  'PRESERVE_EXISTING_SIDECAR' \
  "$EXISTING_SIDECAR_SHA256_FILE" ||
  fail "existing archive SHA-256 sidecar content changed"

if grep -F \
  'save ' \
  "$EXISTING_SIDECAR_DOCKER_CALLS" \
  >/dev/null
then
  fail "existing sidecar destination did not stop docker save"
fi

rm -rf "$EXISTING_SIDECAR_TMP_ROOT"

printf '%s\n' 'EXISTING_IMAGE_ARCHIVE_SIDECAR_REJECTED=PASS'
printf '%s\n' 'EXISTING_SIDECAR_STOPPED_DOCKER_SAVE=PASS'

printf '%s\n' 'RELEASE_IMAGE_ARCHIVE_IDENTITY_REGRESSION=PASS'
