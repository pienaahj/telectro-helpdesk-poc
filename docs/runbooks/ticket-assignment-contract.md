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

For ordinary internal team routing, the native Frappe / Helpdesk Assignment Rule defines the eligible team population and maintains the round-robin cursor.

Where permitted automatic assignment has matching contextual Service Coverage, TELECTRO selects an eligible technician from the native HD Team population. Without matching coverage, ordinary non-CCTV tickets retain native Assignment Rule selection. CCTV requires explicit contextual authorization and eligible Service Coverage; it never uses unrestricted native automatic-assignment fallback.

The current working path is:

1. Ticket routing context is seeded, including Customer, Campus,
   Service Area, and the selected `agent_group`.
2. Explicit ownership exceptions are evaluated first:
   - Partner fulfilment resolves the Partner organisation's
     Default Dispatch User.
   - An eligible internal creator may explicitly select
     Take Ownership.
3. For ordinary internal tickets, `TELECTRO Assignment Policy`
   determines whether automatic assignment is permitted.
4. A matching **True Pool** policy suppresses automatic assignment
   by setting `custom_contextual_assignment_hold = 1`.
5. A matching **Round Robin** policy permits automatic assignment
   through the existing Service Coverage / native HD Team path,
   subject to the applicable eligibility and safety requirements.
6. For **CCTV**, automatic assignment requires complete Customer
   and Campus context, an explicitly approved non-Default contextual
   Round Robin Assignment Policy, and matching Service Coverage
   containing an eligible native HD Team technician.
   Missing context, a missing or generic Default policy, or absent
   or ineligible contextual coverage establishes
   `custom_contextual_assignment_hold = 1` and prohibits
   unrestricted native automatic assignment.
   For non-CCTV Service Areas, no matching Assignment Policy
   preserves existing assignment behavior.
7. `TELECTRO Service Coverage`, where configured, narrows the
   eligible technician population to the intersection of
   matching coverage users and native Assignment Rule users.
8. When contextual coverage selects an eligible technician,
   TELECTRO establishes the assignment and advances the
   existing native Assignment Rule cursor.
9. Without matching contextual coverage, the native Assignment
   Rule remains responsible for ordinary non-CCTV team-member
   selection. CCTV remains held rather than falling through
   to unrestricted native assignment.
10. TELECTRO assignment synchronization keeps Open `ToDo`
    records and `_assign` consistent with the single-owner
    invariant.
11. User-facing Claim, Release, and Controlled Handoff operate
    on top of the canonical ownership state.

The important separation is:

```text
TELECTRO routing policy
    -> determines Service Area and HD Team
    -> handles exceptional direct ownership

Partner fulfilment
    -> resolves the Partner organisation's dispatch owner

Explicit internal Take Ownership
    -> may assign the eligible internal ticket creator

TELECTRO Assignment Policy
    -> True Pool: suppress automatic assignment
    -> Round Robin: permit assignment subject to safety gates
    -> no matching policy: preserve non-CCTV behavior

Restricted CCTV automatic assignment
    -> requires complete Customer / Campus context
    -> requires approved non-Default contextual Round Robin
    -> requires matching eligible Service Coverage
    -> otherwise custom_contextual_assignment_hold = 1

TELECTRO Service Coverage
    -> narrows eligible technicians by context
    -> never expands native HD Team capability

Native HD Team Assignment Rule
    -> defines technician membership and round-robin order
    -> selects ordinary non-CCTV team owners without coverage
    -> provides the cursor shared with contextual assignment
    -> respects custom_contextual_assignment_hold

TELECTRO ownership controls
    -> enforce one accountable owner
    -> synchronize ToDo / _assign
    -> provide Claim / Release / Controlled Handoff
```

A matching True Pool policy does not prevent an authorized user from
manually claiming a ticket or receiving a Controlled Handoff.

When a ticket remains within the same True Pool policy and unchanged
routing context, intentional manual ownership is preserved.

When routing changes into a different True Pool context, stale
assignment ownership is retired and historical assignment ToDos
are cancelled.

When routing changes from True Pool to Round Robin, the contextual
hold is cleared and eligible automatic assignment can resume.

Campus / Site context does not itself establish a direct owner. In particular, Boschendal tickets continue through their Service Area / HD Team routing path unless another explicit ownership exception applies.

---

## Current source of truth in code

The current assignment contract is split across these live components.

### Routing seed

* `telephony.telectro_ticket_routing.seed_ticket_routing`

Seeds routing context, including the final `agent_group`, before assignment is evaluated.

### Initial assignment policy

* `telephony.telectro_round_robin.assign_after_insert`

Despite its historical module name, this function does not maintain a separate hard-coded technician pool or round-robin cursor.

When automatic assignment is permitted, matching contextual Service Coverage may select an eligible technician from the native HD Team population and advance the existing native Assignment Rule cursor. Without matching coverage, ordinary non-CCTV assignment remains with the native Assignment Rule. CCTV does not permit unrestricted native fallback.

### Initial CCTV hold — pre-insert lifecycle protection

New CCTV tickets must receive `custom_contextual_assignment_hold = 1` before their initial database insertion. The `HD Ticket.validate` hook `telephony.telectro_round_robin.initialize_cctv_assignment_hold` executes immediately after `telephony.telectro_ticket_routing.seed_ticket_routing`, ensuring that the Service Area and HD Team have already been established.

This early protection is necessary because Helpdesk's native `HD Ticket.after_insert()` can create an initial Communication. The Communication's `on_update` lifecycle invokes `HDTicket.on_communication_update()`, which saves the parent ticket. That nested save can execute the native Assignment Rule before TELECTRO's `assign_after_insert()` hook runs.

The pre-insert hold therefore prevents premature native CCTV assignment. The subsequent `assign_after_insert()` handler evaluates the contextual Assignment Policy and Service Coverage, retaining the hold when automatic assignment is prohibited or releasing it when eligible contextual Round Robin assignment is permitted.

Partner dispatch and explicitly authorized internal creator Take Ownership remain available while the native CCTV assignment hold is active. The initial hold does not prohibit these intentional ownership paths.

This behaviour was verified through controlled DEV lifecycle tests: ticket 943 demonstrated unauthorized native assignment before the pre-insert correction; ticket 944 verified suppression after the correction; tickets 945 and 946 verified Partner and creator ownership; and ticket 947 verified authorized contextual Round Robin assignment. All test tickets and temporary Service Coverage were rolled back.

The current `assign_after_insert()` behavior is:

* **Partner fulfilment** — resolve and assign the Partner organisation's deterministic Default Dispatch User.

* **Explicit internal direct ownership** — assign the target User when an eligible internal creator explicitly selected Take Ownership.

* **Assignment Policy: True Pool** — set `custom_contextual_assignment_hold = 1` and suppress automatic assignment through the native HD Team Assignment Rule.

* **Assignment Policy: Round Robin** — permit contextual Service Coverage assignment, subject to the applicable authorization and technician eligibility requirements.

* **Restricted CCTV automatic assignment** — require complete Customer and Campus context, an explicitly approved non-Default contextual Round Robin Assignment Policy, and matching Service Coverage with an eligible native HD Team technician.

  Missing CCTV context, a missing or generic Default Assignment Policy, or absent or ineligible contextual Service Coverage establishes `custom_contextual_assignment_hold = 1`. Unrestricted native automatic assignment is prohibited.

* **No matching Assignment Policy** — preserve existing assignment behavior for non-CCTV Service Areas. CCTV remains held rather than falling through to native automatic assignment.

* **Matching Service Coverage** — intersect covered Users with native Assignment Rule membership. When an eligible technician is selected, establish ownership and advance the native rule cursor. If no eligible technician remains, hold the ticket unassigned.

* **No matching Service Coverage** — for non-CCTV Service Areas, clear any contextual assignment hold and allow the native HD Team Assignment Rule to perform ordinary team-member selection. CCTV remains held without automatic assignment.

The contextual Assignment Policy decision is evaluated after Partner fulfilment and explicit internal direct-owner routing.

Campus / Site context does not independently establish a direct owner. Boschendal CCTV tickets use their selected HD Team and native assignment population only when an approved contextual Round Robin policy and matching eligible Service Coverage authorize automatic assignment.

### Routing-change ownership

* `telephony.telectro_reassign_on_update.reassign_if_routing_changed`

Re-evaluates ownership when routing-relevant fields change.

Its current behavior is:

* **Partner fulfilment** — normalize ownership to the selected Partner organisation's Default Dispatch User. Clear any previous contextual assignment hold.

* **Explicit internal direct-owner policy** — normalize ownership to the specified User when required. Clear any previous contextual assignment hold.

* **Assignment Policy: True Pool** — set
  `custom_contextual_assignment_hold = 1` and suppress native automatic assignment.

  * When entering a different True Pool policy, or when Customer, Campus, Service Area, fulfilment party, or HD Team context changes, retire previous ownership.
  * Previous assignment ToDos are cancelled and `_assign` is cleared.
  * When the ticket remains within the same True Pool policy and unchanged routing context, preserve an intentional manual owner.
  * Do not select a replacement technician or advance the native round-robin cursor.

* **Restricted CCTV automatic assignment** — require complete Customer and Campus context, an explicitly approved non-Default contextual Round Robin Assignment Policy, and matching Service Coverage with an eligible native HD Team technician. Incomplete context, a missing or generic Default policy, or absent or ineligible Service Coverage establishes `custom_contextual_assignment_hold = 1` and prevents unrestricted native automatic assignment.

  * When routing changes into a restricted CCTV context, retire stale ownership, cancel previous assignment ToDos, and clear `_assign`.
  * Preserve an existing manual owner only when Customer, Campus, Service Area, fulfilment party, and HD Team remain unchanged and the previous contextual assignment hold was already active.
  * Do not automatically select a replacement technician or advance the native round-robin cursor while the restricted CCTV hold applies.

* **Permitted Round Robin, or no matching policy for non-CCTV** — continue through contextual Service Coverage and the native HD Team assignment mechanism.

  * Clear any stale contextual hold when automatic assignment is permitted.
  * When matching Service Coverage exists, restrict eligibility to covered Users who also belong to the native Assignment Rule.
  * Preserve the current owner when that User remains eligible.
  * Otherwise, select an eligible replacement and advance the existing native cursor.
  * When matching Service Coverage has no eligible native team member, retain the ticket unassigned with a contextual hold.
  * Without matching Service Coverage, non-CCTV tickets may preserve a current owner who remains a valid member of the selected native HD Team.
  * Otherwise, retire stale ownership so the native Assignment Rule can select a replacement for permitted non-CCTV routing.

### Verified routing transitions

The following transitions were verified against persistent DEV Assignment Policies on 12 October 2026:

| Transition | Expected result |
|---|---|
| Boschendal Round Robin to Emerald Life True Pool | Previous owner released; historical ToDo cancelled; contextual hold set |
| Emerald Life True Pool to Boschendal Round Robin | Contextual hold cleared; eligible native team technician assigned |
| Routing change within the same True Pool context | Intentional manual ownership preserved |

The first two transitions were verified through real HD Ticket insert/save lifecycles, including assignment ToDos, `_assign`, native cursor handling, and database rollback.

Manual ownership preservation was verified by a targeted regression test using mocked ownership dependencies.

A routing change does not inherently grant direct ownership.
Customer and Campus determine contextual policy and eligibility,
while accountable ownership remains subject to the established assignment controls.


### Native internal team assignment

The native Frappe Assignment Rule remains the authoritative source of ordinary internal team assignment capability.

Each operational HD Team links to its Assignment Rule through:

```text
HD Team.assignment_rule
```

The native Assignment Rule defines:

- the enabled assignment mechanism;
- the ordered technician population;
- the shared round-robin cursor;
- the condition under which native automatic assignment is allowed.

The pilot uses native `Round Robin` assignment for its configured operational teams.

Contextual Service Coverage does not replace this native configuration or introduce a separate technician pool.

When matching Service Coverage exists:

- TELECTRO intersects the covered Users with the native Assignment Rule's technician population.
- TELECTRO may select an eligible technician using the native assignment order and cursor.
- The selected technician receives canonical assignment ownership.
- The existing native Assignment Rule cursor is advanced.
- An empty eligible intersection results in a contextual hold, not assignment to an uncovered technician.

When no matching Service Coverage exists, the native Assignment Rule remains responsible for ordinary non-CCTV team-member selection, provided automatic assignment is permitted. CCTV requires matching eligible contextual Service Coverage and remains held without it; unrestricted native fallback is prohibited.

The canonical native Assignment Rule condition includes:

```python
status == 'Open' and agent_group == '<HD Team>' and not custom_contextual_assignment_hold
```

The contextual assignment durability hook maintains this condition for linked operational team rules during migration.

The native Assignment Rule evaluates after the TELECTRO `HD Ticket` `on_update` hooks. This allows routing decisions, contextual holds, and stale-owner cleanup to complete before native automatic assignment is considered.

An explicit True Pool Assignment Policy suppresses native automatic assignment but does not prohibit authorized manual Claim or Controlled Handoff.

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

The live assignment architecture uses native Frappe Assignment Rules together with TELECTRO contextual assignment controls. It does not maintain a separate hard-coded technician pool or round-robin cursor.

The current responsibility split is:

```text
Routing and HD Team selection:
    TELECTRO routing code

Partner fulfilment ownership:
    Partner organisation Default Dispatch User

Exceptional internal direct ownership:
    explicit creator Take Ownership

Automatic assignment mode:
    TELECTRO Assignment Policy
    -> True Pool / Round Robin / existing fallback

Native technician capability:
    HD Team.assignment_rule
    -> enabled native Assignment Rule
    -> configured technician membership

Contextual technician eligibility:
    TELECTRO Service Coverage
    -> intersection with native rule membership

Round-robin order and cursor:
    native HD Team Assignment Rule

Ordinary team-member selection:
    TELECTRO -> when automatic assignment is permitted and eligible contextual Service Coverage exists
    native Assignment Rule -> permitted non-CCTV fallback without matching coverage
    neither -> when custom_contextual_assignment_hold = 1
    CCTV -> requires approved contextual Round Robin and eligible Service Coverage; no unrestricted native fallback

Canonical active ownership:
    open assignment ToDo

Compatibility / mirrored assignment state:
    HD Ticket._assign

Operational ownership actions:
    Claim / Release / Controlled Handoff
```

The former hard-coded TELECTRO round-robin pool implementation is no longer the live mechanism for ordinary internal team assignment.

Native Assignment Rules remain active operational runtime configuration. Their enabled state, technician membership, assignment condition, and round-robin cursor must be preserved and verified.

Contextual Assignment Policy determines whether automatic assignment is permitted. Service Coverage restricts eligible technicians when applicable, but cannot expand the native HD Team's assignment capability.

Campus / Site does not independently establish accountable ownership. Customer and Campus context may select an Assignment Policy or Service Coverage configuration, but ownership remains subject to the selected HD Team and the established assignment controls.

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

### 3) Contextual policy and native HD Team assignment handle ordinary internal routing

When no Partner fulfilment or explicit direct-owner exception applies, TELECTRO evaluates the ticket's contextual Assignment Policy.

The selected `agent_group` identifies the operational `HD Team`.

The assignment decision follows three paths, subject to an additional CCTV authorization gate. Automatic CCTV assignment requires complete Customer and Campus context, an explicitly approved non-Default contextual Round Robin Assignment Policy, and matching Service Coverage containing an eligible native HD Team technician. Otherwise, `custom_contextual_assignment_hold = 1` prevents unrestricted native automatic assignment. Explicit True Pool policies continue to suppress automatic assignment while permitting authorized manual ownership.

**Path A — Explicit True Pool policy**

When a matching `TELECTRO Assignment Policy` specifies `True Pool`, automatic assignment is suppressed.

The ticket remains in its selected HD Team with:

```text
custom_contextual_assignment_hold = 1
_assign = []
no Open assignment ToDo
```

The native Assignment Rule respects the contextual hold and does not select an automatic owner.

An authorized technician can subsequently Claim the ticket, or an authorized user can perform a Controlled Handoff.

**Path B — Permitted Round Robin with contextual Service Coverage, or no matching policy for non-CCTV**

When automatic assignment is permitted, TELECTRO checks for matching `TELECTRO Service Coverage` records.

If coverage exists, the eligible population is the intersection of:

- Users in the matching Service Coverage records.
- Users in the selected HD Team's native Assignment Rule.

TELECTRO selects an eligible technician using the native Assignment Rule's membership order and existing round-robin cursor.

The selected User receives canonical ownership, and the native cursor is advanced.

If matching Service Coverage exists but no technician belongs to both populations, automatic assignment is suppressed through the contextual hold.

**Path C — Permitted non-CCTV routing without contextual Service Coverage**

When no matching Service Coverage records exist for a non-CCTV ticket and automatic assignment is permitted, the native Assignment Rule remains responsible for ordinary team-member selection. CCTV cannot enter this fallback path.

The routing path is:

```text
routing fields
    -> seed_ticket_routing()
    -> agent_group / HD Team
    -> contextual assignment hold cleared
    -> HD Team.assignment_rule
    -> native Frappe Round Robin
    -> accountable team member
```

For non-CCTV Service Areas, no matching Assignment Policy preserves existing assignment behavior rather than imposing a new automatic-assignment requirement. For CCTV, neither a missing Assignment Policy nor absent contextual Service Coverage authorizes native automatic assignment.

Across all three paths, native HD Team membership remains the capability boundary. Contextual Service Coverage can restrict that membership but cannot expand it.

TELECTRO sets or clears `custom_contextual_assignment_hold` during ticket assignment evaluation. The migration durability hook maintains the corresponding safeguard in native Assignment Rule conditions, preventing native automatic assignment from overriding an intentional contextual hold.

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

* Routing first establishes the final `agent_group` and selected HD Team.
* TELECTRO does not choose technicians from a separate Python `POOLS` map.
* Partner fulfilment and explicit internal Take Ownership take precedence over contextual automatic assignment.
* A matching True Pool Assignment Policy suppresses automatic assignment through `custom_contextual_assignment_hold`.
* When automatic assignment is permitted, matching Service Coverage restricts eligibility to covered technicians who are also members of the selected HD Team's native Assignment Rule.
* When eligible contextual coverage exists, TELECTRO selects the technician using the native assignment order and cursor.
* The existing native Assignment Rule cursor is advanced following contextual technician selection.
* When matching Service Coverage has no eligible native team member, the ticket remains unassigned with a contextual hold.
* When no matching Service Coverage exists, the enabled native Assignment Rule performs ordinary Round Robin selection only for permitted non-CCTV routing. CCTV remains held and does not enter native automatic-assignment fallback.
* Assignment ownership is represented by the canonical Open assignment `ToDo` and mirrored in `_assign`.
* TELECTRO synchronization preserves the single-accountable-owner invariant.

The former hard-coded TELECTRO round-robin pool and cursor implementation has been removed from the live ordinary team-assignment path.

The native Assignment Rule remains the authoritative configuration for technician membership and round-robin cursor state. Contextual Service Coverage narrows this population without introducing a competing assignment system.

---

### True pool / unclaimed state

The pilot distinguishes between an explicit **True Pool Assignment Policy** and the **unclaimed ownership state** of an HD Ticket.

These concepts are related but are not interchangeable.

#### Explicit contextual True Pool policy

A matching `TELECTRO Assignment Policy` with `assignment_mode = True Pool` suppresses automatic assignment for its configured Customer, Campus, and Service Area context.

The ticket remains associated with its selected HD Team.

The assignment lifecycle sets:

```text
custom_contextual_assignment_hold = 1
```

The corresponding native Assignment Rule condition prevents automatic assignment while this hold is active.

An initially unclaimed ticket under this policy has:

```text
HD Ticket._assign = []
no Open assignment ToDo
```

An authorized technician may subsequently Claim the ticket, or an authorized user may establish ownership through Controlled Handoff.

The policy remains True Pool even when the ticket has a manually established accountable owner. The contextual hold prevents automatic assignment; it does not prohibit deliberate ownership.

When the ticket remains within the same True Pool policy and unchanged routing context, intentional manual ownership is preserved.

A routing transition into a different True Pool context retires stale ownership, while a transition to permitted Round Robin clears the contextual hold and allows automatic assignment to resume.

#### General unclaimed ownership state

An active ticket is unclaimed when there is currently no accountable owner.

Its canonical ownership state is:

```text
HD Ticket._assign = []
no Open assignment ToDo
```

This state does not, by itself, establish that a True Pool Assignment Policy applies.

A ticket may also remain unassigned because contextual Service Coverage has no eligible native team member, or because another assignment path has not established an owner.

True Pool therefore does not require a synthetic pool User and is not the former fallback for a team missing from a Python round-robin map.

The assignment policy, contextual hold, HD Team, and canonical ownership state must be inspected together to determine why a ticket is unassigned.

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

### Example E — true pool and unclaimed ownership

An active ticket is unclaimed when no accountable owner is currently established.

Its canonical ownership state is:

```text
no Open assignment ToDo
_assign = []
```

This state may result from an explicit True Pool Assignment Policy, an empty contextual technician eligibility intersection, or another assignment path that has not established ownership.

An explicit True Pool policy additionally establishes:

```text
custom_contextual_assignment_hold = 1
```

The contextual hold prevents native automatic assignment while leaving authorized manual Claim and Controlled Handoff available.

A manually claimed ticket can therefore remain governed by a True Pool Assignment Policy even though it now has an accountable owner.

**Verified DEV example — Emerald Life CCTV**

The persistent DEV Assignment Policy for Customer `Emerald Life` and Service Area `CCTV` specifies `True Pool`.

A real HD Ticket insert lifecycle verified:

```text
Customer = Emerald Life
Service Area = CCTV
HD Team = CCTV
Assignment Policy = True Pool

custom_contextual_assignment_hold = 1
_assign = []
Open assignment ToDos = 0
native round-robin cursor = unchanged
```

The lifecycle test used temporary HD Ticket `934`, and its database transaction was rolled back after verification.

This demonstrates that Emerald Life CCTV tickets can remain unclaimed without receiving an automatic technician assignment, even when an enabled native CCTV Assignment Rule exists.

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

### Example H — Boschendal CCTV contextual Round Robin

The persistent DEV Assignment Policy for Customer `Customer B`, Campus `Boschendal`, and Service Area `CCTV` specifies `Round Robin`.

`Customer B` is the DEV customer identity used for Boschendal. Production customer identity and operational technician membership must be verified independently.

A real HD Ticket insert lifecycle verified:

```text
Customer = Customer B
Campus = Boschendal
Service Area = CCTV
HD Team = CCTV
Assignment Policy = Round Robin

custom_contextual_assignment_hold = 0
_assign = ["tech.bravo@local.test"]
Open assignment ToDos = 1
native round-robin cursor = advanced
```

The lifecycle test used temporary HD Ticket `935`, and its database transaction was rolled back after verification.

This demonstrates that Boschendal CCTV tickets can receive automatic accountable ownership while Emerald Life CCTV tickets remain governed by their separate True Pool policy.

The DEV CCTV Assignment Rule currently has only one technician, `tech.bravo@local.test`. This proves successful assignment and cursor advancement but does not establish multi-technician rotation fairness.

The intended production Boschendal technician population must be configured and verified before CCTV automatic assignment is activated in production.

---

## Current boundaries

The current pilot assignment contract is intentionally bounded.

It currently provides:

* routing-driven HD Team selection
* native Frappe Assignment Rule membership, round-robin cursor, and ordinary assignment fallback
* contextual `TELECTRO Assignment Policy` supporting True Pool and Round Robin modes
* contextual `TELECTRO Service Coverage` restricting technician eligibility to the native Assignment Rule population
* contextual assignment holds preventing unintended native automatic assignment
* explicit Partner dispatch ownership
* explicit eligible internal creator Take Ownership
* one accountable ticket owner
* distinction between explicit True Pool policy and general unclaimed ownership state
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
* Assignment Policy determines whether contextual automatic assignment uses True Pool or Round Robin
* no matching Assignment Policy preserves existing assignment behavior for non-CCTV Service Areas; CCTV requires an explicitly approved non-Default contextual Assignment Policy before automatic assignment is permitted
* ordinary internal team-member selection is performed by TELECTRO when matching eligible contextual Service Coverage applies, or by the native Assignment Rule when permitted non-CCTV routing has no matching coverage; CCTV never uses unrestricted native fallback
* native Assignment Rules remain authoritative for technician membership, assignment condition, and the shared round-robin cursor
* contextual Service Coverage restricts native technician eligibility but cannot expand it
* `custom_contextual_assignment_hold` prevents native automatic assignment when an explicit True Pool policy applies, contextual coverage has no eligible native technician, or CCTV lacks complete context, an approved contextual policy, or matching eligible Service Coverage
* native Assignment Rules are active runtime configuration
* hard-coded Python `POOLS` are not the live ordinary team-assignment mechanism
* assignment represents accountable ownership, not contributor participation
* routing seed must establish the final `agent_group` before ordinary team assignment is expected to behave predictably
* the current accountable owner may be retained across a routing change when that User remains eligible in the destination HD Team and any applicable contextual Service Coverage
* intentional manual ownership is preserved when a ticket remains within the same True Pool policy and unchanged routing context, or within an unchanged, previously held restricted-CCTV context
* stale ownership is retired when the current owner becomes invalid for the destination context, allowing permitted contextual or native assignment to establish replacement ownership
* open assignment `ToDo` state is canonical for active owned tickets
* `_assign` is a mirrored/cache representation of accountable ownership
* an unclaimed ticket has `_assign = []` and no Open assignment `ToDo`
* an explicit True Pool Assignment Policy can remain active after authorized manual Claim or Controlled Handoff establishes ownership
* `Helpdesk Team` is an HD Team routing destination and is not synonymous with true pool
* terminal (`Resolved` / `Closed` / `Archived`) means `_assign = []` and no Open assignment `ToDo`
* terminal cleanup takes precedence over Partner fulfilment assignment enforcement and ordinary assignment repair
* Claim establishes accountable ownership from true pool
* Release returns accountable ownership to the pool with a required reason
* Controlled Handoff is the approved supervisor/coordinator accountability-transfer path
* Controlled Handoff is audited in `TELECTRO Assignment Handoff Log`
* the audit trail is visible in `TELECTRO Assignment Handoff Audit`
* Partner fulfilment uses an explicit organisation-aware dispatch override and bypasses ordinary internal team-member selection
* Campus / Site does not independently establish a direct owner; Customer and Campus context may determine Assignment Policy and Service Coverage, while native HD Team technician capability remains authoritative
* generic direct Assign/Unassign remains intentionally guarded where it would violate the pilot ownership model

---

## Proof order for assignment issues

When proving or debugging assignment behavior, use this order:

1. **Confirm routing inputs and final routing state.**

   * `email_account`
   * `custom_customer` / `customer`
   * `custom_site_group` and other relevant Campus / Site context
   * `custom_service_area`
   * `agent_group`
   * relevant Partner ownership fields
   * `custom_take_ownership_on_create` when explicit creator ownership is in question
   * current ticket status, including whether the ticket is terminal

2. **Determine whether an explicit ownership exception applies.**

   * Partner fulfilment / dispatch ownership?
   * eligible internal creator with explicit Take Ownership?
   * existing manual Claim or Controlled Handoff?
   * ordinary internal HD Team assignment?

   Partner fulfilment and eligible explicit creator ownership take precedence over contextual automatic assignment. Existing deliberate manual ownership must also be considered before interpreting the assignment state.

3. **Resolve the contextual Assignment Policy for ordinary internal routing.**

   * Determine whether an enabled `TELECTRO Assignment Policy` matches the ticket context.
   * Confirm the selected Customer, Campus, and Service Area.
   * Apply the configured specificity order: Customer/Campus, Campus, Customer, then Default.
   * Confirm whether the effective mode is `True Pool`, `Round Robin`, or no matching policy.
   * A matching True Pool policy suppresses automatic assignment.
   * A matching Round Robin policy permits automatic assignment through the existing assignment mechanisms, subject to contextual authorization and eligibility requirements.
   * For CCTV, automatic assignment additionally requires complete Customer and Campus context and an explicitly approved non-Default contextual Round Robin policy. Missing context, a missing policy, or a generic Default policy requires a contextual hold.
   * For non-CCTV Service Areas, no matching policy preserves existing assignment behavior rather than introducing a new global default.

4. **Inspect contextual Service Coverage when automatic assignment is permitted.**

   * Determine whether matching `TELECTRO Service Coverage` records exist.
   * Identify the covered Users for the effective ticket context.
   * Compare those Users with the technician membership of the selected HD Team's native Assignment Rule.
   * Confirm that the eligible population is the intersection of contextual coverage and native rule membership.
   * When matching coverage has no eligible native technician, expect the ticket to remain unassigned with a contextual hold.
   * When no matching coverage exists, ordinary native HD Team assignment remains the fallback only for permitted non-CCTV routing. CCTV requires matching eligible contextual Service Coverage and must remain held without it.

5. **Inspect the selected HD Team, native Assignment Rule, and contextual hold.**

   * `HD Team.assignment_rule`
   * linked Assignment Rule exists
   * rule is enabled when automatic assignment is expected
   * rule applies to `HD Ticket`
   * native Assignment Rule membership is correctly configured
   * `Assignment Rule.assign_condition` includes the contextual hold safeguard
   * `custom_contextual_assignment_hold` reflects the effective assignment decision
   * no enabled structural orphan Assignment Rule competes with the linked rule
   * inspect the native round-robin cursor when contextual selection or rotation behavior is in question

   A contextual hold may be intentional. Do not clear it merely because the ticket has no accountable owner.

6. **Inspect canonical ownership and assignment synchronization.**

   * Inspect relevant assignment `ToDo` rows, including historical non-Open rows.
   * Confirm the current Open assignment count.
   * Identify the accountable User, if any.
   * Inspect `assignment_rule` and `status` on relevant ToDo records.
   * Confirm that an active owned ticket has exactly one Open assignment ToDo.
   * Confirm that an unclaimed ticket has no Open assignment ToDo.
   * Inspect `_assign` and verify that it mirrors canonical ownership.
   * Do not treat `_assign` alone as proof of assignment correctness.

7. **If routing context changed, verify ownership transitions.**

   * Establish the previous and current Customer, Campus, Service Area, fulfilment party, and HD Team context.
   * Determine whether the effective Assignment Policy changed.
   * For a transition into a different True Pool context, confirm stale ownership was retired and the contextual hold established.
   * For an unchanged True Pool policy and routing context, confirm intentional manual ownership was preserved.
   * For routing changes into restricted CCTV context, confirm `custom_contextual_assignment_hold = 1`, stale assignment ToDos are cancelled, and `_assign` no longer identifies the previous owner.
   * For unchanged, previously held restricted CCTV context, confirm an intentionally established manual owner is preserved. Verify that Customer, Campus, Service Area, fulfilment party, and HD Team are unchanged.
   * For a transition from True Pool to permitted Round Robin, confirm the contextual hold was cleared.
   * When automatic assignment is permitted, verify that an existing owner remains eligible under both native team membership and applicable Service Coverage before preserving ownership.
   * If the previous owner is no longer eligible, verify that stale ownership was retired and permitted replacement assignment was evaluated.
   * Check the native cursor when contextual round-robin selection occurred.

8. **Inspect operational ownership controls and use repair tooling only when justified.**

   * Claim
   * Release
   * Controlled Handoff
   * Partner dispatch normalization
   * eligible internal creator Take Ownership
   * assignment synchronization and drift repair tools

   Do not run assignment repair merely to populate an intentionally unclaimed True Pool ticket or a ticket held by restricted CCTV authorization. For CCTV, first verify complete Customer and Campus context, an approved non-Default contextual Round Robin Assignment Policy, and matching eligible Service Coverage before expecting automatic assignment. Never clear a restricted CCTV hold or enable unrestricted native fallback merely to force assignment. Establish the effective policy, contextual hold, eligibility, and canonical ToDo state before deciding that repair is appropriate.

### Why this order matters

Routing, automatic assignment policy, technician eligibility, and accountable ownership are related but separate responsibilities.

The ordinary internal assignment path is:

```text
routing inputs
    -> final agent_group / HD Team
    -> contextual Assignment Policy
        -> True Pool: hold; suppress automatic assignment
        -> CCTV: require complete Customer / Campus context and approved non-Default contextual Round Robin
        -> non-CCTV: Round Robin or no policy may evaluate eligibility
    -> contextual Service Coverage
        -> matching eligible coverage: native membership intersection
        -> no eligible native technician: contextual hold
        -> CCTV without matching eligible coverage: hold; no native fallback
        -> non-CCTV without matching coverage: native assignment fallback
    -> contextual hold or permitted technician selection
    -> canonical assignment ToDo when owned
    -> mirrored _assign
```

Partner fulfilment and explicit eligible internal creator Take Ownership take precedence over contextual automatic assignment.

Campus / Site context does not independently establish direct ownership. It can, however, determine which Assignment Policy or Service Coverage configuration applies.

An unassigned ticket is not necessarily an assignment failure. It may represent an intentional True Pool policy or a contextual hold caused by the absence of an eligible technician.

The most reliable operational proof therefore starts with routing context and ownership exceptions, resolves the applicable Assignment Policy and Service Coverage, verifies native team eligibility and the contextual hold, and then examines canonical assignment `ToDo` state.

The `_assign` field remains a mirrored representation and must not be treated as independent proof of accountable ownership.

When native Assignment Rule behavior itself is under investigation, inspect historical non-Open `ToDo` rows as well. Frappe may treat statuses other than `Cancelled` as existing assignment state.

Assignment repair should only follow confirmation of unintended ownership drift or inconsistent assignment state.

---

## Current repo-backed helpers/tools relevant to this contract

The assignment contract is currently supported by repo-backed code and helpers including:

* routing seed logic

  * `telephony.telectro_ticket_routing.seed_ticket_routing`

* routing policy

  * `telephony.telectro_routing_policy.resolve_ticket_routing_policy`

* initial ownership and contextual assignment

  * `telephony.telectro_round_robin.assign_after_insert`
  * `telephony.assignment_policy`
  * `telephony.service_coverage`
  * `telephony.native_team_assignment`
  * the historical `telectro_round_robin` module name is retained, but there is no separate hard-coded technician pool or round-robin cursor
  * Assignment Policy determines whether contextual automatic assignment is suppressed or permitted
  * Service Coverage restricts eligible technicians to the native Assignment Rule membership
  * contextual technician selection uses the existing native assignment cursor
  * when matching Service Coverage is absent, ordinary selection remains with the native Assignment Rule

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

* contextual assignment durability

  * `telephony.setup.contextual_assignment_durability`
  * runs through the registered `after_migrate` hook
  * ensures linked operational HD Team Assignment Rules retain the `not custom_contextual_assignment_hold` safeguard in `assign_condition`
  * prevents native automatic assignment from overriding an intentional contextual hold
  * does not configure production technician membership, enable disabled Assignment Rules, or create Customer-specific Assignment Policies

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
* `TELECTRO Assignment Policy` modes, matching specificity, precedence, or enabled-state behavior
* Customer / Campus / Service Area policy resolution
* `TELECTRO Service Coverage` matching, technician eligibility, or native membership intersection
* `custom_contextual_assignment_hold` lifecycle behavior
* native Assignment Rule `assign_condition` contextual hold safeguards
* native round-robin cursor handling during contextual technician selection
* True Pool manual ownership preservation or transitions between True Pool and Round Robin
* production activation procedures for contextual Assignment Policies, Service Coverage, and native Assignment Rules
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
