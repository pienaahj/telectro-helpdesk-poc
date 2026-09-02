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
- routing and assignment lifecycle behavior
- `_assign` / `ToDo` synchronization
- repair tooling
- real ticket outcomes from both email and manual intake paths

The assignment model is intentionally practical and bounded.

---

## High-level assignment model

The pilot currently uses a **hybrid routing and assignment model**.

TELECTRO application code decides **where** a ticket should be routed and handles explicit ownership exceptions.

For ordinary internal team routing, native Frappe / Helpdesk **Assignment Rules** decide **which member of the selected HD Team** becomes the accountable owner.

The current working path is:

1. ticket routing context is seeded
2. explicit ownership exceptions are evaluated
3. Partner fulfilment may establish the Partner organisation's deterministic Default Dispatch User
4. an eligible internal creator may explicitly choose Take Ownership
5. ordinary internal tickets retain the selected `agent_group`
6. the native Assignment Rule linked to that `HD Team` selects the accountable team member
7. TELECTRO assignment synchronization keeps open `ToDo` and `_assign` state consistent with the pilot single-owner invariant
8. user-facing Claim, Release, and Controlled Handoff operate on top of that canonical ownership state

The important separation is:

```text
TELECTRO routing policy
    -> decides team / exceptional direct owner

Partner fulfilment
    -> resolves the Partner organisation's deterministic dispatch owner

Explicit internal Take Ownership
    -> may establish the eligible internal ticket creator as owner

Native HD Team Assignment Rule
    -> chooses the member of an ordinary internal team

TELECTRO ownership controls
    -> enforce one accountable owner
    -> synchronize ToDo / _assign
    -> provide Claim / Release / Controlled Handoff
```

Campus / Site context does not itself establish a direct owner. In particular, Boschendal tickets continue through their Service Area / HD Team routing path unless another explicit ownership exception applies.

---

## Current source of truth in code

The current assignment contract is split across these live components.

### Routing seed

* `telephony.telectro_ticket_routing.seed_ticket_routing`

Seeds routing context, including the final `agent_group`, before assignment is evaluated.

### Initial assignment policy

* `telephony.telectro_round_robin.assign_after_insert`

Despite the historical module name, ordinary internal round-robin selection is no longer performed here.

The current `assign_after_insert()` behavior is:

* Partner fulfilment -> resolve and assign the Partner organisation's deterministic Default Dispatch User
* explicit internal direct-owner policy -> assign the returned `target_user`; the current internal exception is an eligible ticket creator who explicitly selected Take Ownership
* ordinary internal team routing -> create no assignment itself and allow the native HD Team Assignment Rule to assign a team member

Campus / Site is not an initial direct-owner policy. Boschendal and other ordinary internal tickets remain on the Service Area -> HD Team -> native Assignment Rule path.

### Routing-change ownership

* `telephony.telectro_reassign_on_update.reassign_if_routing_changed`

Re-evaluates ownership when routing-relevant fields change.

Its current behavior is:

* Partner fulfilment -> normalize ownership to the selected Partner organisation's Default Dispatch User
* explicit internal direct-owner policy with a `target_user` -> normalize ownership to that User
* ordinary internal team routing:

  * preserve the current accountable owner when that User remains valid in the newly selected HD Team
  * otherwise retire stale assignment state so the native Assignment Rule for the current HD Team can select the replacement owner

### Native internal team assignment

Ordinary internal team ownership is selected through the native Frappe Assignment Rule linked from:

```text
HD Team.assignment_rule
```

The active pilot HD Team rules use native `Round Robin` assignment.

The Assignment Rule evaluates after the TELECTRO `HD Ticket` `on_update` hooks, so routing and stale-owner cleanup are completed before native team assignment is applied.

### Partner organisation / dispatch identity

* `telephony.partner_identity.resolve_partner_dispatch_user`

Resolves the deterministic dispatch User for Partner fulfilment from the selected Partner organisation and validates that the organisation, membership, User, and Partner capability are eligible for dispatch.

### Assignment synchronization / hygiene

* `telephony.telectro_assign_sync.dedupe_assign_field`
* `telephony.telectro_assign_sync.sync_ticket_assignments`

These enforce the pilot ownership invariant after assignment:

* open assignment `ToDo` is canonical for active ownership
* `_assign` is its mirrored/cache representation
* an active owned ticket has one accountable owner
* duplicate ownership state is collapsed
* terminal tickets have no active assignment
* Partner fulfilment is normalized to its deterministic dispatch User

### Claim / Release / Controlled Handoff

* `telephony.telectro_claim.*`

Implements the pilot-safe operational ownership actions:

* **Claim** — atomically take accountable ownership of a true-pool ticket
* **Release** — return accountable ownership to the pool with a reason
* **Controlled Handoff** — transfer accountability to one new User with audit evidence

### Assign UI / API guardrails

* `telephony.overrides.assign_to.*`

Restrict generic Frappe Assign/Unassign behavior where it would violate the pilot's single-accountable-owner model.

---

## Important current truth

The live assignment architecture is **not an app-owned round-robin implementation**.

The current responsibility split is:

```text
Routing / policy:
    TELECTRO application code

Ordinary team-member selection:
    native HD Team Assignment Rule

Partner fulfilment ownership:
    Partner organisation Default Dispatch User

Exceptional internal direct ownership:
    explicit creator Take Ownership

Canonical active ownership:
    open assignment ToDo

Compatibility / mirrored assignment state:
    HD Ticket._assign

Operational ownership actions:
    Claim / Release / Controlled Handoff
```

The former hard-coded TELECTRO round-robin pool implementation is no longer the live mechanism for ordinary internal team assignment.

Native Assignment Rules are therefore active operational runtime state, not merely historical or dormant configuration.

Campus / Site does not itself establish accountable ownership. It remains routing context and must not bypass the selected HD Team's normal assignment path merely because a ticket belongs to a particular campus.

---

## Assignment phases

### 1) Routing/team context is seeded first

Before ordinary team assignment runs, the ticket must have enough routing context to determine which ownership path applies.

Examples:

* email-created ticket from the `PABX` mailbox -> `agent_group = PABX`
* manual ticket with `custom_service_area = PABX` -> `agent_group = PABX`
* ordinary fallback routing -> `agent_group = Helpdesk Team`

Routing determines the destination team. It does not itself choose a member of that team.

### 2) Explicit ownership exceptions are evaluated

After insert, `assign_after_insert()` handles ownership paths that deliberately bypass ordinary team-member selection.

Current explicit ownership paths include:

* Partner fulfilment -> selected Partner organisation's Default Dispatch User
* eligible internal creator with explicit Take Ownership -> ticket creator

The internal Take Ownership path is opt-in. It applies only when the creator selected the Take Ownership field and qualifies as an eligible internal technician-like User.

Partner-originated and Partner-fulfilled tickets are excluded from the internal creator Take Ownership path.

Campus / Site is not a direct-owner exception. A Boschendal ticket, for example, continues through its Service Area -> HD Team -> native Assignment Rule path unless another explicit ownership exception applies.

When an explicit ownership exception applies, TELECTRO code establishes the accountable owner directly.

### 3) Native HD Team assignment handles ordinary internal routing

If no direct-owner policy applies, `assign_after_insert()` deliberately creates no assignment.

The selected `agent_group` identifies the `HD Team`.

That team's linked native Frappe Assignment Rule then evaluates during `on_update`.

For the active pilot teams, these rules use native `Round Robin` assignment to select a User from the team's Assignment Rule membership.

The ordinary internal path is therefore:

```text
routing fields
    -> seed_ticket_routing()
    -> agent_group / HD Team
    -> HD Team.assignment_rule
    -> native Frappe Assignment Rule
    -> accountable team member
```

### 4) TELECTRO synchronization canonicalizes ownership state

After assignment activity, the TELECTRO synchronization layer preserves the pilot ownership invariant:

```text
Owned active ticket:
  exactly one Open assignment ToDo
  _assign = ["accountable.owner@example"]

True pool ticket:
  no Open assignment ToDo
  _assign = []
```

---

## Current assignment paths

### Native round-robin HD Teams

Ordinary internal team-member selection is now driven by the native Assignment Rule linked from each operational `HD Team`.

The current enabled DEV pilot configuration includes:

* `Routing`

  * native `Round Robin`
  * `tech.alfa@local.test`
  * `tech.bravo@local.test`

* `PABX`

  * native `Round Robin`
  * `tech.charlie@local.test`

* `SIM`

  * native `Round Robin`
  * `tech.bravo@local.test`

* `Internet Connection`

  * native `Round Robin`
  * `tech.alfa@local.test`
  * `tech.bravo@local.test`

* `CCTV`

  * native `Round Robin`
  * `tech.bravo@local.test`

* `Helpdesk Team`

  * native `Round Robin`
  * `hendrik@local.test`

The individual rule document names may change as configuration is recreated or reconciled. The durable contract is the link:

```text
HD Team
    -> assignment_rule
    -> enabled native Assignment Rule
    -> eligible team Users
```

Do not encode Assignment Rule document suffixes as operational policy.

#### Native round-robin behavior

For an ordinary internal team ticket:

* routing first establishes the final `agent_group`
* TELECTRO does not choose a team member from a Python `POOLS` map
* the enabled Assignment Rule linked to the selected `HD Team` evaluates
* native Frappe `Round Robin` chooses an eligible User
* Frappe creates the assignment `ToDo`
* TELECTRO synchronization preserves the single-accountable-owner invariant and mirrored `_assign` state

The former hard-coded TELECTRO round-robin pool and cursor implementation has been removed from the live ordinary team-assignment path.

---

### True pool / unclaimed state

A true-pool ticket is an active ticket for which there is currently **no accountable owner**.

Its canonical ownership state is:

```text
HD Ticket._assign = []
no Open assignment ToDo
```

A ticket can remain in this state when assignment has not produced an accountable owner.

True pool is therefore an ownership state, not a synthetic pool User and not the old fallback for a team missing from a Python round-robin map.

#### Claim from true pool

The pilot **Claim** action allows a User to take accountability for a true-pool ticket.

Claim is first-claim-wins and normalizes the resulting state to:

```text
exactly one Open assignment ToDo
_assign = ["claiming.user@example"]
```

#### Release to pool

The pilot **Release** action allows the current accountable owner to return the ticket to the pool with a required reason.

The intended resulting ownership state is:

```text
no Open assignment ToDo
_assign = []
```

Release is an explicit operational ownership action. It is separate from the native team's initial assignment decision.

---

### Partner fulfilment override

There is a special organisation-aware assignment path for tickets where:

- `custom_fulfilment_party = "Partner"`
- `custom_fulfilment_partner` identifies the Partner organisation responsible for fulfilment

Partner fulfilment does not use a hard-coded Partner User.

Instead, `assign_after_insert()` passes `custom_fulfilment_partner` to:

- `telephony.partner_identity.resolve_partner_dispatch_user`

The resolver requires:

- the Partner organisation to exist
- the Partner organisation to be enabled
- a Default Dispatch User to be configured
- the Default Dispatch User to be an enabled member of that Partner organisation
- the Frappe User to exist and be enabled
- the User to have at least one Partner capability role

If any of those conditions fail, Partner dispatch fails closed with a validation error. The ticket does not silently fall through into normal internal round-robin or pool assignment.

Once the dispatch User has been resolved:

- normal internal round-robin and pool assignment are bypassed
- an existing open assignment `ToDo` is not overwritten
- an existing `_assign` owner is not overwritten
- if the ticket is still effectively unassigned, one open assignment `ToDo` is ensured for the resolved Default Dispatch User
- `_assign` is then mirrored from canonical open `ToDo` state

The important identity distinction is:

```text
Partner organisation
    != Partner User
    != assignment ownership

TELECTRO Partner
    -> identifies the Partner organisation

TELECTRO Partner Member
    -> associates authorised Users with that organisation

Default Dispatch User
    -> identifies the deterministic operational recipient for Partner fulfilment

Open assignment ToDo / _assign
    -> represents current accountable ticket ownership
```

This prevents Partner-fulfilment tickets from being silently pulled into the normal internal round-robin/pool flow while keeping Partner organisation identity separate from operational assignment ownership.

---

## Canonical truth model

The pilot currently treats **open assignment `ToDo` state as canonical** for active owned tickets.

That means:

- open assignment `ToDo` rows are the most authoritative assignment state for owned tickets
- `_assign` mirrors the canonical owner for Frappe/Helpdesk compatibility
- sync/repair logic restores `_assign` from canonical open `ToDo` state where needed

The current invariant is:

```text
Active owned ticket:
  exactly one Open assignment ToDo
  HD Ticket._assign = ["accountable.owner@local.test"]

True pool ticket:
  no Open assignment ToDo
  HD Ticket._assign = []

Terminal ticket (Resolved / Closed / Archived):
  no Open assignment ToDo
  HD Ticket._assign = []
```
For assignment lifecycle purposes, `Resolved`, `Closed`, and `Archived` are terminal states.

When a ticket becomes terminal:

- any Open assignment `ToDo` rows are cancelled
- `_assign` is cleared
- terminal cleanup takes precedence over Partner fulfilment assignment enforcement and ordinary assignment repair
- `_assign` must not recreate an assignment on a terminal ticket

### Why this matters

This avoids relying on stale or drifted `_assign` alone.

It also keeps:

- routing / assignment lifecycle
- claim/handoff behavior
- repair scripts

anchored to the same practical ownership model.

---

## `_assign` behavior and drift handling

`_assign` is still important, but it is treated as a mirrored representation of canonical assignment state rather than the sole source of truth.

### Current rules

- `_assign` should reflect open `ToDo` assignees for non-terminal tickets
- terminal tickets must have `_assign = []` and no Open assignment `ToDo`
- duplicate users should not be present
- canonical ordering should be preserved where relevant
- drift between `_assign` and `ToDo` should be repaired, not ignored

### Current hygiene behavior

#### De-dupe on validate

During validate:

- duplicate users are removed from `_assign`

#### Sync on update

On update:

- terminal tickets cancel Open assignment `ToDo` rows and clear `_assign`
- terminal cleanup runs before Partner fulfilment assignment enforcement and ordinary assignment repair
- multiple open `ToDo` rows on non-terminal tickets are collapsed
- `_assign` is mirrored from canonical open `ToDo` state
- missing `ToDo` can be recreated from `_assign` only when appropriate for a non-terminal ticket

#### Repair tooling exists

Repo-backed repair tooling exists to:

- scan recent tickets
- detect drift
- recreate missing `ToDo`
- collapse duplicates
- mirror `_assign` back into a consistent state

---

## User-facing assignment contract

For pilot users, ticket assignment represents accountable ownership.

Direct generic Assign/Unassign is intentionally restricted because the generic Frappe assignment UI can create multi-assignee or drift-prone states that do not match the pilot ownership model.

### Current rule

Users should use the pilot-safe ownership actions:

- **Claim** — take ownership from the true pool
- **Release** — return own ticket to the true pool with a reason
- **Controlled Handoff** — supervisor/coordinator transfer of accountability to a new owner

Generic Assign/Unassign is not the normal pilot reassignment path.

### Controlled Handoff

Controlled Handoff is the approved accountability-transfer path for supervisor/coordinator intervention.

Controlled Handoff:

- transfers accountability from the current owner or pool to one new accountable owner
- does not add a second assignee
- requires a reason
- writes a ticket timeline comment
- records a durable audit row in `TELECTRO Assignment Handoff Log`

The audit row captures:

```text
ticket
ticket subject
changed on
changed by
from user
to user
reason
source
```

---

## Verified current examples

### Example A — inbound `PABX`

A proven inbound `PABX` path establishes:

```text
email_account = PABX
custom_service_area = PABX
agent_group = PABX
```

For ordinary Telectro fulfilment, the enabled native Assignment Rule linked to the `PABX` HD Team selects an eligible team member.

In the current DEV pilot configuration this results in:

```text
accountable owner = tech.charlie@local.test
exactly one Open assignment ToDo
_assign = ["tech.charlie@local.test"]
```

The important contract is not the individual DEV User. It is:

```text
PABX routing
    -> agent_group = PABX
    -> PABX HD Team
    -> linked enabled Assignment Rule
    -> eligible team member
```

### Example B — inbound `Routing`

A proven inbound `Routing` path establishes:

```text
email_account = Routing
custom_service_area = Routing
agent_group = Routing
```

The native Assignment Rule linked to the `Routing` HD Team performs ordinary team-member selection.

The current DEV pilot membership contains Alfa and Bravo.

The resulting owned-ticket invariant remains:

```text
exactly one Open assignment ToDo
_assign = ["selected.accountable.owner"]
```

### Example C — manual `PABX`

A manual ticket routed through:

```text
custom_service_area = PABX
agent_group = PABX
```

uses the same native HD Team Assignment Rule path as an inbound email ticket.

The intake mechanism may differ, but once final routing has selected `PABX`, ordinary internal team-member selection follows the same assignment contract.

### Example D — ordinary fallback team routing

An ordinary ticket that does not map to one of the more specific operational teams may route to:

```text
agent_group = Helpdesk Team
```

`Helpdesk Team` is itself an operational HD Team and may have an enabled native Assignment Rule.

It must therefore not be treated as synonymous with the true pool.

The normal path is:

```text
fallback routing
    -> agent_group = Helpdesk Team
    -> Helpdesk Team.assignment_rule
    -> native Assignment Rule
    -> accountable team member
```

### Example E — true pool

A true-pool ticket is one for which no accountable owner is currently established.

Its ownership state is:

```text
no Open assignment ToDo
_assign = []
```

It remains visible as unclaimed operational work until an ownership action establishes an accountable owner.

Claim is the normal pilot action for taking ownership of such a ticket.

### Example F — routing change where current owner becomes invalid

A routing change from one internal team to another re-evaluates ownership.

A proven example is conceptually:

```text
Routing / Alfa
    -> routing changes to PABX
    -> Alfa is not eligible for PABX
    -> stale assignment is retired
    -> native PABX Assignment Rule evaluates
    -> eligible PABX owner is selected
```

The critical contract is:

```text
invalid owner in destination team
    -> do not preserve stale ownership
    -> allow destination HD Team Assignment Rule to select a replacement
```

### Example G — routing change where current owner remains valid

If the current accountable owner is also eligible for the destination HD Team, ownership is deliberately preserved.

A proven example is conceptually:

```text
Routing / Alfa
    -> routing changes to Internet Connection
    -> Alfa is eligible for Internet Connection
    -> existing accountable ownership retained
    -> no assignment churn
```

The `agent_group` represents the current routing destination.

An existing assignment `ToDo` may still record the Assignment Rule that originally created that ownership. That historical `assignment_rule` value on the `ToDo` does not override the ticket's current routing state.

---

## Current boundaries

The current pilot assignment contract is intentionally bounded.

It currently provides:

* routing-driven HD Team selection
* native Frappe Assignment Rule team-member selection
* explicit Partner dispatch ownership
* explicit eligible internal creator Take Ownership
* one accountable ticket owner
* true-pool / unclaimed state
* Claim
* Release
* Controlled Handoff
* `ToDo` / `_assign` synchronization and drift repair

It does **not** currently try to provide:

* semantic/business-level duplicate suppression
* multiple parallel accountable HD Ticket owners
* contributor/subtask semantics inside HD Ticket assignment
* highly dynamic workload balancing beyond configured native Assignment Rule behavior
* a second custom Python round-robin membership model alongside HD Team configuration

If explicit multi-person work tracking becomes necessary, it should be modelled separately from accountable HD Ticket ownership rather than by adding parallel assignment owners.

---

## Important operational truths

* routing policy and assignment are separate responsibilities
* TELECTRO routing logic determines the destination team or an exceptional direct owner
* ordinary internal team-member selection is performed by the native Assignment Rule linked to the selected `HD Team`
* native Assignment Rules are active runtime configuration
* hard-coded Python `POOLS` are not the live ordinary team-assignment mechanism
* assignment represents accountable ownership, not contributor participation
* routing seed must establish the final `agent_group` before ordinary team assignment is expected to behave predictably
* the current accountable owner may be retained across a routing change when that User is valid in the destination HD Team
* stale ownership is retired when the current owner is not valid for the destination HD Team, allowing the destination native Assignment Rule to select a replacement
* open assignment `ToDo` state is canonical for active owned tickets
* `_assign` is a mirrored/cache representation of accountable ownership
* true pool means `_assign = []` and no Open assignment `ToDo`
* `Helpdesk Team` is an HD Team routing destination and is not synonymous with true pool
* terminal (`Resolved` / `Closed` / `Archived`) means `_assign = []` and no Open assignment `ToDo`
* terminal cleanup takes precedence over Partner fulfilment assignment enforcement and ordinary assignment repair
* Claim establishes accountable ownership from true pool
* Release returns accountable ownership to the pool with a required reason
* Controlled Handoff is the approved supervisor/coordinator accountability-transfer path
* Controlled Handoff is audited in `TELECTRO Assignment Handoff Log`
* the audit trail is visible in `TELECTRO Assignment Handoff Audit`
* Partner fulfilment uses an explicit organisation-aware dispatch override and bypasses ordinary internal team-member selection
* Campus / Site context does not by itself establish a direct owner; ordinary Boschendal tickets continue through Service Area -> HD Team -> native Assignment Rule assignment
* generic direct Assign/Unassign remains intentionally guarded where it would violate the pilot ownership model

---

## Proof order for assignment issues

When proving or debugging assignment behavior, use this order:

1. confirm routing inputs and final routing state

   * `email_account`
   * `custom_service_area`
   * `custom_site_group` / other relevant routing context
   * `agent_group`
   * relevant Partner ownership fields
   * `custom_take_ownership_on_create` when explicit creator ownership is in question

2. determine which ownership path applies

   * Partner fulfilment / dispatch path?
   * explicit eligible internal creator Take Ownership path?
   * ordinary internal HD Team assignment?
   * existing true-pool state?

3. for ordinary internal routing, inspect the selected HD Team

   * `HD Team.assignment_rule`
   * linked Assignment Rule exists
   * rule is enabled
   * rule applies to `HD Ticket`
   * rule condition matches the ticket
   * eligible Assignment Rule Users exist
   * no enabled structural orphan Assignment Rule is competing with the currently linked HD Team rule

4. inspect assignment `ToDo` state

   * all relevant `ToDo` rows, not only Open rows when diagnosing native Assignment Rule behavior
   * current Open assignment count
   * accountable User
   * `assignment_rule`
   * status

5. inspect `_assign`

   * confirm it mirrors current accountable ownership
   * do not treat `_assign` alone as canonical proof

6. if routing changed, establish whether the current owner remains valid

   * valid member of destination HD Team -> ownership may be preserved
   * invalid for destination HD Team -> stale ownership should be retired before native reassignment

7. inspect explicit ownership controls when relevant

   * Claim
   * Release
   * Controlled Handoff
   * Partner dispatch normalization
   * eligible internal creator Take Ownership

8. use assignment repair/proof tooling only when drift or inconsistent historical state is suspected

### Why this order matters

Routing and accountable ownership are related but separate concerns.

The normal internal path is:

```text
routing inputs
    -> final agent_group
    -> HD Team
    -> current linked native Assignment Rule
    -> accountable User
    -> assignment ToDo
    -> mirrored _assign
```

Partner fulfilment or explicit eligible internal creator Take Ownership may deliberately bypass ordinary team-member selection.

Campus / Site context alone does not bypass ordinary team-member selection.

The most reliable operational proof therefore starts with routing context and the applicable ownership path, then examines canonical assignment `ToDo` state, and only then uses `_assign` as the mirrored representation.

When native Assignment Rule behavior itself is under investigation, inspect non-Open historical `ToDo` rows as well because Frappe may treat statuses other than `Cancelled` as existing assignment state.

---

## Current repo-backed helpers/tools relevant to this contract

The assignment contract is currently supported by repo-backed code and helpers including:

* routing seed logic

  * `telephony.telectro_ticket_routing.seed_ticket_routing`

* routing policy

  * `telephony.telectro_routing_policy.resolve_ticket_routing_policy`

* initial ownership policy

  * `telephony.telectro_round_robin.assign_after_insert`
  * historical module name retained; ordinary team-member round-robin is native

* routing-change ownership logic

  * `telephony.telectro_reassign_on_update.reassign_if_routing_changed`

* Partner dispatch identity

  * `telephony.partner_identity.resolve_partner_dispatch_user`

* assignment synchronization

  * `telephony.telectro_assign_sync.dedupe_assign_field`
  * `telephony.telectro_assign_sync.sync_ticket_assignments`

* pilot ownership actions

  * `telephony.telectro_claim.*`

* generic Assign/Unassign guardrails

  * `telephony.overrides.assign_to.*`

* assignment proof / repair helpers

* HD Team durability validation

  * `telephony.setup.hd_team_durability`

* manual ticket intake runbook

* email ticket intake runbook

* bench verification runbook

### Related

* `docs/runbooks/ticket-status-and-workspace-baseline.md`

---

## When to revisit this runbook

Revisit this runbook if any of the following change:

* routing seed mappings
* routing policy / exceptional direct-owner rules
* HD Team membership
* `HD Team.assignment_rule` relationships
* native Assignment Rule method or conditions
* Assignment Rule User membership
* Partner organisation / membership / Default Dispatch User rules
* explicit internal creator Take Ownership policy
* `_assign` / `ToDo` source-of-truth model
* true-pool semantics
* Claim / Release behavior
* Controlled Handoff behavior
* assignment override restrictions
* routing-change owner-preservation rules
* terminal assignment cleanup
* pilot move toward contributor/subtask or more complex ownership models

Do not reintroduce a second hard-coded Python membership / round-robin model alongside native HD Team assignment without an explicit architectural decision and corresponding update to this contract.
