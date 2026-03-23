# telectro-helpdesk-poc

Local **TELECTRO ERPNext + Helpdesk + Telephony** pilot repo for **macOS** using **Docker Compose**.

This repo is used to:

- stand up a reproducible local pilot
- verify current live behavior against repo-backed code and exported config
- support small, evidence-based customization slices
- keep container work synchronized back to host git

This repo is intentionally practical and pilot-oriented rather than productized.

---

## Purpose

This project supports a local ERPNext pilot with:

- **ERPNext / Frappe**
- **Helpdesk**
- **Telephony customizations**
- Docker-based local development
- a workflow that prioritizes:
  - **read first**
  - **verify current live behavior first**
  - **change one small slice at a time**
  - **sync container edits back to host git**

This README is intentionally high-level. Detailed operational contracts and proof workflows live in the runbooks.

---

## Working method

Current working preference for this repo:

1. **First choice:** edit files **in-container** using VSCode Dev Containers / Container extension
2. **Second choice:** use **bench console** for site-aware verification and diagnostics
3. **Last resort:** `docker compose exec ...`, ad hoc shell commands, or heredocs

General rule:

- verify existing code and live behavior before augmenting it
- keep slices narrow and reversible
- treat **host git** as the final source of truth

---

## High-level setup model

This repo follows a useful **two-phase** structure:

1. **Bring up ERPNext** cleanly as the baseline stack
2. **Add Helpdesk (+ Telephony)** afterwards

This keeps base environment bring-up separate from pilot customization work.

---

## Repo contents

Main items include:

- `compose.yaml`
- `compose.override.yaml` _(if used locally)_
- `.env` / local env configuration
- helper scripts in `bin/`
- Telephony app changes and exported fixtures
- pilot-specific documentation and developer utilities

Main scripts:

- `bin/up.sh` — start the stack
- `bin/down.sh` — stop the stack
- `bin/new-site.sh` — create the site and install ERPNext
- `bin/helpdesk-install.sh` — install Helpdesk + Telephony onto an existing site
- `bin/bench-launch.sh` — open `bench --site frontend console`
- `bin/bench-term.sh` — open a backend shell
- `bin/pull-telephony-changes.sh` — sync edited Telephony files from container back to host repo

---

## Quick start

### 1. Clone and prepare env

```bash
git clone git@github.com:pienaahj/telectro-helpdesk-poc.git
cd telectro-helpdesk-poc
cp .env.template .env.local
```

Edit local values as needed.

### 2. Start the stack

```bash
./bin/up.sh
```

### 3. Create the site

```bash
./bin/new-site.sh
```

### 4. Open ERPNext

Open the configured local site, typically:

- <http://localhost:8080>

Then log in with the site credentials you configured.

### 5. Install Helpdesk + Telephony

Once ERPNext is healthy:

```bash
./bin/helpdesk-install.sh
```

At a high level, this installs the additional apps, runs the required migrations, clears cache, and prepares the site for Helpdesk / Telephony work.

---

## Developer workflow

This repo is no longer just about getting ERPNext running.

It is mainly used for:

- verifying current pilot behavior
- refining Helpdesk / Telephony customizations
- validating routing and assignment behavior
- maintaining exported fixtures
- keeping local development reproducible
- supporting TELECTRO-specific workspace, workflow, and ticketing hardening

That means work should be approached from the point of view of:

- **current verified behavior**
- **small pilot slices**
- **no business-semantics guessing**

---

## Bench console workflow

For most diagnostics, use:

```bash
./bin/bench-launch.sh
```

This opens the most useful working context for pilot verification:

- backend container
- `/home/frappe/frappe-bench`
- `bench --site frontend console`

Use it for:

- inspecting live metadata
- verifying DocType state
- running controlled tests
- reloading Python modules during development
- checking live behavior instead of guessing from fixtures alone

---

## Backend shell workflow

If you need a plain shell inside the backend container:

```bash
./bin/bench-term.sh
```

Use this for:

- file inspection
- shell-level diagnostics
- manual bench commands
- container-level debugging

---

## Syncing container edits back to host

During pilot work it is common to edit files inside the running container.

Before committing, sync those edits back to the host repo:

```bash
./bin/pull-telephony-changes.sh
git status --porcelain
```

Rules:

- host git is the source of truth
- do not leave important edits stranded only inside the container
- verify the resulting diff before commit or PR

---

## Known environment gotcha: node / yarn paths

On the Frappe / ERPNext image, `node` and `yarn` may exist only under user-specific nvm paths.

Bench subprocesses may not inherit that PATH cleanly, which can lead to errors such as:

- `FileNotFoundError: [Errno 2] No such file or directory: 'yarn'`
- `/usr/bin/env: 'node': No such file or directory`

In this pilot, the working fix has been to provide stable paths such as:

- `/usr/local/bin/node`
- `/usr/local/bin/yarn`

---

## Documentation

The pilot documentation is organized around a small set of canonical documents to reduce duplication and drift.

### Start here

- [Pilot Docs Index](docs/runbooks/README.md)

### Core runbooks

- [Bench Verification Playbook](docs/runbooks/bench-verification.md)
- [Mail Health Runbook](docs/runbooks/mail-health.md)
- [Email Ticket Intake Runbook](docs/runbooks/email-ticket-intake.md)
- [Manual Ticket Intake Runbook](docs/runbooks/manual-ticket-intake.md)
- [Ticket Assignment Contract](docs/runbooks/ticket-assignment-contract.md)
- [Ticket Status and Workspace Baseline](docs/runbooks/ticket-status-and-workspace-baseline.md)

### Reference notes

- Email Reference _(maintained in Obsidian / working notes)_

### Documentation rule

When a topic changes:

1. update the canonical source first
2. update this README only if the document map or entry points changed

The README stays intentionally high-level; detailed operational behavior belongs in the runbooks and reference notes.

---

## Important dev note: assignment override behavior

The pilot includes hardening around `HD Ticket` assignment by overriding assignment behavior in Telephony.

Override location:

- `apps/telephony/telephony/overrides/assign_to.py`

A few practical rules matter during development:

### Response shape matters

The Assign modal expects `assign_to.add()` to return a list-like result.

If the override returns the wrong shape, the UI can fail with errors such as:

- `TypeError: e.map is not a function`

Rule:

- overridden `add()` must return a plain Python list so the HTTP response becomes:

```json
{ "message": [ ... ] }
```

### Incoming payload shape matters too

The UI may send `assign_to` as a JSON-list string, for example:

```text
'["tech.alfa@local.test"]'
```

If that is treated as a literal username, ToDo creation can fail with errors such as:

- `LinkValidationError: Could not find Allocated To: ["tech.alfa@local.test"]`

Rule:

- normalize `assign_to` into a real list of users before assignment handling

### Reload behavior

During bench-console testing, reloading the module may be enough:

```python
import importlib
from telephony.overrides import assign_to as t
importlib.reload(t)
```

For browser verification after code changes, the safer refresh is usually:

```bash
docker compose restart backend
```

### DB lock hygiene

Interactive bench sessions can leave transactions open.

End test cycles with one of:

```python
frappe.db.commit()
# or
frappe.db.rollback()
```

This helps avoid lock-related confusion and InnoDB timeout issues.

---

## Stop / reset

### Stop containers

```bash
./bin/down.sh
```

### Hard reset

```bash
docker compose down -v
```

Only do this if you intentionally want to wipe the site, databases, and related volumes.

---

## Pilot guardrails

When working in this repo:

- do not change business semantics from gut feel alone
- verify live behavior before editing fixtures
- keep one slice focused at a time
- prefer proof over assumption
- export or sync changes only when the intended contract is actually decided

This README intentionally stays at the repo/workflow level. Detailed contracts and proof paths belong in the linked runbooks.

