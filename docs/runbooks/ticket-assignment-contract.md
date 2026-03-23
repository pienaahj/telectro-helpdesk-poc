# Ticket Assignment Contract (Pilot)

Goal: document the current intended assignment behavior for pilot `HD Ticket` records, so routing and ownership outcomes remain understandable, provable, and reproducible.

This runbook describes the **current pilot assignment contract**. It reflects the system as it works now, not a future idealized assignment architecture.

Use this runbook when:

- validating assignment outcomes
- explaining current pilot ownership behavior
- proving whether a ticket followed the intended routing / assignment path
- checking drift between routing, `ToDo`, and `_assign`

---

## Purpose

This runbook reflects behavior recently proven from:

- routing seed logic
- post-insert assignment behavior
- `_assign` / `ToDo` synchronization
- repair tooling
- real ticket outcomes from both email and manual intake paths

The assignment model is intentionally practical and bounded.

---

## High-level assignment model

The pilot currently uses an **app-owned assignment model**.

Assignment is not primarily driven by active Assignment Rules.

The current working path is:

1. ticket is created
2. routing/team context is seeded
3. post-insert assignment logic runs
4. open `ToDo` and `_assign` state are normalized
5. user-facing claim/handoff operates on top of that normalized state

---

## Current source of truth in code

The current assignment contract is split across these live components.

### Routing seed

- `telephony.telectro_ticket_routing.seed_ticket_routing`

Seeds routing/team context before assignment runs.

### Initial assignment

- `telephony.telectro_round_robin.assign_after_insert`

Handles the first ownership decision after insert.

### Assignment synchronization / hygiene

- `telephony.telectro_assign_sync.dedupe_assign_field`
- `telephony.telectro_assign_sync.sync_ticket_assignments`

Keep `_assign` and open `ToDo` state consistent and collapse drift.

### Assign UI / API guardrails

- `telephony.overrides.assign_to.*`

Enforce pilot-safe assignment behavior and block direct assign/unassign for pilot tech users.

---

## Important current truth

The live assignment mechanism is **app-owned**.

Existing Assignment Rules in the environment are currently historical or dormant config and are **not** the primary active runtime assignment path.

---

## Assignment phases

### 1) Routing/team context is seeded first

Before assignment runs, the ticket must have enough routing context to determine which assignment path applies.

Examples:

- email-created ticket from `PABX` mailbox -> `agent_group = PABX`
- manual ticket with `custom_service_area = PABX` -> `agent_group = PABX`
- blank/manual fallback path -> `agent_group = Helpdesk Team`

Assignment only becomes predictable once this routing seed step has happened.

### 2) Post-insert assignment decides the initial owner/path

After insert, `assign_after_insert()` determines what to do based on:

- `agent_group`
- `custom_fulfilment_party`
- existing open `ToDo`
- existing `_assign`

### 3) Synchronization makes the state canonical

After insert/update, assignment sync logic ensures:

- duplicate assignees are removed
- duplicate open `ToDo` rows are collapsed
- `_assign` mirrors canonical open `ToDo` state

---

## Current assignment paths

### Round-robin groups

The current app-owned round-robin pools are:

- `Routing`
  - `tech.alfa@local.test`
  - `tech.bravo@local.test`

- `PABX`
  - `tech.charlie@local.test`

- `SIM`
  - `tech.bravo@local.test`

These groups are treated as round-robin groups by `assign_after_insert()`.

#### Round-robin behavior

For a round-robin group:

- the group-specific cursor is read from cache
- the next assignee is selected
- the cursor advances
- exactly one open `ToDo` is ensured for the chosen user
- `_assign` is mirrored from the resulting open `ToDo`

Round-robin assignment is app-owned and cache-backed. It is not currently driven by active Assignment Rule execution.

---

### Pool-user fallback groups

For groups that are **not** in the round-robin pool map:

- no RR user is chosen
- the ticket is seeded to the pool path instead

Current pool user:

- `helpdesk@local.test`

#### Pool fallback behavior

If the ticket:

- has no open `ToDo`
- and `_assign` is empty

then pool fallback creates exactly one open `ToDo` for the pool user and mirrors `_assign` from that `ToDo`.

This is the safe default / unclaimed path.

---

### Partner override

There is a special override path for tickets where:

- `custom_fulfilment_party = "Partner"`

In that case:

- round-robin and normal pool seeding are bypassed
- the ticket is seeded to the partner-user path if it is still effectively unassigned

Current partner user constant:

- `partner@local.test`

This prevents partner-fulfilment tickets from being silently pulled into the normal internal RR/pool flow.

---

## Canonical truth model

The pilot currently treats **open `ToDo` state as canonical**.

That means:

- open `ToDo` rows are the most authoritative assignment state
- `_assign` mirrors open `ToDo` assignees
- sync/repair logic restores `_assign` from canonical open `ToDo` state where needed

### Why this matters

This avoids relying on stale or drifted `_assign` alone.

It also keeps:

- post-insert assignment
- claim/handoff behavior
- repair scripts

anchored to the same practical ownership model.

---

## `_assign` behavior and drift handling

`_assign` is still important, but it is treated as a mirrored representation of canonical assignment state rather than the sole source of truth.

### Current rules

- `_assign` should reflect open `ToDo` assignees
- duplicate users should not be present
- canonical ordering should be preserved where relevant
- drift between `_assign` and `ToDo` should be repaired, not ignored

### Current hygiene behavior

#### De-dupe on validate

During validate:

- duplicate users are removed from `_assign`

#### Sync on update

On update:

- multiple open `ToDo` rows are collapsed
- `_assign` is mirrored from canonical open `ToDo` state
- missing `ToDo` can be recreated from `_assign` when appropriate

#### Repair tooling exists

Repo-backed repair tooling exists to:

- scan recent tickets
- detect drift
- recreate missing `ToDo`
- collapse duplicates
- mirror `_assign` back into a consistent state

---

## User-facing assignment contract

For pilot tech users, direct Assign/Unassign is intentionally restricted.

### Current rule

Users with the pilot tech role should use:

- Claim
- Handoff

rather than generic Assign/Unassign actions.

### Why

This protects the pilot workflow from:

- accidental direct ownership churn
- bypassing the intended queue/pool flow
- UI actions that create inconsistent assignment artifacts

### Assign override guard

The current assign override blocks direct assign/unassign operations for:

- `TELECTRO-POC Tech`

while leaving admin/system-level operations available where appropriate.

This is intentional and part of the pilot safety model.

---

## Verified current examples

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

### Example C — manual `PABX`

A proven manual `PABX` ticket currently lands with:

- `email_account = None`
- `custom_service_area = PABX`
- `agent_group = PABX`
- `_assign = ["tech.charlie@local.test"]`
- exactly one open `ToDo` for Charlie

### Example D — fallback/manual unclaimed path

If the ticket lands in a non-round-robin/default path:

- pool fallback seeds the pool user
- `_assign` mirrors the pool `ToDo`

This is the intended safe fallback / unclaimed path.

---

## Current boundaries

The current pilot assignment contract is intentionally bounded.

It does **not** currently try to provide:

- semantic/business-level duplicate suppression
- Assignment-Rule-driven runtime ownership as the primary live source
- complex multi-owner assignment semantics
- highly dynamic workload balancing beyond the current RR/pool model

---

## Important operational truths

- assignment is currently app-owned
- routing seed must happen before assignment is expected to behave predictably
- open `ToDo` state is canonical
- `_assign` mirrors canonical open `ToDo` state
- pool fallback is the safe default for non-RR groups
- partner fulfilment is explicitly overridden
- pilot tech direct assign/unassign is intentionally blocked
- disabled Assignment Rules are not the live runtime mechanism

---

## Proof order for assignment issues

When proving or debugging assignment behavior, use this order:

1. confirm routing seed fields
   - `email_account`
   - `custom_service_area`
   - `agent_group`

2. confirm ticket creation path
   - email vs manual

3. inspect open `ToDo`
   - count
   - assignee(s)
   - status

4. inspect `_assign`

5. inspect post-insert assignment expectations
   - RR group?
   - pool fallback?
   - partner override?

6. use repair/proof tooling if drift is suspected

### Why this order matters

It prevents misleading conclusions based on `_assign` alone or on stale UI assumptions.

The most reliable operational ownership proof is:

- routing context
- then open `ToDo`
- then mirrored `_assign`

---

## Current repo-backed helpers/tools relevant to this contract

The assignment contract is currently supported by repo-backed code and helpers including:

- routing seed app code
- round-robin / pool assignment app code
- assignment sync logic
- assign override guard
- assignment proof helper
- assignment repair helper
- manual ticket intake runbook
- email ticket intake runbook
- bench verification runbook

### Related

- `docs/runbooks/ticket-status-and-workspace-baseline.md`

---

## When to revisit this runbook

Revisit this runbook if any of the following change:

- round-robin pools
- pool user
- partner user
- routing seed mappings
- `_assign` / `ToDo` source-of-truth model
- claim/handoff UX rules
- assignment override restrictions
- decision to re-activate or rely on Assignment Rules
- pilot move toward more complex ownership/dispatch models
