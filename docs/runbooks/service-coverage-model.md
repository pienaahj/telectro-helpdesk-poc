# TELECTRO Service Coverage Model

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

