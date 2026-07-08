# ERPNext / Helpdesk Pilot Onboarding and Training Readiness Checklist

## Purpose

This checklist defines what must be ready before Telectro, Partner, and Customer users are onboarded onto the ERPNext / Helpdesk pilot.

It is not a process guide and it is not a technical runbook.

Use this checklist to confirm that the training package, onboarding actions, user roles, screenshots, and proof steps are ready before inviting users.

## How this checklist fits with the other pilot docs

This checklist sits above the role and activity guides.

Related documents:

* `docs/user-guides/pilot-welcome-guides.md`

  * role-based orientation for Telectro, Partner, and Customer users.
* `docs/user-guides/activity-process-guides.md`

  * practical step-by-step workflows for common ticket activities.
* `docs/runbooks/pilot-docs-index.md`

  * index of pilot documentation layers.
* `docs/runbooks/customer-ticket-lifecycle-v1.md`

  * canonical customer ticket lifecycle and Customer portal visibility model.
* `docs/runbooks/ticket-assignment-contract.md`

  * canonical assignment, claim, release, and handoff model.
* `docs/runbooks/ticket-evidence-v1.md`

  * canonical ticket evidence and Customer-visible attachment model.

Avoid duplicating those documents here.

This checklist should answer:

* which guides exist;
* which roles need which guides;
* which screenshots are required;
* which screenshots are blocked by production proof;
* which training activities must be demonstrated;
* which onboarding actions must be verified before real users are invited.

---

# 1. Readiness summary

## Current state

The training package is partly ready.

Ready now:

* role-based Welcome Guides;
* Activity Process Guide structure;
* onboarding and training readiness control checklist;
* Customer-visible evidence update process;
* claim, release, and controlled handoff process;
* internal note vs Customer-visible update process;
* Customer ticket resolution process;
* Customer portal request, follow-up, update, evidence, and resolved-outcome processes;
* Partner acceptance, work-done, and Telectro review processes;
* Coordinator / Supervisor operational review processes;
* role-specific quick-start sections;
* screenshot checklist placeholders.

Still needed:

* production screenshots;
* first-user invitation and password setup proof;
* final training pack assembly;
* production screenshot follow-up pass for guides that currently use screenshot placeholders.

Blocked by production setup:

* production admin login proof;
* outgoing email proof;
* welcome/reset/setup email proof;
* real public HTTPS password setup link proof;
* first production user onboarding screenshots;
* production Customer portal screenshots;
* production Partner workspace screenshots;
* production Telectro workspace screenshots.

## Current risk

The main risk is not the absence of role guides.

The main risk is starting onboarding before the complete path has been proven:

1. user account created;
2. role profile applied;
3. welcome/setup email sent;
4. user opens public HTTPS setup link;
5. user sets password;
6. user logs in;
7. user lands in the expected workspace or portal;
8. user can perform only the actions intended for that role;
9. user has a simple guide for what to do next.

---

# 2. Audience readiness matrix

## 2.1 Telectro Technician

### Required documents

* `docs/user-guides/pilot-welcome-guides.md`

  * Technician Guide
  * Technician quick start
* `docs/user-guides/activity-process-guides.md`

  * Add a Customer-visible update with photo/document evidence
  * Claim, release, and handoff ticket ownership
  * Internal notes and Customer-visible updates
  * Resolve a Customer ticket

### Still needed

* Technician screenshot pack
* Production screenshot follow-up pass for Customer-facing evidence and completion evidence examples

### Required screenshots

* TELECTRO-POC Tech Workspace
* My Current Work
* Assigned to me
* Shared with me
* Ticket detail page
* Customer Request card
* Fault Location card
* Internal note action
* Customer-visible update action
* Customer-visible evidence selector
* Controlled Handoff action
* Release action
* Resolve Customer Ticket dialog

### Training actions to demonstrate

* Open My Current Work
* Open an assigned ticket
* Read the Customer Request
* Check Fault Location
* Add an internal note
* Add a Customer-visible update
* Attach evidence to a ticket
* Select evidence in a Customer-visible update
* Claim a ticket
* Release a ticket with a reason
* Understand when not to use generic assignment
* Resolve a Customer ticket after the outcome is confirmed

### Onboarding proof required

* Technician user can log in.
* Technician lands on or can access the Tech Workspace.
* Technician can open My Current Work.
* Technician can open assigned tickets.
* Technician can see Customer Request and Fault Location context.
* Technician can use intended ticket actions.
* Technician does not rely on Partner or Customer portal workflows.

---

## 2.2 Telectro Coordinator

### Required documents

* `docs/user-guides/pilot-welcome-guides.md`

  * Coordinator Guide
  * Coordinator quick start
* `docs/user-guides/activity-process-guides.md`

  * Claim, release, and handoff ticket ownership
  * Internal notes and Customer-visible updates
  * Add a Customer-visible update with photo/document evidence
  * Review current work
  * Check unclaimed tickets
  * Check aging and at-risk tickets
  * Check first-response risk
  * Intervene on a stale or blocked ticket
  * Review Partner acceptance queue
  * Review Partner work completion queue

### Still needed

* Coordinator screenshot pack

### Required screenshots

* TELECTRO-POC Coordinator Workspace
* Operational queue
* Unclaimed tickets
* Aging tickets
* Customer Ticket Oversight
* First response risk
* Partner Acceptance Review Queue
* Partner Work Completion Review Queue
* Ticket handoff action
* Ticket release/handoff reason examples

### Training actions to demonstrate

* Open Coordinator Workspace
* Check unclaimed tickets
* Check aging tickets
* Check Customer first-response risk
* Open a ticket that needs coordination
* Decide whether to prompt, handoff, release, or escalate
* Use Controlled Handoff
* Review Partner acceptance queue
* Review Partner work completion queue
* Identify tickets with unclear next action

### Onboarding proof required

* Coordinator user can log in.
* Coordinator lands on or can access the Coordinator Workspace.
* Coordinator can open operational reports.
* Coordinator can open tickets from reports.
* Coordinator can use intended coordination actions.
* Coordinator can see Partner review queues where applicable.
* Coordinator does not bypass controlled assignment rules.

---

## 2.3 Telectro Ops / Supervisor

### Required documents

* `docs/user-guides/pilot-welcome-guides.md`

  * Ops / Supervisor Guide
  * Ops quick start
* `docs/user-guides/activity-process-guides.md`

  * Claim, release, and handoff ticket ownership
  * Internal notes and Customer-visible updates
  * Review current work
  * Check aging and at-risk tickets
  * Check first-response risk
  * Intervene on a stale or blocked ticket

### Still needed

* Supervisor screenshot pack

### Required screenshots

* TELECTRO-POC Ops Workspace
* Operational snapshot
* Total active / unassigned / partner queue number cards
* Team Load chart
* Aging and at-risk tickets report
* First response / SLA risk report
* Coordinator governance card
* Coordinator uplift history

### Training actions to demonstrate

* Open Ops Workspace
* Review operational snapshot
* Check active/unassigned/partner queue numbers
* Review workload by technician/team
* Review aging and at-risk tickets
* Review first-response or SLA risk
* Identify blocked/stale tickets
* Decide whether to follow up with coordinator, technician, or management
* Avoid using Ops reports as a replacement for ticket updates

### Onboarding proof required

* Supervisor user can log in.
* Supervisor lands on or can access the Ops Workspace.
* Supervisor can open governance and reporting views.
* Supervisor can open tickets from reports.
* Supervisor can see operational health without needing technician workflow shortcuts.
* Supervisor understands that Customer tickets do not need formal Customer portal sign-off before Telectro closure.

---

## 2.4 Partner user

### Required documents

* `docs/user-guides/pilot-welcome-guides.md`

  * Partner Welcome Guide
  * Partner quick start
  * Partner responds to an acceptance request
  * Partner submits work done
  * Review Partner acceptance
  * Review Partner completed work

### Still needed

* Partner screenshot pack

### Required screenshots

* TELECTRO-POC Partner Workspace
* Partner Log Ticket page
* Partner Submitted tickets
* Partner Active tickets
* Partner ticket detail page
* Partner acceptance action
* Submit Work Done action
* Partner Archived tickets
* Route/access denial proof for internal Telectro pages, if needed

### Training actions to demonstrate

* Open Partner Workspace
* Log a Partner service request
* Review submitted tickets
* Review active Partner tickets
* Accept or reject requested Partner work
* Submit work done
* Respond to Partner rework and resubmit work done
* Understand that Telectro reviews Partner completion
* Understand that Partner users do not close Telectro-owned review steps
* Understand that Partner users do not access internal Telectro workspaces or reports

### Onboarding proof required

* Partner user can log in.
* Partner lands on or can access the Partner Workspace.
* Partner can log a ticket.
* Partner can view only intended Partner tickets.
* Partner can use Partner actions where applicable.
* Partner cannot access internal Telectro workspaces, reports, or HD Ticket forms outside the intended Partner surfaces.

---

## 2.5 Customer portal user

### Required documents

* `docs/user-guides/pilot-welcome-guides.md`

  * Customer Welcome Guide
  * Customer quick start

* `docs/user-guides/activity-process-guides.md`

  * Customer logs a support request
  * Customer adds follow-up information
  * Customer views latest update
  * Customer downloads Customer-visible evidence
  * Customer checks resolved ticket outcome

### Still needed

* Customer screenshot pack

### Required screenshots

* Support Requests list
* Log a Support Request button
* New Support Request page
* Service area selector
* Fault Point selector
* Selected Fault Point details
* Add photo/evidence during request creation
* Ticket detail page
* Latest update card
* Customer-visible activity/timeline
* Add information action
* Customer-visible evidence download
* Resolved ticket outcome

### Training actions to demonstrate

* Open Support Requests
* Log a support request
* Choose service area
* Choose closest fault point or asset
* Add clear subject and description
* Attach photos or evidence where useful
* Submit request
* Reopen ticket
* View latest update
* Add follow-up information
* Understand that the Customer portal is not a formal sign-off workflow
* Understand that Telectro closes tickets after confirming the work outcome through the normal direct service process

### Onboarding proof required

* Customer user can log in.
* Customer lands on or can access Support Requests.
* Customer can log a support request.
* Customer can view their own submitted tickets.
* Customer can add follow-up information.
* Customer can see Customer-visible updates.
* Customer can download Customer-visible evidence.
* Customer cannot see Telectro internal notes.

---

# 3. Document readiness checklist

## Required repo-backed documents

* [ ] `docs/user-guides/pilot-welcome-guides.md`
* [ ] `docs/user-guides/activity-process-guides.md`
* [ ] `docs/user-guides/onboarding-training-readiness-checklist.md`
* [ ] `docs/runbooks/pilot-docs-index.md`

## Existing Welcome Guide coverage

* [ ] Technician Guide
* [ ] Coordinator Guide
* [ ] Ops / Supervisor Guide
* [ ] Partner Welcome Guide
* [ ] Customer Welcome Guide
* [ ] Shared Pilot Boundaries
* [ ] Screenshot Checklist
* [ ] One-page quick starts

## Existing Activity Process Guide coverage

* [x] Add a Customer-visible update with photo/document evidence
* [x] Claim, release, and handoff ticket ownership
* [x] Internal notes and Customer-visible updates
* [x] Resolve a Customer ticket
* [x] Customer logs a support request
* [x] Customer adds follow-up information
* [x] Customer views latest update
* [x] Customer downloads Customer-visible evidence
* [x] Customer checks resolved ticket outcome
* [x] Partner responds to an acceptance request
* [x] Partner submits work done
* [x] Review Partner acceptance
* [x] Review Partner completed work
* [x] Review current work
* [x] Check unclaimed tickets
* [x] Check aging and at-risk tickets
* [x] Check first-response risk
* [x] Intervene on a stale or blocked ticket
* [x] Review Partner acceptance queue
* [x] Review Partner work completion queue

## Activity Process Guide follow-up items

### Internal Telectro ticket execution

* [ ] Extend internal note / Customer-visible update guide after production screenshots are captured
* [ ] Extend Customer-visible evidence update guide after production screenshots are captured

---

# 4. Screenshot readiness checklist

## Screenshot storage rule

Keep screenshot-heavy training material in Obsidian unless a screenshot is deliberately selected for repo-backed documentation.

Repo docs should remain text-first and durable.

## Screenshot status categories

Use these labels while assembling the training pack:

* `Ready from local proof`
* `Needs production retake`
* `Blocked by production setup`
* `Optional`
* `Do not use`

## Screenshots ready from local/dev proof

Use local/dev screenshots only when the UI behaviour has already been proven and the screenshot does not need production identity, production URL, or real user onboarding proof.

Candidate local/dev screenshot areas:

* role workspaces;
* ticket detail layout;
* Customer Request card;
* Fault Location card;
* My Current Work;
* Customer-visible update dialog;
* internal note action;
* evidence attachment workflow;
* Partner workspace;
* Customer portal layout.

## Screenshots that should be retaken in production

Retake these once production setup is available:

* login screen;
* first landing page after login;
* role workspace landing pages;
* Customer portal landing page;
* Partner workspace landing page;
* production ticket list views;
* production ticket detail views;
* production Customer-visible update proof;
* production evidence download proof.

## Screenshots blocked by production setup

Do not finalise these until the production admin email and first-user setup flow are proven:

* welcome/setup email received;
* password setup link;
* public HTTPS setup page;
* first successful password creation;
* first user login after password setup;
* first production user landing page;
* production email delivery proof;
* production Customer portal login proof;
* production Partner login proof.

## Screenshot quality checklist

Before accepting a screenshot into the training pack, confirm:

* [ ] it shows the correct role or portal;
* [ ] it does not show private credentials;
* [ ] it does not expose unrelated Customer data;
* [ ] it does not expose internal-only notes in Customer-facing material;
* [ ] it has a short caption;
* [ ] it is close to the related step;
* [ ] it does not duplicate a screenshot already used elsewhere;
* [ ] it reflects the current UI wording;
* [ ] it is not based on an unproven production claim.

---

# 5. Onboarding go/no-go checklist

Do not invite real users until these checks are complete or explicitly accepted as pending.

## Production access

* [ ] Production site is reachable over HTTPS.
* [ ] ERPNext setup wizard has been completed.
* [ ] Production admin user can log in.
* [ ] Desk loads without blank screens.
* [ ] Helpdesk loads without blank screens.
* [ ] Assets load correctly.
* [ ] Websocket/session behaviour appears stable.
* [ ] Timezone is set correctly.
* [ ] Currency/defaults are correct for the pilot.

## Email and password setup

* [ ] Outgoing email is configured.
* [ ] Test email sends successfully.
* [ ] Welcome/setup email sends successfully.
* [ ] Password setup/reset link uses public HTTPS URL.
* [ ] Test user can set password.
* [ ] Test user can log in after setting password.
* [ ] Failed or expired setup-link behaviour is understood.

## Role and workspace access

* [ ] Technician role profile tested.
* [ ] Coordinator role profile tested.
* [ ] Supervisor role profile tested.
* [ ] Partner role profile tested.
* [ ] Customer portal user tested.
* [ ] Technician lands on or can access Tech Workspace.
* [ ] Coordinator lands on or can access Coordinator Workspace.
* [ ] Supervisor lands on or can access Ops Workspace.
* [ ] Partner lands on or can access Partner Workspace.
* [ ] Customer lands on or can access Support Requests.
* [ ] Partner cannot access internal Telectro workspaces/reports.
* [ ] Customer cannot access internal Telectro workspaces/reports.
* [ ] Customer cannot see internal notes.

## Ticket flow smoke tests

* [ ] Customer can log a support request.
* [ ] Customer request appears internally.
* [ ] Internal user can open the ticket.
* [ ] Customer Request context is visible internally.
* [ ] Fault Location context is visible internally.
* [ ] Internal note can be added.
* [ ] Customer-visible update can be sent.
* [ ] Customer-visible update appears in Customer portal.
* [ ] Evidence can be attached to a ticket.
* [ ] Evidence can be selected in Customer-visible update.
* [ ] Customer can download Customer-visible evidence.
* [ ] Technician can claim/release/handoff where applicable.
* [ ] Partner can log a Partner request.
* [ ] Partner acceptance flow works where applicable.
* [ ] Partner submit work done flow works where applicable.
* [ ] Telectro can review Partner work.
* [ ] Customer ticket can be resolved after Telectro confirms the work outcome.

## Training pack readiness

* [ ] Welcome Guides are current.
* [ ] Activity Process Guides are current enough for first onboarding.
* [ ] Onboarding/training readiness checklist is current.
* [ ] Role-specific screenshot packs are assembled or marked pending.
* [ ] Production-only screenshots are not presented as proven until verified.
* [ ] One-page quick starts are available.
* [ ] Training sequence is agreed.
* [ ] Known limitations are documented.
* [ ] Support/escalation person is identified for first onboarding session.

## Final training pack assembly

Use this section before the first onboarding session to confirm that the training material is assembled, clearly labelled, and safe to use.

The final training pack does not need every production screenshot before dry-run preparation can start.

It must, however, clearly separate:

* repo-backed written guidance;
* Obsidian screenshot packs;
* production screenshots still pending;
* live-demo-only sections;
* production proof that has not yet been completed.

### Minimum assembled pack

For each audience, prepare a small role pack containing:

* the relevant Welcome Guide section;
* the relevant Activity Process Guides;
* the role-specific quick start;
* screenshot pack status;
* known production-proof blockers;
* trainer notes for live-demo-only steps;
* support/escalation contact for questions after onboarding.

### Role pack status labels

Use one of these labels for each role pack:

* `Ready for dry run` — written guides are current, demo flow is known, and missing screenshots are clearly marked.
* `Ready for production onboarding` — production access, password setup, role login, screenshots, and smoke flow are proven.
* `Live-demo only` — screenshots are missing or stale, but the trainer can safely demonstrate the flow.
* `Blocked by production proof` — the role cannot be honestly onboarded until production setup, access, email, or HTTPS proof is complete.

### Screenshot handling

Do not block dry-run preparation only because screenshots are missing.

Instead:

* mark missing screenshots as `Pending production screenshot`;
* mark replacement screenshots as `Retake in production`;
* mark temporary demo-only areas as `Live-demo only`;
* keep screenshot-heavy material in Obsidian unless deliberately selected for repo-backed documentation.

### Production-proof handling

Do not describe any production-only onboarding step as proven until it has actually been tested.

This applies especially to:

* first-user invitation email;
* setup/reset password email;
* public HTTPS setup link;
* first production role login;
* Customer portal access;
* Partner workspace access;
* outgoing Customer-visible email, if used during onboarding proof.

### Assembly checklist

* [ ] Each role has a named role pack.
* [ ] Each role pack links to the correct Welcome Guide section.
* [ ] Each role pack links to the correct Activity Process Guides.
* [ ] Each role pack identifies required screenshots.
* [ ] Missing screenshots are labelled as pending, retake, or live-demo-only.
* [ ] Production-only proof is not presented as complete unless tested.
* [ ] Known limitations are listed in trainer notes.
* [ ] A dry-run sequence is prepared before first live onboarding.
* [ ] A support/escalation person is named.
* [ ] Post-session feedback capture is prepared.

---

# 6. Suggested onboarding sequence

## Phase 1 — Internal Telectro pilot users

Start with internal Telectro users before Partner or Customer onboarding.

Recommended order:

1. Supervisor / Ops user
2. Coordinator user
3. Technician user

Reason:

* internal users must understand the process before external users are invited;
* Customer and Partner activity creates tickets that Telectro must be ready to handle;
* supervisors/coordinators need to know how to monitor early risk.

## Phase 2 — Partner user

Onboard Partner users after internal Telectro users can handle Partner-side review queues.

Do not onboard Partner users until Telectro can:

* request Partner acceptance;
* review Partner acceptance;
* review Partner submitted work;
* send rework back where needed;
* keep Partner access contained.

## Phase 3 — Customer portal user

Onboard Customer users after internal Telectro users can handle Customer tickets end-to-end.

Do not onboard Customer users until Telectro can:

* receive Customer support requests;
* send Customer-visible updates;
* attach and expose Customer-visible evidence correctly;
* resolve Customer tickets;
* explain that Customer portal sign-off is not required for normal closure.

---

# 7. Suggested training session checklist

## Before the session

* [ ] Confirm attendees and roles.
* [ ] Confirm test users exist.
* [ ] Confirm test users can log in.
* [ ] Confirm screenshots are available or mark live-demo-only sections.
* [ ] Confirm demo tickets exist.
* [ ] Confirm no private/sensitive data is visible in training examples.
* [ ] Confirm the trainer can access all required workspaces/portals.

## During the session

* [ ] Start with the role’s Welcome Guide.
* [ ] Show the relevant workspace or portal.
* [ ] Walk through the one-page quick start.
* [ ] Demonstrate one normal ticket flow.
* [ ] Demonstrate one mistake or boundary to avoid.
* [ ] Show where Activity Process Guides live.
* [ ] Confirm what users should do when stuck.
* [ ] Capture questions and missing guide items.

## After the session

* [ ] Record which users attended.
* [ ] Record which flows were demonstrated.
* [ ] Record which screenshots still need replacement.
* [ ] Record which guide sections caused confusion.
* [ ] Record follow-up actions.
* [ ] Update the guide backlog where needed.

---

# 8. Known pending items

These items are expected to remain pending until Telectro production setup is unblocked.

* Production admin email/account confirmation.
* ERPNext setup wizard completion.
* Outgoing email verification.
* First-user welcome/setup email proof.
* Public HTTPS password setup proof.
* First production role login proof.
* Production screenshots.
* Final Customer/Partner onboarding screenshots.

Until these are proven, the training package can be prepared but should not claim that the production onboarding path has been verified.

---

# 9. Maintenance rule

Keep this checklist as the onboarding control document.

When updating it:

* keep role orientation in the Welcome Guides;
* keep step-by-step workflows in Activity Process Guides;
* keep technical implementation truth in runbooks;
* keep screenshot-heavy training material in Obsidian unless deliberately selected for repo;
* mark production-only proof as pending until it has actually been tested;
* avoid implying that first-user email/password setup works before it has been verified.
