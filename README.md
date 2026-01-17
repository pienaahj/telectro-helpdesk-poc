# telectro-helpdesk-poc

Wrapper repo for an **ERPNext + Frappe Helpdesk** pilot running locally on **macOS** via **Docker Compose**.

The approach is intentionally two-phase:

1) **Bring up ERPNext** cleanly (baseline stack)
2) **Add Helpdesk (+ Telephony)** afterwards (so we can keep the base stable)

---

## What’s in here

- `compose.yaml` (+ `compose.override.yaml` if you use it)
- `bin/up.sh` / `bin/down.sh` – start/stop the stack
- `bin/new-site.sh` – create the site
- `bin/helpdesk-install.sh` – add Helpdesk + Telephony to an existing ERPNext site
- optional scripts (older experiments): `bin/install-apps.sh`, `bin/seed-demo.sh`, etc.

> Tip: Many scripts were created before the “ERPNext first, Helpdesk later” decision. Treat anything except `up/down/new-site/helpdesk-install` as optional until proven needed.

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

Your helpdesk-install.sh should ensure those exist (usually by symlinking).

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
- then use build: for backend
  