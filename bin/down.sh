#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

compose() { docker compose "$@"; }

echo "🐳 stopping local stack with standard Docker Compose:"
echo " - compose.yaml"
echo " - compose.override.yaml, if present"

compose down