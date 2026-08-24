# Partner Operating Model

Goal: document the current Partner organisation, membership, identity, containment, and dispatch model used by the ERPNext / Helpdesk pilot.

This runbook describes the **current implemented Partner operating model**. It replaces the earlier assumption that one hard-coded Partner User represents the Partner boundary.

Use this runbook when:

- configuring a Partner organisation
- onboarding or staging Partner users
- proving Partner tenant containment
- explaining request-side versus fulfilment-side Partner identity
- validating Partner fulfilment dispatch
- reviewing Partner-related workflow or reporting behavior
- preparing controlled Partner production acceptance tests

---

## Purpose

Partner identity is organisation-based.

A Frappe `User` is an authenticated person/account. It is not itself the Partner tenant.

The current model separates:

- authentication
- Partner capability
- Partner organisation identity
- organisation membership
- Partner fulfilment dispatch
- ticket assignment ownership

Those concepts must remain distinct.

---

## Current source of truth

The core Partner identity model is implemented in:

- `telephony.partner_identity`
- `TELECTRO Partner`
- `TELECTRO Partner Member`

Partner fulfilment assignment uses:

- `telephony.telectro_round_robin.assign_after_insert`
- `telephony.partner_identity.resolve_partner_dispatch_user`

Assignment ownership remains governed by the ticket assignment contract:

- `docs/runbooks/ticket-assignment-contract.md`

---

## Core identity model

The current model is:

```text
Frappe User
    -> authenticated account

Partner capability role
    -> determines whether the User may perform Partner actions

TELECTRO Partner Member
    -> associates a User with a Partner organisation

TELECTRO Partner
    -> identifies the Partner organisation / tenant

Default Dispatch User
    -> deterministic operational recipient for Partner fulfilment

Open assignment ToDo / _assign
    -> current accountable ticket ownership
```

These concepts are related, but they are not interchangeable.

In particular:

```text
User
    != Partner organisation

Partner role
    != Partner organisation membership

Partner membership
    != Default Dispatch User

Default Dispatch User
    != Partner organisation identity

Partner organisation identity
    != ticket assignment ownership
```

---

## Partner capability roles

The current Partner capability roles are:

- `TELECTRO-POC Role - Partner`
- `TELECTRO-POC Role - Partner Creator`

Partner roles provide capability.

They do **not** establish which Partner organisation a User represents.

Organisation identity is determined separately through enabled `TELECTRO Partner Member` membership.

This separation is deliberate.

A User must not gain access to another Partner organisation merely because the User has a Partner role.

---

## Partner organisation

`TELECTRO Partner` is the Partner organisation / tenant record.

Its current fields are:

- Partner Name
- Enabled
- Default Dispatch User
- Members
- Notes

Partner Name is required and unique.

The record is named from Partner Name.

`Enabled` defaults to enabled when a new record is created unless deliberately changed.

A Partner organisation may exist without members.

A Partner organisation may also exist without a Default Dispatch User.

Therefore:

> The existence of a Partner organisation does not by itself mean that the organisation is ready for Partner-user access or Partner fulfilment dispatch.

---

## Partner membership

Partner membership is stored in the `TELECTRO Partner Member` child table.

Each membership row contains:

- User
- Enabled

User is required.

Membership defaults to enabled unless deliberately changed.

The same User cannot appear more than once in the Members table of the same Partner organisation.

A User may belong to more than one Partner organisation because organisation identity is resolved from enabled membership across Partner records.

Only enabled membership under an enabled Partner organisation participates in normal Partner tenant resolution.

---

## Enabled organisation membership

`get_enabled_partner_names_for_user()` returns only Partner organisations where:

- the User has an enabled `TELECTRO Partner Member` row; and
- the parent `TELECTRO Partner` organisation is enabled.

Partner roles are intentionally not part of this tenant-resolution function.

The model therefore separates:

```text
Membership
    -> Which Partner organisation does this User represent?

Capability role
    -> What Partner actions may this User perform?
```

Both may be required by a workflow, but they answer different questions.

---

## Partner organisation resolution for a User

`resolve_partner_name_for_user()` resolves the Partner organisation represented by an authenticated User.

The current rules are:

### No enabled Partner membership

If the User has no enabled membership in an enabled Partner organisation:

- Partner organisation resolution is rejected.

The system does not guess an organisation from the User's role or email address.

### One enabled Partner membership

If the User belongs to exactly one enabled Partner organisation:

- that organisation may be resolved automatically when no organisation was explicitly supplied.

### Multiple enabled Partner memberships

If the User belongs to more than one enabled Partner organisation:

- an explicit Partner organisation must be selected.

The system does not silently choose one organisation.

### Explicit Partner selection

If an explicit Partner organisation is supplied:

- it must be one of the User's enabled Partner memberships.

Otherwise resolution is rejected.

This is a tenant-containment boundary.

---

## Partner ticket identity

Partner organisation identity on an `HD Ticket` is dimension-specific.

The current legitimate Partner dimensions are:

```text
Request Source = Partner
    -> custom_request_partner

Fulfilment Party = Partner
    -> custom_fulfilment_partner
```

A Partner field only establishes ticket-party identity when its corresponding party dimension is actually `Partner`.

### Request-side Partner identity

When:

```text
custom_request_source = Partner
```

the requesting Partner organisation is:

```text
custom_request_partner
```

### Fulfilment-side Partner identity

When:

```text
custom_fulfilment_party = Partner
```

the fulfilling Partner organisation is:

```text
custom_fulfilment_partner
```

### Fail-closed ticket identity

If the matching Partner organisation field is blank, that side contributes no Partner organisation identity.

The system does not infer ticket-party identity from:

- a Partner role
- assignment ownership
- `_assign`
- an arbitrary populated Partner field whose corresponding party dimension is not `Partner`

---

## Ticket visibility and tenant containment

`user_has_partner_ticket_membership()` provides the core organisation-membership test for Partner ticket access.

The User must be an enabled member of at least one enabled Partner organisation that is legitimately a party to the ticket.

Conceptually:

```text
Partner organisations legitimately party to ticket
INTERSECT
enabled Partner organisations for User
```

must produce at least one organisation.

If the intersection is empty, the membership check fails.

This prevents Partner access from being based merely on:

- Partner role
- User email
- ticket assignment
- a historical hard-coded Partner account
- unrelated Partner organisation membership

Ticket containment follows organisation membership.

---

## Default Dispatch User

`Default Dispatch User` is an operational dispatch setting on `TELECTRO Partner`.

It is **not** the Partner organisation identity.

At the Partner DocType level, Default Dispatch User is optional.

If a Default Dispatch User is configured, the Partner record requires that User to be an enabled member of the same Partner organisation.

This allows Partner organisations to exist before they are ready for fulfilment dispatch.

---

## Partner fulfilment dispatch readiness

Partner fulfilment uses stronger runtime validation than the basic Partner record itself.

`resolve_partner_dispatch_user()` requires:

- a Partner organisation to be supplied
- the Partner organisation to exist
- the Partner organisation to be enabled
- a Default Dispatch User to be configured
- the Default Dispatch User to be an enabled member of that Partner organisation
- the Frappe User to exist and be enabled
- the User to have at least one Partner capability role

Only after all of those checks pass is the Default Dispatch User returned for Partner fulfilment assignment.

Therefore:

```text
Partner organisation exists
    != Partner fulfilment dispatch-ready
```

and:

```text
Partner organisation enabled
    != Partner fulfilment dispatch-ready
```

A Partner organisation becomes dispatch-ready only when its operational dispatch configuration also satisfies the runtime eligibility checks.

---

## Partner fulfilment assignment

For a ticket where:

```text
custom_fulfilment_party = Partner
```

`custom_fulfilment_partner` identifies the fulfilling Partner organisation.

The assignment path resolves that organisation's valid Default Dispatch User before applying Partner fulfilment assignment.

Normal internal round-robin and pool routing are bypassed for Partner fulfilment.

The resolved Default Dispatch User is the deterministic operational recipient.

The Partner organisation itself remains the tenant identity.

Current assignment ownership remains represented by canonical open assignment `ToDo` state and mirrored `_assign` state.

See:

- `docs/runbooks/ticket-assignment-contract.md`

for the complete assignment contract.

---

## Partner workflow trains

Partner collaboration is divided into two distinct workflow trains.

They represent different business directions and must not be treated as the same process.

The valid trains are:

```text
Partner-originated / Telectro-fulfilled
    -> Partner acceptance train

non-Partner-originated / Partner-fulfilled
    -> Partner work-completion train
```

The implementation normalises the Partner-specific state fields according to those dimensions.

---

## Partner-originated / Telectro-fulfilled acceptance train

The Partner acceptance train applies when:

```text
custom_request_source = Partner
custom_fulfilment_party != Partner
```

This means:

- the Partner organisation originated the request;
- Telectro or another non-Partner party is fulfilling the request;
- the Partner may later be asked to accept Telectro's handling of that request.

The requesting Partner organisation is represented by:

```text
custom_request_partner
```

This train uses:

- `custom_partner_acceptance_state`
- `custom_partner_accepted_on`

Partner work-completion fields do not belong to this train.

### Train normalisation

For a valid Partner-originated / Telectro-fulfilled ticket, the implementation clears:

- `custom_partner_work_state`
- `custom_partner_work_completed`

This prevents Partner work-completion state from leaking into the acceptance train.

### Request Partner acceptance

Telectro may request Partner acceptance on a non-terminal Partner-originated ticket when acceptance has not already been requested or processed.

The acceptance state becomes:

```text
Pending Partner Acceptance
```

A request comment is recorded and the Partner is notified through the applicable Partner notification path.

`Rework Required` is deliberately eligible for another acceptance request after Telectro has completed the requested rework.

The following states are not eligible for another normal acceptance request:

- `Pending Partner Acceptance`
- `Accepted by Partner`
- `Reviewed by Telectro`

### Partner accepts

The Partner-side acceptance action requires:

- Partner ticket access;
- Request Source = `Partner`;
- Fulfilment Party != `Partner`;
- non-terminal ticket status;
- Partner Acceptance State = `Pending Partner Acceptance`;
- an acceptance note.

On successful acceptance:

```text
Partner Acceptance State
    -> Accepted by Partner
```

If an acceptance date is supplied:

```text
custom_partner_accepted_on
    -> supplied acceptance date
```

The acceptance note is recorded and Telectro is notified.

### Partner requests acceptance rework

Instead of accepting, the Partner may require rework.

The action requires:

- Partner ticket access;
- Request Source = `Partner`;
- Fulfilment Party != `Partner`;
- non-terminal ticket status;
- Partner Acceptance State = `Pending Partner Acceptance`;
- a rework reason.

The state becomes:

```text
Rework Required
```

The rework reason is recorded and Telectro is notified.

After Telectro completes the necessary correction or clarification, Telectro may request Partner acceptance again.

### Telectro reviews accepted Partner acceptance

Once:

```text
Partner Acceptance State = Accepted by Partner
```

an authorised internal reviewer may review the Partner acceptance.

The current outcomes are:

#### Review only

```text
Ticket status
    -> unchanged

Partner Acceptance State
    -> remains Accepted by Partner
```

A review comment is recorded.

`Review only` is deliberately non-terminal.

It does **not** mark the acceptance state as `Reviewed by Telectro`.

#### Resolve

```text
Partner Acceptance State
    -> Reviewed by Telectro

Ticket status
    -> Resolved
```

Open assignment `ToDo` rows are closed and `_assign` is cleared.

#### Close

```text
Partner Acceptance State
    -> Reviewed by Telectro

Ticket status
    -> Closed
```

Open assignment `ToDo` rows are closed and `_assign` is cleared.

---

## Non-Partner-originated / Partner-fulfilled work train

The Partner work-completion train applies when:

```text
custom_request_source != Partner
custom_fulfilment_party = Partner
```

This means:

- the request did not originate from the Partner;
- Telectro assigned fulfilment responsibility to a Partner organisation.

The fulfilling Partner organisation is represented by:

```text
custom_fulfilment_partner
```

This train uses:

- `custom_partner_work_state`
- `custom_partner_work_completed`

Partner acceptance fields do not belong to this train.

### Train normalisation

For a valid non-Partner-originated / Partner-fulfilled ticket, the implementation clears:

- `custom_partner_acceptance_state`
- `custom_partner_accepted_on`

This prevents Partner acceptance state from leaking into the work-completion train.

### Initial Partner work state

When the ticket enters the Partner fulfilment train and no Partner Work State is already present, the implementation seeds:

```text
Partner Work State
    -> Assigned to Partner
```

### Partner submits work done

The Partner may submit completed work only when:

- the Partner has ticket access;
- Request Source != `Partner`;
- Fulfilment Party = `Partner`;
- the ticket is not terminal;
- the current work state permits submission;
- a work-done note is supplied.

Submission is permitted from:

- blank state;
- `Assigned to Partner`;
- `Rework Required`.

Submission is rejected if work has already been submitted as:

```text
Work Completed by Partner
```

On successful submission:

```text
Partner Work State
    -> Work Completed by Partner
```

If a completion date is supplied:

```text
custom_partner_work_completed
    -> supplied completion date
```

The work-done note is recorded and Telectro is notified.

### Telectro reviews Partner work

An authorised internal reviewer may review Partner work when the ticket belongs to the Partner fulfilment train.

The normal review condition is:

```text
Partner Work State = Work Completed by Partner
```

The current review outcomes are:

#### Review only

```text
Partner Work State
    -> remains Work Completed by Partner

Ticket status
    -> unchanged
```

A review comment is recorded.

Assignment state is canonicalised, but Partner work remains awaiting a later decision.

#### Accept work

```text
Partner Work State
    -> Reviewed by Telectro

Ticket status
    -> unchanged
```

The Partner work is accepted without resolving or closing the ticket.

Open Partner assignment `ToDo` rows are closed and:

```text
_assign = []
```

This is an important distinction:

```text
Partner work accepted
    != ticket resolved
    != ticket closed
```

The ticket may remain active for further Telectro or Customer-facing work.

#### Request rework

A rework reason is required.

The result is:

```text
Partner Work State
    -> Rework Required

custom_partner_work_completed
    -> cleared
```

The Partner is notified that further work is required.

Assignment state is canonicalised so the Partner work train can continue.

The Partner may subsequently submit work done again.

#### Resolve

Resolution is permitted when Partner Work State is:

- `Work Completed by Partner`; or
- `Reviewed by Telectro`.

The result is:

```text
Partner Work State
    -> Reviewed by Telectro

Ticket status
    -> Resolved
```

Open assignment `ToDo` rows are closed and `_assign` is cleared.

#### Close

Closure is permitted when Partner Work State is:

- `Work Completed by Partner`; or
- `Reviewed by Telectro`.

The result is:

```text
Partner Work State
    -> Reviewed by Telectro

Ticket status
    -> Closed
```

Open assignment `ToDo` rows are closed and `_assign` is cleared.

---

## Why the Partner trains remain separate

The implementation deliberately distinguishes:

```text
Partner -> Telectro request
```

from:

```text
Telectro/non-Partner -> Partner fulfilment
```

The normalisation rules are:

```text
Request Source = Partner
Fulfilment Party != Partner
    -> keep acceptance fields
    -> clear work-completion fields

Request Source != Partner
Fulfilment Party = Partner
    -> keep work-completion fields
    -> clear acceptance fields

Anything else
    -> clear both Partner train state sets
```

This prevents:

- Partner acceptance from being used for Partner fulfilment work;
- Partner work completion from being used as acceptance of a Partner-originated request;
- Customer or unrelated tickets from carrying stale Partner workflow state;
- both Partner trains from being active on the same ticket.

The two trains may involve the same Partner organisation model and Partner-safe interface, but they represent different business responsibilities and state machines.

## Fail-closed principles

The current Partner model deliberately fails closed where identity is ambiguous or invalid.

Examples include:

- no enabled organisation membership
- selecting an organisation outside the User's enabled memberships
- multiple enabled organisations without explicit selection
- missing Partner organisation for Partner dispatch
- disabled Partner organisation
- missing Default Dispatch User when dispatch is required
- dispatch User not being an enabled member of the organisation
- disabled or missing Frappe dispatch User
- dispatch User lacking Partner capability
- ticket party dimension not actually being Partner
- missing Partner organisation identity on the applicable ticket side

The system should not compensate for these conditions by:

- guessing a Partner organisation
- treating a role as tenant identity
- using a hard-coded Partner User
- falling through into internal assignment
- treating `_assign` as Partner tenant identity

These fail-closed boundaries are part of the Partner containment model.

---

## Partner onboarding and staging

Partner onboarding is organisation-first.

Creating a Frappe `User` and assigning a Partner role does not by itself create Partner tenant identity.

The Partner organisation and membership relationship must be established deliberately.

### Recommended onboarding sequence

The operational sequence is:

```text
Create or confirm Partner organisation
    -> create or identify Partner User
    -> assign required Partner capability / Role Profile
    -> add User as Partner organisation member
    -> configure Default Dispatch User where fulfilment dispatch is required
    -> verify organisation membership and dispatch configuration
    -> deliberately enable the organisation/User for live use
    -> complete the normal invitation/password setup process
    -> perform fresh Partner browser proof
```

The exact Frappe welcome/setup-email procedure remains governed by the current onboarding procedure.

The important Partner-specific rule is that organisation identity and membership must exist before Partner access is treated as ready.

### Stage the Partner organisation deliberately

A `TELECTRO Partner` record may exist before onboarding is complete.

For controlled staging, the organisation may be kept disabled until its intended configuration has been reviewed.

Because new Partner records normally default to enabled, disabling a staging organisation must be a deliberate action.

Before treating the organisation as ready for Partner use, confirm:

- Partner Name is correct;
- the organisation represents the intended real or synthetic Partner tenant;
- intended Partner Users exist;
- membership rows are correct;
- membership enablement is deliberate;
- required Partner capability roles are present;
- Default Dispatch User is configured if Partner fulfilment dispatch is required;
- the Default Dispatch User satisfies the dispatch-readiness contract.

A Partner organisation that is only used for Partner-originated requests does not require a Default Dispatch User merely to establish tenant identity.

A Default Dispatch User becomes mandatory when Partner fulfilment dispatch is required.

### Add Partner membership

The Partner User must be associated with the correct organisation through `TELECTRO Partner Member`.

Do not infer organisation membership from:

- the User's email domain;
- User name;
- Partner role;
- Role Profile;
- ticket ownership.

For a User expected to operate as a full Partner user, confirm that the intended organisation membership is enabled before live Partner access is tested.

### Multi-organisation Users

A User may be an enabled member of more than one Partner organisation.

In that case:

- the User does not have one globally implied Partner tenant;
- workflows requiring Partner identity must use explicit organisation selection where required;
- the selected organisation must be one of the User's enabled Partner memberships.

Do not configure or document a multi-organisation User as though the User itself were the Partner identity.

### Configure fulfilment dispatch separately

If the Partner will receive work from Telectro:

- select the intended Default Dispatch User;
- confirm that User is an enabled member of the same organisation;
- confirm the Frappe User is enabled;
- confirm the User has Partner capability.

Do not use Default Dispatch User as a substitute for organisation membership.

Do not assume every organisation member is the dispatch recipient.

### Activation and invitation

Activation should be deliberate.

Before sending the normal welcome/setup communication or treating the Partner as live, confirm the organisation-level configuration first.

The browser proof must then use the actual Partner account and the intended organisation membership.

Administrator or System Manager access is not a substitute for Partner containment proof.

---

## Production Partner acceptance policy

Partner production testing must preserve real Partner tenant boundaries.

A Telectro-controlled test User must **not** be attached to a real Partner organisation merely to obtain Partner browser or workflow proof.

### Synthetic Partner organisation

When controlled Partner production proof requires a test identity, use a dedicated synthetic Partner organisation.

The preferred naming convention is:

```text
[PILOT TEST] Partner
```

The organisation must be clearly identifiable as test data.

A Telectro-controlled Partner test User may be:

- a member of this synthetic organisation;
- its Default Dispatch User when fulfilment-dispatch proof requires one.

It must not be added to a real Partner tenant for convenience.

### Synthetic organisation lifecycle

The synthetic Partner organisation should be enabled only when required for controlled proof.

Where there is no ongoing need for it after acceptance testing:

- disable the synthetic organisation after proof;
- retain only the evidence required by the release procedure.

Do not confuse disabling the synthetic organisation with deleting valid release evidence.

### Production smoke tickets

Do not create fake operational tickets merely to make Partner reports or queues non-empty.

For Partner UI/report proof:

- use valid existing test evidence where appropriate;
- accept a legitimate empty state where that proves the surface correctly;
- create a new smoke ticket only when an end-to-end workflow genuinely requires one.

If a Partner smoke ticket is required:

- use the synthetic Partner organisation;
- label the ticket clearly as pilot/test evidence;
- keep it separate from real operational history;
- remove or archive it according to the production data rule;
- never reuse it later as normal operational history.

A smoke ticket must never be created against a real Partner organisation solely to simplify testing.

### Partner browser proof

Partner browser proof requires more than a Partner role.

The proof account must have the intended:

- Frappe User identity;
- Partner capability;
- enabled Partner organisation membership;
- Partner organisation context;
- dispatch configuration where Partner fulfilment is being tested.

Use a fresh browser state such as:

```text
private/incognito session
sign out and back in
fresh role-appropriate production login
```

Verify both positive and containment behavior.

Positive proof should demonstrate the applicable Partner capabilities.

Containment proof should demonstrate that the User cannot cross into:

- unrelated Partner organisation tickets;
- internal Telectro workspaces;
- internal reports;
- raw/internal HD Ticket surfaces outside the approved Partner interface.

Where a suitable negative-test identity does not exist, record the negative proof as deferred or not verified rather than assuming it passed.

---

## Operational verification

When verifying Partner organisation behavior, distinguish business-semantic proof from exact database proof.

Use Frappe-aware tools for behavior that depends on:

- DocType semantics;
- roles;
- memberships;
- permissions;
- Partner identity resolution;
- workflow state.

Use exact SQL inspection where the required proof is specifically about persisted database rows or values.

For Partner verification, always state which layer was proved.

Examples:

```text
Partner membership semantics
    -> Frappe-aware proof

exact TELECTRO Partner Member rows
    -> database proof

Partner ticket containment
    -> Frappe-aware permission / identity proof

assignment ToDo / _assign state
    -> assignment contract proof
```

Do not infer one layer solely from another.

---

## Related runbooks

Use these documents with this operating model:

- `docs/runbooks/ticket-assignment-contract.md`
  - accountable ownership, Partner fulfilment assignment, `ToDo`, and `_assign`

- `docs/runbooks/production-runtime-release.md`
  - production release and Phase 21 browser verification

- `docs/user-guides/onboarding-training-readiness-checklist.md`
  - practical onboarding and training readiness

- `docs/user-guides/pilot-welcome-guides.md`
  - role-appropriate Partner user guidance

- `docs/user-guides/activity-process-guides.md`
  - detailed Partner acceptance and Partner work processes

This runbook is the canonical source for the Partner organisation / membership / dispatch identity model.
