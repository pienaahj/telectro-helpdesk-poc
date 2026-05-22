# Customer Intake Codex Brief

## Purpose

This brief prepares the minimum Customer Web Intake slice for a controlled Codex-assisted implementation.

The customer intake slice is not a broad customer portal. It is a small operational entry point that allows a customer/contact to submit a structured issue or request without relying on phone, WhatsApp, or an initial email.

The intended value is to collect enough structured information upfront so that Telectro can create or receive a useful ticket with better context than an unstructured first contact normally provides.

## Current status

Status:

```text
Prepared for Codex planning.
Not implemented yet.
Not promised as complete for production.
```

This slice should be treated as a near-term deployment-readiness gap if Telectro expects customer-side ticket creation during first operational use.

## Business goal

Provide one controlled customer-facing intake path that can:

- capture a new issue/request from a customer or contact
- collect structured context required by Telectro
- avoid reliance on phone, WhatsApp, or initial email for first contact
- create or feed into the current pilot ticket/intake path
- keep internal routing, assignment, Partner containment, and evidence handling safe

## Minimum viable slice

In scope for the first implementation:

- one customer-facing entry page
- one structured intake form
- sensible required-field validation
- one controlled backend submission path
- creation of the intended ticket or intake record
- clear success message
- understandable failure message
- documentation of assumptions and smoke-test steps

Possible form fields:

```text
Contact name
Contact email
Contact phone
Customer / organisation
Site / campus / location
Service area or issue category
Issue/request summary
Issue/request details
Urgency or severity indicator, if already supported
Optional evidence/photo/file attachment, only if it can reuse the existing private evidence model safely
```

The final field list should be confirmed during planning before implementation.

## Explicit non-goals

The first slice must not attempt to build a full portal.

Out of scope:

- customer account management
- customer ticket history
- customer self-service dashboard
- SLA promises or SLA calculations
- WhatsApp/media intake automation
- incoming email replacement
- broad website redesign
- public knowledge base
- automatic Service Coverage routing changes
- automatic reassignment logic
- broad notification/email tuning
- bulk user/customer import
- changes to Partner containment rules
- changes to existing internal ticket ownership semantics

## Safety and architecture constraints

The implementation must:

- reuse existing project patterns where possible
- stay inside the `telephony` app conventions
- avoid broad refactors
- avoid changing assignment/routing behaviour
- avoid creating ToDos unless an existing proven ticket creation path already does so intentionally
- avoid writing `_assign` directly unless reusing a current accepted helper path
- preserve private-file/evidence assumptions
- avoid exposing raw private file URLs
- avoid exposing internal Desk/HD Ticket surfaces to unauthorised external users
- list unresolved business assumptions instead of silently deciding them

## Recommended Codex process

Use two Codex passes.

### Pass 1: planning only

Codex should inspect the repo and propose an implementation plan.

No files should be edited in this pass.

### Pass 2: implementation

Only after the plan has been reviewed manually should Codex implement the narrow approved slice.

The implementation pass must stay within the reviewed plan unless it stops and explains why the plan needs to change.

## Codex planning prompt

Use the following prompt for the first Codex pass.

```text
You are working in the ERPNext/Frappe/Helpdesk pilot repo for Telectro.

Task: planning only. Do not edit files.

Goal:
Plan the smallest viable Customer Web Intake slice. The purpose is to let a customer/contact submit a structured issue/request without relying on phone, WhatsApp, or initial email, and to collect the minimum information needed to create a useful HD Ticket or intake record.

Context:
This repo contains a custom Frappe app called telephony. The pilot already has internal workspaces, Partner-safe pages, Partner workflows, ticket evidence upload/list/download, Service Coverage visibility, and Helpdesk ticket workflows. The customer intake slice must fit into those existing patterns.

Constraints:
- Inspect the existing repo before proposing changes.
- Reuse existing Frappe/Helpdesk/telephony app patterns.
- Keep the slice narrow and reversible.
- Do not design a full customer portal.
- Do not invent unresolved business semantics.
- Do not change assignment/routing behaviour.
- Do not bypass Partner/customer containment rules.
- Prefer one page, one form, one controlled creation path.
- Preserve private evidence/file handling assumptions.
- List assumptions instead of silently deciding them.
- Do not make code changes in this planning pass.

Please produce:
1. Existing files/patterns inspected.
2. Recommended implementation approach.
3. Proposed files to touch/create.
4. Data fields required on the form.
5. Record creation path recommendation.
6. Permission/security considerations.
7. Smoke-test steps.
8. Risks and unresolved questions.
9. Explicit non-goals.
10. Confirmation that no code changes were made.
```

## Codex implementation prompt template

Use this only after the planning pass has been reviewed.

```text
You are working in the ERPNext/Frappe/Helpdesk pilot repo for Telectro.

Task: implement only the approved minimum Customer Web Intake slice from the reviewed plan.

Approved boundary:
- one customer-facing entry page
- one structured intake form
- one controlled backend submission path
- create the intended ticket or intake record
- clear success/failure messages
- no full portal
- no routing/assignment rewrite
- no unrelated refactors

Requirements:
- Reuse existing repo patterns.
- Keep changes narrow and reversible.
- Preserve Partner/internal containment.
- Preserve private evidence assumptions.
- Do not expose raw private file URLs.
- Add or update only the documentation needed for this slice.
- Provide a file list and test steps.

Before finishing, report:
1. Files changed.
2. What was implemented.
3. How to test it.
4. Expected created record shape.
5. Assumptions made.
6. Follow-up items deliberately left out.
```

## Acceptance criteria

A successful minimum implementation must satisfy:

- customer intake page renders
- form validates required fields sensibly
- submission creates the intended HD Ticket or intake record
- created record contains contact/customer/location/service-area context
- success message is clear
- failure state is understandable
- internal users can find the created record through expected operational reports or ticket lists
- no Partner route containment regression
- no internal Desk/HD Ticket exposure to unauthorised external users
- no routing or assignment rewrite
- no broad workspace/report refactor
- documentation includes assumptions and smoke-test steps

## Review checklist for Codex output

Evaluate Codex output before committing.

### Boundary discipline

Check for:

- no broad refactors
- no unrelated cleanup
- no invented portal architecture
- no surprise routing/assignment changes
- no unrelated fixture drift

### Reuse of existing patterns

Check whether it reused:

- existing page patterns
- existing whitelisted method style
- existing ticket creation helpers where appropriate
- existing evidence/private file handling where appropriate
- existing role/permission conventions

### Operational fit

Confirm:

- submitted records are usable by Telectro
- required context is captured
- internal users can find the result
- the implementation does not assume a dispatcher model unless explicitly approved
- Service Coverage remains visibility/reporting only unless separately approved

### Testability

Confirm there is a short smoke path:

- open page
- submit valid form
- verify created record
- verify internal visibility
- test missing required fields
- test unauthorised access assumptions

### Documentation

Confirm the implementation records:

- assumptions
- non-goals
- changed files
- test steps
- follow-up items

## Suggested smoke-test path

After implementation, run a controlled smoke test.

Suggested subject:

```text
CUSTOMER INTAKE SMOKE TEST - structured web form
```

Minimum checks:

1. Open the customer intake page.
2. Submit with missing required fields and confirm validation.
3. Submit a valid test request.
4. Confirm success message.
5. Confirm HD Ticket or intake record was created.
6. Confirm contact/customer/location/service-area fields landed correctly.
7. Confirm internal user can find the created record.
8. Confirm expected workspace/report visibility.
9. Confirm no inappropriate raw Desk access is exposed.
10. If evidence upload is included, confirm private-file handling uses the controlled model.

## Deployment-readiness note

If Telectro expects customers or Boschendal contacts to submit requests directly during first operational use, this slice should be implemented and smoke-tested before go-live.

If Telectro does not require customer-side ticket creation during first operational use, this slice can be deferred without blocking the first technical deployment, provided the deferral is recorded.

## Current recommended stance

Treat Customer Web Intake as:

```text
Important near-term pilot slice.
Codex-suitable if tightly bounded.
Not part of the already-proven production deployment foundation.
Not a blocker for technical deployment unless Telectro requires customer-side submission at launch.
```
