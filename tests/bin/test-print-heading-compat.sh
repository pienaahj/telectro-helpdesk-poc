#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

mkdir "$TMP_ROOT/pristine"
docker run --rm --pull=never --network none --entrypoint tar frappe/erpnext:v15.94.1 \
    -C /home/frappe/frappe-bench -cf - \
    apps/frappe/frappe/printing/doctype/print_heading \
    apps/erpnext/erpnext/setup/doctype/print_heading |
    tar -xf - -C "$TMP_ROOT/pristine"

python3 - "$ROOT_DIR/docker/apply-print-heading-compat.py" "$TMP_ROOT" <<'PY'
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

helper, temporary = map(Path, sys.argv[1:])
frappe = Path("apps/frappe/frappe/printing/doctype/print_heading/print_heading.json")
erpnext = Path("apps/erpnext/erpnext/setup/doctype/print_heading/print_heading.json")


def setup(case):
    return Path(shutil.copytree(temporary / "pristine", temporary / case))


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def run(root, *args, error=None):
    result = subprocess.run([sys.executable, helper, *args],
                            env={**os.environ, "FRAPPE_BENCH_ROOT": str(root)},
                            capture_output=True, text=True)
    if error:
        assert result.returncode != 0, result.stdout
        evidence = json.loads(result.stderr)
        assert evidence["print_heading_compat"] == "REFUSED" and error in evidence["reason"], evidence
        return
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


root = setup("image")
original = snapshot(root)
evidence = run(root)
assert evidence["print_heading_compat"] == "PASS"
assert evidence["model_sync"] == [str(erpnext)]
assert snapshot(root) == {p: data for p, data in original.items() if p != frappe}
applied = snapshot(root)
run(root, error="Missing")
assert snapshot(root) == applied
print("PRINT_HEADING_BUILD_INVENTORY_AND_STRICT_REEXECUTION=PASS")

for case, path in (("frappe_drift", frappe), ("erpnext_drift", erpnext)):
    root = setup(case)
    (root / path).write_bytes((root / path).read_bytes() + b"\n")
    before = snapshot(root)
    run(root, "--backup", root / "backup/original.json", error="SHA-256 mismatch")
    assert snapshot(root) == before and not (root / "backup").exists()
    print("PRINT_HEADING_" + case.upper() + "_REFUSED_BEFORE_MUTATION=PASS")

for case, path in (("frappe_missing", frappe), ("erpnext_missing", erpnext)):
    root = setup(case)
    (root / path).unlink()
    before = snapshot(root)
    run(root, error="Missing")
    assert snapshot(root) == before
print("PRINT_HEADING_MISSING_INPUT_REFUSED_BEFORE_MUTATION=PASS")

root = setup("duplicate")
third = root / "apps/third/third/setup/doctype/print_heading/print_heading.json"
third.parent.mkdir(parents=True)
shutil.copyfile(root / erpnext, third)
before = snapshot(root)
run(root, error="Unexpected Print Heading model inventory")
assert snapshot(root) == before
print("PRINT_HEADING_UNEXPECTED_MODEL_SOURCE_REFUSED=PASS")

root = setup("volume")
backup = root / "apps/.telectro-compat/print-heading/frappe-original.json"
original = snapshot(root)
run(root, "--backup", backup)
assert backup.read_bytes() == original[frappe]
original_backup = backup.read_bytes()
backup.write_bytes(b"tampered")
before = snapshot(root)
run(root, "--restore", backup, error="SHA-256 mismatch")
assert snapshot(root) == before
backup.write_bytes(original_backup)
assert run(root, "--restore", backup)["print_heading_compat"] == "RESTORED"
assert snapshot(root) == original
print("PRINT_HEADING_CHECKED_VOLUME_BACKUP_AND_ROLLBACK=PASS")
PY
