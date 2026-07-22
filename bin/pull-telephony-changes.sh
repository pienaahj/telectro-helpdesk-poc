#!/usr/bin/env bash
set -euo pipefail

trap 'echo "ERROR: pull-telephony-changes failed on line ${LINENO}" >&2' ERR

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"

OVERLAY_REL="apps/telephony/telephony"
OVERLAY_ROOT="${REPO_ROOT}/${OVERLAY_REL}"
BACKEND_SERVICE="${BACKEND_SERVICE:-backend}"
CONTAINER_ROOT="/home/frappe/frappe-bench/apps/telephony/telephony"

DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  bin/pull-telephony-changes.sh
  bin/pull-telephony-changes.sh --dry-run

The script synchronizes Git-tracked Telephony overlay files from the
development backend container to the same repository paths.

Fixture files are deliberately excluded. Use the controlled fixture-export
workflow for fixture changes.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac

  shift
done

if [ ! -d "${OVERLAY_ROOT}" ]; then
  echo "ERROR: Telephony overlay directory does not exist:" >&2
  echo "  ${OVERLAY_ROOT}" >&2
  exit 1
fi

if ! docker compose ps --status running --services |
  grep -qx "${BACKEND_SERVICE}"
then
  echo "ERROR: backend service is not running: ${BACKEND_SERVICE}" >&2
  exit 1
fi

SNAPSHOT="$(mktemp -d "${TMPDIR:-/tmp}/telephony-pull.XXXXXX")"
TRACKED_MANIFEST="${SNAPSHOT}/tracked.txt"
MISSING_MANIFEST="${SNAPSHOT}/missing.txt"

cleanup() {
  rm -rf "${SNAPSHOT}"
}

trap cleanup EXIT

echo "=== Telephony exact-path pull ==="
echo "Repository: ${REPO_ROOT}"
echo "Branch:     $(git branch --show-current)"
echo "Container:  ${BACKEND_SERVICE}:${CONTAINER_ROOT}"

if [ "${DRY_RUN}" -eq 1 ]; then
  echo "Mode:       dry run"
else
  echo "Mode:       write"
fi

echo
echo "=== Taking container snapshot ==="

mkdir -p "${SNAPSHOT}/container"

docker compose cp \
  "${BACKEND_SERVICE}:${CONTAINER_ROOT}/." \
  "${SNAPSHOT}/container/"

echo
echo "=== Building tracked overlay manifest ==="

git ls-files "${OVERLAY_REL}" |
  while IFS= read -r repository_path; do
    [ -n "${repository_path}" ] || continue

    printf '%s\n' \
      "${repository_path#"${OVERLAY_REL}/"}"
  done |
  sort > "${TRACKED_MANIFEST}"

TRACKED_COUNT="$(
  wc -l < "${TRACKED_MANIFEST}" |
    tr -d ' '
)"

FIXTURE_COUNT="$(
  awk '
    /^fixtures\// {
      count += 1
    }
    END {
      print count + 0
    }
  ' "${TRACKED_MANIFEST}"
)"

SOURCE_COUNT="$((TRACKED_COUNT - FIXTURE_COUNT))"

printf 'Tracked overlay files: %s\n' "${TRACKED_COUNT}"
printf 'Tracked source files:  %s\n' "${SOURCE_COUNT}"
printf 'Skipped fixture files: %s\n' "${FIXTURE_COUNT}"

echo
echo "=== Preflight: tracked paths must exist in container ==="

: > "${MISSING_MANIFEST}"

while IFS= read -r relative_path; do
  [ -n "${relative_path}" ] || continue

  case "${relative_path}" in
    fixtures/*)
      continue
      ;;
  esac

  if [ ! -f "${SNAPSHOT}/container/${relative_path}" ]; then
    printf '%s\n' "${relative_path}" >> "${MISSING_MANIFEST}"
  fi
done < "${TRACKED_MANIFEST}"

if [ -s "${MISSING_MANIFEST}" ]; then
  echo "ERROR: tracked source paths are missing from the container:" >&2

  while IFS= read -r relative_path; do
    printf '  %s\n' "${relative_path}" >&2
  done < "${MISSING_MANIFEST}"

  echo >&2
  echo "No host files were changed." >&2
  exit 1
fi

echo "Tracked-path preflight: PASS"

echo
echo "=== Static local dependency audit ==="


python3 - \
  "${REPO_ROOT}" \
  "${OVERLAY_REL}" \
  "${SNAPSHOT}/container" <<'PY'
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path


repo = Path(sys.argv[1]).resolve()
overlay_rel = Path(sys.argv[2])
snapshot = Path(sys.argv[3]).resolve()


def module_name(relative_name: str) -> str | None:
    path = Path(relative_name)

    if path.suffix != ".py":
        return None

    if path.name == "__init__.py":
        parts = path.parent.parts
    else:
        parts = path.with_suffix("").parts

    return ".".join(("telephony", *parts))


def modules_below(root: Path) -> set[str]:
    result = {"telephony"}

    for source_path in root.rglob("*.py"):
        if "__pycache__" in source_path.parts:
            continue

        relative_name = source_path.relative_to(root).as_posix()
        module = module_name(relative_name)

        if module:
            result.add(module)

    return result


def is_custom_module(module: str) -> bool:
    if not module.startswith("telephony."):
        return False

    relative = module.removeprefix("telephony.")
    first = relative.split(".", 1)[0]

    if first.startswith(
        (
            "telectro_",
            "customer_",
            "partner_",
            "debug_",
        )
    ):
        return True

    if first in {
        "assign_guard",
        "docshare_guard",
        "ops_kpis",
        "partner_kpis",
        "service_coverage",
    }:
        return True

    if relative.startswith("monkey_patches."):
        return True

    if relative.startswith("setup.workspace_visibility"):
        return True

    if relative.startswith("api.workspace"):
        return True

    if ".telectro_" in relative:
        return True

    return False


def resolve_module(
    dotted_path: str,
    available_modules: set[str],
) -> str | None:
    parts = dotted_path.split(".")

    for stop in range(len(parts), 0, -1):
        candidate = ".".join(parts[:stop])

        if candidate in available_modules:
            return candidate

    return None


tracked_output = subprocess.check_output(
    ["git", "ls-files", overlay_rel.as_posix()],
    cwd=repo,
    text=True,
)

tracked_files = {
    Path(line).relative_to(overlay_rel).as_posix()
    for line in tracked_output.splitlines()
    if line.strip()
}

tracked_source = {
    relative_name
    for relative_name in tracked_files
    if not relative_name.startswith("fixtures/")
}

tracked_modules = {"telephony"}

for relative_name in tracked_source:
    module = module_name(relative_name)

    if module:
        tracked_modules.add(module)

container_modules = modules_below(snapshot)

runtime_missing: set[tuple[str, str]] = set()
custom_untracked: set[tuple[str, str]] = set()
upstream_dependencies: set[str] = set()
syntax_errors: list[tuple[str, str]] = []


def inspect_dependency(
    source_file: str,
    dotted_path: str,
) -> None:
    if not dotted_path.startswith("telephony."):
        return

    resolved = resolve_module(
        dotted_path,
        container_modules,
    )

    if resolved is None:
        runtime_missing.add(
            (
                source_file,
                dotted_path,
            )
        )
        return

    if resolved in tracked_modules:
        return

    if is_custom_module(resolved):
        custom_untracked.add(
            (
                source_file,
                resolved,
            )
        )
        return

    upstream_dependencies.add(resolved)


for relative_name in sorted(tracked_source):
    relative_path = Path(relative_name)

    if relative_path.suffix != ".py":
        continue

    source_path = snapshot / relative_name

    try:
        source = source_path.read_text(
            encoding="utf-8"
        )
        tree = ast.parse(
            source,
            filename=relative_name,
        )
    except (SyntaxError, UnicodeDecodeError) as exc:
        syntax_errors.append(
            (
                relative_name,
                str(exc),
            )
        )
        continue

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                inspect_dependency(
                    relative_name,
                    alias.name,
                )

        elif isinstance(node, ast.ImportFrom):
            imported = node.module or ""

            inspect_dependency(
                relative_name,
                imported,
            )


hooks_path = snapshot / "hooks.py"

if hooks_path.exists():
    try:
        hooks_tree = ast.parse(
            hooks_path.read_text(
                encoding="utf-8"
            ),
            filename="hooks.py",
        )
    except (SyntaxError, UnicodeDecodeError) as exc:
        syntax_errors.append(
            (
                "hooks.py",
                str(exc),
            )
        )
    else:
        dotted_path_pattern = re.compile(
            r"^telephony"
            r"(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"
        )

        for node in ast.walk(hooks_tree):
            if not (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
            ):
                continue

            dotted_path = node.value.strip()

            if dotted_path_pattern.match(
                dotted_path
            ):
                inspect_dependency(
                    "hooks.py",
                    dotted_path,
                )


if syntax_errors:
    print(
        "Syntax errors detected:",
        file=sys.stderr,
    )

    for relative_name, error in syntax_errors:
        print(
            f"  {relative_name}: {error}",
            file=sys.stderr,
        )

    raise SystemExit(1)


if runtime_missing:
    print(
        "Telephony dependencies missing from "
        "the container runtime:",
        file=sys.stderr,
    )

    for source_file, imported in sorted(
        runtime_missing
    ):
        print(
            f"  {source_file}: {imported}",
            file=sys.stderr,
        )

    raise SystemExit(1)


if custom_untracked:
    print(
        "Custom Telephony dependencies exist "
        "in the container but are not tracked:",
        file=sys.stderr,
    )

    for source_file, imported in sorted(
        custom_untracked
    ):
        print(
            f"  {source_file}: {imported}",
            file=sys.stderr,
        )

    raise SystemExit(1)


print(
    {
        "tracked_python_modules": len(
            tracked_modules
        ),
        "container_python_modules": len(
            container_modules
        ),
        "upstream_dependencies_allowed": len(
            upstream_dependencies
        ),
        "runtime_missing": 0,
        "custom_untracked": 0,
        "syntax_errors": 0,
    }
)

print("Static dependency audit: PASS")
PY

echo
echo "=== Synchronizing tracked source files ==="

CHANGED_COUNT=0
UNCHANGED_COUNT=0

while IFS= read -r relative_path; do
  [ -n "${relative_path}" ] || continue

  case "${relative_path}" in
    fixtures/*)
      continue
      ;;
  esac

  source_path="${SNAPSHOT}/container/${relative_path}"
  destination_path="${OVERLAY_ROOT}/${relative_path}"

  if cmp -s "${source_path}" "${destination_path}"; then
    UNCHANGED_COUNT="$((UNCHANGED_COUNT + 1))"
    continue
  fi

  printf 'UPDATE  %s\n' "${relative_path}"
  CHANGED_COUNT="$((CHANGED_COUNT + 1))"

  if [ "${DRY_RUN}" -eq 1 ]; then
    continue
  fi

  mkdir -p "$(dirname "${destination_path}")"

  if [ -f "${destination_path}" ]; then
    cat "${source_path}" > "${destination_path}"
  else
    cp "${source_path}" "${destination_path}"

    INDEX_MODE="$(
      git ls-files -s -- "${OVERLAY_REL}/${relative_path}" |
        awk '{print $1}'
    )"

    if [ "${INDEX_MODE}" = "100755" ]; then
      chmod +x "${destination_path}"
    else
      chmod -x "${destination_path}"
    fi
  fi
done < "${TRACKED_MANIFEST}"

printf 'Changed source files:   %s\n' "${CHANGED_COUNT}"
printf 'Unchanged source files: %s\n' "${UNCHANGED_COUNT}"

echo
echo "=== Container-only custom-looking candidates ==="

python3 - \
  "${REPO_ROOT}" \
  "${OVERLAY_REL}" \
  "${SNAPSHOT}/container" <<'PY'
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


repo = Path(sys.argv[1]).resolve()
overlay_rel = Path(sys.argv[2])
snapshot = Path(sys.argv[3]).resolve()

tracked_output = subprocess.check_output(
    ["git", "ls-files", overlay_rel.as_posix()],
    cwd=repo,
    text=True,
)

tracked = {
    Path(line).relative_to(overlay_rel).as_posix()
    for line in tracked_output.splitlines()
    if line.strip()
}

patterns = [
    "telectro_*.py",
    "customer_*.py",
    "partner_*.py",
    "debug_*.py",
    "assign_guard.py",
    "docshare_guard.py",
    "ops_kpis.py",
    "partner_kpis.py",
    "service_coverage.py",
    "monkey_patches/*.py",
    "ftelephony/doctype/telectro_*/*",
    "ftelephony/report/telectro_*/*",
    "ftelephony/page/telectro_*/*",
    "public/js/telectro_*",
]

candidates: set[str] = set()

for pattern in patterns:
    for source_path in snapshot.glob(pattern):
        if not source_path.is_file():
            continue

        relative_name = source_path.relative_to(snapshot).as_posix()

        if (
            "__pycache__" in source_path.parts
            or source_path.suffix in {".pyc", ".pyo"}
        ):
            continue

        if relative_name not in tracked:
            candidates.add(relative_name)


if candidates:
    print(
        "Review these files manually; they were not copied:"
    )

    for relative_name in sorted(candidates):
        print(f"  {relative_name}")
else:
    print("None")
PY

echo
echo "=== Fixture policy ==="
echo "Fixture files were not copied."
echo "Use bin/export-telephony-fixtures.sh for controlled fixture changes."

if [ "${DRY_RUN}" -eq 0 ]; then
  echo
  echo "=== Repository validation ==="

  git diff --check

  echo "Whitespace validation: PASS"
fi

echo
echo "=== Result ==="
git status --short

echo

if [ "${DRY_RUN}" -eq 1 ]; then
  echo "Dry run complete. No host files were changed."
else
  git diff --stat
  echo
  echo "Telephony tracked-source pull complete."
fi