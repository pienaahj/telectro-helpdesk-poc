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

## Obsidian and PDF pack alignment rule

Repo documents are the canonical source for pilot process, readiness, access rules, and go/no-go decisions.

Obsidian may be used for presentation copy, screenshots, trainer notes, pagination, role-pack assembly, and PDF export preparation.

PDF packs are distribution outputs, not a separate source of truth.

When Obsidian or PDF material describes a process, role boundary, screenshot status, or production-proof claim, it should stay aligned with the repo-controlled Welcome Guides, Activity Process Guides, and this readiness checklist.

If an Obsidian note is older than the repo guidance, mark it as one of:

* `Current training/export copy`
* `Needs repo comparison`
* `Stale/archive candidate`

Do not silently reuse stale Obsidian notes in final training packs.

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
* screenshot checklist placeholders;
* production outgoing Email Account configuration;
* production outgoing Email Queue processing to `Sent` without recipient errors;
* production Welcome email generation for synthetic Customer and Partner users;
* production Welcome email generation using the public `https://erp.telectro.co.za` host and `/update-password` setup route.

Still needed:

* controlled real-inbox receipt proof for the onboarding email path;
* successful password setup through the public HTTPS setup link;
* first login after password setup;
* role-specific landing and access proof after first login;
* failed or expired setup-link behaviour proof;
* production screenshots;
* final training pack assembly;
* production screenshot follow-up pass for guides that currently use screenshot placeholders.

Production onboarding acceptance proof still required:

* production admin login proof;
* controlled real-inbox receipt of a test / onboarding email;
* successful public HTTPS password setup in a browser;
* first production role login after password setup;
* first production user onboarding screenshots;
* production Customer portal screenshots;
* production Partner workspace screenshots;
* production Telectro workspace screenshots.

The production email path should no longer be described as blocked by unproven SMTP configuration, Email Queue processing, Welcome-email generation, or public setup-link generation; those application-side layers are now proven.

Production inspection on 2026-08-25 established:

* one enabled default outgoing Email Account, `ERP Admin Outgoing`;
* the default outgoing account configured for SMTP submission through `mail.telectro.co.za:587` with TLS;
* recent Email Queue and recipient rows reaching `Sent` with no recorded errors;
* production `Welcome to Telectro` messages generated for synthetic Customer and Partner users;
* Welcome messages containing the public `https://erp.telectro.co.za/update-password` setup route.

Those checks prove application-side configuration, queue processing, Welcome-email generation, and public setup-link generation. They do not by themselves prove that a human received the message in a real mailbox, opened the setup link successfully, set a password, or completed the subsequent role login.

## Current risk

The main risk is not the absence of role guides.

The main risk is starting onboarding before the complete user acceptance path has been proven:

1. user account created;
2. role profile applied;
3. welcome/setup email generated and delivered;
4. user receives the message in the intended mailbox;
5. user opens the public HTTPS setup link;
6. user sets password;
7. user logs in;
8. user lands in the expected workspace or portal;
9. user can perform only the actions intended for that role;
10. user has a simple guide for what to do next.

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

* Technician User exists, is enabled, and has the intended Role Profile.
* Technician has a native active `HD Agent` identity for the Helpdesk agent experience.
* Technician can access the native Helpdesk agent application.
* Technician lands on or can access the Tech Workspace.
* Technician can open My Current Work.
* Technician can open assigned tickets.
* Technician can see Customer Request and Fault Location context.
* Technician can use intended ticket actions.
* Technician has deliberate membership in the required HD Team or Teams.
* HD Team membership is reflected in the linked native Assignment Rule.
* The linked Assignment Rule is enabled when the Team has one or more members.
* A ticket routed through a canonical pilot ticket-intake path can be assigned to the Technician and produces matching `_assign` and open ToDo state.
* Technician does not rely on Partner or Customer portal workflows.

Production proof on 2026-08-25 established the native Helpdesk identity and routing mechanics using `christo@telectro.co.za`:

* native `HD Agent` creation through Helpdesk `get_agent()` was proven;
* creating the `HD Agent` did not add Team or Assignment Rule membership;
* adding Christo to `PABX` automatically added him to `PABX - Support Rotation-13` and enabled the rule;
* controlled Ticket `14` was natively assigned to Christo with matching `_assign`, one open ToDo, and Assignment Rule `last_user`;
* Ticket `14` appeared under `My Current Work` as `Assigned to me`;
* Christo could open Ticket `14` successfully.

Ticket `14` was created through the native Helpdesk `/helpdesk` Create path solely as a controlled identity and routing proof. That route is not a canonical pilot ticket-intake path and does not prove the normal ERPNext HD Ticket creation form, pilot field rules, defaults, field order, or normal intake workflow.

A final Technician onboarding acceptance proof must therefore repeat the assignment/access smoke test using a canonical pilot ticket-intake path.

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

## 2.4 Partner organisation and user

### Required documents

* `docs/runbooks/partner-operating-model.md`

  * Partner organisation / tenant identity
  * Partner membership
  * Partner capability roles
  * Default Dispatch User
  * Partner acceptance versus Partner work-completion trains
  * Partner production-test containment policy

* `docs/user-guides/pilot-welcome-guides.md`

  * Partner Welcome Guide
  * Partner quick start
  * Partner responds to an acceptance request
  * Partner submits work done
  * Review Partner acceptance
  * Review Partner completed work

### Still needed

* Partner screenshot pack

### Organisation and user setup to verify

* Correct `TELECTRO Partner` organisation exists.
* Organisation enablement is deliberate.
* Intended Partner User exists.
* Required Partner Role Profile / capability is assigned.
* User is an enabled member of the correct Partner organisation.
* Default Dispatch User is configured when Partner fulfilment dispatch is required.
* Default Dispatch User is an enabled member of the same Partner organisation.
* Real Partner organisations do not contain Telectro-controlled synthetic test Users.
* Multi-organisation membership is handled deliberately where applicable.

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

* Open Partner Workspace.
* Log a Partner service request under the correct Partner organisation.
* Review submitted tickets.
* Review active Partner tickets.
* Respond to a Partner acceptance request where Telectro handled a Partner-originated request.
* Submit work done where Telectro assigned fulfilment work to the Partner.
* Respond to Partner work rework and resubmit work done.
* Understand that Partner acceptance and Partner work completion are separate workflow trains.
* Understand that Telectro reviews Partner acceptance and completed Partner work.
* Understand that Partner users do not close Telectro-owned review steps.
* Understand that Partner users do not access internal Telectro workspaces or reports.

### Onboarding proof required

* Partner organisation identity is configured correctly.
* Partner User has the intended Partner capability.
* Partner User has enabled membership in the intended Partner organisation.
* Partner User can log in.
* Partner lands on or can access the Partner Workspace.
* Partner can log a ticket against an organisation the User is permitted to represent.
* Partner can view only tickets legitimately associated with an enabled Partner organisation the User represents.
* Partner can use Partner actions where applicable.
* Partner fulfilment dispatch resolves correctly where fulfilment dispatch is part of the onboarding proof.
* Partner cannot access unrelated Partner organisation tickets.
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

## Screenshot source and production data rule

Training and Welcome Guide screenshots may use local/dev demo data when the screenshot demonstrates generic UI behaviour, layout, actions, queues, or role navigation.

Production screenshots are required only when the screenshot proves production-specific behaviour, such as public HTTPS access, password setup links, first-user login, production email delivery, Customer portal access, or Partner workspace access.

Do not create fake/demo operational tickets in production for training screenshots.

If production smoke testing requires a record, keep it minimal, clearly labelled as smoke-test evidence, and do not reuse it as normal training material.

## Screenshot status categories

Use these labels while assembling the training pack:

* `Ready from local proof`
* `Needs production retake`
* `Blocked by production onboarding proof`
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

* [x] Outgoing email is configured.
* [x] Production Email Queue processing reaches `Sent` without recipient errors.
* [ ] Controlled test email receipt is confirmed in a real inbox.
* [x] Welcome/setup email is generated and queued successfully.
* [ ] Welcome/setup email receipt is confirmed in a controlled real inbox.
* [x] Generated password setup/reset link uses the public `https://erp.telectro.co.za` URL.
* [ ] Test user can open the public HTTPS setup link successfully.
* [ ] Test user can set password.
* [ ] Test user can log in after setting password.
* [ ] Failed or expired setup-link behaviour is understood.

## Role and workspace access

* [ ] Technician role profile tested.
* [x] Native Helpdesk `HD Agent` identity creation has been proven with a controlled production internal user.
* [x] `HD Agent` identity has been proven independent of HD Team and Assignment Rule membership.
* [x] HD Team membership has been proven to synchronise to the linked native Assignment Rule and enable the rule when the first Team member is added.
* [ ] Coordinator role profile tested.
* [ ] Supervisor role profile tested.
* [ ] Partner role profile tested.
* [ ] Partner organisation exists and is configured deliberately.
* [ ] Partner User has enabled membership in the intended Partner organisation.
* [ ] Partner organisation containment has been tested.
* [ ] Default Dispatch User has been verified where Partner fulfilment dispatch is required.
* [ ] Customer portal user tested.
* [ ] Technician lands on or can access Tech Workspace.
* [ ] Coordinator lands on or can access Coordinator Workspace.
* [ ] Supervisor lands on or can access Ops Workspace.
* [ ] Partner lands on or can access Partner Workspace.
* [ ] Customer lands on or can access Support Requests.
* [ ] Partner cannot access internal Telectro workspaces/reports.
* [ ] Partner cannot access tickets belonging only to an unrelated Partner organisation.
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
* [x] Controlled native Helpdesk round-robin assignment produces matching `_assign` and exactly one open ToDo for the assigned internal user.
* [x] Controlled assigned work appears in `My Current Work` and the assigned internal user can open the ticket.
* [ ] Technician assignment/access smoke test has been repeated using a canonical pilot ticket-intake path.
* [ ] Technician can claim/release/handoff where applicable.
* [ ] Partner can log a Partner-originated request under the correct Partner organisation.
* [ ] Partner acceptance flow works for a Partner-originated / non-Partner-fulfilled ticket where applicable.
* [ ] Partner fulfilment dispatch resolves to the configured Default Dispatch User where applicable.
* [ ] Partner submit work done flow works for a non-Partner-originated / Partner-fulfilled ticket where applicable.
* [ ] Telectro can review Partner acceptance.
* [ ] Telectro can review Partner completed work.
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

For each internal Helpdesk user, complete the operational onboarding layers separately:

1. create or verify the enabled Frappe User;
2. apply and verify the intended Role Profile;
3. establish the native active `HD Agent` identity;
4. verify access to the native Helpdesk agent application and intended role workspace;
5. add deliberate membership to the required HD Team or Teams;
6. verify that Helpdesk synchronises the same user into each linked native Assignment Rule;
7. verify that the Assignment Rule enables when the Team becomes populated;
8. create a controlled ticket through a canonical pilot ticket-intake path;
9. verify routing to the intended Team, matching `_assign`, and exactly one open ToDo;
10. verify that the assigned ticket appears in `My Current Work` and opens successfully for the user.

`HD Agent` identity and HD Team membership are separate onboarding controls. Creating or obtaining an `HD Agent` must not be treated as making the user routable.

The native Helpdesk `/helpdesk` Create Ticket route may be used for isolated Helpdesk mechanism testing, but it is not a canonical pilot ticket-intake path and must not be used as evidence for the normal ERPNext ticket creation form or pilot field-validation behaviour.

## Phase 2 — Partner organisation and user

Onboard Partner organisations and their Users after internal Telectro users can handle Partner-side review queues.

Partner onboarding is organisation-first.

Before inviting a Partner User, confirm:

* the correct Partner organisation exists;
* organisation enablement is deliberate;
* the intended User has the required Partner capability;
* the User has enabled membership in the correct Partner organisation;
* Default Dispatch User is configured when Partner fulfilment dispatch is required;
* tenant containment has been verified.

Do not onboard Partner users until Telectro can:

* request Partner acceptance;
* review Partner acceptance;
* review Partner submitted work;
* send rework back where needed;
* keep Partner access contained by organisation membership.

For controlled production testing, use a dedicated synthetic Partner organisation for Telectro-controlled test identities. Do not add synthetic test Users to real Partner organisations merely to obtain browser or workflow proof.

See `docs/runbooks/partner-operating-model.md` for the canonical Partner organisation, membership, dispatch, and production-test model.

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

These items remain pending until production onboarding acceptance proof is complete.

Already production-proven:

* outgoing Email Account configuration;
* Email Queue / recipient processing to `Sent` without recorded errors;
* Welcome-email generation for synthetic Customer and Partner users;
* generation of the public `https://erp.telectro.co.za/update-password` setup route.

Still pending:

* production admin login proof;
* controlled real-inbox receipt of an onboarding email;
* successful browser opening of the public HTTPS setup link;
* successful password setup by the test user;
* first production role login after password setup;
* failed or expired setup-link behaviour proof;
* production screenshots;
* final Customer/Partner onboarding screenshots.

Until the remaining acceptance checks are proven, the training package can be prepared but should not claim that the complete first-user production onboarding path has been verified.

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
