#!/usr/bin/env python3
"""Write a shell-safe release-state file using atomic replacement."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable


KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


class StateWriteError(Exception):
    """Raised when release-state input or output is invalid."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Write a validated shell-safe KEY=value state file using a "
            "temporary sibling file and atomic replacement."
        )
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination .env file. Its parent directory must already exist.",
    )
    parser.add_argument(
        "--allowed-key",
        action="append",
        default=[],
        metavar="KEY",
        help="Allowed key. Repeat once for each key in the schema.",
    )
    parser.add_argument(
        "--required-key",
        action="append",
        default=[],
        metavar="KEY",
        help="Required non-empty key. Repeat once for each required key.",
    )
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="State field to write. Repeat once for each field.",
    )
    return parser.parse_args()


def validate_key(key: str, context: str) -> None:
    if not KEY_PATTERN.fullmatch(key):
        raise StateWriteError(
            f"{context} contains an invalid key {key!r}; "
            "keys must match [A-Z][A-Z0-9_]*"
        )


def unique_keys(values: Iterable[str], context: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for key in values:
        validate_key(key, context)

        if key in seen:
            raise StateWriteError(f"{context} contains duplicate key {key!r}")

        seen.add(key)
        result.append(key)

    return result


def parse_fields(items: Iterable[str]) -> dict[str, str]:
    fields: dict[str, str] = {}

    for item in items:
        if "=" not in item:
            raise StateWriteError(
                f"field {item!r} must use the form KEY=VALUE"
            )

        key, value = item.split("=", 1)
        validate_key(key, "field")

        if key in fields:
            raise StateWriteError(f"duplicate field {key!r}")

        if "\x00" in value:
            raise StateWriteError(f"field {key!r} contains a NUL byte")

        if "\n" in value or "\r" in value:
            raise StateWriteError(
                f"field {key!r} contains a line break; "
                "release-state values must remain single-line"
            )

        fields[key] = value

    return fields


def validate_schema(
    allowed_keys: list[str],
    required_keys: list[str],
    fields: dict[str, str],
) -> None:
    if not allowed_keys:
        raise StateWriteError("at least one --allowed-key is required")

    allowed = set(allowed_keys)
    required = set(required_keys)

    unknown_required = required - allowed
    if unknown_required:
        names = ", ".join(sorted(unknown_required))
        raise StateWriteError(
            f"required keys are not present in the allowed schema: {names}"
        )

    unknown_fields = set(fields) - allowed
    if unknown_fields:
        names = ", ".join(sorted(unknown_fields))
        raise StateWriteError(f"unknown fields supplied: {names}")

    missing_required = required - set(fields)
    if missing_required:
        names = ", ".join(sorted(missing_required))
        raise StateWriteError(f"required fields are missing: {names}")

    empty_required = sorted(
        key for key in required_keys if fields.get(key, "") == ""
    )
    if empty_required:
        names = ", ".join(empty_required)
        raise StateWriteError(f"required fields are empty: {names}")



def serialize_state(
    allowed_keys: list[str],
    fields: dict[str, str],
) -> str:
    lines = [
        f"{key}={shlex.quote(fields[key])}"
        for key in allowed_keys
        if key in fields
    ]

    return "\n".join(lines) + "\n"


def validate_shell_syntax(path: Path) -> None:
    try:
        result = subprocess.run(
            ["bash", "-n", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise StateWriteError(
            "bash was not found; cannot validate the state file"
        ) from error

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise StateWriteError(
            f"generated state file failed bash -n: {detail}"
        )


def write_atomic(output: Path, content: str) -> None:
    parent = output.parent

    if not parent.exists():
        raise StateWriteError(
            f"output parent directory does not exist: {parent}"
        )

    if not parent.is_dir():
        raise StateWriteError(
            f"output parent is not a directory: {parent}"
        )

    temporary_path: Path | None = None

    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=str(parent),
            text=True,
        )
        temporary_path = Path(temporary_name)

        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary_path, 0o600)
        validate_shell_syntax(temporary_path)

        os.replace(temporary_path, output)
        temporary_path = None

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def main() -> int:
    args = parse_args()

    try:
        allowed_keys = unique_keys(args.allowed_key, "allowed schema")
        required_keys = unique_keys(args.required_key, "required schema")
        fields = parse_fields(args.field)

        validate_schema(
            allowed_keys=allowed_keys,
            required_keys=required_keys,
            fields=fields,
        )

        content = serialize_state(
            allowed_keys=allowed_keys,
            fields=fields,
        )

        write_atomic(args.output, content)

    except StateWriteError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"RELEASE_STATE_WRITTEN={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
