# Ticket Assignment Contract (Pilot)

Goal: document the current intended assignment behavior for pilot `HD Ticket` records, so routing and ownership outcomes remain understandable, provable, and reproducible.

## Purpose

This runbook describes the **current pilot assignment contract**.

It reflects the behavior that has been recently proven from:

- routing seed logic,
- post-insert assignment behavior,
- `_assign` / `ToDo` synchronization,
- repair tooling,
- and real ticket outcomes from both email and manual intake paths.

It is intentionally practical and describes the system as it works now, not a future idealized assignment architecture.

## High-level assignment model

The pilot currently uses an **app-owned assignment model**.

Assignment is not primarily driven by active Assignment Rules.

The current working path is:

1. ticket is created
2. routing/team context is seeded
3. post-insert assignment logic runs
4. `_assign` and `ToDo` state are normalized
5. user-facing claim/handoff flow operates on top of that

## Current source of truth

The current assignment contract is split across these live components:

### Routing seed

- `telephony.telectro_ticket_routing.seed_ticket_routing`

This seeds routing/team context before assignment runs.

### Initial assignment

- `telephony.telectro_round_robin.assign_after_insert`

This handles the first ownership decision after insert.

### Assignment synchronization / hygiene

- `telephony.telectro_assign_sync.dedupe_assign_field`
- `telephony.telectro_assign_sync.sync_ticket_assignments`

These keep `_assign` and open `ToDo` state consistent and collapse assignment drift.

### Assign UI / API guardrails

- `telephony.overrides.assign_to.*`

These enforce pilot-safe assign behavior and block direct assign/unassign for pilot tech users.

## Important current truth

The current live assignment mechanism is **app-owned**.

Existing Assignment Rules in the environment are currently historical / dormant config and are **not** the primary active runtime assignment path.

## Assignment phases

## 1) Routing/team context is seeded first

Before assignment runs, the ticket must have enough routing context to determine which assignment path applies.

Examples:

- email-created ticket from `PABX` mailbox -> `agent_group = PABX`
- manual ticket with `custom_service_area = PABX` -> `agent_group = PABX`
- blank/manual fallback path -> `agent_group = Helpdesk Team`

Assignment only becomes predictable when this routing seed step has already happened.

## 2) Post-insert assignment decides the initial owner/path

After insert, `assign_after_insert()` determines what to do based on:

- `agent_group`
- `custom_fulfilment_party`
- existing open `ToDo`
- existing `_assign`

## 3) Synchronization makes the state canonical

After insert/update, assignment sync logic ensures:

- duplicate assignees are removed
- duplicate open ToDos are collapsed
- `_assign` mirrors the canonical open `ToDo` state

## Current assignment paths

## Round-robin groups

The current app-owned round-robin pools are:

- `Routing`
  - `tech.alfa@local.test`
  - `tech.bravo@local.test`

- `PABX`
  - `tech.charlie@local.test`

- `SIM`
  - `tech.bravo@local.test`

These groups are treated as round-robin groups by `assign_after_insert()`.

### Round-robin behavior

For a round-robin group:

- the group-specific cursor is read from cache
- the next assignee is selected
- the cursor advances
- exactly one open `ToDo` is ensured for the chosen user
- `_assign` is mirrored from the resulting open `ToDo`

### Important note

Round-robin assignment is currently app-owned and cache-backed.

It is not currently driven by active Assignment Rule execution.

## Pool-user fallback groups

For groups that are **not** in the round-robin pool map:

- no RR user is chosen
- the ticket is seeded to the pool path instead

Current pool user:

- `helpdesk@local.test`

### Pool fallback behavior

If the ticket:

- has no open `ToDo`
- and `_assign` is empty

then pool fallback creates exactly one open `ToDo` for the pool user and mirrors `_assign` from that `ToDo`.

This is the safe default/unclaimed path.

## Partner override

There is a special override path for tickets where:

- `custom_fulfilment_party = "Partner"`

In that case:

- round-robin and normal pool seeding are bypassed
- the ticket is seeded to the partner user path if it is still effectively unassigned

Current partner user constant:

- `partner@local.test`

### Why this exists

This allows pilot tickets intended for partner fulfilment to avoid being silently pulled into the normal internal RR/pool flow.

## Current canonical truth model

The pilot currently treats **open `ToDo` state as canonical**.

That means:

- open `ToDo` rows are the most authoritative assignment state
- `_assign` mirrors open `ToDo` assignees
- assignment repair/sync logic restores `_assign` from open `ToDo` state where needed

## Why this matters

This avoids relying on stale or drifted `_assign` alone.

It also keeps:

- post-insert assignment,
- claim/handoff behavior,
- and repair scripts

anchored to the same practical ownership model.

## `_assign` behavior

`_assign` is still important, but it is treated as a mirrored representation of canonical assignment state rather than the sole source of truth.

### Current rules

- `_assign` should reflect open `ToDo` assignees
- duplicate users should not be present
- canonical ordering should be preserved where relevant
- drift between `_assign` and `ToDo` should be repaired, not ignored

## Duplicate and drift handling

The pilot includes explicit assignment hygiene.

### De-dupe on validate

During validate:

- duplicate users are removed from `_assign`

This prevents downstream assignment sync from multiplying ownership artifacts.

### Sync on update

On update:

- multiple open `ToDo` rows are collapsed
- `_assign` is mirrored from canonical open `ToDo` state
- missing `ToDo` can be recreated from `_assign` when appropriate

### Repair tooling exists

There is repo-backed repair tooling for assignment drift.

This exists to:

- scan recent tickets
- detect drift
- recreate missing `ToDo`
- collapse duplicates
- mirror `_assign` back into a consistent state

## User-facing assignment contract

For pilot tech users, direct Assign/Unassign is intentionally restricted.

### Current rule

Users with the pilot tech role should use:

- Claim
- Handoff

rather than direct generic Assign/Unassign actions.

### Why

This protects the pilot workflow from:

- accidental direct ownership churn
- bypassing the intended queue/pool flow
- UI actions that create inconsistent assignment artifacts

## Assign override guard

The current assign override blocks direct assign/unassign operations for:

- `TELECTRO-POC Tech`

while leaving admin/system-level operations available where appropriate.

This is intentional and part of the pilot safety model.

## Real assignment examples already proven

## Example A — inbound `PABX`

A proven inbound `PABX` ticket currently lands with:

- `email_account = PABX`
- `custom_service_area = PABX`
- `agent_group = PABX`
- `_assign = ["tech.charlie@local.test"]`
- exactly one open `ToDo` for Charlie

## Example B — inbound `Routing`

A proven inbound `Routing` ticket currently lands with:

- `email_account = Routing`
- `custom_service_area = Routing`
- `agent_group = Routing`
- `_assign = ["tech.alfa@local.test"]`
- exactly one open `ToDo` for Alfa

## Example C — manual `PABX`

A proven manual `PABX` ticket currently lands with:

- `email_account = None`
- `custom_service_area = PABX`
- `agent_group = PABX`
- `_assign = ["tech.charlie@local.test"]`
- exactly one open `ToDo` for Charlie

## Example D — fallback/manual unclaimed path

If the ticket lands in a non-round-robin/default path:

- pool fallback seeds the pool user
- `_assign` mirrors the pool `ToDo`

This is the intended safe fallback/unclaimed path.

## Current boundaries

The current pilot assignment contract is intentionally bounded.

It does **not** currently try to do all of the following:

- semantic/business-level duplicate suppression
- broad assignment-rule-driven automation as the live runtime source
- complex multi-owner assignment semantics
- highly dynamic workload balancing beyond the current RR/pool model

## Important operational truths

- assignment is currently app-owned
- routing seed must happen before assignment is expected to behave predictably
- open `ToDo` state is canonical
- `_assign` mirrors canonical open `ToDo` state
- pool fallback is the safe default for non-RR groups
- partner fulfilment is explicitly overridden
- pilot tech direct assign/unassign is intentionally blocked
- disabled Assignment Rules are not the live runtime mechanism

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

5. inspect post-insert assignment logic expectations
   - RR group?
   - pool fallback?
   - partner override?

6. use repair/proof tooling if drift is suspected

## Why this order matters

It prevents misleading conclusions based on `_assign` alone or on stale UI assumptions.

The most reliable operational ownership proof is:

- routing context,
- then open `ToDo`,
- then mirrored `_assign`.

## Current repo-backed helpers/tools relevant to this contract

The assignment contract is currently supported by repo-backed code and helpers including:

- routing seed app code
- round-robin/pool assignment app code
- assignment sync logic
- assign override guard
- assignment proof helper
- assignment repair helper
- manual ticket intake runbook
- email ticket intake runbook
- bench verification runbook

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
ract

The assignment contract is currently supported by repo-backed code and helpers including:

- routing seed app code
- round-robin/pool assignment app code
- assignment sync logic
- assign override guard
- assignment proof helper
- assignment repair helper
- manual ticket intake runbook
- email ticket intake runbook
- bench verification runbook

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
