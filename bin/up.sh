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

echo "🐳 starting local stack with:"
printf ' - %s\n' "${FILES[@]}"

compose up -d

# Ensure helpdesk/telephony are importable in the bench venv.
# This fixes the "ModuleNotFoundError: No module named 'telephony'" after container recreate.
echo "🔧 ensuring bench venv sees installed apps (helpdesk/telephony) ..."
compose exec -T -u frappe backend bash -lc '
set -euo pipefail
cd /home/frappe/frappe-bench

# Only do this if the app folders exist
fix_one () {
  local app="$1"
  if [[ -d "apps/${app}" ]]; then
    echo " - apps/${app} present; ensuring editable install..."
    ./env/bin/python -c "import ${app}" >/dev/null 2>&1 \
      && echo "   ✅ ${app} already importable" \
      || (./env/bin/python -m pip install -e "apps/${app}" && echo "   ✅ installed ${app}")
  else
    echo " - apps/${app} missing; skip"
  fi
}

fix_one helpdesk
fix_one telephony

# quick visibility check (non-fatal)
./env/bin/python - << "PY" || true
import sys
apps_paths = [p for p in sys.path if "frappe-bench/apps" in p]
print("apps paths on sys.path:", apps_paths)
PY
'

# optional: wait for backend healthy (your backend has a healthcheck)
echo "⏳ waiting for backend to be healthy..."
for i in {1..60}; do
  cid="$(compose ps -q backend 2>/dev/null || true)"
  status="$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || true)"
  [[ "$status" == "healthy" ]] && echo "✅ backend healthy" && exit 0
  sleep 2
done

echo "⚠️ backend did not become healthy in time (continuing anyway)"