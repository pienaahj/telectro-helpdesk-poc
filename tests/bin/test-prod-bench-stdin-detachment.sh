#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

TEST_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TEST_DIR"
}

trap cleanup EXIT

MOCK_COMPOSE="$TEST_DIR/mock-compose"
MOCK_ENV="$TEST_DIR/.env.production"

printf '' > "$MOCK_ENV"

cat > "$MOCK_COMPOSE" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "version" ]]; then
  exit 0
fi

stdin_payload="$(cat)"

if [[ -n "$stdin_payload" ]]; then
  printf 'MOCK_COMPOSE_STDIN_EOF=NO\n'
  printf 'UNEXPECTED_STDIN=%q\n' "$stdin_payload"
  exit 99
fi

printf 'MOCK_COMPOSE_STDIN_EOF=YES\n'
MOCK

chmod +x "$MOCK_COMPOSE"

export TEST_MOCK_COMPOSE="$MOCK_COMPOSE"
export TEST_MOCK_ENV="$MOCK_ENV"

cd "$ROOT_DIR"

set +e

TEST_OUTPUT="$(
  bash <<'PARENT'
set -euo pipefail

COMPOSE="$TEST_MOCK_COMPOSE" \
PROD_ENV_FILE="$TEST_MOCK_ENV" \
  ./bin/prod-bench.sh --site regression.test version

printf 'WRAPPER_STATUS=0\n'
printf 'POST_WRAPPER_MARKER\n'
PARENT
)"

TEST_STATUS=$?

set -e

printf '%s\n' "$TEST_OUTPUT"
printf 'TEST_STATUS=%s\n' "$TEST_STATUS"

grep -qx 'MOCK_COMPOSE_STDIN_EOF=YES' <<<"$TEST_OUTPUT"
grep -qx 'WRAPPER_STATUS=0' <<<"$TEST_OUTPUT"
grep -qx 'POST_WRAPPER_MARKER' <<<"$TEST_OUTPUT"
[[ "$TEST_STATUS" -eq 0 ]]

printf '%s\n' \
  'PROD_BENCH_STDIN_DETACHMENT_REGRESSION=PASS'
