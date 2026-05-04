# Pilot Docs Index

Canonical index for the TELECTRO ERPNext pilot documentation set.

This note exists to keep the documentation set navigable, reduce duplication, and make it clear which document is the canonical source for each topic.

---

## Purpose

Use this index to answer:

- which document should I read first?
- which document is the source of truth for this topic?
- where should new notes be added?
- what should be linked instead of duplicated?

The goal is to keep the doc set:

- current
- navigable
- non-duplicated
- trustworthy

---

## Documentation principles

When updating docs in this pilot:

- prefer **one canonical document per topic**
- link to the canonical document instead of copying whole sections
- keep README high-level and stable
- keep runbooks operational and proof-oriented
- keep exploratory notes out of canonical runbooks unless they are still actively useful
- avoid embedding live secrets or environment-sensitive values in general reference notes

---

## Reading order

If you are re-entering the project after time away, read in this order:

1. **README**
   - repo purpose
   - local setup shape
   - working method
   - container/bench workflow
   - high-level pilot guardrails

2. **Pilot Docs Index** _(this note)_
   - where each topic lives
   - which doc is canonical
   - where to add future material

3. **Bench Verification Playbook**
   - proof discipline
   - source-of-truth order
   - bench/session staleness guardrails

4. Topic-specific runbook(s), depending on the task:
   - **Email Ticket Intake Runbook**
   - **Mail Health Runbook**
   - **Manual Ticket Intake Runbook**
   - **Ticket Assignment Contract**
   - **Ticket Status and Workspace Baseline**

5. **Email Reference**
   - full command/reference note for mail environment, delivery verification, and email-specific diagnostics

---

## Canonical document map

### 1) Repo overview and developer workflow

**Canonical source:** `README.md`

**Use for:**

- what this repo is
- how local setup works
- script entry points
- in-container vs bench vs shell working method
- container-to-host sync discipline
- high-level pilot guardrails

**Do not duplicate elsewhere:**

- full setup instructions
- full script catalog
- general repo purpose text

**Link from elsewhere when needed.**

---

### 2) Proof discipline / verification method

**Canonical source:** `docs/runbooks/bench-verification.md`

**Use for:**

- how to prove current behavior safely
- proof hierarchy
- stale bench / stale browser / stale module guardrails
- inbound proof order
- breadcrumb interpretation basics

**Read this when:**

- results look contradictory
- you are about to trust a proof result
- you are debugging poller/ticket behavior
- you have been away from the project and need to re-anchor on method

**Do not duplicate elsewhere:**

- general proof philosophy
- “fresh bench first” rules
- core source-of-truth ordering

Other docs should assume this method and link back here.

---

### 3) Email environment / mail reference

**Canonical source:** `Email Reference` _(Obsidian / notes)_

**Use for:**

- host vs container mail networking
- mail account inspection commands
- test email delivery commands
- mailbox verification steps
- relevant redacted config references
- email routing signal notes

**Read this when:**

- checking whether mail is landing
- validating mail container state
- looking up shell commands
- writing email-related runbooks

**Do not duplicate elsewhere:**

- raw shell command catalogs
- host/container mail networking explanation
- mailbox inspection cheat-sheet content

Runbooks should link here rather than re-copying environment detail.

---

### 4) Mail health / scheduler + breadcrumb health

**Canonical source:** `docs/runbooks/mail-health.md`

**Use for:**

- whether the pilot mail path is healthy
- scheduler/job/log proof flow
- poller breadcrumb meanings
- separating mail-path health from ticket business outcome
- current preferred proof helpers

**Read this when:**

- checking whether email intake is alive
- the question is “did the poller run?”
- Stage A breadcrumbs seem missing
- a ticket did not appear and you need to know whether it is a mail-path problem or not

**Do not duplicate elsewhere:**

- detailed poller health flow
- scheduler/job log checking steps
- breadcrumb key meaning definitions
- `UNSEEN` / `\SEEN` health implications

---

### 5) Email-created ticket behavior

**Canonical source:** `docs/runbooks/email-ticket-intake.md`

**Use for:**

- current pilot contract for email-created `HD Ticket`
- mailbox-driven routing seed
- intake enrichment expectations
- assignment-after-insert behavior for inbound mail
- known operational truths for email intake

**Read this when:**

- validating an email-created ticket
- checking mailbox-to-area or area-to-team outcomes
- checking whether assignment behavior matches the email path contract
- deciding whether an issue is enrichment, routing, or assignment

**Do not duplicate elsewhere:**

- email intake flow contract
- mailbox mapping contract
- email-created ticket examples
- email-path assignment expectations

Link to:

- **Mail Health Runbook** for health proof
- **Email Reference** for environment commands
- **Bench Verification Playbook** for proof method

---

### 6) Manual ticket behavior

**Canonical source:** `docs/runbooks/manual-ticket-intake.md`

**Use for:**

- current contract for manually created tickets
- default field values
- ticket type UX behavior
- manual routing seed behavior
- current first-capture boundary

**Read this when:**

- validating manual ticket creation
- checking service-area/manual routing behavior
- checking default save behavior
- comparing future manual-capture changes against the current baseline

**Do not duplicate elsewhere:**

- manual ticket default matrix
- field/UX behavior details
- manual routing examples
- first-capture scope/boundary wording

**Important note:**
This runbook describes **current pilot behavior**. It should not be used as the place to settle still-open Service Area business semantics prematurely.

---

### 7) Assignment model / ownership contract

**Canonical source:** `docs/runbooks/ticket-assignment-contract.md`

**Use for:**

**Use for:**

- current app-owned assignment model
- routing -> assignment -> sync flow
- round-robin groups
- true pool fallback
- partner override
- `ToDo` vs `_assign` source-of-truth model
- claim/handoff restrictions
- true pool vs owned-ticket assignment invariant
- Controlled Handoff audit behaviour
- `TELECTRO Assignment Handoff Log`
- `TELECTRO Assignment Handoff Audit`

**Read this when:**

- checking assignment outcomes
- investigating `_assign` / `ToDo` drift
- verifying whether routing seeded the right ownership path
- explaining why Assignment Rules are not the live runtime mechanism

**Do not duplicate elsewhere:**

- assignment architecture explanation
- round-robin / pool / partner logic
- `_assign` vs `ToDo` truth model
- claim/handoff contract

Other docs should reference this rather than restating assignment theory.

---

### 8) Ticket status baseline / workspace baseline

**Canonical source:** `docs/runbooks/ticket-status-and-workspace-baseline.md`

**Use for:**

- operational trust boundary date
- `Resolved` vs `Archived`
- workspace baseline intent
- reporting exclusion rule for `Archived`
- rationale for the post-cleanup status model

**Read this when:**

- interpreting older pilot tickets
- deciding whether old records are valid proof anchors
- updating reports/workspaces
- explaining why archived residue is not normal operational history

**Do not duplicate elsewhere:**

- trust boundary explanation
- archive/reporting rules
- workspace baseline rationale

---

### 9) Supervisor monitoring and intervention model

**Canonical source:** `docs/runbooks/supervisor-operating-model.md`

**Use for:**

- understanding the intended working model for the pilot
- understanding the supervisor’s operational shell and reports
- understanding the supervisor’s use of Controlled Handoff
- understanding where the handoff audit report fits in the supervisor/coordinator workflow

**Read this when:**

- you are a supervisor or technician trying to understand how work is intended to flow
- you are trying to understand the supervisor’s role in monitoring and intervening in the queue
- you are trying to understand the intended use of the supervisor reports

**Do not duplicate elsewhere:**

- supervisor monitoring model
- supervisor report intent

---

### If the question is

**“How do I prove this safely?”**  
Read: **Bench Verification Playbook**

**“Is the mail path healthy?”**  
Read: **Mail Health Runbook**

**“How should an email-created ticket behave?”**  
Read: **Email Ticket Intake Runbook**

**“How should a manual ticket behave?”**  
Read: **Manual Ticket Intake Runbook**

**“Why did this ticket assign this way?”**  
Read: **Ticket Assignment Contract**

**“Why is this old ticket not trustworthy?”**  
Read: **Ticket Status and Workspace Baseline**

**“What are the actual mail commands / container checks again?”**  
Read: **Email Reference**

**“How do I stand this repo up and work in it?”**  
Read: **README.md**

**“How should a supervisor monitor and intervene?”**  
Read: **Supervisor Operating Model**

**"How to understand the SLA timing signals?"**
Read: **SLA and Supervisor Risk Signals**

---

## Suggested folder / note roles

### Repo docs (`docs/runbooks/`)

Use for:

- stable operational runbooks
- repo-backed current contracts
- proof and workflow notes tied to live pilot behavior

### Obsidian notes

Use for:

- fuller reference notes
- working notes that may later be promoted into runbooks
- planning notes
- decision support
- stakeholder-facing drafts

### README

Use for:

- repo entry point
- stable developer overview
- high-level workflow
- links into the canonical runbooks

---

## What should not be duplicated

Try not to repeat these in multiple places:

- full mail-shell command sets
- proof philosophy / staleness rules
- assignment model theory
- mailbox-to-routing contract
- `ToDo` vs `_assign` source-of-truth explanation
- archive/trust-boundary rationale

Each of those now has a natural canonical home.

---

## When creating a new document

Before adding a new doc, ask:

1. Is this a new topic, or does it belong inside an existing canonical doc?
2. Is this stable enough to be a runbook, or still a working note?
3. Am I adding new truth, or duplicating existing truth?
4. Should this live in the repo, or in Obsidian first?
5. Can this be a short note that links back to a canonical source?

### Good reasons for a new runbook

- a new operational workflow exists
- a stable new proof flow has been established
- a topic has become too large for its current parent doc
- the same question keeps reappearing during debugging or handover

### Bad reasons for a new runbook

- copying a section because it is convenient
- freezing still-unsettled business meaning too early
- creating a second “summary” of a topic that already has a canonical home

---

## Candidate future docs

These would be reasonable additions later if the need persists:

- **Developer Workflow Note**
  - focused day-to-day coding/proof/export cycle
- **Fixtures and Export Discipline**
  - when to export, when not to, sync rules
- **Field Model / Classification Decision Note**
  - only once Service Area semantics are actually decided
- **Architecture / Container Map**
  - if onboarding or handover needs this often
- **Common Verification Commands**
  - only if it adds value beyond the existing Email Reference and runbooks

---

## Maintenance rule

When a topic changes:

1. update the **canonical source first**
2. update this index only if:
   - the canonical source changed name/path
   - the topic moved
   - the reading order changed
   - a new canonical document was added

This index should stay light and navigational, not become another duplicated reference note.

---

## Current doc set summary

At the moment, the doc set has a good emerging split:

- **README** = repo entry point
- **Bench Verification Playbook** = proof method
- **Email Reference** = command/reference note
- **Mail Health Runbook** = mail-path health
- **Email Ticket Intake Runbook** = inbound email contract
- **Manual Ticket Intake Runbook** = manual capture contract
- **Ticket Assignment Contract** = ownership model, true-pool invariant, Controlled Handoff, and handoff audit trail
- **Ticket Status and Workspace Baseline** = operational trust boundary and archive policy
- **Supervisor Operating Model** = supervisor monitoring, intervention model, and handoff audit usage
- **SLA and Supervisor Risk Signals** = where Helpdesk SLA timing is configured, how `response_by` / `resolution_by` are derived, and how supervisor risk signals should interpret those fields

That is a healthy baseline for the pilot.

---

## Note

This index is not the source of truth for any individual topic.

Its job is to point to the source of truth and reduce drift.

- only if it adds value beyond the existing Email Reference and runbooks

---
