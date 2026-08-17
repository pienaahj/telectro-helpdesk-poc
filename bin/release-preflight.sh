#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

REPO_DIR="${REPO_DIR:-$DEFAULT_REPO_DIR}"
RELEASE_DATE="${RELEASE_DATE:-}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ -z "$RELEASE_DATE" ]]; then
  fail "RELEASE_DATE is required"
fi

if [[ ${#RELEASE_DATE} -ne 8 || "$RELEASE_DATE" == *[!0-9]* ]]; then
  fail "RELEASE_DATE must use YYYYMMDD format; observed: $RELEASE_DATE"
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

SOURCE_BRANCH="$(
  git \
    -C "$REPO_DIR" \
    branch \
    --show-current
)"

if [[ -z "$SOURCE_BRANCH" ]]; then
  fail "detached HEAD is not a valid release source"
fi

if [[ "$SOURCE_BRANCH" != "main" ]]; then
  fail "release source branch must be main; observed: $SOURCE_BRANCH"
fi

WORKTREE_STATUS="$(
  git \
    -C "$REPO_DIR" \
    status \
    --short
)"

if [[ -n "$WORKTREE_STATUS" ]]; then
  fail "working tree must be clean for release preflight"
fi

if ! git \
  -C "$REPO_DIR" \
  fetch \
  --quiet \
  origin
then
  fail "failed to fetch origin"
fi

if ! ORIGIN_MAIN_SHA="$(
  git \
    -C "$REPO_DIR" \
    rev-parse \
    --verify \
    origin/main \
    2>/dev/null
)"; then
  fail "origin/main is unavailable after fetch"
fi

DIVERGENCE="$(
  git \
    -C "$REPO_DIR" \
    rev-list \
    --left-right \
    --count \
    HEAD...origin/main
)"

read -r AHEAD BEHIND <<<"$DIVERGENCE"

if [[ "$AHEAD" -ne 0 || "$BEHIND" -ne 0 ]]; then
  fail \
    "local main must exactly match origin/main; ahead=$AHEAD behind=$BEHIND"
fi

FULL_COMMIT_SHA="$(
  git \
    -C "$REPO_DIR" \
    rev-parse \
    HEAD
)"

SHORT_COMMIT_SHA="${FULL_COMMIT_SHA:0:7}"
RELEASE_ID="${RELEASE_DATE}-${SHORT_COMMIT_SHA}"
SOURCE_ARTIFACT="/tmp/telectro-app-${RELEASE_ID}.tar.gz"

printf '%s\n' \
  "RELEASE_DATE=$RELEASE_DATE" \
  "SOURCE_BRANCH=$SOURCE_BRANCH" \
  "FULL_COMMIT_SHA=$FULL_COMMIT_SHA" \
  "SHORT_COMMIT_SHA=$SHORT_COMMIT_SHA" \
  "ORIGIN_MAIN_SHA=$ORIGIN_MAIN_SHA" \
  "AHEAD=$AHEAD" \
  "BEHIND=$BEHIND" \
  "RELEASE_ID=$RELEASE_ID" \
  "SOURCE_ARTIFACT=$SOURCE_ARTIFACT"

printf '\n%s\n' \
  'RELEASE_IDENTITY_DEFINED' \
  'LOCAL_GIT_RELEASE_PREFLIGHT_OK'
