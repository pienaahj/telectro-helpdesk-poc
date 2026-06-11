# Production Script Safety

This document classifies repository helper scripts for production deployment safety.

The purpose is to avoid accidentally running local/pilot helper scripts on the production VM.

## Rule of thumb

Do not assume a script is production-safe because it lives in `bin/`.

Before running any script on the production VM, confirm:

```text
Does it use the production env file?
Does it use compose.production.yaml?
Does it avoid local compose.override.yaml?
Does it avoid .env.local?
Does it avoid local/test mailbox names?
Does it avoid moving git branches?
Does it avoid mutating running containers unexpectedly?
Does it avoid stopping production services without confirmation?
```

## Repository root production safety

Production safety is not only about scripts.

The repository root also contains files that affect Docker Compose behaviour.

Tracked root files:

| File                      | Production stance                                                                                                                               |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `.env.production.example` | Production template only. Safe to track. Must not contain real secrets.                                                                         |
| `.env.template`           | Local/template reference. Do not use as production env without review.                                                                          |
| `compose.yaml`            | Shared base Compose file. Used in both local and production paths.                                                                              |
| `compose.production.yaml` | Production Compose override. Must be used for production through `./bin/prod-compose.sh`.                                                       |
| `compose.override.yaml`   | Local Docker Compose override. Docker Compose may auto-load this with plain `docker compose`. Do not use plain `docker compose` for production. |
| `compose.local.yaml`      | Local-only Compose helper. Not part of production deployment unless explicitly reviewed.                                                        |

Ignored local/runtime files:

| File/path         | Production stance                                                                                    |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| `.env`            | Local env file. Ignored. Do not rely on it for production.                                           |
| `.env.production` | Real production env file. Ignored. Must exist only on the production VM or secure operator machine.  |
| `*.tgz`           | Local backup artefacts. Ignored. Not part of production deployment.                                  |
| `backups/`        | Local backup output. Ignored. Production backups must target the agreed server-side backup location. |
| `tmp/`            | Local scratch directory. Ignored. Not production input.                                              |
| `.DS_Store`       | macOS artefact. Ignored. Not production input.                                                       |
| `__pycache__/`    | Python runtime cache. Ignored. Not production input.                                                 |
| `import/`         | Local ignored import/work area. Not production input unless explicitly reviewed.                     |
| `ops/`            | Local ignored operations/work area. Not production input unless explicitly reviewed.                 |

## Plain Docker Compose warning

Do not run this on the production VM:

```bash
docker compose up -d
docker compose down
docker compose ps
docker compose config
```

Plain Docker Compose from the repository root can load local/default files such as:

```text
compose.yaml
compose.override.yaml
.env
```

Production must deliberately use:

```text
compose.yaml
compose.production.yaml
.env.production
```

Use the production wrapper instead:

```bash
./bin/prod-compose.sh config
./bin/prod-compose.sh ps
./bin/prod-compose.sh up -d
```

The production wrapper exists to avoid accidentally applying local Compose override behaviour on the production VM.

## Production-safe preflight scripts

These scripts are intended for production-readiness proof.

| Script                       | Classification                                 | Notes                                                                                                                                                       |
| ---------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bin/prod-host-preflight.sh` | Production-safe read-only diagnostic           | Does not install packages, change firewall, change SELinux, or start containers.                                                                            |
| `bin/prod-compose.sh`        | Production Compose wrapper                     | Standardizes `.env.production`, `compose.yaml`, and `compose.production.yaml`.                                                                              |
| `bin/prod-render-compose.sh` | Production-safe read-only Compose render check | Renders production Compose config and checks for app-owned public edge red flags.                                                                           |
| `bin/prod-bench.sh`          | Production bench wrapper                       | Runs bench inside the production backend container through `bin/prod-compose.sh`; does not use `.env.local`, `.env`, `pwd.yml`, or `compose.override.yaml`. |

## Local/development wrappers

These scripts are useful locally but should not be used directly on the production VM.

| Script                | Classification             | Reason                                                                                                                                 |
| --------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `bin/up.sh`           | Local development only     | Uses standard local Compose behaviour and may load `compose.override.yaml`; also mutates the backend venv to repair local app imports. |
| `bin/down.sh`         | Local development only     | Uses standard local Compose behaviour; production shutdown must be deliberate and explicit.                                            |
| `bin/status.sh`       | Local status helper        | Uses only `compose.yaml`; production status should use `./bin/prod-compose.sh ps`.                                                     |
| `bin/restart-core.sh` | Local/dev restart helper   | Uses only `compose.yaml`; production restart should use a production wrapper and explicit operator confirmation.                       |
| `bin/migrate.sh`      | Local/dev migration helper | Sources `.env.local`; production migration must use a production site/env path.                                                        |

## Pilot/dev setup scripts

These scripts helped build and iterate the pilot. They should be reviewed before any production use.

| Script                    | Classification                          | Reason                                                                                                                                    |
| ------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `bin/helpdesk-install.sh` | Pilot helper; not production-safe as-is | Assumes containers and site already exist; fetches moving branches; includes pilot/local instructions; treats `bench build` as non-fatal. |
| `bin/install-apps.sh`     | Needs review                            | May be app-install relevant, but production behaviour must be inspected before use.                                                       |
| `bin/new-site.sh`         | Needs review; high impact               | Site creation is production-relevant but must be explicit, env-safe, and reviewed.                                                        |
| `bin/pilot-check.sh`      | Pilot/dev only                          | Pilot naming and assumptions.                                                                                                             |
| `bin/pilot-smoke.sh`      | Pilot/dev only; possible reference      | Smoke ideas may be useful, but production smoke should avoid pilot assumptions.                                                           |
| `bin/mail-user.sh`        | Needs review; likely pilot/dev          | Mail user creation is environment-specific and may not apply to production mail.                                                          |
| `bin/write-ops-kpis.sh`   | Needs review                            | May mutate application records/config; production use must be deliberate.                                                                 |

## Dev sync/export helpers

These scripts are for development workflow and should not be part of production deployment.

| Script                                        | Classification                                          |
| --------------------------------------------- | ------------------------------------------------------- |
| `bin/export-customizations.sh`                | Dev/export helper                                       |
| `bin/export-telephony-fixtures.sh`            | Dev/export helper                                       |
| `bin/pull-helpdesk-changes.sh`                | Dev sync helper                                         |
| `bin/pull-site-config.sh`                     | Dev sync helper                                         |
| `bin/pull-telephony-changes.sh`               | Dev sync helper                                         |
| `bin/restore-fixture-noise.sh`                | Dev repo hygiene helper                                 |
| `bin/restore-telephony-noise-incl-hd-team.sh` | Dev repo hygiene helper                                 |
| `bin/seed-demo.sh`                            | Demo/dev only                                           |
| `bin/bench-launch.sh`                         | Local interactive helper                                |
| `bin/bench-term.sh`                           | Local interactive helper                                |
| `bin/bench.sh`                                | Local bench wrapper; needs review before production use |
| `bin/up-helpdesk.sh`                          | Local/pilot helper                                      |

## Production equivalents

Use these production-safe commands first:

```bash
./bin/prod-host-preflight.sh
./bin/prod-render-compose.sh
./bin/prod-compose.sh config
./bin/prod-compose.sh ps
./bin/prod-bench.sh --site <site-name> list-apps
```

For production start/stop/restart/migrate operations, do not reuse local scripts blindly.

Prefer creating explicit production scripts such as:

```text
bin/prod-up.sh
bin/prod-restart-core.sh
bin/prod-migrate.sh
bin/prod-backup-site.sh
```

Each production script should:

- use `bin/prod-compose.sh`;
- require `.env.production`;
- avoid `.env.local`;
- avoid `compose.override.yaml`;
- avoid local/test defaults;
- print what it is about to do;
- fail loudly;
- avoid hiding production failures;
- require explicit confirmation for destructive or disruptive operations.

## Current stance

The current production-safe path is:

```text
Use existing pilot scripts locally.
Use prod-* scripts for production preflight.
Create additional prod-* scripts one at a time only after reviewing the corresponding local helper.
```
