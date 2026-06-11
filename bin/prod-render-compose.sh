#!/usr/bin/env bash
set -euo pipefail

# Render and inspect production Docker Compose configuration.
#
# This script is intentionally read-only.
# It does not start, stop, restart, create, or delete containers.
#
# It is safe to run before deployment to prove that Compose interpolation,
# env file loading, and production file merging behave as expected.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_FILE="${OUTPUT_FILE:-/tmp/telectro-production-compose.rendered.yaml}"

die() {
  printf "\nERROR: %s\n\n" "$*" >&2
  exit 1
}

log() {
  printf "\n==> %s\n" "$*" >&2
}

cd "$ROOT_DIR"

[[ -x ./bin/prod-compose.sh ]] || die "Missing executable ./bin/prod-compose.sh"

log "Rendering production Compose config to $OUTPUT_FILE"
./bin/prod-compose.sh config > "$OUTPUT_FILE"

log "Rendered Compose file created"
ls -lh "$OUTPUT_FILE"

log "Checking for production edge red flags"
if grep -nE 'traefik|80:80|443:443|certs' "$OUTPUT_FILE"; then
  cat >&2 <<'EOF'

WARN:
Potential production edge red flag found above.

Expected production shape:
- no application-owned Traefik public edge;
- no public 80:80 publish;
- no public 443:443 publish;
- no application-side public certificate mount.

Review before continuing.
EOF
else
  log "No obvious app-owned public edge red flags found"
fi

log "Published ports found in rendered Compose"
grep -n -C 6 'published:' "$OUTPUT_FILE" || true

log "Done"