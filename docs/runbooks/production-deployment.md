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

## Current Deployment Readiness Status

This section records the current practical readiness position for the first production-facing technical deployment.

It should be reviewed with Telectro before scheduling deployment.

### Ready / largely proven in pilot

The following areas have working pilot implementation and local proof:

- Core ERPNext/Frappe/Helpdesk application stack in Docker
- TELECTRO role profiles and role-based workspaces
- Internal Tech, Coordinator, and Ops workspace landing behaviour
- Partner workspace and Partner route containment
- Manual ticket creation and internal ticket workflow
- Partner Request, Partner Acceptance, and Partner Work review flows
- Controlled ticket evidence model using private Frappe File records
- Internal and Partner-safe evidence upload/list/download paths
- Take Photo evidence capture path
- My Current Work report
- My Team Load report
- My Team Tickets report based on Service Coverage
- Partner Current Work and Partner workflow reports
- Production Docker Compose skeleton direction with Traefik entry through ports 80/443
- Production smoke-test checklist
- Backup/restore expectations
- HTTPS/certificate handling guidance
- Production email rollout model
- Native Helpdesk customer portal selected as Customer Intake V1 foundation
- Customer Website User containment proof
- Customer portal Service Area capture and routing proof
- Native customer portal private attachment/evidence proof

### Partially ready / needs production wiring

The following areas have a clear direction but still need production-specific configuration or final implementation before real deployment:

- Final production hostname and Frappe site name alignment
- Production `.env` / secrets model
- Final production image/app installation strategy
- Final production frontend/nginx image tag
- Certificate file placement on the server
- Reverse proxy TLS wiring using the supplied certificate
- Production backup command/location/retention implementation
- Restore test procedure on production-like infrastructure
- SMTP/outgoing email configuration, if email is in first deployment scope
- Initial production user creation approach
- Initial TELECTRO Service Coverage row setup from the confirmed personnel/service-area matrix
- Customer Intake V1 production setup: Customer Website Users, Contact to HD Customer links, Customer role permissions, and Default HD Ticket Template field configuration

### Waiting on Telectro

The following inputs are still required from Telectro before production deployment can be scheduled safely:

- Final production hostname
- DNS owner/contact and DNS change timing
- Clean Ubuntu VM/server access
- Public IP address
- SSH/admin access method
- Firewall owner/contact
- Confirmation that ports 80 and 443 may be opened
- Certificate hostname, file set, expiry date, and renewal owner
- Approved method for transferring certificate files/private key
- SMTP details, if outgoing email is required for first deployment
- Decision on whether incoming mailbox processing is in scope for first deployment
- Confirmed production user/contact list
- Confirmed service-area/team/coverage matrix
- Backup storage location
- Backup retention expectation
- Restore owner/test expectation
- Deployment owner
- Smoke-test sign-off owner
- Operational go-live owner/date/window

### Deliberate non-goals for first technical deployment

The following should not block the first controlled technical deployment unless Telectro explicitly moves them into scope:

- Fully automated GitHub deployment pipeline
- Docker Swarm or multi-server clustering
- High-availability setup
- Incoming helpdesk email automation
- WhatsApp/media intake automation
- Browser/mobile push notifications
- Advanced monitoring dashboards
- Service Coverage automatically changing assignment/routing
- Bulk automated user import
- Full notification/email tuning

### Current deployment stance

The current recommended stance is:

```text
Deploy manually from a reviewed Git tag to a clean Ubuntu server.
Use the production Docker Compose merge.
Expose only ports 80/443 publicly, plus restricted SSH where required.
Configure HTTPS using the supplied Telectro certificate.
Run migrations and smoke tests.
Take a first known-good backup.
Treat this as technical deployment first, not operational go-live.
```

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

### Production user/contact onboarding model

Production onboarding should separate four different concepts:

```text
Internal login users:
Telectro staff who use Desk/workspaces/reports.

Partner login users:
Partner users who access Partner-safe workspaces/pages.

Customer login users:
Customer Website Users who use the native Helpdesk customer portal.

Contacts only:
People recorded for organisation/contact context but not expected to log in.
```

Do not create every person as a login user by default.

A production spreadsheet should identify each person as one of:

```text
Internal login user
Partner login user
Customer login user
Contact only
Notification recipient only
```

Recommended onboarding columns:

```text
Name
Email address
Organisation / customer / partner
Person type
Login required
User type
Role Profile
Individual roles, if no Role Profile applies
Customer / HD Customer
Contact record required
Contact -> HD Customer link required
Partner organisation, if applicable
Service areas / coverage
Campus/customer coverage
Should receive email
Welcome/password reset email allowed
Notes
```

### Telectro onboarding spreadsheet input review

An updated Telectro spreadsheet was received for production user/contact and service-area planning.

Spreadsheet tabs reviewed:

```text
Boschendal
Telectro default
Lanzerac
Personnel
User accounts
```

The spreadsheet provides two different kinds of production input:

```text
User/contact onboarding:
- Personnel
- User accounts

Service-area coverage:
- Boschendal
- Telectro default
- Lanzerac
```

Initial user-account interpretation:

```text
Internal Telectro login users:
- Jacques Loubser
- Pierre
- Sean
- Armandt
- Kyle
- Jayden
- Dewaldt
- Christo
- Hendrik Pienaar

Partner login user:
- CN Services

Boschendal-side contacts / undecided access:
- Zayros Gabriels
- Jan Dorfling
- Jasmine Batey
```

Important note:

```text
The spreadsheet should not be treated as a direct import file yet.
It is a planning/input source that still needs access decisions, role/profile mapping, and data cleanup before production account creation.
```

Open cleanup items:

```text
- Confirm Dewald vs Dewaldt naming and email address.
- Confirm whether Boschendal IT staff should be Customer Website Users, contacts only, notification recipients, or another customer-side access type.
- Confirm exact role profile mapping for "Technician / Supervisor" users.
- Confirm exact role profile mapping for "Coordinator / Supervisor" users.
- Confirm whether CN Services needs Partner-only access and which Partner organisation/ticket visibility rules apply.
- Align spreadsheet Service Area labels with app values:
  - Internet Connectivity vs Internet Connection
  - Quotes & Surveys vs Quotes & Site Surveys
```

Service-area coverage interpretation:

```text
The Boschendal, Telectro default, and Lanzerac tabs provide coverage signals by person and service area.
These should inform routing, team visibility, and My Team Load style reports, but should not be imported blindly until user accounts and final service-area labels are confirmed.
```

Current decision:

```text
Use the spreadsheet as the current production onboarding and service-coverage input source.
Do not bulk-create users or coverage records from it until the open cleanup items are confirmed.
```

#### Internal Telectro users

Internal users should normally be System Users with the correct Telectro role profile.

Expected profiles include:

```text
TELECTRO-POC Profile – Technician
TELECTRO-POC Profile – Coordinator-Technician
TELECTRO-POC Profile – Supervisor
```

Internal onboarding checks:

```text
- user can log in
- expected role profile applies
- expected workspace landing works
- user does not have unnecessary administrator access
- user appears correctly in assignment/routing/team coverage where applicable
```

#### Partner users

Partner users should be created only when Partner-side login is required.

Partner users should receive Partner-specific roles/profiles only and must remain contained to Partner-safe surfaces.

Partner onboarding checks:

```text
- Partner user can log in
- Partner workspace loads
- Partner route guard blocks unsafe Desk routes
- Partner user can access only Partner-safe ticket pages/reports
- Partner user cannot access raw HD Ticket list/form/report surfaces
```

#### Customer users

Customer Intake V1 uses the native Helpdesk customer portal.

Customer users should be Website Users, not Desk/System Users.

Expected Customer user setup:

```text
user_type = Website User
role = Customer
HD Ticket permissions = read/create/write allowed, delete denied
```

Customer organisation setup:

```text
User email -> Contact
Contact -> Dynamic Link -> HD Customer
```

Customer onboarding checks:

```text
- customer user can log in
- customer can open /helpdesk/my-tickets/new
- customer can create a ticket
- ticket owner/raised_by is the customer user
- ticket contact resolves
- ticket customer resolves through Contact -> HD Customer
- customer can see their own tickets
- customer cannot access /app, /app/report, /app/hd-ticket, or Telectro workspaces
```

#### Contacts only

Some people should exist only as Contacts.

This applies when a person may be referenced for customer/organisation context or email communication but should not log in.

Contact-only records should not receive role profiles or Desk access.

#### Email onboarding caution

Do not bulk-send welcome emails or password reset emails until outgoing SMTP has been proven.

Recommended production sequence:

```text
1. Create or verify a small controlled test batch.
2. Prove outgoing SMTP with one controlled recipient.
3. Prove login and workspace/portal containment.
4. Only then widen onboarding to the confirmed production user list.
```

#### Minimum onboarding pass set

Before first operational go-live, confirm:

```text
- each login user has an intended user type
- each login user has the intended role/profile
- customer users are Website Users
- partner/customer users are contained
- Contact -> HD Customer links exist for customer portal users
- service-area/team coverage is configured for internal routing where required
- no contact-only person has unnecessary login access
- email sending has been proven before bulk invitations
```

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

The production command must explicitly select the production merge and the server-local production env file.

Expected command shape:

```bash
docker compose \
  --env-file /opt/telectro-helpdesk/.env.production \
  -f compose.yaml \
  -f compose.production.yaml \
  up -d
```

Production must not use the plain local command:

```bash
docker compose up -d
```

The plain command is for local development only, where Docker Compose automatically loads `compose.override.yaml`.

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

### Customer Intake smoke test

If Customer Intake is in scope for the first production deployment, test with one controlled customer Website User.

Check:

- customer user can log in as a Website User
- customer can open `/helpdesk/my-tickets/new`
- customer can create a ticket with Service Area selected
- created ticket has `owner` and `raised_by` set to the customer user
- created ticket resolves `contact`
- created ticket resolves `customer` through Contact -> HD Customer linkage
- created ticket has `custom_request_source = Customer`
- created ticket stores the selected `custom_service_area`
- existing Telectro routing consumes the selected Service Area
- customer can upload one small attachment during ticket creation
- uploaded file is private
- uploaded file is attached directly to the HD Ticket
- customer can view the created ticket in `/helpdesk/my-tickets`
- customer cannot access `/app`, `/app/report`, `/app/hd-ticket`, or Telectro workspaces

Pass condition:

```text
A controlled customer Website User can create a customer portal ticket with Service Area and attachment evidence, the ticket routes correctly, and the customer remains contained to customer-safe portal surfaces.
```

Deferred checks:

Campus/Fault Point Location Link capture remains deferred until customer-safe Location lookup/filtering is designed and proven.
Customer article suggestions remain suppressed unless Redis Stack / RediSearch is explicitly added later.

Then update the **Minimum pass set for first technical deployment** only if Customer Intake is in scope. Add:

```markdown
If Customer Intake is in scope for first production use, the Customer Intake smoke test should also pass with a controlled customer Website User.
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
- My Team Tickets
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

## Production HTTPS and Certificate Model

HTTPS is required for production browser access.

The certificate confirms to the browser that the production web address is trusted and that traffic between the user and the site is encrypted.

Certificate availability is an important input, but it does not by itself complete HTTPS setup.

HTTPS requires:

- agreed production hostname
- DNS pointing that hostname to the production server
- firewall access on required ports
- certificate files
- private key
- reverse proxy configuration
- renewal ownership
- browser smoke testing

### Plain-language explanation

Users should access the system through a secure web address such as:

```text
https://support.telectro.co.za
```

The browser checks whether:

- the certificate is valid
- the certificate matches the address
- the certificate is not expired
- the certificate was issued by a trusted certificate authority
- the server is presenting the correct certificate chain

If any of these are wrong, users may see browser warnings or may be blocked from accessing the site.

### Hostname and certificate match

The certificate must match the production hostname.

Example:

```text
Production hostname:
support.telectro.co.za
```

The certificate must be valid for:

```text
support.telectro.co.za
```

or for a wildcard that covers it, such as:

```text
*.telectro.co.za
```

A certificate for one hostname does not automatically work for a different hostname.

For example, a certificate for:

```text
www.telectro.co.za
```

does not necessarily cover:

```text
support.telectro.co.za
```

unless the certificate includes that name or is a suitable wildcard certificate.

### DNS requirement

The chosen production hostname must point to the production server.

Required decision:

```text
Who controls DNS for the Telectro domain?
```

Required action:

```text
Create or update the DNS record so the production hostname points to the production server public IP address.
```

Example:

```text
support.telectro.co.za -> production server public IP
```

HTTPS cannot be tested properly from normal user browsers until DNS points to the correct server or a controlled temporary hosts-file test is used.

### Firewall requirement

The production server must allow browser traffic.

Expected public ports:

```text
80   HTTP, mainly for redirect/certificate validation/renewal
443  HTTPS, normal browser access
```

Port `443` is required for normal HTTPS access.

Port `80` is commonly used for:

- redirecting HTTP users to HTTPS
- certificate validation/renewal, depending on certificate approach
- initial smoke testing

Administrative SSH access may also be required:

```text
22   SSH, preferably restricted where possible
```

Database, Redis, backend, worker, scheduler, and websocket ports should not be publicly exposed.

### Certificate files

Certificate material commonly includes:

```text
certificate file
private key file
chain/intermediate certificate file
```

File extensions may vary.

Examples:

```text
.crt
.key
.pem
.ca-bundle
fullchain.pem
privkey.pem
```

The exact file names are less important than understanding what each file is for.

### Certificate file roles

#### Certificate file

The certificate file identifies the hostname and the certificate authority that issued the certificate.

This file is usually safe to distribute to the server components that need it.

#### Private key file

The private key proves that the server is allowed to use the certificate.

This file is sensitive.

Rules:

- do not commit the private key to Git
- do not paste the private key into runbooks
- do not send it through casual channels
- restrict file permissions on the server
- only allow required administrators/services to read it

If the private key is exposed, the certificate should be considered compromised and may need to be replaced.

#### Chain/intermediate certificate file

The chain file helps browsers verify that the certificate was issued by a trusted certificate authority.

If the chain is missing or incorrect, some browsers or devices may show trust errors even if the certificate itself is valid.

### Certificate storage on the server

The agreed certificate storage path must be documented before deployment.

Example intent:

```text
/opt/telectro-erpnext/certs
```

or:

```text
/etc/telectro-erpnext/certs
```

The final path should depend on the chosen production compose and reverse proxy structure.

Storage rules:

- certificate files live on the production server
- certificate private keys stay outside Git
- file ownership and permissions must be restricted
- the Docker/reverse proxy service must be able to read the required files
- the path must be included in the deployment/restore notes

### Reverse proxy responsibility

In production, HTTPS should normally be handled by a reverse proxy.

Expected traffic flow:

```text
Browser
  -> HTTPS on port 443
  -> reverse proxy
  -> internal Docker network
  -> ERPNext/Frappe frontend/backend services
```

The reverse proxy is responsible for:

- listening on ports `80` and `443`
- presenting the certificate
- redirecting HTTP to HTTPS, if configured
- forwarding traffic to the correct internal service
- preserving required headers for Frappe/ERPNext

Possible reverse proxy choices include:

- Traefik
- Nginx
- Caddy

The project should use the simplest reverse proxy model that fits the chosen production Docker Compose structure.

### Frappe / ERPNext site URL

The Frappe site configuration should align with the production hostname.

Example:

```text
Production hostname:
support.telectro.co.za

Frappe site name:
support.telectro.co.za
```

This avoids confusion in:

- bench commands
- site configuration
- email links
- notification links
- browser redirects
- HTTPS configuration

The final site name must be decided before production site creation or restore.

### Email links and HTTPS

If the system sends email notifications, links in those emails should point to the HTTPS production address.

For example:

```text
https://support.telectro.co.za/app
```

not:

```text
http://localhost:8080
```

and not an internal Docker hostname.

This means the production site URL and email configuration must be checked together.

### Certificate renewal

Every certificate has an expiry date.

The production plan must document:

- certificate expiry date
- who owns renewal
- how renewal is done
- where renewed files must be placed
- whether services must be restarted/reloaded after renewal
- how renewal is tested

An expired certificate can cause browser warnings and may block users from accessing the system.

### Manual certificate vs automated certificate

There are two broad certificate models.

#### Manual / supplied certificate

Telectro supplies the certificate files.

Deployment responsibility:

- place files on server
- configure reverse proxy to use them
- track expiry date
- replace files before expiry
- reload/restart proxy after renewal

This appears to be the current likely model because Telectro has confirmed that a certificate is available.

#### Automated certificate

A reverse proxy or certificate tool requests and renews the certificate automatically, for example through Let's Encrypt.

Deployment responsibility:

- configure DNS
- expose required ports
- configure reverse proxy/certificate resolver
- monitor renewal
- confirm renewal works

This may be considered later, but should not be assumed unless Telectro confirms this is preferred.

### Certificate handling during backup and restore

Certificate private keys and secrets need careful restore handling.

The restore plan must answer:

- are certificate files backed up?
- where are they stored?
- who can access them?
- can the certificate be reissued instead?
- what happens if the private key is lost?
- what happens if the private key is exposed?

Certificate private keys must not be included in Git-based backups or documentation.

### HTTPS smoke checks

After deployment, confirm the HTTPS path before sign-off.

Browser checks:

- production URL opens over HTTPS
- browser shows no certificate warning
- certificate hostname matches the production hostname
- certificate is not expired
- certificate chain is trusted
- login page loads over HTTPS
- static assets load without `/assets/...` errors or mixed-content warnings
- email-generated links use the HTTPS production hostname, if email is in scope

Command-line checks:

```bash
curl -I http://support.telectro.co.za
curl -Ik https://support.telectro.co.za
```

Expected result:

```text
HTTP redirects to HTTPS.
HTTPS returns a response from Traefik/frontend.
The certificate presented to the browser matches the production hostname.
```

The exact hostname must be replaced with the confirmed `PRODUCTION_HOSTNAME`.

If the HTTPS check fails, do not proceed to operational sign-off until the certificate, Traefik dynamic TLS config, DNS, and firewall path have been checked.

Suggested command-line checks may be added later once the production hostname is known.

### Minimum HTTPS pass set for first technical deployment

For the first technical deployment, the minimum acceptable HTTPS state is:

- production hostname confirmed
- certificate hostname match confirmed
- DNS points to the production server, or a temporary controlled test method is documented
- ports `80` and `443` are open as required
- reverse proxy presents the certificate
- browser access over HTTPS works without warnings
- login page loads without missing asset errors
- certificate expiry date is recorded
- renewal owner is recorded

### Open decisions

The following still need to be confirmed:

- final production hostname
- whether the certificate is single-name or wildcard
- exact certificate file names supplied by Telectro
- certificate expiry date
- certificate renewal owner
- certificate storage path on the server
- reverse proxy choice
- whether HTTP should redirect to HTTPS
- whether certificate renewal is manual or automated
- whether certificate files are backed up or reissued during restore

## Production Email Model

Email is a production dependency, but it should be introduced in controlled phases.

There are three separate concerns that should not be mixed together:

```text
Frappe User email address:
The login identity for a person.

Outgoing email:
The system sends emails through SMTP.

Incoming email:
The system reads a mailbox and creates tickets from received emails.
```

A production user can exist before all email features are fully proven, but password reset emails, welcome emails, email notifications, and incoming ticket creation depend on email configuration being correct.

### Plain-language explanation

For production, email answers several different questions:

- Can users log in with their real email address?
- Can the system send password reset or welcome emails?
- Can the system send controlled notifications?
- Should the system receive emails and create tickets from them?
- Which mailbox should be used for system sending?
- Which mailbox should be used for incoming support requests, if any?

These should be handled step by step.

### Frappe User email address

In Frappe/ERPNext, a user account is usually identified by an email address.

Example:

```text
technician@telectro.co.za
```

This email address is the user's login identity.

This is different from configuring a mailbox that Frappe connects to.

A user account answers:

```text
Who can log in?
```

It does not automatically prove:

```text
Can the system send email?
Can the system read a mailbox?
Can password reset emails be delivered?
```

### Frappe Email Account

A Frappe Email Account is a configured mailbox/server connection.

It may be used for:

```text
sending outgoing email
receiving incoming email
or both
```

A Frappe Email Account usually requires mail server details such as:

- SMTP server
- SMTP port
- username
- password or app-password
- sender address
- security mode
- IMAP/POP server, if incoming mail is required
- IMAP/POP port, if incoming mail is required

This requires authentication to the real mail server.

### Outgoing email

Outgoing email means the system sends messages to users.

Examples:

- welcome emails
- password reset emails
- assignment/update notifications, if enabled
- controlled test messages
- workflow-related communication, if configured later

Outgoing email should be proven before full user onboarding.

Required information:

- SMTP server
- SMTP port
- SMTP username
- SMTP password or app-password
- sender email address
- whether TLS/SSL is required
- whether the sender address is allowed by Telectro mail policy
- controlled test recipient

Suggested sender examples:

```text
support@telectro.co.za
helpdesk@telectro.co.za
no-reply@telectro.co.za
```

The final sender address must be confirmed by Telectro.

### Incoming email

Incoming email means the system reads a mailbox and creates tickets from received emails.

This is more complex than outgoing email.

Incoming email may introduce:

- duplicate ticket risk
- mail loops
- signature images as attachments
- unexpected attachments
- spam/noise
- sender/contact mapping issues
- permission/routing ambiguity
- mailbox polling errors
- confusion between human replies and new tickets

Incoming helpdesk mailbox processing should only be enabled when explicitly in scope.

Recommended first production stance:

```text
Phase 1:
Outgoing email only.

Phase 2:
Incoming helpdesk mailbox after production site, HTTPS, backup, restore, and user access are stable.
```

### Recommended production email rollout

#### Phase 1: Local functional proof

Continue using the local Docker mail server for development and pilot workflow testing.

This proves:

- workflows
- role behaviour
- notification creation
- ticket routing
- user interface behaviour
- Partner-safe routing
- email-triggered logic in a controlled environment, if needed

This does not prove real SMTP delivery.

#### Phase 2: Controlled outgoing SMTP proof

Configure one real outgoing mail account or test mailbox.

Use a controlled Telectro test recipient.

Prove:

- Frappe can authenticate to SMTP
- one controlled email can be sent
- the email arrives in a real inbox
- sender address looks correct
- email is not blocked, quarantined, or rejected
- generated links use the HTTPS production hostname

Do not send bulk welcome/password reset emails before this passes.

#### Phase 3: Small user login batch

Create or activate a small first batch of users.

Suggested users:

- one administrator/internal admin
- one technician
- one coordinator/supervisor
- one Partner/customer-side user, if Partner access is in scope

Prove:

- users can log in
- role profiles are correct
- workspace landing is correct
- password reset/welcome email works, if used
- no user receives inappropriate access

#### Phase 4: Wider user onboarding

Only after SMTP and login smoke checks pass, create or activate the wider confirmed production user list.

Before wider onboarding, confirm:

- email addresses are correct
- users who should log in are marked clearly
- users who are contacts only are not created as login users unnecessarily
- role/profile assignments are confirmed
- notification expectations are confirmed

#### Phase 5: Incoming mailbox processing, if required

Enable incoming helpdesk mailbox processing only after first production stability is proven.

Before enabling, confirm:

- mailbox address
- IMAP/POP access method
- polling behaviour
- ticket creation rules
- sender/contact mapping
- attachment handling expectation
- spam/noise expectations
- mail loop prevention
- who monitors failed intake

### User creation and email delivery

Production user creation and production email delivery are related, but not the same.

A user can be created with an email address before outgoing email is proven.

However:

- welcome emails will not deliver until SMTP works
- password resets will not deliver until SMTP works
- notification emails will not deliver until SMTP works
- incorrect email addresses may create onboarding problems

Recommended rule:

```text
Do not bulk-create or invite all real users until outgoing SMTP has been proven.
```

### Login users vs contacts only

The production user spreadsheet should distinguish between:

```text
Login user:
A person who signs in to the system.

Contact only:
A person recorded as a contact but not expected to log in.

Notification recipient:
A person who may receive email communication.

Partner/customer-side user:
A restricted user who may access Partner/customer-safe surfaces.
```

Do not assume every person in a contact list needs a login account.

This is especially important for Boschendal contacts.

### Partner/customer-side email considerations

Partner/customer-side users need extra care.

Before creating Partner/customer-side login users, confirm:

- should they log in at all?
- should they only receive email?
- should they see Partner-safe ticket pages?
- should they create new requests?
- should they see only their own organisation/customer tickets?
- should they receive Notification Log alerts?
- should they receive emails?

Partner/customer-side access should not be inferred from an email address alone.

The access model must be confirmed before production onboarding.

### Notification expectations

The current pilot Notification V1 model is based on in-app Notification Log alerts.

Email notifications should not be promised automatically unless configured and tested.

Plain-language position:

```text
In-system notifications and workspace/report visibility remain the operational source of truth.

Email may be added for selected high-value events after outgoing email is proven.
```

This avoids promising full email-driven operations before SMTP behaviour is confirmed.

### Email links and production URL

Any email generated by production should point to the production HTTPS hostname.

Correct example:

```text
https://support.telectro.co.za/app
```

Incorrect examples:

```text
http://localhost:8080
http://frontend:8080
http://backend:8000
```

Before sending production emails, confirm that generated links use the production HTTPS address.

### Test mailbox

A controlled Telectro mailbox is useful for first proof.

Suggested use:

- first outgoing SMTP test
- first password reset/welcome email test
- first notification email test, if enabled
- first incoming mailbox test, if incoming mail is in scope

The test mailbox should be used before emailing the wider user list.

### Email smoke checks

Outgoing email smoke check:

- SMTP account configured
- SMTP authentication succeeds
- one controlled email sends
- real inbox receives the email
- sender address is correct
- links point to HTTPS production hostname
- no unexpected bulk email is triggered

Incoming email smoke check, only if in scope:

- mailbox connection succeeds
- one controlled inbound email is received
- expected ticket is created
- sender/contact mapping is acceptable
- attachments do not break intake
- no duplicate ticket is created
- no mail loop occurs

### Minimum email pass set for first technical deployment

For first technical deployment, email can be handled in one of two ways.

#### If outgoing email is in scope

Minimum pass set:

- SMTP details confirmed
- controlled sender mailbox confirmed
- controlled recipient confirmed
- one outgoing test email delivered
- generated links use HTTPS production hostname
- no bulk onboarding email sent before proof

#### If outgoing email is not yet in scope

Minimum pass set:

- email marked as deferred
- users are not told to rely on password reset/welcome emails
- onboarding uses a controlled manual process
- incoming mailbox processing remains disabled
- Telectro understands email is not yet part of the technical deployment pass

### More Open decisions

The following still need to be confirmed:

- system sender email address
- SMTP server
- SMTP port
- SMTP security mode
- SMTP username
- SMTP password/app-password handling
- controlled test recipient
- whether welcome emails should be sent
- whether password reset emails should be used during onboarding
- whether email notifications are required for first production use
- whether incoming helpdesk mailbox processing is in scope
- incoming mailbox address, if required
- IMAP/POP details, if required
- who monitors failed email sending
- who monitors incoming email intake
- whether Boschendal contacts are login users, contacts only, or notification recipients

## Customer Intake V1 Production Model

### Customer Intake V1 production readiness notes

Customer Intake V1 should use the native Helpdesk customer portal as the production foundation.

Detailed discovery and proof are captured in:

```text
docs/runbooks/customer-portal-discovery.md
```

Current production recommendation:

```text
Use native Helpdesk customer portal for customer web intake.
Do not build a custom Customer Intake page for V1 unless a future blocker proves the native portal cannot meet pilot requirements.
```

Minimum production setup expectations:

```text
- Customer users should be Website Users, not Desk/System Users.
- Customer users should use the Customer role with safe HD Ticket read/create/write and no delete.
- Customer Contacts must be linked to HD Customer records for organisation resolution.
- The Default HD Ticket Template should expose custom_service_area as a required customer-visible field.
- custom_request_source should remain backend/hook-owned and should resolve to Customer for portal-created tickets.
- Native customer attachments can be used for Customer Intake evidence if files remain private and attach directly to HD Ticket.
```

Customer Intake V1 should not expose these fields yet:

```text
custom_site_group = Campus
custom_site = Fault Point
```

Reason:

```text
These are Location Link fields. Native Helpdesk does not add customer-specific Location filtering by itself, and broad Location read access could expose unrelated sites or fault points. Campus/Fault Point should remain hidden until a controlled customer-safe Location lookup/filtering model is implemented and proven.
```

Redis / article suggestions decision:

```text
Customer article suggestions are suppressed for the pilot.
Redis Stack / RediSearch is not required for first production deployment unless Telectro explicitly wants customer self-service knowledge base suggestions.
```

Current handling:

```text
helpdesk.api.article.search -> telephony.api.customer_article_search
```

The override returns an empty list so the customer portal does not fail when Redis lacks RediSearch / FT.SEARCH support.

Customer evidence decision:

```text
Native Helpdesk customer portal attachment upload is viable for initial Customer Intake evidence.
Uploaded files must remain private File records attached to HD Ticket.
Custom customer/partner evidence UI, if added later, should use controlled upload/list/download endpoints and must not expose raw private file URLs.
```

Production smoke checks for Customer Intake:

```text
- Customer Website User can log in.
- Customer can open /helpdesk/my-tickets/new.
- Customer can create a ticket with Service Area selected.
- Created ticket has owner/raised_by set to the customer user.
- Created ticket resolves contact and HD Customer correctly.
- Created ticket has custom_request_source = Customer.
- Created ticket stores custom_service_area from the portal.
- Existing Telectro routing consumes the selected Service Area.
- Customer can upload an attachment during ticket creation.
- Uploaded file is private and attached to HD Ticket.
- Customer can view only their own tickets.
- Customer cannot access /app, /app/report, /app/hd-ticket, or Telectro workspaces.
```

Open production decisions:

```text
- Confirm final customer user onboarding process.
- Confirm who creates/maintains Contact -> HD Customer links.
- Confirm final Customer role/HD Ticket permission fixture.
- Confirm file size and allowed file type expectations for customer uploads.
- Decide whether future Campus/Fault Point capture should use a controlled lookup, a simplified Select field, or remain internal-only.
```

## Production Open Decisions and Telectro Inputs

This section consolidates the open decisions and missing inputs required before production deployment can proceed safely.

The purpose is to give Telectro a clear, plain-language checklist of what is still needed.

This list should be reviewed before production deployment starts.

### 1. Access address / hostname

Required decision:

```text
What web address should users type into their browser?
```

Examples:

```text
https://support.telectro.co.za
https://helpdesk.telectro.co.za
https://erp.telectro.co.za
```

Inputs needed:

- final production hostname
- confirmation that Telectro controls the domain
- name/contact of the person who can update DNS
- confirmation that the hostname should be used in email links
- confirmation that this hostname matches or is covered by the certificate

Why this matters:

The hostname connects the browser URL, DNS, HTTPS certificate, Frappe site name, and email links.

### 2. DNS

Required decision:

```text
Who will point the production hostname to the production server?
```

Inputs needed:

- DNS owner/contact
- DNS provider, if known
- production server public IP address
- timing for DNS change
- whether a temporary test hostname is needed before final go-live

Why this matters:

Users cannot reliably access the system by the production hostname until DNS points to the server.

### 3. Production server

Required decision:

```text
Which Ubuntu server will host production?
```

Inputs needed:

- server provider/location
- Ubuntu version
- public IP address
- CPU/RAM/disk details if available
- SSH access method
- deployment/admin user
- who has server admin access
- whether Docker is approved on the server
- whether outbound internet access is available
- whether there is a separate staging/test server

Why this matters:

The production deployment, backups, restore, HTTPS, and smoke tests depend on the server being available and prepared.

### 4. Firewall / public access

Required decision:

```text
Who controls firewall rules and public access?
```

Inputs needed:

- firewall owner/contact
- confirmation that port `443` can be opened for HTTPS
- confirmation that port `80` can be opened if required for redirect/certificate validation
- SSH access policy
- whether SSH can be restricted to trusted IP addresses
- confirmation that database/Redis/internal service ports should remain private

Expected public ports:

```text
80   HTTP, mainly for redirect/certificate validation/renewal
443  HTTPS, normal browser access
```

Administrative access:

```text
22   SSH, preferably restricted where possible
```

Why this matters:

Production should expose only what users and administrators require.

### 5. Certificate

Required decision:

```text
What certificate files are available and who owns renewal?
```

Inputs needed:

- certificate hostname
- whether certificate is wildcard or single-name
- certificate expiry date
- certificate file
- private key file
- chain/intermediate certificate file, if supplied
- renewal owner
- renewal process
- whether certificate can be reissued if needed
- approved method for transferring certificate files to the server

Important rule:

```text
Certificate private keys must not be committed to Git or pasted into documentation.
```

Why this matters:

HTTPS will not work safely unless the certificate matches the hostname, the private key is protected, and renewal responsibility is clear.

### 6. Reverse proxy

Required decision:

```text
Which service will handle HTTPS traffic?
```

Inputs needed:

- preferred reverse proxy approach, if Telectro has one
- whether Traefik, Nginx, or another proxy is preferred
- whether Telectro already has an existing public reverse proxy
- whether the ERPNext stack should manage HTTPS itself
- whether HTTP should redirect to HTTPS

Why this matters:

The reverse proxy presents the certificate and forwards browser traffic to the internal ERPNext/Frappe services.

### 7. Email sending

Required decision:

```text
Which email address should the system send from?
```

Inputs needed:

- sender email address
- SMTP server
- SMTP port
- SMTP security mode
- SMTP username
- SMTP password or app-password handling
- whether the sender is allowed by Telectro mail policy
- controlled test recipient
- whether welcome/password reset emails should be used for onboarding

Suggested sender examples:

```text
support@telectro.co.za
helpdesk@telectro.co.za
no-reply@telectro.co.za
```

Why this matters:

Real user onboarding, password reset, and email notifications depend on outgoing SMTP being proven first.

### 8. Incoming support mailbox

Required decision:

```text
Should the system read incoming emails and create tickets during first production use?
```

Inputs needed if incoming email is in scope:

- incoming mailbox address
- IMAP/POP server
- IMAP/POP port
- authentication method
- polling expectation
- attachment expectation
- spam/noise handling expectation
- who monitors failed intake
- whether this mailbox is dedicated to Helpdesk

Recommended first-production stance:

```text
Prove outgoing email first.
Enable incoming helpdesk mailbox later unless explicitly required for first production use.
```

Why this matters:

Incoming email is more complex than outgoing email and can introduce duplicates, mail loops, signatures as attachments, spam, and routing ambiguity.

### 9. Users and contacts

Required decision:

```text
Who should exist in production and what access should each person have?
```

Inputs needed:

- confirmed user/contact spreadsheet
- name
- email address
- organisation/customer/partner
- login user vs contact only
- role/profile required
- notification expectation
- whether the person should receive email
- whether the person should be able to create requests
- whether the person should access Partner/customer-safe pages
- whether the person is internal Telectro, Boschendal, Partner, or contact-only

Important distinction:

```text
Login user:
A person who signs in to the system.

Contact only:
A person recorded for reference or communication, but not expected to log in.

Notification recipient:
A person who may receive email communication.

Partner/customer-side user:
A restricted user who may access safe external-facing pages.
```

Why this matters:

An email address alone does not define permissions. Access must be deliberate, especially for Boschendal and Partner/customer-side users.

### 10. Teams, service areas, and routing

Required decision:

```text
How should service-area skills and team coverage translate into production configuration?
```

Inputs needed:

- confirmed service-area/team matrix
- which staff cover which service areas
- default routing behaviour
- campus/customer-specific routing expectations
- whether Boschendal has dedicated coverage
- fallback owner/team when no clear match exists
- who may reassign or hand off tickets

Why this matters:

The team spreadsheet can guide production setup, but final routing should only be configured after users and access roles are confirmed.

### 11. Backup storage

Required decision:

```text
Where will production backups be stored?
```

Inputs needed:

- backup location
- backup owner
- whether backups are stored on-server or off-server
- retention period
- who can access backups
- whether server snapshots are available
- whether backups are encrypted/protected
- monitoring expectation
- restore owner

Why this matters:

Production deployment is not safe unless backup and restore expectations are clear before users depend on the system.

### 12. Restore expectation

Required decision:

```text
When and how will restore be tested?
```

Inputs needed:

- restore test owner
- restore test target
- acceptable restore test timing
- expected restore time objective, if any
- whether a staging/test server can be used for restore proof
- what counts as successful restore

Why this matters:

A backup that has never been restored should not be treated as fully proven.

### 13. Deployment ownership

Required decision:

```text
Who approves and performs the first production deployment?
```

Inputs needed:

- deployment owner
- technical approver
- Telectro contact during deployment
- maintenance window
- communication method during deployment
- who can approve rollback
- who can approve go-live

Why this matters:

Deployment should be controlled and auditable, with clear responsibility for decisions.

### 14. Smoke-test sign-off

Required decision:

```text
Who signs off that the technical deployment passed smoke testing?
```

Inputs needed:

- smoke-test owner
- Telectro validation contact
- required test users
- required test workflows
- expected sign-off format
- list of checks that may be deferred

Minimum first technical deployment pass set:

```text
HTTPS browser access
container/service health
Administrator login
at least one internal user login
expected workspace landing
controlled ticket creation
key reports load
backup taken
rollback path understood
```

Why this matters:

Technical deployment should not be confused with operational go-live.

### 15. Operational go-live

Required decision:

```text
When should real users start relying on the system?
```

Inputs needed:

- go-live owner
- go-live date/window
- first user group
- support contact during go-live
- what happens if users find issues
- whether old process remains available temporarily
- whether incoming email is part of go-live
- whether Partner/customer-side users are included in first go-live

Why this matters:

A successful technical deployment does not automatically mean the organisation is ready to switch operational behaviour.

### 16. Open items summary

Before first production deployment, the following must be known:

- production hostname
- DNS owner
- production server access
- firewall owner
- certificate details
- certificate renewal owner
- reverse proxy approach
- production secrets approach
- SMTP sender account, if email is in scope
- initial user/contact list status
- backup location
- rollback path
- smoke-test owner
- go-live/sign-off owner

Before operational go-live, the following should be proven:

- HTTPS access
- service health
- admin login
- internal user login
- workspace landing
- controlled ticket creation
- key reports
- evidence handling, if in scope
- Notification Log, if in scope
- outgoing email, if in scope
- backup taken
- rollback understood
- deferred items recorded

### Current Compose Skeleton Status

The current production Compose skeleton is implementation-adjacent but not yet production-ready.

The production merge currently proves that:

- local development ports `8080` and `9000` are not exposed
- local helper services such as the test mail server and `bench-runner` are not active in the normal production merge
- browser traffic is intended to enter through Traefik on ports `80` and `443`
- Traefik routes browser traffic to the frontend/nginx service
- production site-name usage is parameterised through `SITE_NAME` for:
  - frontend site header
  - backend healthcheck site header
  - create-site default site name
- production DB root password values are parameterised through `MARIADB_ROOT_PASSWORD` in the production override
- the production frontend/nginx image is supplied through `ERPNEXT_NGINX_IMAGE` so production does not silently inherit the moving local `edge` tag

Remaining production risks still visible or not fully resolved:

- production secrets model is documented but not fully converted to Docker secrets
- the final production frontend/nginx image tag still needs to be selected and tested
- production image/app installation strategy is not final
- real hostname, certificate layout, SMTP details, backup location, and user inputs are still pending from Telectro
- production DB root password values are parameterised through `MARIADB_ROOT_PASSWORD` in the production override
- production no longer silently inherits the local `frappe/erpnext-nginx:edge` image tag
- the final production frontend/nginx image tag still needs to be selected and tested

Production site-name usage is now parameterised through `SITE_NAME` for the frontend site header, backend healthcheck site header, and create-site default site name.

## Production Secrets Skeleton

The repository may contain example files that describe required production values, but real production secrets must not be committed to Git.

Example/template files are safe to commit when they contain placeholder values only, such as:

- `.env.production.example`
- certificate layout examples
- Traefik dynamic TLS examples
- documentation describing required values

Real production files must stay server-local and outside Git, for example:

- real production `.env` file
- MariaDB/root passwords
- Frappe Administrator password
- SMTP username/password
- incoming mailbox credentials
- certificate private key
- backup storage credentials
- SSH/private deployment credentials

Suggested server-local production env path:

```bash
/opt/telectro-helpdesk/.env.production
```

Suggested production command shape:

```bash
docker compose \
  --env-file /opt/telectro-helpdesk/.env.production \
  -f compose.yaml \
  -f compose.production.yaml \
  up -d
```

The production Compose skeleton now requires explicit production render values and should not inherit the local development `.env` file into the backend container.

Current production render values include:

```text
ERPNEXT_NGINX_IMAGE
PRODUCTION_HOSTNAME
SITE_NAME
MARIADB_ROOT_PASSWORD
FRAPPE_ADMIN_PASSWORD
DB_ROOT_USERNAME
```

`DB_ROOT_USERNAME` defaults to `root` if omitted.

Use dummy render-proof values when validating Compose structure locally. Do not use real production secrets for local render proof commands.

```bash
PRODUCTION_HOSTNAME=support.telectro.co.za \
SITE_NAME=support.telectro.co.za \
ERPNEXT_NGINX_IMAGE=frappe/erpnext-nginx:edge \
FRAPPE_ADMIN_PASSWORD=render-proof-admin-password \
MARIADB_ROOT_PASSWORD=render-proof-db-root-password \
DB_ROOT_USERNAME=root \
docker compose -f compose.yaml -f compose.production.yaml config > /tmp/telectro-production-compose.rendered.yaml
```

`docker compose config` expands environment variables into the rendered output. Rendered production config files must not be committed or shared when real production secrets are used.

Minimum render checks:

```bash
grep -n 'published: "8080"\|published: "9000"' /tmp/telectro-production-compose.rendered.yaml || true

grep -niE 'local\.test|dev@example\.com|senderpassword|Alfa#1tech|Bravo#1tech|Charlie#1tech|ADMIN_PASSWORD: admin|DB_ROOT_PASSWORD: admin|SITE_NAME: frontend|TRAEFIK_DOMAIN: frontend' /tmp/telectro-production-compose.rendered.yaml || true

grep -n 'published: "80"\|published: "443"' /tmp/telectro-production-compose.rendered.yaml || true
```

Expected result:

```text
No published 8080/9000 ports.
No local/test env leakage.
Traefik publishes 80/443 only.
```

## Production Update and Security Patch Policy

Frappe/ERPNext update notifications must not be ignored, especially when they mention security fixes.

However, updates must not be applied casually during the pilot or directly on production without a controlled rehearsal. Framework, ERPNext, Helpdesk, and custom app behaviour are tightly coupled, and updates may introduce:

- database migrations
- asset rebuild requirements
- Helpdesk UI changes
- permission or routing behaviour changes
- workspace/report fixture drift
- custom app compatibility issues
- Partner containment regressions
- evidence/attachment handling regressions

For the pilot, update notifications should be recorded and reviewed, but not clicked through blindly.

Before production go-live, a controlled update rehearsal should be completed on a branch or staging/local copy.

Minimum update rehearsal sequence:

1. Record current versions:

   ```bash
       bench version
       bench --site frontend list-apps
   ```

2. Take a backup before updating:

   ```bash
       bench --site frontend backup --with-files
   ```

3. Update deliberately according to the chosen production image/app strategy.
4. Run migrations:

   ```bash
       bench --site frontend migrate
   ```

5. Rebuild assets if needed:

   ```bash
       bench build
   ```

6. Restart services.

7. Run the pilot smoke test.

Minimum smoke test after any framework/app update:

- Administrator login
- internal user login
- Partner user login
- role-based landing pages
- Partner route containment
- HD Ticket open/save
- manual ticket creation
- Partner Request creation
- Partner Acceptance flow
- Partner Work flow
- evidence upload/list/download
- Take Photo path
- My Current Work report
- Partner Current Work report
- key workspace pages
- Notification Log check
- production compose render check

Production rule:

Do not go live knowingly behind on available security fixes unless the risk is explicitly accepted and recorded.

If an update cannot be applied before go-live, record:

- current installed versions
- available target versions
- reason for deferral
- risk owner
- planned update window
- rollback plan

### Local Backup Helper

A local/manual helper script exists at:

```bash
    ./bin/backup-site.sh
```

It runs a Frappe backup with files for the selected site and copies the artifacts to:

```bash
    ./backups/<SITE>/
```

The helper is useful for local rehearsal and pre-change safety checks, but it is not the final production backup system. Production still requires a server-side backup location, retention policy, restore test, and ownership decision.

The backups/ directory contains sensitive database and private-file data and must remain ignored by Git.

### Local Compose Default

For local development, the supported startup command is:

```bash
docker compose up -d
```

or:

```bash
./bin/up.sh
```

Local browser-facing ports are defined in compose.override.yaml, which Docker Compose loads automatically together with compose.yaml.

Expected local published ports:

```bash
docker compose ps frontend websocket
```

Expected shape:

```bash
frontend    0.0.0.0:8080->8080/tcp
websocket   0.0.0.0:9000->9000/tcp
```

If frontend only shows:

```bash
8080/tcp
```

then the frontend container is running but not published to the host, and the browser will not reach <http://localhost:8080>.

Production must not use the plain local command. Production must use the explicit production merge, for example:

```bash
docker compose \
  --env-file /opt/telectro-helpdesk/.env.production \
  -f compose.yaml \
  -f compose.production.yaml \
  up -d
```

Because production explicitly selects compose.yaml and compose.production.yaml, the local compose.override.yaml is not included in the production merge.
