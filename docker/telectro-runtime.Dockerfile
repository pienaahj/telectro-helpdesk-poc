# syntax=docker/dockerfile:1.7

ARG ERPNEXT_IMAGE=frappe/erpnext:v15.94.1
ARG HELPDESK_IMAGE=ghcr.io/frappe/helpdesk:v1.18.1

FROM --platform=linux/amd64 ${HELPDESK_IMAGE} AS helpdesk_source

FROM --platform=linux/amd64 ${ERPNEXT_IMAGE} AS runtime

USER root

ENV CI=1
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

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
    ./env/bin/pip install --no-cache-dir -e ./apps/helpdesk -e ./apps/telephony; \
    mkdir -p sites; \
    ls -1 apps | sort > sites/apps.txt; \
    echo "--- apps.txt ---"; \
    cat sites/apps.txt; \
    echo "--- tool versions ---"; \
    node --version; \
    npm --version; \
    yarn --version; \
    bench version; \
    echo "--- import proof ---"; \
    ./env/bin/python -c "import frappe, erpnext, helpdesk, telephony; print('IMPORTS_OK')"; \
    echo "--- overlay proof ---"; \
    test -f apps/helpdesk/desk/src/pages/ticket/TicketCustomer.vue; \
    test -f apps/telephony/telephony/telectro_round_robin.py; \
    test -f apps/telephony/telephony/hooks.py

RUN set -eux; \
    mkdir -p sites; \
    printf '%s\n' '{"socketio_port": 9000}' > sites/common_site_config.json; \
    cat sites/common_site_config.json; \
    bench build

LABEL org.opencontainers.image.title="Telectro ERPNext Helpdesk Runtime"
LABEL org.opencontainers.image.description="ERPNext runtime with Helpdesk, Telephony, and Telectro overlays"