# Manual Ticket Intake Runbook (Pilot)

Goal: document the current intended behavior for manually created `HD Ticket` records in the pilot, so manual intake stays predictable and future changes can be evaluated against a clear baseline.

## Purpose

This runbook describes the **current pilot contract** for manual ticket creation.

It is intentionally practical and reflects the system as currently designed and proven, not a future idealized workflow.

## Current design intent

Manual intake should allow an operator to log a valid ticket quickly with the minimum routing/location context needed to get work started.

The pilot does **not** require full pinpointing of the fault or equipment at creation time in every case.

That deeper specificity can be added later during triage or fulfilment.

## Current defaults for new manual tickets

On a new manual `HD Ticket`, the current pilot setup defaults or seeds the following:

- `ticket_type`
  - defaults to `Faults`

- `custom_request_type`
  - defaults to `General Assistance`

- `custom_fulfilment_party`
  - defaults to `Telectro`

- `custom_request_source`
  - defaults to `Customer`

These defaults support fast operator intake while still allowing later refinement.

## Ticket Type UX behavior

The manual form uses client-side UX logic to switch between two practical modes:

### Fault-like mode

Applies when `ticket_type` is one of:

- `Faults`
- `Incident`

In this mode, fault-oriented fields are shown, including:

- fault category
- fault asset
- site / location fields
- service area
- severity

### Request-like mode

Everything else is treated as request-like for pilot purposes.

In this mode:

- request-oriented fields are shown
- fault-oriented fields are hidden unless already populated

### Important UX note

If fault-oriented fields already contain values, they remain visible even when the form switches to request-like mode. This prevents the UI from hiding data the operator has already entered.

## Current minimum manual save contract

The current pilot intentionally allows a manual ticket to be saved without forcing full fault pinpointing.

This is by design.

The system currently aims to require enough information to:

- log the work,
- preserve the initial context,
- and allow routing/assignment to happen,

without forcing the operator to capture every possible technical detail up front.

### What is intentionally not required at first capture

Depending on the case, the operator may not yet know:

- exact fault asset
- exact dispatch anchor / fault point
- full equipment-level detail

The pilot allows those to be added later.

## Routing and assignment contract

Manual routing is **not** driven by mailbox input, because manual tickets have no `email_account`.

Instead, manual routing follows this pattern:

1. The operator selects or leaves blank the service/routing fields on the form.
2. Server-side routing seed logic runs on validation.
3. Post-insert assignment logic uses the seeded group/team to determine assignment outcome.

## Server-side routing seed behavior

The current app-owned routing seed logic behaves as follows for manual tickets:

- if `custom_service_area` is blank:
  - it defaults to `Other`

- if `agent_group` is blank:
  - it is seeded from `custom_service_area`
  - if no specific mapping exists, it falls back to `Helpdesk Team`

This logic now lives in app code and is no longer dependent on an enabled Server Script.

## Manual routing examples

### Example A — blank service area

If the operator creates a manual ticket and does not specify a service area:

- `custom_service_area` becomes `Other`
- `agent_group` becomes `Helpdesk Team`

This is the safe default/manual catch-all path.

### Example B — explicit `PABX`

If the operator sets:

- `custom_service_area = PABX`

then server-side routing seeds:

- `agent_group = PABX`

and the existing post-insert assignment logic routes the ticket to the PABX assignment path.

### Example C — explicit `Routing`

If the operator sets:

- `custom_service_area = Routing`

then server-side routing seeds:

- `agent_group = Routing`

and the existing post-insert assignment logic routes the ticket to the Routing assignment path.

## Assignment behavior after insert

Initial assignment is handled after insert by app code.

Current behavior is:

- known round-robin groups use the configured app-owned pool/rotation logic
- non-round-robin groups seed the pool user path
- `_assign` and open `ToDo` state are then normalized/canonicalized by the existing assignment sync logic

This means manual tickets and email-created tickets converge into the same downstream assignment contract once routing is seeded correctly.

## What is intentionally deferred

The pilot currently does **not** require all of the following at first capture:

- precise equipment selection
- precise fault anchor / dispatch point
- deeper asset layering for every case

Those are valid future improvements, but they are intentionally not required for the current pilot intake contract.

## Current pilot boundary

The current manual intake design optimizes for:

- fast logging
- enough routing context
- predictable assignment outcome
- minimal operator friction

It does **not** yet try to enforce the most detailed possible technical capture at creation time.

## Known UX notes

### Ticket Type mode banner

The client-side mode banner has been hardened so that:

- mode switching no longer throws console errors
- mode changes do not stack duplicate banners

### Save behavior

The current save behavior is intentionally permissive enough to allow pilot operators to log tickets with minimum viable routing/location context, rather than blocking until every downstream detail is known.

## Proof points behind this runbook

This behavior has been recently re-proven by:

- manual ticket creation tests
- inbound email ticket creation tests
- backend verification of:
  - `custom_service_area`
  - `agent_group`
  - `_assign`
  - open `ToDo` state

## When to revisit this runbook

Revisit this runbook if any of the following change:

- manual ticket required fields
- default `ticket_type`
- routing seed mappings
- assignment-after-insert behavior
- equipment / fault-detail capture requirements
- pilot decision to require more precise location/asset selection at creation time

## Field contract for manual ticket capture

The current pilot manual-capture contract is:

- **`ticket_type`**
  - broad ticket mode / top-level classification
  - used to distinguish fault-like vs request-like capture flow
  - examples: `Faults`, `Incident`, `Service Request`, `Assistance`

- **`custom_request_type`**
  - request subtype for request-like work
  - used to describe what kind of request is being made
  - examples: `Access Request`, `Quote / Pricing`, `Installation / Move`

- **`custom_service_area`**
  - routing domain / operational ownership field
  - used to determine which service area should own and route the ticket
  - examples: `Routing`, `PABX`, `SIM`, `Fiber`, `Faults`, `Other`

### Practical interpretation

- `ticket_type` answers: **what broad kind of ticket is this?**
- `custom_request_type` answers: **what kind of request is it?**
- `custom_service_area` answers: **where should this go operationally?**

