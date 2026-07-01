# ERPNext / Helpdesk Pilot Welcome Guides

## Purpose

These welcome guides give each pilot party a practical starting point for using the Telectro ERPNext / Helpdesk pilot.

The goal is not to document every technical detail. The goal is to help users understand:

- where they land;
- what they are responsible for;
- what they should look at first;
- which actions they should use;
- which actions they should avoid;
- what a normal workflow looks like.

Screenshots can be added below each relevant section in Obsidian.

---

## How to use this guide

Use this document as a screenshot-enhanced onboarding guide for the pilot.

This guide is for orientation:

- where each role starts;
- which workspace or portal they use;
- what each role is responsible for;
- what a normal workflow looks like;
- which actions users should and should not use.

Detailed step-by-step activity instructions live separately in:

- `docs/user-guides/activity-process-guides.md`

Use the Activity Process Guides for workflows that need more detail than belongs in a Welcome Guide, especially non-obvious processes such as attaching evidence to a ticket before selecting it in a Customer-visible update.

Recommended screenshot style:

- add one screenshot per important screen;
- keep each screenshot close to the step it explains;
- add a short caption below each screenshot;
- avoid documenting internal technical setup unless the user needs it to do their work;
- avoid duplicating detailed activity screenshots that belong in the Activity Process Guides.

Suggested screenshot caption format:

```markdown
> Screenshot: TELECTRO-POC Tech Workspace showing My Current Work.
```

---

# 1. Telectro Internal Welcome Guide

Telectro internal users work in role-specific workspaces.

The pilot currently separates internal operation into three main workspaces:

- `TELECTRO-POC Tech Workspace`
- `TELECTRO-POC Coordinator Workspace`
- `TELECTRO-POC Ops Workspace`

Each workspace has a different purpose. A user may have more than one role, but the workflow should still remain clear: technicians execute work, coordinators keep work moving, and ops/supervisors watch the health of the operation.

---

## 1.1 Technician Guide

### Workspace

`TELECTRO-POC Tech Workspace`

### Main purpose

The Tech Workspace is the day-to-day working area for technicians.

Technicians use it to:

- see work assigned to them;
- see work shared with them;
- open tickets;
- understand the customer request;
- review the fault location;
- add updates;
- hand off work where needed;
- complete or resolve work when appropriate.

### Typical users

Examples:

- Alfa
- Bravo
- Charlie
- other technician-style users

### Basic technician workflow

1. Log in.
2. Land on `TELECTRO-POC Tech Workspace`.
3. Open `My Current Work`.
4. Review tickets assigned to you.
5. Review tickets shared with you.
6. Open the ticket that needs action.
7. Read the customer request.
8. Review the fault location / fault point / equipment context.
9. Decide the next action:
   - work the ticket;
   - add a customer-visible update;
   - add an internal note;
   - hand off to another technician;
   - release the ticket if it was incorrectly assigned;
   - resolve the customer ticket when the work outcome has been confirmed.
10. Keep the ticket updated until it leaves your responsibility.

### Key screens to screenshot

```markdown
> Screenshot: TELECTRO-POC Tech Workspace landing page.
```

```markdown
> Screenshot: My Current Work report showing assigned and shared tickets.
```

```markdown
> Screenshot: Ticket detail page showing customer request and activity.
```

```markdown
> Screenshot: Customer Request context card.
```

```markdown
> Screenshot: Fault Location card showing site, fault point, equipment, and map link.
```

```markdown
> Screenshot: Controlled Handoff / assignment action.
```

```markdown
> Screenshot: Resolve Customer Ticket dialog.
```

### Important technician concepts

#### Assigned to me

These are tickets where you are the current responsible technician.

You should review these first because they represent work that is currently sitting with you.

#### Shared with me

These are tickets where you have visibility or involvement, but may not be the primary owner.

Shared tickets should be reviewed when you are helping, being consulted, or preparing to take over work.

#### Customer Request context

The Customer Request card shows the original customer-facing request.

Use this before acting so you understand what the customer actually reported.

#### Fault Location context

The Fault Location card helps the technician understand where the issue is located.

It may include:

- customer;
- campus;
- fault point;
- category;
- equipment reference;
- map link.

Use this before contacting the customer or travelling to a site.

### Technician do

- Check `My Current Work` regularly.
- Use the ticket detail page as the source of truth.
- Read the customer request before acting.
- Review location and equipment context before acting.
- Add clear customer-visible updates when the customer needs to know progress.
- Add internal notes when the information is useful to Telectro but not appropriate for the customer.
- Use controlled claim, release, and handoff actions.
- Resolve Customer tickets only after Telectro has confirmed the work outcome through the normal direct customer process.

### Technician do not

- Do not bypass the controlled assignment / handoff flow.
- Do not treat Customer tickets as Partner acceptance/rework tickets.
- Do not wait for formal Customer portal sign-off before closure.
- Do not expose internal notes as customer-visible updates.
- Do not create duplicate tickets for the same issue unless there is a clear reason.

### What done looks like for a technician

A technician’s work on a ticket is done when one of the following is true:

- the ticket has been resolved after the work outcome was confirmed;
- the ticket was handed off to the correct next technician;
- the ticket was released because it was incorrectly assigned;
- the ticket was updated with the required information and is waiting on another party.

---

## 1.2 Coordinator Guide

### Workspace

`TELECTRO-POC Coordinator Workspace`

### Main purpose

The Coordinator Workspace is the operational control point.

Coordinators use it to:

- prevent tickets from getting stuck;
- monitor unclaimed work;
- monitor aging work;
- watch first-response risk;
- coordinate handoffs;
- follow up on partner/customer-related actions;
- keep the operational queue moving.

### Typical users

Examples:

- coordinator-technician users;
- weekend coordinator users;
- ad-hoc dispatcher/coordinator role users.

### Basic coordinator workflow

1. Log in.
2. Land on `TELECTRO-POC Coordinator Workspace`.
3. Review the current operational queue.
4. Check for unclaimed tickets.
5. Check for aging or at-risk tickets.
6. Review Customer tickets that need first response.
7. Review Partner acceptance or Partner work completion queues where applicable.
8. Open tickets that need coordination.
9. Decide the next coordination action:
   - prompt a technician;
   - coordinate a handoff;
   - request partner action;
   - follow up on stalled work;
   - escalate to Ops/Supervisor;
   - confirm that the ticket has a clear next owner/action.
10. Repeat through the day to keep the queue healthy.

### Key screens to screenshot

```markdown
> Screenshot: TELECTRO-POC Coordinator Workspace landing page.
```

```markdown
> Screenshot: Active operational queue.
```

```markdown
> Screenshot: Unclaimed or aging tickets view.
```

```markdown
> Screenshot: Customer Ticket Oversight report.
```

```markdown
> Screenshot: Tickets with no first response.
```

```markdown
> Screenshot: Partner Acceptance Review Queue.
```

```markdown
> Screenshot: Partner Work Completion Review Queue.
```

```markdown
> Screenshot: Ticket handoff or share context.
```

### Important coordinator concepts

#### Unclaimed tickets

Unclaimed tickets are operational risk.

The coordinator should make sure they are claimed, assigned, or routed correctly.

#### Aging tickets

Aging tickets may indicate that work is stuck, waiting on someone, or missing a next action.

The coordinator should review these and make sure each ticket has a clear owner and next step.

#### Customer first response

Customer-originated tickets need timely first response.

The coordinator should use Customer Ticket Oversight to identify tickets that have not yet received a customer-visible response.

#### Partner review queues

Partner queues exist to keep partner collaboration contained and reviewable.

The coordinator should help ensure partner acceptance and work completion do not sit unattended.

### Coordinator do

- Review operational queues regularly.
- Keep unclaimed and aging tickets visible.
- Watch for first-response risk.
- Use controlled workflows to move work forward.
- Confirm that every active ticket has a clear next action.
- Escalate to Ops/Supervisor when a ticket is blocked or risky.
- Help technicians by improving clarity and flow.

### Coordinator do not

- Do not become an uncontrolled manual reassignment shortcut.
- Do not bypass claim/release/handoff controls.
- Do not close Customer tickets without the appropriate Telectro-side confirmation.
- Do not expose internal coordination notes to customers unless they are deliberately written as customer-visible updates.
- Do not use Partner workflows for Customer sign-off.

### What done looks like for a coordinator

A coordinator’s work is done when:

- unclaimed work is routed or claimed;
- aging tickets have a clear next action;
- first-response risks are identified and followed up;
- partner review queues are being monitored;
- blocked tickets are escalated;
- active tickets have clear ownership.

---

## 1.3 Ops / Supervisor Guide

### Workspace

`TELECTRO-POC Ops Workspace`

### Main purpose

The Ops Workspace is the supervisor and governance view.

Ops users use it to:

- understand overall ticket health;
- monitor workload;
- identify SLA/first-response risk;
- review aging and at-risk work;
- supervise team performance;
- govern coordinator uplift where applicable;
- understand whether the pilot process is working.

### Typical users

Examples:

- supervisor users;
- ops users;
- management-style pilot users;
- users responsible for monitoring the health of the operation.

### Basic ops workflow

1. Log in.
2. Land on `TELECTRO-POC Ops Workspace`.
3. Review the operational snapshot.
4. Check number cards such as:
   - total active tickets;
   - unassigned tickets;
   - partner queue tickets.
5. Review workload by technician/team.
6. Review aging and at-risk tickets.
7. Review SLA or first-response risk.
8. Review coordinator governance/uplift where applicable.
9. Open reports or tickets that need supervision.
10. Decide whether to:
    - follow up with a coordinator;
    - follow up with a technician;
    - escalate a risk;
    - adjust operating process;
    - review pilot readiness with the team.

### Key screens to screenshot

```markdown
> Screenshot: TELECTRO-POC Ops Workspace landing page.
```

```markdown
> Screenshot: Ops operational snapshot.
```

```markdown
> Screenshot: Total active / unassigned / partner queue number cards.
```

```markdown
> Screenshot: Team Load chart.
```

```markdown
> Screenshot: Aging and at-risk tickets report.
```

```markdown
> Screenshot: First response / SLA risk report.
```

```markdown
> Screenshot: Coordinator governance card or history report.
```

### Important ops concepts

#### Operational snapshot

The snapshot gives a quick view of the current state of the operation.

Use it to understand whether the ticket queue is healthy or needs intervention.

#### Workload visibility

Team and technician workload views help identify imbalance.

Ops users should use this to guide supervision, not to bypass normal assignment controls.

#### Aging and at-risk tickets

These tickets may indicate process failure, unclear ownership, or operational blockage.

Ops should use these reports to prompt action through the coordinator or responsible team.

#### Coordinator governance

Coordinator uplift is a controlled governance function.

Ops should use the governance view to understand who has coordinator capability and when it was granted or removed.

### Ops do

- Review operational health regularly.
- Watch workload and aging trends.
- Use reports to identify risk.
- Escalate blocked or risky work.
- Govern coordinator access where applicable.
- Use the workspace for supervision and pilot process improvement.

### Ops do not

- Do not use the Ops Workspace as the normal technician execution path.
- Do not bypass controlled ticket ownership flows.
- Do not treat reports as a replacement for clear ticket updates.
- Do not assume Customer tickets need formal portal sign-off before closure.
- Do not expose internal governance or supervisory notes to customers.

### What done looks like for Ops

Ops work is done when:

- the current queue health is understood;
- risks have been identified;
- blocked work has been escalated;
- coordinator/technician follow-up is clear;
- pilot process issues have been captured for improvement.

---

# 2. Partner Welcome Guide

## Main purpose

The Partner workflow gives partner users a contained way to interact with Telectro.

Partners can:

- log service requests;
- view their submitted tickets;
- view active partner-related tickets;
- accept partner work when requested;
- submit work done when Partner-side work is complete;
- view archived Partner tickets.

Partner access is intentionally limited. Partner users should not use internal Telectro workspaces, Desk reports, or internal ticket forms.

---

## Partner workspace

Partner users should use:

`TELECTRO-POC Partner Workspace`

---

## Basic partner workflow

1. Log in as a Partner user.
2. Open the Partner Workspace.
3. Use `Log Ticket` to create a new service request for Telectro.
4. Review submitted tickets.
5. Review active tickets.
6. If Telectro requests Partner acceptance, review and accept/reject as appropriate.
7. If work is assigned to the Partner, complete the work outside the system.
8. Use `Submit Work Done` when Partner-side work is complete.
9. Review archived tickets where needed.

---

## Key screens to screenshot

```markdown
> Screenshot: TELECTRO-POC Partner Workspace.
```

```markdown
> Screenshot: Partner Log Ticket page.
```

```markdown
> Screenshot: Partner Submitted tickets.
```

```markdown
> Screenshot: Partner Active tickets.
```

```markdown
> Screenshot: Partner ticket detail page.
```

```markdown
> Screenshot: Partner acceptance action.
```

```markdown
> Screenshot: Submit Work Done action.
```

```markdown
> Screenshot: Partner Archived tickets.
```

---

## Partner do

- Use the Partner Workspace.
- Log clear service requests.
- Provide enough detail for Telectro to understand the request.
- Review active Partner tickets regularly.
- Respond to Partner acceptance requests when asked.
- Submit work done only when the Partner-side work is complete.

---

## Partner do not

- Do not use internal Telectro workspaces.
- Do not use Desk reports.
- Do not use internal HD Ticket forms.
- Do not expect access to Telectro internal notes.
- Do not close Telectro-owned review steps yourself.
- Do not use Customer portal workflows.

---

## What done looks like for a Partner

Partner work is done when:

- a new request has been submitted to Telectro; or
- requested Partner acceptance has been completed; or
- assigned Partner work has been completed and submitted for Telectro review.

---

# 3. Customer Welcome Guide

## Main purpose

The Customer portal gives Boschendal customer users a simple way to:

- log support requests;
- identify the affected service area;
- choose the closest fault point or asset;
- attach photos or evidence;
- view progress;
- add more information when needed.

The Customer portal is not a formal sign-off system. Telectro confirms completion directly with the customer through the normal service process and then closes the ticket from the Telectro side.

---

## Customer portal

Customer users should use:

`Support Requests`

---

## Basic customer workflow

1. Log in as a Customer user.
2. Open `Support Requests`.
3. Select `Log a Support Request`.
4. Choose the relevant service area.
5. Choose the affected fault point or fault asset.
6. Add a short subject.
7. Add a clear description.
8. Attach photos, equipment labels, access notes, or evidence where helpful.
9. Submit the request.
10. Return to the ticket later to view progress or add more information.

---

## Key screens to screenshot

```markdown
> Screenshot: Boschendal Support Requests list.
```

```markdown
> Screenshot: Log a Support Request button.
```

```markdown
> Screenshot: New Support Request page.
```

```markdown
> Screenshot: Fault Point selector.
```

```markdown
> Screenshot: Selected Fault Point details.
```

```markdown
> Screenshot: Ticket detail page.
```

```markdown
> Screenshot: Latest update card.
```

```markdown
> Screenshot: Add information action.
```

---

## Important customer concepts

### Support Requests list

The Support Requests list shows the customer’s logged support requests.

Use it to check status and return to existing requests.

### Log a Support Request

Use this action to create a new support request.

A good request includes:

- the affected service area;
- the closest fault point or asset;
- a clear subject;
- a useful description;
- photos or evidence where helpful.

### Fault Point

The Fault Point helps Telectro understand where the issue is located.

Customers should choose the closest known location. If the exact point is not available, choose the closest recognisable point and explain the exact location in the description.

### Latest update

The Latest update card shows the most recent customer-visible update from the ticket activity.

Customers only see information intended for them. Internal Telectro notes are not shown in the Customer portal.

### Add information

Use `Add information` when more detail needs to be sent to Telectro after the ticket has been created.

Useful examples:

- photos;
- access notes;
- equipment labels;
- corrected location details;
- additional symptoms;
- contact availability.

---

## Customer do

- Choose the closest fault point or asset.
- Use a short, clear subject.
- Add enough detail for Telectro to understand the request.
- Attach photos where useful.
- Use `Add information` instead of logging a duplicate request.
- Check the ticket later for updates.

---

## Customer do not

- Do not log duplicate requests for the same issue unless there is a clear reason.
- Do not use the portal as a formal sign-off process.
- Do not expect to see Telectro internal notes.
- Do not choose a random fault point if a closer known point is available.
- Do not close tickets as part of the normal Customer workflow.

---

## What done looks like for a Customer

Customer portal work is done when:

- the support request has been submitted with enough detail; or
- additional requested information has been added to the ticket; or
- the customer has reviewed the latest visible progress update.

Formal Customer portal sign-off is not required before Telectro closes the ticket.

---

# 4. Shared Pilot Boundaries

These boundaries apply across the pilot.

## Customer tickets

Customer tickets are closed by Telectro after Telectro confirms the work outcome through direct customer interaction.

The Customer portal should show useful progress and resolution information, but it is not a formal approval/rework workflow.

## Partner tickets

Partner workflows are separate from Customer workflows.

Partner users are contained to Partner pages and Partner actions.

Partner users should not access internal Telectro reports or Customer portal workflows.

## Internal Telectro work

Internal Telectro users should use the correct workspace for their role:

- Tech Workspace for execution;
- Coordinator Workspace for flow control;
- Ops Workspace for supervision and governance.

## Assignment and handoff

Controlled claim, release, and handoff actions should be used instead of uncontrolled direct assignment.

This keeps ticket ownership auditable and prevents duplicate or stale assignments.

## Customer-visible vs internal information

Customer-visible updates should be written clearly for the customer.

Internal notes should be used for information that should stay inside Telectro.

Customers should not expect every internal note or operational decision to appear in the Customer portal.

---

# 5. Screenshot Checklist

Use this checklist when enhancing the guide in Obsidian.

## Telectro Tech screenshots

- [ ] TELECTRO-POC Tech Workspace
- [ ] My Current Work
- [ ] Assigned to me
- [ ] Shared with me
- [ ] Ticket detail page
- [ ] Customer Request card
- [ ] Fault Location card
- [ ] Controlled Handoff action
- [ ] Resolve Customer Ticket dialog

## Telectro Coordinator screenshots

- [ ] TELECTRO-POC Coordinator Workspace
- [ ] Operational queue
- [ ] Unclaimed tickets
- [ ] Aging tickets
- [ ] Customer Ticket Oversight
- [ ] First response risk
- [ ] Partner Acceptance Review Queue
- [ ] Partner Work Completion Review Queue

## Telectro Ops screenshots

- [ ] TELECTRO-POC Ops Workspace
- [ ] Operational snapshot
- [ ] Number cards
- [ ] Team Load chart
- [ ] Aging and at-risk report
- [ ] SLA / first response risk report
- [ ] Coordinator governance card
- [ ] Coordinator uplift history

## Partner screenshots

- [ ] TELECTRO-POC Partner Workspace
- [ ] Log Ticket page
- [ ] Submitted tickets
- [ ] Active tickets
- [ ] Partner ticket detail page
- [ ] Partner acceptance action
- [ ] Submit Work Done action
- [ ] Archived tickets

## Customer screenshots

- [ ] Support Requests list
- [ ] Log a Support Request button
- [ ] New Support Request page
- [ ] Fault Point selector
- [ ] Selected Fault Point details
- [ ] Ticket detail page
- [ ] Latest update card
- [ ] Add information action

---

# 6. Suggested one-page quick starts

These can be used later as shorter handouts.

## Technician quick start

1. Open `TELECTRO-POC Tech Workspace`.
2. Open `My Current Work`.
3. Work tickets assigned to you first.
4. Open the ticket and read the Customer Request.
5. Check Fault Location before acting.
6. Add updates or internal notes as needed.
7. Use controlled handoff/release when needed.
8. Resolve only when the work outcome has been confirmed.

## Coordinator quick start

1. Open `TELECTRO-POC Coordinator Workspace`.
2. Check unclaimed and aging tickets.
3. Check Customer first-response risk.
4. Check Partner review queues.
5. Make sure every active ticket has a next action.
6. Escalate blocked or risky work.

## Ops quick start

1. Open `TELECTRO-POC Ops Workspace`.
2. Review operational snapshot.
3. Check workload and at-risk tickets.
4. Review SLA / first-response risk.
5. Review governance where applicable.
6. Follow up through coordinators or responsible teams.

## Partner quick start

1. Open `TELECTRO-POC Partner Workspace`.
2. Log new requests from the Partner page.
3. Review active Partner tickets.
4. Respond to Partner acceptance requests.
5. Submit work done when Partner-side work is complete.

## Customer quick start

1. Open `Support Requests`.
2. Select `Log a Support Request`.
3. Choose service area and fault point.
4. Add subject, description, and photos if useful.
5. Submit the request.
6. Reopen the ticket later to view progress or add information.

