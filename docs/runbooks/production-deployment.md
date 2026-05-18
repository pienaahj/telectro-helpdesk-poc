# Production Deployment Runbook

## Purpose

This runbook captures the requirements, deployment model, backup/rollback expectations, and operational checks required before the ERPNext Pilot can be deployed to a production-facing server.

The first production deployment should be treated as a controlled technical deployment, not an instant go-live.

## Production Readiness Questions

The questions below are intended to be answerable by non-DevOps stakeholders.

Where possible, the questions avoid technical implementation terms and focus on operational ownership:

- who owns the server
- who owns the domain
- who owns the certificate
- who owns email
- who signs off testing
- who approves go-live

The answers to these questions must be confirmed before production deployment starts.

## 1. Access address

What address should users type into their browser to access the system?

Examples:

- <https://support.telectro.co.za>
- <https://erp.telectro.co.za>
- <https://helpdesk.telectro.co.za>

Required answer:

- Preferred web address
- Whether Telectro controls this domain
- Who can update the domain settings

Why this matters:

The web address is the name users will bookmark and use daily.

The HTTPS certificate must match this address, and the domain must point to the production server before public HTTPS access can work correctly.

## 2. Server

Where will the production system run?

Required answer:

- Server provider or hosting location
- Ubuntu version if known
- Public IP address
- SSH access method
- Who has admin access
- Whether Docker is allowed
- Whether outbound internet access is allowed

## 3. Firewall / public access

Who controls which ports are open to the internet?

Required answer:

- Who manages firewall rules
- Whether ports 80 and 443 can be opened
- Whether SSH should be limited to specific IP addresses

Why this matters:

A production system exposed to the internet should only expose the minimum required ports.

Expected public access:

```text
80   HTTP, mainly for certificate setup/renewal and redirecting users to HTTPS
443  HTTPS, normal browser access
```

Administrative access:

```text
22   SSH, preferably restricted to trusted IP addresses where possible
```

Other application/database ports should not normally be exposed directly to the internet.

## 4. Certificate

Telectro has confirmed that the certificate is available.

Required answer:

- What domain name is the certificate for?
- Is it a wildcard certificate, for example \*.telectro.co.za?
- What files are available?
- Who renews the certificate?
- When does it expire?

Why this matters:

The certificate enables HTTPS.

A certificate usually consists of a public certificate file, a private key file, and sometimes a chain/intermediate certificate file.

The private key is sensitive and must not be committed to Git, pasted into documentation, or shared casually.

The certificate also needs a renewal plan. An expired certificate will cause browser warnings and may block users from accessing the system.

## 5. Email

Which real email address should the system use for outgoing mail and testing?

Required answer:

- SMTP server address
- SMTP port
- username
- whether password/app-password is available
- sender email address
- whether the account can receive replies
- whether inbound ticket creation from email is required now or later

For pilot production, we may choose:

```text
Phase 1: outgoing email only
Phase 2: incoming helpdesk mailbox after production is stable
```

Why this matters:

There are two separate email concerns:

```text
Outgoing email:
The system sends messages to users.

Incoming email:
The system reads a mailbox and creates tickets from received emails.
```

For first production deployment, outgoing email is the safer first milestone.

Incoming helpdesk mailbox processing can be enabled later after the production site, HTTPS, backups, and basic user access are stable.

## 6. Real users

Which users should exist at first production setup?

Required answer:

- Telectro admin/contact
- technicians
- coordinator/supervisor users
- partner users
- Boschendal contacts
- which users should receive email notifications
- which users should only be login users

Use a spreadsheet to confirm the first production user list before creating accounts.

Suggested columns:

```text
Name
Email address
Organisation / customer / partner
User type
Required role/profile
Should receive email notifications
Should be able to log in
Notes
```

Important distinction:

```text
User account:
A person who can log in to Frappe/ERPNext.
```

Email account:
A mailbox the system connects to for sending or receiving email.

A user can be created before full email testing is complete, but password reset, welcome emails, and notifications depend on outgoing email being configured correctly.

## What can be tested locally

The following can continue to be tested in the local Docker environment using test users and the local mail server:

- roles
- role profiles
- workspaces
- reports
- Partner route guard
- Partner-safe ticket pages
- ticket workflow
- evidence upload
- assignment and routing logic
- Notification Log row creation
- manual ticket creation
- Partner acceptance and Partner work review flows

Local testing proves the application logic.

It does not prove public HTTPS, real DNS, real SMTP delivery, or real mailbox intake.

## What needs real or staging infrastructure

The following require a real production-like environment:

- DNS pointing the chosen web address to the server
- public firewall access
- HTTPS certificate installation
- real browser access over HTTPS
- outgoing SMTP authentication
- real email delivery
- incoming mailbox processing, if required
- production backup location
- restore testing from production-style backup
- production user login testing

These should be tested before operational go-live.

## Recommended rollout phases

### Phase 1: Production requirements confirmed

Confirm:

- web address
- server access
- firewall ownership
- certificate details
- email account details
- initial user/contact list
- backup location
- go-live owner
- testing/sign-off owner

### Phase 2: Technical deployment

Deploy the system to the production server using a controlled manual process.

This phase proves:

- Docker Compose deployment
- site availability
- database migration
- application startup
- administrator login

This is not yet operational go-live.

### Phase 3: HTTPS proof

Prove:

- domain resolves to the server
- HTTPS works
- certificate matches the chosen domain
- browser access is clean
- HTTP redirects to HTTPS if required

### Phase 4: Email proof

Prove outgoing email first.

Check:

- system can authenticate to SMTP
- test email is delivered to a real inbox
- sender address is acceptable
- messages are not blocked or rejected

Incoming helpdesk mailbox processing should only be enabled after outgoing email is stable.

### Phase 5: User smoke testing

Create or activate a small first batch of users.

Minimum smoke checks:

- administrator login
- technician login
- coordinator/supervisor login
- Partner login
- workspace landing
- ticket creation
- Partner-safe ticket access
- evidence upload/download
- notification visibility

### Phase 6: Controlled go-live

Only after technical deployment, HTTPS, email, backups, and smoke checks are proven should the site be considered ready for operational use.

---

## Not in scope for the first production deployment

The first production deployment should not try to solve everything at once.

The following can come later:

- fully automated GitHub deployment pipeline
- incoming helpdesk mailbox automation
- advanced notification tuning
- browser/mobile push notifications
- multi-server clustering
- Docker Swarm
- high-availability setup
- automated user imports
- advanced monitoring dashboards

The first goal is a controlled, recoverable, single-server deployment with known backup, rollback, HTTPS, email, and smoke-test procedures.

## Local POC vs Production Structure

The current local environment has been valuable for proving ERPNext, Helpdesk, custom workflow behaviour, reports, workspaces, Partner containment, evidence handling, and notifications.

However, the local setup should not be treated as a production deployment template without review.

The production deployment should preserve the lessons learned from the local POC, but replace local/testing assumptions with explicit production decisions.

### Local POC assumptions

The current local POC has the following assumptions:

- Runs on a Mac using Docker Desktop.
- Uses local access through `http://localhost:8080`.
- Uses the Frappe site name `frontend`.
- Uses test/admin passwords during setup.
- Uses a local Docker mail server for email testing.
- Allows manual bench-console and container-level repair during discovery.
- Allows Helpdesk/Telephony installation and troubleshooting inside running containers.
- Uses local/test users and local/test email addresses.
- Uses local Docker volumes for database, sites, logs, and assets.
- Does not prove public DNS, public HTTPS, real SMTP delivery, or real user onboarding.

These assumptions are acceptable for development and pilot discovery.

They are not sufficient for production without adjustment.

### Production requirements

The production environment needs different assumptions:

- Runs on an Ubuntu server.
- Uses a real web address agreed with Telectro.
- Uses HTTPS.
- Uses a production Frappe site name, preferably aligned with the agreed web address.
- Uses real secrets instead of test passwords.
- Keeps secrets, certificate private keys, and SMTP credentials outside Git.
- Exposes only the minimum required public ports.
- Keeps database, Redis, backend, worker, scheduler, and websocket services internal to Docker networking.
- Uses a repeatable application deployment process.
- Uses known image versions or a controlled custom image.
- Has a documented backup and restore process.
- Has a documented rollback process.
- Has production smoke checks before operational go-live.

### Lessons from the local POC that must be preserved

#### Shared assets volume

The local setup proved that ERPNext/Frappe assets must be visible consistently to both the backend and frontend/nginx containers.

The production compose structure must explicitly mount the same assets volume into the expected backend and frontend paths.

Expected pattern:

```yaml
backend:
  volumes:
    - assets:/home/frappe/frappe-bench/sites/assets

frontend:
  volumes:
    - assets:/var/www/html/assets
```

If backend and frontend do not see the same built assets, the system can fail with missing /assets/... files or login/runtime errors.

**Helpdesk and Telephony installation**
The local setup also proved that Helpdesk and Telephony must be installed in a repeatable way.

Production should avoid relying on one-off manual repair steps inside running containers.

Risky production pattern:

```text
start containers
manually fix node/yarn
bench get-app helpdesk
bench get-app telephony
pip install editable apps
bench install-app
bench build
restart until healthy
```

Recommended production pattern:

```text
application code comes from Git or a controlled image
data lives in volumes
secrets live outside Git
deployment steps are repeatable
```

For production, the preferred long-term direction is to build or use a controlled application image that already contains the required apps and tooling.

**Local test secrets must not move to production**
The local POC may use simple values such as admin for passwords.

Production must not reuse these values.

Production secrets include:

- database root password
- site database password
- Frappe Administrator password
- SMTP password or app-password
- certificate private key
- any deployment SSH keys or tokens

These values must be stored outside Git.

**Site name**
The local site name is currently frontend.

Production should use a deliberate site name.

Preferred production pattern:

```text
support.telectro.co.za
```

or another agreed hostname.

This keeps bench commands, site configuration, DNS, and HTTPS terminology aligned.

Example:

```bash
bench --site support.telectro.co.za migrate
```

### Public access

The local POC exposes the app through localhost.

Production should expose user traffic through HTTPS only.

Expected public access:

```text
80   HTTP, mainly for certificate validation/renewal and redirect
443  HTTPS, normal browser access
```

SSH may be required for administration, but should be restricted where possible.

Other ports should not normally be publicly exposed.

### Mac versus Ubuntu architecture

The local development machine and the production Ubuntu server may use different CPU architectures.

For example:

```text
Mac: ARM architecture
Ubuntu server: likely amd64/x86_64
```

This matters if Docker images are built locally and copied to the server.

For first production deployment, the safer options are:

- build on the Ubuntu server from a tagged Git checkout; or
- use a proper multi-platform image build process later.

The first production process should avoid relying on an image built only for the Mac architecture.

### Decisions still required

Before writing production deployment scripts, the following structure decisions must be confirmed:

- production hostname / site name
- reverse proxy approach
- certificate placement and renewal approach
- secrets storage approach
- whether to build a custom application image
- whether production builds happen on the Ubuntu server or through a later CI pipeline
- production volume names
- backup paths and retention
- restore test process
- first deployment smoke-test checklist

### Recommended first production structure

For the first production deployment, prefer a boring and auditable structure:

```text
Git tag
  ↓
manual deploy from tag
  ↓
Docker Compose up
  ↓
migrate
  ↓
smoke test
  ↓
backup/rollback proof
```

GitHub Actions and automated production deployment can be introduced later, after the manual process is proven.

### Not production-safe as-is

The following local POC details should not be copied directly into production:

- admin passwords
- localhost-only assumptions
- local Docker mail server assumptions
- manual container repair as a normal deployment step
- unpinned or moving images for critical services
- public exposure of database, Redis, backend, scheduler, worker, or websocket ports
- storing secrets or certificate keys in Git
- assuming a Mac-built Docker image will run on the Ubuntu server

## Production Users, Teams, and Service Areas

The Telectro service-area/team spreadsheet is an external input document.

It can be used to design:

- service-area coverage
- initial team structure
- routing expectations
- user-role planning

It should not be treated as a final production user-import source until:

- email addresses are confirmed
- login requirements are confirmed
- notification expectations are confirmed
- role profiles are confirmed
- Boschendal access model is confirmed

## First Production Deployment Command Flow

This section describes the intended first production deployment flow.

The exact commands may change after the production server, hostname, secrets model, certificate layout, and Docker Compose production structure are confirmed.

The goal of this section is to define the order of operations before writing deployment scripts.

The first production deployment should be manual, controlled, and auditable. Automation can be added later after the manual process is proven.

### 1. Confirm production inputs

Before touching the production server, confirm the required production inputs.

Required inputs:

- production hostname / web address
- production server IP address
- SSH access method
- administrator access owner
- firewall owner
- certificate files and expiry date
- SMTP account details, if outgoing email will be tested
- initial user/contact spreadsheet status
- backup location
- rollback expectation
- go-live/sign-off owner

Do not begin production deployment if the hostname, server access, certificate handling, and backup location are still unknown.

### 2. Prepare Ubuntu server

Prepare the Ubuntu server as a Docker host.

Expected preparation:

- confirm Ubuntu version
- update package lists
- install required OS updates
- create or confirm deployment/admin user
- configure SSH access
- confirm disk space
- confirm outbound internet access
- confirm firewall rules
- install Docker
- install Docker Compose plugin
- confirm Docker runs after reboot

The production server should not expose database, Redis, backend, worker, scheduler, or websocket ports directly to the internet.

Expected public ports:

```text
80   HTTP, mainly for redirect/certificate validation/renewal
443  HTTPS, normal browser access
```

Administrative SSH access may also be required, preferably restricted where possible.

### 3. Clone repository

Clone the project repository on the production server using a controlled deployment path.

Example deployment location:

```text
/opt/telectro-erpnext
```

The exact path can be changed, but it should be documented and used consistently.

The production server should deploy from Git, not from manually copied edited files.

### 4. Checkout release tag

Production should deploy from a Git tag, not from a moving branch.

Expected flow:

```text
git fetch --tags
git checkout <release-tag>
```

The release tag should represent a known reviewed state.

Avoid deploying directly from a working branch unless this is explicitly agreed as an emergency/manual intervention.

### 5. Configure production environment and secrets

Create the required production environment and secret files on the server.

These values must not be committed to Git.

Examples of production secrets:

- database root password
- site database password
- Frappe Administrator password
- SMTP password or app-password
- certificate private key
- deployment SSH key or token, if used later
- any API keys or integration credentials

The repository may contain safe examples such as:

```text
.env.example
```

But the real production values must live only on the server or in an approved secrets store.

### 6. Place certificate files

Place certificate files on the production server in the agreed location.

Typical certificate material may include:

```text
certificate file
private key file
chain/intermediate certificate file
```

The private key is sensitive.

Rules:

- do not commit certificate private keys to Git
- do not paste private keys into runbooks
- restrict file permissions
- document expiry date
- document renewal owner
- document renewal process

The certificate must match the chosen production hostname.

### 7. Start Docker Compose stack

Start the production Docker Compose stack using the production compose files.

The exact compose command depends on the final production compose structure.

Expected intent:

```text
docker compose -f compose.yaml -f compose.production.yaml up -d
```

The production stack should use:

- production-safe secrets
- stable image versions or a controlled custom image
- persistent volumes
- internal Docker networking
- HTTPS reverse proxy configuration
- no direct public database/Redis/backend exposure

### 8. Run migration and build steps

After the stack is running, run the required Frappe/ERPNext site commands.

Expected operations may include:

```text
bench --site <production-site> migrate
bench --site <production-site> clear-cache
bench --site <production-site> clear-website-cache
bench build
```

The exact commands should be confirmed once the final production image and compose structure are chosen.

If the production image already contains built assets, the build step may be different or unnecessary.

### 9. Run service health checks

Confirm that the containers are running and healthy.

Checks should include:

- backend health
- frontend/reverse proxy health
- database health
- Redis health
- websocket service
- queue workers
- scheduler
- site ping endpoint
- browser access

Example intent:

```text
/api/method/ping returns successfully
```

Do not proceed to user testing until service health checks pass.

### 10. Run smoke checks

Run a small production smoke-test checklist before calling the deployment successful.

Minimum smoke checks:

- administrator login
- internal user login
- Partner user login, if available
- expected workspace landing
- create or open a test ticket
- run key reports
- Partner-safe ticket page opens
- evidence list/upload/download works, if in scope
- Notification Log visibility works, if in scope
- outgoing email test succeeds, if SMTP is configured
- HTTPS browser access is clean

Smoke testing proves that the deployment is usable.

It is not the same as operational go-live.

### 11. Take first known-good backup

After the first successful technical deployment and smoke test, take a known-good backup.

The backup should include:

- database
- Frappe sites data
- private files
- public files/assets if required
- relevant configuration
- any production-specific restore notes

The backup location and retention policy must be documented.

A backup that has never been restored should not be treated as fully proven.

### 12. Document rollback path

Before go-live, document how to roll back.

Rollback options may include:

- return to previous Git tag
- restore previous database/site backup
- restore previous compose configuration
- restart previous known-good containers
- disable public access temporarily if the deployment is unsafe

The rollback path must be understandable before production users depend on the system.

### 13. Separate deployment from go-live

The first production deployment is a technical milestone.

It does not automatically mean operational go-live.

Production go-live should happen only after:

- deployment completed
- HTTPS confirmed
- backup completed
- rollback understood
- smoke checks passed
- required users confirmed
- Telectro sign-off received
- support/contact process agreed
-