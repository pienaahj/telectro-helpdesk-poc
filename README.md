# telectro-helpdesk-poc

Wrapper repo for an **ERPNext + Frappe Helpdesk** pilot running locally on **macOS** via **Docker Compose**.

This repo is intentionally **two-phase**:

1. **Bring up ERPNext** cleanly (baseline stack)
2. **Add Helpdesk (+ Telephony)** afterwards (keep the base stable and reproducible)

---

## What’s in here

- `compose.yaml` (+ `compose.override.yaml` if used)
- `bin/up.sh` / `bin/down.sh` — start/stop the stack
- `bin/new-site.sh` — create the site (ERPNext installed here)
- `bin/helpdesk-install.sh` — add Helpdesk + Telephony to an existing site
- Helper scripts:
  - `bin/bench-launch.sh` — jump into `bench --site frontend console`
  - `bin/pull-telephony-changes.sh` — pull container edits back to host repo

> Tip: Some scripts were created before the “ERPNext first, Helpdesk later” decision.
> Treat anything except `up/down/new-site/helpdesk-install` as optional until proven needed.

---

## Quick start (ERPNext only)

### 1 Clone + env

```bash
git clone git@github.com:pienaahj/telectro-helpdesk-poc.git
cd telectro-helpdesk-poc
cp .env.template .env.local    # edit secrets + SITE_NAME if applicable
```

---

### 2 Start the stack

```bash
./bin/up.sh
```

### 3 Create the site (ERPNext installed here)

```bash
./bin/new-site.sh
```

### 4 Open ERPNext

Open:

- <http://localhost:8080>
  (or your configured $SITE_NAME, if you’re using nip.io / hostnames)

Login:

- Administrator
- password: whatever you configured (often admin in this POC)

## Add Helpdesk (+ Telephony) after ERPNext

Once ERPNext is up and stable, run:

```bash
./bin/helpdesk-install.sh
```

What this does (high level):

- ensures node + yarn are usable by the frappe user (bench subprocesses)
- bench get-app telephony
- bench get-app helpdesk
- installs apps on the site
- migrates + clears cache
- (optionally) builds assets

## Known gotcha (important)

On the frappe/erpnext image, node/yarn may exist under nvm paths (e.g. /home/frappe/.nvm/...)
but bench subprocesses run without that PATH, so you can see errors like:

- FileNotFoundError: [Errno 2] No such file or directory: 'yarn'
- /usr/bin/env: 'node': No such file or directory

The fix we used in the pilot is to provide stable paths:

- /usr/local/bin/node
- /usr/local/bin/yarn

---

## Developer utilities (quality of life)

### Bench console (most-used)

```bash
./bin/bench-launch.sh
```

This drops you into:

- backend container
- /home/frappe/frappe-bench
- bench --site frontend console
  Your helpdesk-install.sh should ensure those exist (usually by symlinking).

### Pull Telephony edits from container back to host

During debugging it’s easy to edit files inside the container. Before committing/PRs,
pull the updated files back into the host repo:

```bash
./bin/pull-telephony-changes.sh
git status --porcelain
```

This repo treats host git as the final source of truth.

---

## Assignment (HD Ticket) — UI contract + payload gotchas (pilot critical)

The pilot hardens assignment behaviour by overriding:

- frappe.desk.form.assign_to.add
- frappe.desk.form.assign_to.remove
- frappe.desk.form.assign_to.remove_multiple

Override lives in:

- apps/telephony/telephony/overrides/assign_to.py

### UI contract: response shape must be a list

The Assign modal (assign_to.js) expects assign_to.add to return a list-like value (it calls .map()).
If the override returns an object (e.g. { "results": [...] }), the modal can hang with:

- TypeError: e.map is not a function

**Rule:** overridden add() must return a plain Python list so the HTTP response is:

```json
{ "message": [ ... ] }
```

### UI payload: assign_to may arrive as a JSON list string

The UI can post assign_to as a stringified JSON list:

```text
'["tech.alfa@local.test"]'
```

If treated as a literal username, core ToDo creation fails with:

- LinkValidationError: Could not find Allocated To: ["tech.alfa@local.test"]

**Rule:** normalize assign_to into a list of users (parse JSON list strings).

### Reload notes (bench vs UI)

- Bench console tests may require reloading the module:

```python
import importlib
from telephony.overrides import assign_to as t
importlib.reload(t)
```

- The browser hits a running server process. After changing override code, the safest refresh is:

```bash
docker compose restart backend
```

### DB lock hygiene (avoid InnoDB lock timeouts)

Interactive bench sessions can keep transactions open. Always end tests with one of:

```python
frappe.db.commit()
# or
frappe.db.rollback()
```

---

## Stop / reset

Stop containers:

```bash
./bin/down.sh
```

If you want a hard reset (wipe volumes, data, apps):

```bash
docker compose down -v
```

(Only do this if you’re fine losing the site + DB.)

## Next steps (pilot checklist)

- dd Company TELECTRO-POC
- Add Customers / Locations
- Decide your ticket model (customer, site, asset, service_area, severity)
- Teams + Assignment Rules
- SLA profiles
- Export customizations (if you keep using it):

```bash
  ./bin/export-customizations.sh
```

## Todo / improvements

### If we keep doing this, we’ll build a custom image to eliminate runtime package installs

- Bake node/yarn into a custom backend image

This makes installs deterministic and avoids any runtime apt-get fallback. Something like:

- Dockerfile.backend that starts from frappe/erpnext:v15.94.1
- installs node 20 + yarn classic (or just corepack yarn)
- use build: for backend in compose

```yaml
---
```

