#!/usr/bin/env bash
set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import json
from pathlib import Path

path = Path(
    "apps/telephony/telephony/fixtures/role_profile.json"
)

def require(condition, message):
    if not condition:
        raise SystemExit(
            f"COORDINATOR_PROFILE_VALIDATION_ERROR: {message}"
        )

require(path.is_file(), "Role Profile fixture missing")

profiles = json.loads(path.read_text())
require(isinstance(profiles, list), "Invalid fixture structure")

prefix = "TELECTRO-POC Role - "
common = {"Agent", "Support Team"}
tech = {prefix + "Tech", prefix + "Tech Workspace"}
coord = {
    prefix + "Coordinator Ops",
    prefix + "Coordinator Workspace",
}

expected = {
    "TELECTRO-POC Profile - Technician": common | tech,
    "TELECTRO-POC Profile - Coordinator-Technician":
        common | tech | coord,
    "TELECTRO-POC Profile - Coordinator": common | coord,
}

for name, required_roles in expected.items():
    matches = [
        row for row in profiles
        if row.get("name") == name
    ]
    require(len(matches) == 1, f"Profile count invalid: {name}")

    profile = matches[0]
    require(profile.get("doctype") == "Role Profile", name)
    require(profile.get("role_profile") == name, name)

    children = profile.get("roles") or []
    observed = [row.get("role") for row in children]

    require(
        len(observed) == len(required_roles)
        and set(observed) == required_roles,
        f"Role set mismatch: {name}: {observed}",
    )

    for child in children:
        require(
            child.get("parent") == name
            and child.get("parentfield") == "roles"
            and child.get("parenttype") == "Role Profile",
            f"Invalid role child metadata: {name}",
        )

    print(f"PROFILE={name}")
    print(f"ROLES={sorted(observed)}")
    print("PROFILE_ROLE_CONTRACT=PASS")

print("COORDINATOR_ONLY_TECHNICIAN_EXCLUSION=PASS")
print("COORDINATOR_ONLY_PROFILE_SEMANTIC_VALIDATION=PASS")
PY
