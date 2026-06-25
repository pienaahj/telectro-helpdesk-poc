#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROD_ENV_FILE="${PROD_ENV_FILE:-.env.production}"

if [[ ! -f "$PROD_ENV_FILE" ]]; then
  echo "Missing production env file: $PROD_ENV_FILE" >&2
  echo "Set PROD_ENV_FILE=/path/to/.env.production" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$PROD_ENV_FILE"
set +a

: "${ERPNEXT_IMAGE:?Set ERPNEXT_IMAGE in $PROD_ENV_FILE}"
: "${PRODUCTION_DATA_ROOT:?Set PRODUCTION_DATA_ROOT in $PROD_ENV_FILE}"

ASSETS_DIR="${PRODUCTION_DATA_ROOT%/}/assets"

PLATFORM_ARGS=()
if [[ -n "${DOCKER_PLATFORM:-}" ]]; then
  PLATFORM_ARGS=(--platform "$DOCKER_PLATFORM")
fi

echo "==> Seeding production assets"
echo "==> Runtime image: $ERPNEXT_IMAGE"
echo "==> Target assets directory: $ASSETS_DIR"

mkdir -p "$ASSETS_DIR"

docker run --rm "${PLATFORM_ARGS[@]}" "$ERPNEXT_IMAGE" bash -lc '
  set -euo pipefail

  ASSETS_DIR="/home/frappe/frappe-bench/sites/assets"

  test -f "$ASSETS_DIR/assets.json"
  test -f "$ASSETS_DIR/assets-rtl.json"

  # Important:
  # sites/assets contains app asset symlinks. The production host bind mount
  # needs the actual files, not symlinks back into the image filesystem.
  tar -h -C "$ASSETS_DIR" -cf - .
' | tar -xf - -C "$ASSETS_DIR"

echo "==> Seeded assets proof"
test -f "$ASSETS_DIR/assets.json"
test -f "$ASSETS_DIR/assets-rtl.json"

ASSETS_DIR="$ASSETS_DIR" python - <<'PY'
import json
import os
from pathlib import Path

assets_root = Path(os.environ["ASSETS_DIR"])
manifest = json.loads((assets_root / "assets.json").read_text())

missing = []
checked = 0

for logical_name, asset_url in manifest.items():
    if not isinstance(asset_url, str):
        continue
    if not asset_url.startswith("/assets/"):
        continue

    checked += 1
    target = assets_root / asset_url.removeprefix("/assets/")
    if not target.exists():
        missing.append((logical_name, str(target)))

print(f"checked_manifest_targets={checked}")

if missing:
    print("--- missing manifest targets ---")
    for logical_name, target in missing[:80]:
        print(f"MISSING {logical_name} -> {target}")
    raise SystemExit(1)

print("ASSET_MANIFEST_TARGETS_OK")
PY

find "$ASSETS_DIR" -maxdepth 3 -type f | sort | sed -n "1,120p"

echo "==> Done"
