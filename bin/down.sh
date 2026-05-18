#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

FILES=(-f compose.yaml)

# Local-only Compose settings:
# - localhost port exposure
# - local development services
# - anything that should not be part of production
[[ -f compose.local.yaml ]] && FILES+=(-f compose.local.yaml)

# Local override kept for machine-specific overrides, such as pinned local volume names.
[[ -f compose.override.yaml ]] && FILES+=(-f compose.override.yaml)

compose() { docker compose "${FILES[@]}" "$@"; }

echo "🐳 stopping local stack with:"
printf ' - %s\n' "${FILES[@]}"

compose down "$@"

