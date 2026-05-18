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

## Production Smoke-Test Checklist

This checklist defines the minimum checks that should pass after a production deployment before the deployment is treated as technically successful.

Smoke testing is not the same as operational go-live.

A smoke test answers:

```text
Is the deployed system reachable, usable, and safe enough for controlled validation?
```

Operational go-live answers:

```text
Are real users ready to start depending on the system?
```

The first production deployment should pass smoke testing before Telectro is asked to validate operational workflows.

### Smoke-test principles

- Use a small controlled set of test users.
- Do not create all production users until the login, role, email, and workspace behaviour has been proven.
- Do not use real operational tickets for the first smoke test.
- Keep test tickets clearly identifiable.
- Record the smoke-test date, tester, release tag, and result.
- If a smoke test fails, fix the cause before go-live rather than treating it as a training issue.

Suggested smoke-test record:

```text
Date:
Release tag:
Production hostname:
Tester:
Result:
Notes:
```

### 1. HTTPS and browser access

Confirm:

- production hostname opens in a browser
- browser shows HTTPS without certificate warnings
- certificate matches the production hostname
- certificate is not expired
- HTTP access redirects to HTTPS, if configured
- login page loads without asset errors
- no obvious `/assets/...` 404 errors appear in browser/network checks

Pass condition:

```text
A user can open the production URL over HTTPS and reach the login page without browser certificate warnings or missing asset errors.
```

### 2. Container and service health

Confirm the production Docker stack is healthy.

Check:

- reverse proxy / frontend is running
- backend is running and healthy
- database is running
- Redis cache is running
- Redis queue is running
- websocket service is running
- queue workers are running
- scheduler is running
- no restart loop is visible

Example checks may include:

```text
docker compose ps
/api/method/ping
container logs
```

Pass condition:

```text
Required containers are running, the site ping succeeds, and no core service is repeatedly restarting.
```

### 3. Administrator login

Confirm the Administrator or agreed admin user can log in.

Check:

- login succeeds
- Desk loads
- no setup wizard appears unexpectedly
- user can access expected admin areas
- site version/app list can be checked if needed

Pass condition:

```text
Admin user can log in and access Desk successfully.
```

### 4. Internal user login

Confirm at least one internal Telectro user can log in.

Use a controlled test/internal user, not the full production user list.

Check:

- login succeeds
- expected role profile applies
- expected workspace appears
- Helpdesk / ticket areas are reachable as intended
- user does not receive inappropriate administrator access

Suggested users to test when available:

- technician
- coordinator
- supervisor/ops

Pass condition:

```text
Internal user can log in and sees the expected internal workspace and permissions.
```

### 5. Partner / customer-side login

If Partner or customer login is in scope for the first deployment, confirm at least one controlled Partner-side user.

Check:

- login succeeds
- Partner workspace loads
- Partner user does not land on raw Desk surfaces
- Partner route guard still blocks inappropriate pages
- Partner user can open only Partner-safe ticket pages
- Partner user cannot access raw HD Ticket list/form/report surfaces outside the safe model

Pass condition:

```text
Partner-side user can access the intended Partner-safe surfaces and is blocked from internal/raw Desk surfaces.
```

### 6. Workspace landing behaviour

Confirm landing behaviour for the expected user types.

Check:

- Partner user lands on `TELECTRO-POC Partner`
- Technician user lands on `TELECTRO-POC Tech`
- Coordinator user lands on `TELECTRO-POC Coordinator`
- Supervisor/Ops user lands on `TELECTRO-POC Ops`

Pass condition:

```text
Each tested user lands on the expected workspace without manual URL correction.
```

### 7. Ticket creation smoke test

Create one clearly marked test ticket.

Suggested subject:

```text
SMOKE TEST - Production deployment validation
```

Check:

- ticket can be created
- required fields work
- routing/assignment behaves as expected
- ticket opens after creation
- timeline/activity is usable
- no unexpected server error appears

Pass condition:

```text
A controlled test ticket can be created, opened, and routed without errors.
```

### 8. Internal ticket workflow

Using the smoke-test ticket, confirm the basic internal workflow.

Check:

- internal user can open the ticket
- ticket status can be updated as expected
- assignment/ownership is visible
- comments can be added
- relevant reports include or exclude the ticket correctly

Pass condition:

```text
Internal users can work with a ticket through the expected basic workflow.
```

### 9. Partner-safe ticket workflow

If Partner workflow is in scope, test with a controlled Partner-visible ticket.

Check:

- Partner-safe ticket page opens
- Partner sees safe ticket fields only
- Partner acceptance/work actions appear only when expected
- Partner action updates backend state correctly
- internal user can review the Partner action
- Partner cannot bypass via raw HD Ticket routes

Pass condition:

```text
Partner workflow can be completed through Partner-safe pages without exposing internal ticket surfaces.
```

### 10. Evidence / attachment smoke test

If ticket evidence is in scope for the first deployment, test a small safe file.

Check:

- internal user can upload evidence
- Partner user can upload evidence, if in scope
- evidence is stored as private file
- evidence appears in the controlled evidence list
- evidence can be downloaded through the controlled endpoint
- raw private file URL is not relied on as the primary access path

Suggested test file:

```text
small PNG or PDF clearly marked as smoke-test evidence
```

Pass condition:

```text
Evidence upload/list/download works through the controlled UI and endpoint model.
```

### 11. Reports and queues

Open the key production reports.

Minimum internal checks:

- My Current Work
- My Team Load
- Partner Current Work, if Partner workflow is in scope
- Partner Acceptance Review Queue, if acceptance workflow is in scope
- Partner Acceptance Rework Queue, if acceptance rework is in scope

Check:

- report loads
- columns render
- data rows render or show an acceptable empty state
- report does not expose inappropriate data to restricted users
- workspace shortcut opens the expected report

Pass condition:

```text
Key operational reports load and show expected scoped data for the tested users.
```

### 12. Notification Log smoke test

If Notification V1 is in scope, create or trigger a controlled notification scenario.

Check:

- Notification Log row is created
- internal user can see relevant notification
- Partner user can see relevant Partner-safe notification, if applicable
- Partner notification routes to `/app/partner-ticket/<ticket>`
- mark-as-read works
- Notification Settings is not exposed to Partner users if it should remain blocked

Pass condition:

```text
Notification Log alerts appear and route correctly without exposing unsafe pages.
```

### 13. Outgoing email smoke test

If SMTP is configured for the first deployment, send one controlled test email.

Check:

- Frappe can authenticate to SMTP
- test email sends successfully
- real inbox receives the email
- sender address is correct
- message is not rejected or quarantined
- no unexpected bulk notification is triggered

Suggested recipient:

```text
controlled Telectro test mailbox
```

Pass condition:

```text
A controlled outgoing email is delivered successfully to a real inbox.
```

### 14. Incoming email smoke test

Only run this if incoming helpdesk mailbox processing is explicitly in scope.

Check:

- mailbox connection succeeds
- one controlled inbound email is received
- expected ticket is created
- sender/contact is handled correctly
- attachments/signatures do not break the intake
- no mail loop occurs

Suggested subject:

```text
SMOKE TEST - inbound helpdesk email
```

Pass condition:

```text
One controlled inbound email creates the expected ticket without duplicates or loops.
```

If incoming mailbox processing is not in scope for first deployment, record it as deferred.

### 15. Backup smoke check

After the deployment passes core smoke checks, take a first known-good backup.

Check backup includes:

- database
- site files
- private files
- public files/assets if required
- production-specific configuration notes

Pass condition:

```text
A first known-good backup exists and its location is documented.
```

A backup should not be treated as fully proven until a restore has been tested.

### 16. Rollback readiness check

Before operational go-live, confirm that rollback is understood.

Check:

- previous release/tag is known, if applicable
- backup location is known
- restore owner is known
- public access can be disabled if needed
- rollback decision owner is known

Pass condition:

```text
The team knows how to stop, revert, or restore if the deployment is unsafe.
```

### 17. Smoke-test sign-off

Record the result.

Suggested sign-off format:

```text
Smoke-test date:
Release tag:
Production hostname:
Tester:
Passed:
Failed checks:
Deferred checks:
Notes:
```

A smoke test can pass with explicitly deferred items, but only if those deferred items are not required for the first production use.

Example deferred items:

- incoming email intake
- full real user onboarding
- browser/mobile push notifications
- advanced monitoring
- automated deployment pipeline

### Minimum pass set for first technical deployment

For the first technical deployment to be considered successful, the following should pass:

- HTTPS browser access
- container/service health
- Administrator login
- at least one internal user login
- expected workspace landing
- controlled ticket creation
- key reports load
- backup taken
- rollback path understood

Additional checks become required when those features are part of the first production use.

## Production Backup and Restore Model

The production deployment is not safe until backup and restore expectations are clear.

A backup is useful only if the team knows:

- what is backed up
- where it is stored
- who can access it
- how long it is retained
- how to restore it
- how to prove that restore works

A backup that has never been restored should not be treated as fully proven.

### Backup goals

The backup model must support two different needs:

```text
Recovery:
Restore the system after data loss, server failure, or accidental deletion.

Rollback:
Return to a previous known-good application/database state after a bad deployment.
```

Recovery and rollback are related, but they are not exactly the same thing.

Rollback is usually time-sensitive and deployment-related.

Restore is usually broader and disaster-recovery related.

### What must be backed up

A production backup should include enough data to recreate the working site.

Minimum backup scope:

- MariaDB database
- Frappe site directory
- private files
- public files
- uploaded ticket evidence
- site configuration required for restore
- production-specific notes required to rebuild the environment

For the ERPNext/Helpdesk deployment, the most important data is:

```text
database
sites data
private files
public files
```

The Docker images and application code should be recoverable from Git tags or image registry tags.

Production secrets and certificate private keys should not be stored in Git. Their backup/storage approach must be agreed separately.

### What should not be treated as the only backup

The following are not enough on their own:

- Docker containers
- running volumes with no export
- screenshots
- Git repository only
- application image only
- database backup without files
- files backup without database
- local developer machine copy

The database and files must remain aligned.

For example, a File record in the database may point to a private file on disk. Restoring one without the other can leave broken attachments or evidence links.

### Backup timing

Backups should happen at predictable points.

Required backup moments:

- before first production deployment
- after first successful technical deployment and smoke test
- before every production upgrade/deploy
- after major confirmed configuration changes
- before risky data repair or migration work

Suggested routine backup pattern:

```text
daily backup
retain recent backups for short-term recovery
retain selected older backups for longer-term recovery
```

The exact retention policy must be agreed with Telectro.

### First production deployment backup timing

The first production deployment should have at least two backup-related milestones.

Before deployment:

```text
Confirm where production backups will be stored.
Confirm who owns backup storage.
Confirm how backup files will be protected.
```

After deployment and smoke test:

```text
Take a first known-good backup.
Record backup location.
Record release tag.
Record production hostname.
Record smoke-test result.
```

This first known-good backup becomes the initial recovery point for the production site.

### Backup storage

Backups should not live only inside the same Docker volume as the application.

Preferred storage characteristics:

- outside the running database container
- outside temporary container filesystems
- accessible to the deployment/admin user
- protected from casual access
- protected from accidental deletion where possible
- enough disk space for retention period
- included in server-level backup/snapshot process if one exists

Possible storage options:

```text
server backup directory
mounted backup disk
network share
managed server snapshot
off-server backup storage
```

For first production deployment, the exact backup location must be documented even if the long-term backup system is improved later.

### Backup security

Backups may contain sensitive operational data.

Backups may include:

- customer details
- contact details
- ticket history
- comments
- attachments
- evidence files
- email-related content
- internal operational notes

Backup files should therefore be protected.

Rules:

- do not commit backups to Git
- do not store backups in the application repo
- restrict file permissions
- avoid copying backups to personal machines unless explicitly needed
- avoid sending backups through casual channels
- document who is allowed to access backups

### Secrets and certificates

Secrets and certificate private keys need their own handling.

Examples:

- database passwords
- Frappe Administrator password
- SMTP password or app-password
- certificate private key
- deployment SSH key
- integration credentials

These should not be stored in Git or pasted into runbooks.

The backup/restore plan must answer:

- where secrets are stored
- who can access them
- how a restore gets the required secrets back
- how certificates are restored or reissued
- who owns certificate renewal

If secrets are lost, a database/file restore may still not be enough to make the site operational.

### Restore model

A restore procedure should explain how to rebuild a working site from backup.

At minimum, restore documentation should cover:

- which backup file or backup set to use
- where the backup is located
- how to stop the running stack safely
- how to restore the database
- how to restore site files
- how to restore private/public files
- how to apply required secrets/configuration
- how to start the stack again
- how to run migrations if needed
- how to run smoke checks after restore

The restore process must be tested before production reliance becomes high.

### Restore test expectation

A restore test should prove that the backup is usable.

A basic restore test should confirm:

- site starts after restore
- Administrator login works
- key users can log in
- tickets are visible
- private evidence files are accessible through controlled endpoints
- reports load
- Notification Log still behaves as expected
- email configuration is either restored or intentionally reconfigured
- HTTPS still works or is intentionally reattached

Suggested restore-test record:

```text
Restore-test date:
Backup used:
Restore target:
Tester:
Result:
Issues found:
Follow-up actions:
```

### Rollback model

Rollback is the deployment escape path.

Rollback answers:

```text
If this deployment is bad, how do we return to the previous known-good state?
```

Rollback may involve:

- checking out the previous Git tag
- restoring the previous database backup
- restoring previous site files
- restoring previous compose/environment configuration
- restarting the previous known-good stack
- disabling public access temporarily

Rollback should be planned before the deployment starts.

Do not deploy if there is no known rollback path.

### Backup and rollback before each deploy

Before each production deployment, record:

```text
Current release/tag:
Target release/tag:
Backup taken:
Backup location:
Rollback target:
Rollback owner:
Deployment owner:
Smoke-test owner:
```

After deployment, record:

```text
Deployment result:
Smoke-test result:
Known issues:
Rollback needed:
First known-good backup after deploy:
```

### Minimum backup pass set for first technical deployment

For the first technical production deployment, the minimum acceptable backup state is:

- backup location known
- backup owner known
- backup method documented
- first known-good backup taken after smoke test
- backup location recorded
- rollback path documented
- restore test either completed or explicitly scheduled as a follow-up

### Open decisions

The following still need to be confirmed:

- backup storage location
- backup retention period
- whether backups are copied off-server
- whether server snapshots are available
- who owns backup monitoring
- who performs restore if needed
- expected restore time
- whether certificate material is backed up or reissued
- where production secrets are stored
