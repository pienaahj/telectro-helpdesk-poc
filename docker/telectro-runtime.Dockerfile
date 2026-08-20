# syntax=docker/dockerfile:1.7

ARG ERPNEXT_IMAGE=frappe/erpnext:v15.94.1
ARG HELPDESK_IMAGE=ghcr.io/frappe/helpdesk:v1.18.1

FROM --platform=linux/amd64 ${HELPDESK_IMAGE} AS helpdesk_source

FROM --platform=linux/amd64 ${ERPNEXT_IMAGE} AS runtime

USER root

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV NLTK_DATA=/home/frappe/nltk_data

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
      | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg; \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
      > /etc/apt/sources.list.d/nodesource.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends nodejs; \
    npm install -g yarn@1.22.22; \
    node --version; \
    npm --version; \
    yarn --version; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /home/frappe/frappe-bench

COPY --from=helpdesk_source --chown=frappe:frappe /home/frappe/frappe-bench/apps/helpdesk ./apps/helpdesk
COPY --from=helpdesk_source --chown=frappe:frappe /home/frappe/frappe-bench/apps/telephony ./apps/telephony

COPY --chown=frappe:frappe apps/helpdesk/ ./apps/helpdesk/
COPY --chown=frappe:frappe apps/telephony/ ./apps/telephony/

# Production runtime safety:
# Keep HD Team records, but remove pilot-only @local.test team members from
# the production runtime image so install/migrate does not require local dev users.
RUN python - <<'PY'
import json
from pathlib import Path

path = Path("/home/frappe/frappe-bench/apps/telephony/telephony/fixtures/hd_team.json")
if not path.exists():
    raise SystemExit(f"Missing expected fixture: {path}")

data = json.loads(path.read_text())
removed = []

for row in data:
    users = row.get("users")
    if not isinstance(users, list):
        continue

    kept = []
    for child in users:
        user = str(child.get("user", ""))
        if user.endswith("@local.test"):
            removed.append(user)
        else:
            kept.append(child)

    row["users"] = kept

path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")

remaining_local = []
for row in data:
    for child in row.get("users", []) or []:
        user = str(child.get("user", ""))
        if user.endswith("@local.test"):
            remaining_local.append(user)

if remaining_local:
    raise SystemExit(f"Production fixture safety failed; remaining local users: {remaining_local}")

print(f"production_fixture_safety: stripped {len(removed)} @local.test HD Team user assignments")
PY

RUN set -eux; \
    chown -R frappe:frappe ./apps/helpdesk ./apps/telephony

USER frappe

RUN set -eux; \
    ./env/bin/pip install --no-cache-dir "nltk==3.10.0" -e ./apps/helpdesk -e ./apps/telephony; \
    mkdir -p sites; \
    ls -1 apps | sort > sites/apps.txt; \
    echo "--- apps.txt ---"; \
    cat sites/apps.txt; \
    echo "--- tool versions ---"; \
    node --version; \
    npm --version; \
    yarn --version; \
    bench version; \
    echo "--- top-level import proof ---"; \
    ./env/bin/python -c "import frappe, erpnext, helpdesk, telephony; print('TOP_LEVEL_IMPORTS_OK')"; \
    echo "--- Helpdesk overlay proof ---"; \
    test -f apps/helpdesk/desk/src/pages/ticket/TicketCustomer.vue

# Helpdesk's after_migrate hook checks these NLTK resources and downloads them
# when absent. Bake and verify them during image construction so production
# migration does not depend on outbound network access.
RUN ./env/bin/python - <<'PY'
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import nltk
from nltk import data
from nltk.downloader import Downloader


expected_nltk_version = "3.10.0"

if nltk.__version__ != expected_nltk_version:
    raise RuntimeError(
        {
            "expected_nltk_version": expected_nltk_version,
            "actual_nltk_version": nltk.__version__,
        }
    )

download_dir = Path(os.environ["NLTK_DATA"])

required = [
    {
        "package": "averaged_perceptron_tagger_eng",
        "lookup_path": "taggers/averaged_perceptron_tagger_eng.zip",
        "size_bytes": 1539115,
        "sha256": (
            "6025f530624335c67d6547d44757b357"
            "b4e79bae030a0383e9887a92c1718f0b"
        ),
    },
    {
        "package": "punkt_tab",
        "lookup_path": "tokenizers/punkt_tab.zip",
        "size_bytes": 4319076,
        "sha256": (
            "e57f64187974277726a3417ca6f181ec"
            "5403676c717672eef6a748a7b20e0106"
        ),
    },
    {
        "package": "brown",
        "lookup_path": "corpora/brown.zip",
        "size_bytes": 3314357,
        "sha256": (
            "9b275f9b3b95d7bd66ccfb7cd259f445"
            "a13bbe5d1f4107aba09fd3e8364bafa6"
        ),
    },
]

download_dir.mkdir(
    parents=True,
    exist_ok=True,
)

downloader = Downloader(
    download_dir=str(download_dir)
)

for resource in required:
    package = resource["package"]
    lookup_path = resource["lookup_path"]

    result = downloader.download(
        package,
        quiet=False,
    )

    if result is not True:
        raise RuntimeError(
            {
                "package": package,
                "download_result": result,
            }
        )

    zip_path = download_dir / lookup_path

    if not zip_path.is_file():
        raise RuntimeError(
            {
                "package": package,
                "expected_zip": str(zip_path),
                "status": "MISSING",
            }
        )

    actual_size = zip_path.stat().st_size
    actual_sha256 = hashlib.sha256(
        zip_path.read_bytes()
    ).hexdigest()

    if actual_size != resource["size_bytes"]:
        raise RuntimeError(
            {
                "package": package,
                "expected_size_bytes": resource["size_bytes"],
                "actual_size_bytes": actual_size,
            }
        )

    if actual_sha256 != resource["sha256"]:
        raise RuntimeError(
            {
                "package": package,
                "expected_sha256": resource["sha256"],
                "actual_sha256": actual_sha256,
            }
        )

    resolved = data.find(
        lookup_path,
        paths=[str(download_dir)],
    )

    print(
        {
            "package": package,
            "lookup_path": lookup_path,
            "size_bytes": actual_size,
            "sha256": actual_sha256,
            "resolved_location": str(resolved),
            "result": "PASS",
        }
    )

print(
    {
        "nltk_version": nltk.__version__,
        "download_directory": str(download_dir),
        "required_resource_count": len(required),
        "runtime_nltk_assets": "PASS",
    }
)

print("RUNTIME_NLTK_ASSETS_OK")
PY

RUN ./env/bin/python - <<'PY'
from __future__ import annotations

import ast
import importlib
import importlib.util
from pathlib import Path


overlay_root = Path(
    "/home/frappe/frappe-bench/apps/telephony/telephony"
).resolve()

operational_modules = [
    "telephony.telectro_routing_policy",
    "telephony.telectro_round_robin",
    "telephony.telectro_reassign_on_update",
    "telephony.docshare_guard",
    (
        "telephony.ftelephony.doctype."
        "telectro_assignment_handoff_log."
        "telectro_assignment_handoff_log"
    ),
]

context_dependent_modules = [
    "telephony.hooks",
    "telephony.debug_docshare",
    "telephony.monkey_patches.assignment_rule_debug",
]


def require_overlay_origin(
    module_name: str,
    origin_value: str | None,
) -> Path:
    if not origin_value:
        raise RuntimeError(
            f"{module_name}: module has no source origin"
        )

    origin = Path(origin_value).resolve()

    try:
        origin.relative_to(overlay_root)
    except ValueError as exc:
        raise RuntimeError(
            f"{module_name}: resolved outside Telephony overlay: {origin}"
        ) from exc

    return origin


imported = []

for module_name in operational_modules:
    module = importlib.import_module(module_name)

    origin = require_overlay_origin(
        module_name,
        getattr(module, "__file__", None),
    )

    imported.append(module_name)

    print(
        {
            "check": "import",
            "module": module_name,
            "origin": str(origin),
            "result": "PASS",
        }
    )


resolved_and_parsed = []

for module_name in context_dependent_modules:
    spec = importlib.util.find_spec(module_name)

    if spec is None:
        raise RuntimeError(
            f"{module_name}: module specification not found"
        )

    origin = require_overlay_origin(
        module_name,
        spec.origin,
    )

    source = origin.read_text(encoding="utf-8")
    ast.parse(source, filename=str(origin))

    resolved_and_parsed.append(module_name)

    print(
        {
            "check": "resolve-and-parse",
            "module": module_name,
            "origin": str(origin),
            "result": "PASS",
        }
    )


print(
    {
        "operational_modules_imported": len(imported),
        "context_dependent_modules_resolved_and_parsed": len(
            resolved_and_parsed
        ),
        "runtime_overlay_import_proof": "PASS",
    }
)
PY

RUN set -eux; \
    mkdir -p sites; \
    printf '%s\n' '{"socketio_port": 9000}' > sites/common_site_config.json; \
    cat sites/common_site_config.json; \
    bench build

# Frappe's asset build can minify rgba(0, 0, 0, 0.1) to eight-digit hex.
# Premailer's CSS parser rejects that syntax while preparing email HTML.
# Normalize only the known screenshot shadow and fail if the asset changes.
RUN python - <<'PY'
from pathlib import Path

asset_dir = Path("/home/frappe/frappe-bench/sites/assets/frappe/dist/css")
assets = sorted(asset_dir.glob("email.bundle*.css"))

if len(assets) != 1:
    raise SystemExit(
        f"Expected exactly one compiled Frappe email CSS asset in {asset_dir}; "
        f"found {len(assets)}: {[str(asset) for asset in assets]}"
    )

asset_path = assets[0]
css = asset_path.read_text(encoding="utf-8")

before = ".screenshot{box-shadow:0 3px 6px #0000001a;"
after = ".screenshot{box-shadow:0 3px 6px rgba(0,0,0,.1);"

count = css.count(before)

if count != 1:
    raise SystemExit(
        "Expected exactly one known Premailer-incompatible screenshot shadow "
        f"in {asset_path}; found {count}"
    )

css = css.replace(before, after, 1)

if "#0000001a" in css:
    raise SystemExit(
        f"Premailer-incompatible colour remains in {asset_path}"
    )

asset_path.write_text(css, encoding="utf-8")

print(f"email_css_normalization: patched {asset_path}")
PY

LABEL org.opencontainers.image.title="Telectro ERPNext Helpdesk Runtime"
LABEL org.opencontainers.image.description="ERPNext runtime with Helpdesk, Telephony, and Telectro overlays"
