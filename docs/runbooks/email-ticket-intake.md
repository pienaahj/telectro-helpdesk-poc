# Email Ticket Intake Runbook (Pilot)

Goal: document the current intended behavior for email-created `HD Ticket` records in the pilot, so inbound intake remains understandable, provable, and reproducible.

## Purpose

This runbook describes the **current pilot contract** for inbound email ticket creation.

It reflects the behavior that has been recently proven from:

- scheduler/poller execution,
- `Communication` creation,
- ticket enrichment,
- routing seed behavior,
- and post-insert assignment outcome.

It is intentionally practical and describes the system as it works now, not a future idealized intake workflow.

## High-level flow

The current inbound email path is:

1. pilot poller runs
2. mail is fetched from configured inboxes
3. eligible mail becomes a `Communication`
4. linked `HD Ticket` is created or updated
5. intake enrichment runs
6. routing seed logic runs
7. post-insert assignment logic runs
8. `_assign` and `ToDo` state are normalized

## Current proof anchors

When proving inbound email behavior, use this order:

1. poller health
2. `Communication`
3. linked `HD Ticket`
4. `_assign`
5. open `ToDo`
6. Stage A breadcrumbs where relevant

### Why this order matters

`Communication` is currently the safest authoritative proof anchor for inbound mail.

It is more reliable than:

- stale browser state
- guessed ticket IDs
- inferred assignment outcomes without linkage proof

## Poller health contract

The pilot poller is repo-backed and exposed through:

- `telephony.jobs.pull_pilot_inboxes.run`

Current health checks and proofs are supported by:

- `telephony.scripts.job_status_pull_pilot_inboxes`
- `telephony.scripts.proof_pull_pilot_inboxes`

### Current health semantics

- `last_ok`
  - last successful completed run

- `last_err`
  - fatal run failure only

- `last_nonfatal_err`
  - degraded-but-completed inner-loop failure

- `per_account`
  - latest run snapshot

- `last_per_account_nonzero`
  - last meaningful non-idle run snapshot

## Mailbox / inbox contract

The pilot currently uses mailbox-driven email intake.

Examples already proven include:

- `Routing`
- `PABX`

### Mailbox meaning

For inbound email:

- the mailbox is carried on `email_account`
- mailbox value is used for routing seed
- mailbox-driven routing happens before post-insert assignment

## Email-created ticket enrichment

Email-specific enrichment is handled separately from routing.

The intake enrichment path is responsible for things such as:

- setting request source
- mapping sender to customer
- defaulting campus/site where available
- parsing selected email/body-derived context where currently supported
- handling bounce/system/noise paths separately

### Important current field truth

For the pilot, the effective inbound customer field is:

- `custom_customer`

The standard `customer` field is currently **not** the active pilot customer field on this intake path.

### Current campus/site truth

The current campus/site field in active pilot use is:

- `custom_site_group`

## Current routing seed behavior for email

Routing seed logic is now app-owned and repo-backed.

For email-created tickets:

- mailbox wins for service area seed
- service area then seeds team/group

### Current mailbox-to-area mapping

Current mapping includes:

- `PABX` -> `PABX`
- `Routing` -> `Routing`
- `SIM` -> `SIM`
- `Fiber` -> `Fiber`
- `Faults` -> `Faults`

If no explicit mailbox mapping exists, the current fallback is:

- `custom_service_area = Other`

### Current area-to-team mapping

Current mapping includes:

- `Routing` -> `Routing`
- `PABX` -> `PABX`

If no explicit area-to-team mapping exists, the current fallback is:

- `agent_group = Helpdesk Team`

### Important design note

For email-created tickets, mailbox input is authoritative for routing seed.

That differs from the manual path, where:

- user-selected service area is preserved,
- and defaults are only applied when missing.

## Post-insert assignment contract

After insert, assignment is handled by app code.

Current assignment behavior includes:

- round-robin assignment for known configured groups
- pool-user fallback for non-round-robin groups
- partner override handling
- `_assign` and open `ToDo` normalization

### Current assignment owner

The current assignment engine is app-owned.

It is not currently driven by enabled Assignment Rules.

### Important pilot truth

Assignment Rules currently exist in the environment as historical/dormant config, but they are **not** the live active assignment mechanism for the current pilot path.

## Current assignment examples

### Example A — inbound `PABX`

A proven inbound `PABX` ticket currently lands with:

- `email_account = PABX`
- `custom_service_area = PABX`
- `agent_group = PABX`
- `_assign = ["tech.charlie@local.test"]`
- exactly one open `ToDo` for Charlie

### Example B — inbound `Routing`

A proven inbound `Routing` ticket currently lands with:

- `email_account = Routing`
- `custom_service_area = Routing`
- `agent_group = Routing`
- `_assign = ["tech.alfa@local.test"]`
- exactly one open `ToDo` for Alfa

These examples show the current expected pattern:

- mailbox drives routing seed
- routing seed drives assignment path
- canonical `_assign` / `ToDo` state is preserved

## Noise blocking and dedupe boundaries

The poller currently includes low-risk intake protection for:

- blocked/noise messages by metadata
- identity-based dedupe

### Important dedupe boundary

Current dedupe is:

- message identity / re-ingest protection

It is **not**:

- business-level duplicate suppression
- semantic duplicate detection

That broader behavior is intentionally out of scope for the pilot.

## IMAP `UNSEEN` behavior

This was recently re-proven and matters operationally.

For IMAP with sync option `UNSEEN`:

- messages are marked `\SEEN` at fetch time in the Frappe receive pipeline

### Operational implication

This means the email path behaves more like:

- consume-on-fetch

and less like:

- only-consume-on-successful-business-processing

### Why this matters

Blocked, skipped, or errored messages may not naturally reappear just because the business outcome was incomplete.

That is why:

- breadcrumbs,
- `Communication`,
- and explicit proof flow

matter more than assuming the inbox itself will retry by remaining unseen.

## Current minimum inbound contract

A valid inbound ticket currently aims to preserve enough information to:

- identify the source mailbox
- preserve the sender context
- link the inbound mail to a `Communication`
- create/update the linked `HD Ticket`
- seed routing
- assign predictably

It does **not** require all possible downstream technical detail to be known at intake time.

## What is intentionally deferred

The pilot currently does **not** require every inbound email to fully determine:

- final equipment-level pinpointing
- exact downstream fault anchor
- semantic duplicate collapse
- full customer self-service completion flow

Some of these remain future possibilities, but are intentionally not forced into the current pilot intake contract.

## Current customer/site direction

There is an important strategic distinction in the pilot:

- current backend email enrichment can populate customer/site context where available
- but the longer-term intent is not to overfit body parsing for everything
- customer/site confirmation and refinement may increasingly be driven through controlled follow-up flows, such as autoreply / customer link workflows

That means current body-derived behavior should be treated as useful pilot enrichment, not the final architecture.

## Current pilot boundary

The current email intake design optimizes for:

- reproducible poller behavior
- clear proof points
- predictable mailbox-driven routing
- deterministic post-insert assignment
- low-risk noise blocking
- minimum viable intake context

It does **not** yet try to solve every future workflow problem at intake time.

## Current repo-backed components supporting this contract

This contract is now supported by repo-backed code and docs including:

- poller job registration
- poller health proof helpers
- routing seed app code
- assignment-after-insert app code
- mail-health runbook
- bench verification runbook
- manual ticket intake runbook

## Known operational truths to carry forward

- `custom_customer` is the effective inbound customer field for pilot intake
- `custom_site_group` is the current campus/site field in use
- `Communication` is the safest authoritative proof point for inbound mail
- mailbox drives routing seed for email-created tickets
- assignment is currently app-owned, not Assignment Rule-owned
- IMAP `UNSEEN` behaves as consume-on-fetch in the framework receive pipeline
- current dedupe is identity-based only

## When to revisit this runbook

Revisit this runbook if any of the following change:

- mailbox-to-service-area mapping
- area-to-team mapping
- poller health semantics
- intake enrichment logic
- customer/site confirmation flow
- assignment-after-insert behavior
- dedupe policy
- IMAP receive behavior assumptions
- pilot decision to enforce deeper detail at inbound creation time

