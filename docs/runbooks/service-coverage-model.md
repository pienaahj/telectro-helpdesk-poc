# TELECTRO Service Coverage Model


> **Implementation status — 12 October 2026**
>
> This runbook originated as a design proposal. The sections below
> describing proposed V1 functionality, future routing integration,
> open questions, and recommended next steps are retained as historical
> design context.
>
> The current implementation contract is documented immediately below.
> Where historical proposals conflict with this contract, the current
> implementation takes precedence.
>
> DEV verification does not constitute production activation.
> Customer-specific Assignment Policy and Service Coverage records
> are operational database configuration and are not automatically
> deployed as fixtures.

## Current implementation — contextual assignment

The pilot separates three independent responsibilities:

| Component | Responsibility |
|---|---|
| HD Team and native Assignment Rule | Define technician capability and round-robin population |
| TELECTRO Service Coverage | Narrow eligible technicians by Customer, Campus and Service Area |
| TELECTRO Assignment Policy | Decide whether automatic assignment is permitted |

Role Profiles control system access, not customer-specific technician
eligibility.

### Assignment Policy

The implemented `TELECTRO Assignment Policy` DocType supports:

- `enabled`
- `coverage_scope`
- `customer`
- `campus`
- `service_area`
- `assignment_mode`
- `notes`

Supported assignment modes:

- **True Pool** — suppress automatic assignment; allow controlled manual Claim and Handoff.
- **Round Robin** — permit automatic assignment through the existing HD Team and contextual Service Coverage mechanism, subject to applicable authorization and technician eligibility requirements.

Policy matching uses the following precedence:

1. Customer/Campus + Service Area
2. Campus + Service Area
3. Customer + Service Area
4. Default + Service Area

Only enabled policies participate.

Conflicting enabled policies at the same exact scope and context are rejected. For non-CCTV Service Areas, an absent matching Assignment Policy preserves existing assignment behavior rather than imposing a new global default. For CCTV, automatic assignment requires complete Customer and Campus context and an enabled, explicitly scoped non-Default Assignment Policy selecting Round Robin. A missing Assignment Policy or generic Default policy establishes `custom_contextual_assignment_hold = 1` and prevents unrestricted native automatic assignment. An explicit True Pool policy continues to suppress automatic assignment while allowing authorized manual ownership.

### Service Coverage and native assignment

Service Coverage uses the same Customer/Campus specificity order.

For ordinary internal assignment:

1. Resolve the ticket's Customer, Campus, Service Area, and selected HD Team.
2. Resolve the matching Assignment Policy using the established specificity precedence.
3. If True Pool applies, set `custom_contextual_assignment_hold = 1` and suppress automatic assignment while permitting authorized manual ownership.
4. For CCTV, require complete Customer and Campus context and an enabled, explicitly scoped non-Default Round Robin Assignment Policy. Missing context, a missing policy, or a generic Default policy establishes a contextual hold and prohibits unrestricted native automatic assignment.
5. Where automatic assignment is permitted, resolve the selected HD Team's native Assignment Rule and technician membership.
6. Where matching Service Coverage exists, restrict eligible Users to the intersection of contextual coverage and native Assignment Rule membership. An empty eligible intersection establishes a contextual hold.
7. When contextual Service Coverage produces an eligible technician, establish canonical ownership and advance the existing native Assignment Rule cursor.
8. Without matching contextual Service Coverage, permitted non-CCTV routing retains ordinary native HD Team assignment. CCTV instead establishes `custom_contextual_assignment_hold = 1` and remains unavailable for automatic assignment.

Service Coverage never grants assignment capability to a user who is not in the native team's assignment population.

### CCTV pre-insert assignment protection

New CCTV tickets receive `custom_contextual_assignment_hold = 1` during `HD Ticket.validate`, immediately after routing seeding and before the initial database insert. This prevents native Assignment Rule processing from assigning a technician prematurely when Helpdesk creates an initial Communication and its callback triggers a nested ticket save.

The `telephony.telectro_round_robin.initialize_cctv_assignment_hold` validation hook establishes this initial protection. The subsequent `assign_after_insert()` handler resolves the effective Assignment Policy and Service Coverage, retaining the hold for restricted CCTV contexts or releasing it when an eligible contextual Round Robin assignment is authorized.

The hold does not prevent authorized Partner dispatch or explicit internal creator Take Ownership. Neither exception authorizes unrestricted native CCTV assignment.

The complete lifecycle explanation, implementation contract, and controlled DEV verification evidence are maintained in [Ticket Assignment Contract](ticket-assignment-contract.md).

### Ownership precedence

Partner fulfilment and explicit internal Take Ownership decisions
take precedence over contextual automatic-assignment policy.

True Pool does not prohibit manual ownership.

A manually claimed ticket can remain owned while its routing context
continues to match the same True Pool policy. Transitions into a
different pool context retire stale ownership and historical assignment
ToDos as required.

Restricted CCTV assignment holds also permit intentional manual ownership. When a ticket remains in the same Customer, Campus, Service Area, fulfilment party, and HD Team context, and its previous contextual assignment hold was already active, an existing manual owner is preserved. When routing changes into a restricted CCTV context, stale ownership is retired, previous assignment ToDos are cancelled, and `_assign` is cleared. No replacement technician is automatically selected while the restriction applies.

The canonical ownership state remains:

- Owned ticket: one Open assignment ToDo, mirrored in `_assign`.
- Unassigned ticket: no Open assignment ToDo, `_assign = []`.

### Native Assignment Rule safeguard

Linked HD Team Assignment Rules must respect:

`not custom_contextual_assignment_hold`

The existing contextual assignment durability mechanism reconciles
the canonical native rule condition during migration.

This safeguard is necessary but does not itself create customer-specific
Assignment Policies.

### Verified DEV scenarios

On 12 October 2026, the migrated DEV site verified:

| Context | Policy | Expected behavior |
|---|---|---|
| Emerald Life / CCTV | Customer / True Pool | No automatic owner |
| Customer B / Boschendal / CCTV | Customer/Campus / Round Robin | Native CCTV assignment |

DEV evidence:

- 58 targeted regression tests passed.
- Four real-ticket lifecycle scenarios passed.
- Both transitions between Round Robin and True Pool were verified.
- Temporary test tickets and assignment changes were rolled back.

DEV used `Customer B` as the Boschendal ERP Customer identity.
Production Customer and Campus identities must be independently
verified before configuration.

The DEV CCTV rule contained one technician; multi-technician
rotation fairness was not established by these lifecycle tests.

### Production activation boundary

Assignment Policy and Service Coverage records are operational database state, not application fixtures.

Production CCTV native Assignment Rules remain disabled. Deployment of the restricted-CCTV application code does not authorize their activation. Before enabling CCTV automatic assignment, verify the required customer-specific Assignment Policies, complete Customer and Campus context, matching eligible Service Coverage, native HD Team technician membership, and controlled DEV lifecycle evidence. Activation must follow the production release runbook and its explicit safety gates.

A production deployment must:

1. Keep new CCTV automatic assignment inactive until the relevant
   customer-specific protections are established.
2. Complete the production migration and verify the new DocType.
3. Create and verify Emerald Life's Customer-scoped CCTV True Pool policy.
4. Configure and verify Boschendal's CCTV Round Robin policy.
5. Verify native CCTV technician membership and applicable Service Coverage.
6. Activate the native CCTV Assignment Rule only after the preceding
   protections and configuration checks have passed.
7. Record controlled production assignment smoke-test evidence.

The exact release commands and safety gates belong in
`docs/runbooks/production-runtime-release.md`.

The detailed operational ownership behavior belongs in
`docs/runbooks/ticket-assignment-contract.md`.

---

## Purpose

This document captures the intended TELECTRO pilot model for user access, service coverage, routing, and team visibility.

The personnel and service-area updates show that TELECTRO does not operate as one flat technician pool. Team coverage varies by customer, campus, and service area. The pilot therefore needs to keep **access control** separate from **operational coverage**.

Core principle:

```text
Access ≠ Coverage
```

## Access model

Access answers:

```text
What is this user allowed to do in the system?
```

This should continue to be controlled by Frappe Users, Roles, and Role Profiles.

Examples:

```text
TELECTRO-POC Profile - Technician
TELECTRO-POC Profile - Coordinator-Technician
TELECTRO-POC Profile - Supervisor
TELECTRO-POC Partner roles
TELECTRO-POC Partner Creator roles
```

Role Profiles should stay focused on system capability:

```text
Can the user log in?
Can the user work tickets?
Can the user coordinate/reassign/handoff?
Can the user supervise queues?
Can the user use Partner-safe pages?
Can the user create Partner requests?
```

Role Profiles should **not** be multiplied for every customer, campus, or service area combination.

Avoid patterns such as:

```text
Technician - Boschendal - Routing
Technician - Boschendal - PABX
Technician - Lanzerac - CCTV
Technician - Customer A - Internet
```

That would make access management brittle and difficult to maintain.

## Coverage model

Coverage answers:

```text
Where can this person work, assist, route, or be considered part of the team?
```

Coverage should be modelled separately from Role Profiles.

Coverage is contextual and may depend on:

```text
Customer
Campus / Site Group
Service Area
Person / User
Primary or backup responsibility
Active/inactive state
```

Example conceptual rows:

```text
Scope              Customer/Campus     Service Area          User                  Coverage
Customer/Campus    Boschendal          Routing               tech.alfa@local.test  eligible
Customer/Campus    Boschendal          PABX                  tech.bravo@local.test eligible
Customer/Campus    Lanzerac            CCTV                  tech.charlie@local.test eligible
Default            Telectro default    Internet Connection   hendrik@local.test    eligible
Default            Telectro default    Other                 hendrik@local.test    fallback
```

## Fallback rule

Customer/campus-specific coverage should win.

Fallback rule:

```text
1. Try customer/campus-specific coverage for the ticket's service area.
2. If no match exists, use Telectro default coverage for that service area.
3. If no service-area match exists, use a safe default queue/team.
```

This keeps dedicated customer/campus support possible without losing a general Telectro fallback.

## Proposed V1 data shape

A future custom DocType or import-backed table could be shaped around:

```text
TELECTRO Service Coverage
```

Suggested fields:

```text
user
person_name
customer
campus
service_area
coverage_scope
is_primary
is_backup
active
notes
```

Minimum viable V1 fields:

```text
user
campus_or_scope
service_area
active
```

Possible `coverage_scope` values:

```text
Customer/Campus
Default
```

Possible future extensions:

```text
primary / backup ranking
after-hours coverage
escalation order
temporary coverage override
date-valid coverage
```

## Intended consumers

The service coverage model should eventually support:

```text
Routing target selection
My Team Tickets / Team Work Queue visibility
My Team Load drill-downs
Assist visibility for technicians
Coordinator/supervisor workload views
Backup/escalation logic
```

## Routing implications

Current routing should not be rewritten blindly.

Future routing should consider:

```text
Ticket customer
Ticket campus / site group
Ticket service area
Coverage rows
Fallback default coverage
Current assignment rules
Partner fulfilment rules
```

The safest future routing flow:

```text
1. Determine ticket train:
   - Internal Telectro work
   - Partner-originated / Telectro-fulfilled
   - Telectro-originated / Partner-fulfilled

2. Determine customer/campus/service area.

3. Resolve eligible coverage rows.

4. Select target user or queue according to the pilot routing policy.

5. Preserve the single-accountable-owner assignment invariant.
```

## My Team visibility implications

Technician feedback indicates that team visibility is not only about counts.

The current `My Team Load` style gives useful aggregate information, but technicians also need to answer:

```text
Which actual tickets are in my team/customer/service-area context where I can help?
```

This suggests a future report such as:

```text
My Team Tickets
```

or:

```text
Team Work Queue
```

Purpose:

```text
Show active tickets that fall within the current user's service coverage context.
```

Possible filters:

```text
Customer
Campus
Service Area
Assigned Owner
Status
Severity
Bucket
```

Suggested sort:

```text
Severity
Modified desc
Due / SLA risk where available
```

## Relationship to existing reports

Existing reports should not all be replaced.

This model should complement:

```text
My Current Work
My Team Load
Partner Workflow War Room
New Partner Tickets
Tickets Assigned to Partner
Tickets Submitted by Partner
Partner Current Work
```

Likely future changes:

```text
My Team Load:
  Remain useful as aggregate counts.

My Team Tickets / Team Work Queue:
  Become the drill-through report for actual tickets.

Routing:
  Gradually consume service coverage once the model is stable.
```

## Verified existing implementation anchors

Initial code inspection confirms that the pilot already has stable ticket context fields that can support service coverage without adding new HD Ticket fields.

Existing HD Ticket context fields:

```text
custom_customer
custom_site_group
custom_service_area
```

These fields are already used across:

```text
HD Ticket custom field fixtures
site/campus validation
ticket routing
Partner ticket creation
Partner-safe ticket detail
Partner reports
My Current Work
Repeat Faults by Location
Share Ticket Context
workspace/report context display
```

This means the Service Coverage model should consume the existing ticket context rather than create parallel customer, campus, or service-area fields.

## Verified routing anchors

Existing routing already separates several concerns:

```text
custom_service_area -> agent_group/team routing
custom_site_group -> campus-aware routing policy
_assign / ToDo -> accountable owner state
```

The current campus-aware routing policy treats Campus / `custom_site_group` as the primary routing anchor and returns a policy result rather than directly mutating `_assign`.

This is a useful boundary for V1.

Service Coverage should not initially replace the current routing policy. It should first provide a verified coverage lookup model that can be consumed by reports and later by routing.

## V1 implementation decision

For V1, Service Coverage should power visibility before assignment.

Initial consumer:

```text
My Team Tickets / Team Work Queue
```

Purpose:

```text
Show active tickets that fall within the current user's customer/campus/service-area coverage context.
```

Non-goal for V1:

```text
Do not automatically reassign tickets from Service Coverage yet.
Do not change Partner workflow ownership rules.
Do not change the single-accountable-owner invariant.
Do not replace My Current Work or My Team Load.
```

Recommended report relationship:

```text
My Current Work:
  Personal action queue: assigned, shared, and workflow items needing attention.

My Team Load:
  Aggregate workload/count view.

My Team Tickets / Team Work Queue:
  Drill-through list of actual tickets in the user's coverage context.
```

## Proposed V1 lookup behaviour

Suggested first matching order:

```text
1. Match active coverage rows for exact Customer + Campus + Service Area.
2. If no rows match, try Campus + Service Area.
3. If no rows match, try Customer + Service Area.
4. If no rows match, try Default + Service Area.
5. If no rows match, fall back to existing team/queue visibility.
```

V1 should be read-only from a routing perspective. Once the report behaviour is proven with real Telectro data, routing can consume the same coverage lookup later.

## Relationship to Partner workflow

Partner workflow states remain separate from service coverage.

Coverage should not break or bypass:

```text
Partner acceptance state
Partner work state
Partner evidence visibility
Partner-safe ticket page
Partner notifications
Partner acceptance/rework audit trail
```

Partner-related trains should continue using the existing controlled Partner workflow actions.

## Relationship to ticket sharing

Coverage is not the same as sharing.

Use:

```text
Share Ticket Context
```

when a specific person needs to review or assist with a specific ticket.

Use coverage when:

```text
The system needs to know which team/persons are generally relevant for a customer/campus/service-area context.
```

A shared ticket should remain visible in `My Current Work` as personal shared work.

Coverage-based team visibility should power broader team reports.

## Pilot decision

For the TELECTRO pilot:

```text
Role Profiles control access.
Service Coverage controls operational context.
```

Do not encode customer/campus/service-area mutations into Role Profiles.

## Open questions

```text
Should coverage rows be maintained manually in a DocType, imported from spreadsheet, or both?

Do we need primary vs backup coverage in V1?

Should campus-specific coverage override customer-level coverage?

Should coverage drive routing immediately, or first only drive reports?

Should technicians see all tickets in their coverage context, or only tickets owned by people in the same coverage group?

How should Partner/customer users be represented in coverage, if at all?

How should inactive/temporary coverage be handled?
```

## Recommended next steps

```text
1. Normalise the personnel and service-area spreadsheets into one coverage matrix.
2. Confirm the user/account access matrix separately.
3. Decide the V1 TELECTRO Service Coverage DocType shape.
4. Create a small fixture/import path for coverage rows.
5. Build My Team Tickets or Team Work Queue as the first consumer.
6. Only then adjust routing to use coverage.
```
