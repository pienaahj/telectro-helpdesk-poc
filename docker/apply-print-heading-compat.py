#!/usr/bin/env python3
"""Keep ERPNext's standard Print Heading model in the combined runtime."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys


FRAPPE = Path("apps/frappe/frappe/printing/doctype/print_heading/print_heading.json")
ERPNEXT = Path("apps/erpnext/erpnext/setup/doctype/print_heading/print_heading.json")
SOURCE_HASHES = {
    FRAPPE: "87da438354d942c6f9b5ffd5eb507b3e32ef904a975159862db13b3545aa62bc",
    ERPNEXT: "0f2144a5011688d4fdb14d6f230d9c47657210f12439a7e8a0aac9a58a9ed446",
}


def digest(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Missing or non-regular file: {path}")
    return sha256(path.read_bytes()).hexdigest()


def require_hash(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: expected {expected}, got {actual}")


def require_inventory(root, expected):
    # Model sync discovers <app package>/<module>/doctype/<name>/<name>.json.
    sources = {path.relative_to(root) for path in
               (root / "apps").glob("*/*/*/doctype/print_heading/print_heading.json")}
    if sources != expected:
        raise ValueError(f"Unexpected Print Heading model inventory: {sorted(map(str, sources))}")
    return sorted(map(str, sources))


def transform(root, backup=None, restore=None):
    require_hash(root / ERPNEXT, SOURCE_HASHES[ERPNEXT])
    require_hash(restore or root / FRAPPE, SOURCE_HASHES[FRAPPE])
    controllers = {path.with_suffix(".py"): digest(root / path.with_suffix(".py"))
                   for path in SOURCE_HASHES}
    require_inventory(root, {ERPNEXT} if restore else set(SOURCE_HASHES))

    if restore:
        restore.rename(root / FRAPPE)
    elif backup:
        if backup.name == FRAPPE.name or backup.exists() or backup.is_symlink():
            raise ValueError(f"Backup path must be new and outside model sync: {backup}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        (root / FRAPPE).rename(backup)
        require_hash(backup, SOURCE_HASHES[FRAPPE])
    else:
        (root / FRAPPE).unlink()

    require_hash(root / ERPNEXT, SOURCE_HASHES[ERPNEXT])
    if restore:
        require_hash(root / FRAPPE, SOURCE_HASHES[FRAPPE])
    for path, expected in controllers.items():
        require_hash(root / path, expected)
    return {
        "print_heading_compat": "RESTORED" if restore else "PASS",
        "source_sha256": {str(path): value for path, value in SOURCE_HASHES.items()},
        "controller_sha256": {str(path): value for path, value in controllers.items()},
        "model_sync": require_inventory(root, set(SOURCE_HASHES) if restore else {ERPNEXT}),
        "backup": str(backup) if backup else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--backup", type=Path, help="move the original to this path on the same volume")
    mode.add_argument("--restore", type=Path, help="restore and consume a verified original backup")
    args = parser.parse_args()
    root = Path(os.environ.get("FRAPPE_BENCH_ROOT", "/home/frappe/frappe-bench")).resolve()
    try:
        print(json.dumps(transform(root, args.backup, args.restore), sort_keys=True))
    except (OSError, ValueError) as exc:
        print(json.dumps({"print_heading_compat": "REFUSED", "reason": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
