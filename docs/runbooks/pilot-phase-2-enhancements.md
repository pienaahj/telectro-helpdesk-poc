# Pilot Phase 2 Enhancements

## Accepted Phase 2 specification — 16 November 2026

**Status: business scope approved for development planning; implementation and production deployment remain unauthorized.**

### Business requirement and acceptance criterion

Pierre's authoritative requirement is:

> I would like to know what my technicians are busy with and how much time they spend on it.

This is the primary acceptance criterion. Telectro needs lightweight employee
time booking suited to a small, informally operated business. Evaluate every
feature against this requirement. The booking interface must be simple and quick.

This section defines the original accepted functional scope and takes precedence
over conflicting historical candidates below. The dated V1 revision that follows
takes precedence on the decisions it explicitly updates. The original material
is retained for traceability. Phase 2 remains separate from the current pilot
baseline and the current production correction release.

### Time booking and work contexts

Use native ERPNext Timesheet and Timesheet Detail. Technicians must be able to
record actual working hours, identify their work, associate appropriate references,
and view and correct their own bookings. Mistaken or duplicate entries must be
correctable without an approval process.

| Work context | Intended association |
| --- | --- |
| Helpdesk | HD Ticket |
| Project | Lightweight ERPNext Project; Task optional |
| Customer Support | Customer-related assistance without a required ticket or Project |
| Internal | Administration, planning and other internal activities |

Emergency/Unplanned is an independent classification, not another hours ledger
or an additional work context. It must never duplicate booked hours. Retain native
Activity Type and Description.

### Operational customer identity and retention

Reuse HD Customer, subject to appropriate authorization. An HD Customer may exist
without an ERPNext Customer, User or Contact; this was functionally verified in
DEV. Support more than 100 operational customers not yet onboarded into ERPNext,
using the existing optional HD Customer → ERPNext Customer relationship.

Preserve stable legacy/Gwizz identification when available. The precise
migration-key mechanism remains an implementation decision.

Booked hours must remain available when a referenced Project or ticket is
completed, archived or subsequently removed. Prevent accidental loss of historical
booking information. Exact deletion/archiving safeguards and the correction audit
mechanism require design and verification; ordinary reference deletion must not
silently erase the booking history.

### Reporting

The primary report is **Employee Booked Hours**, with progressive drill-down:

Company → Employee → Work Context → Customer / Ticket / Project → Individual Time Entry.

Support a work-first view where practical. Count each valid booking once, including
native Draft Timesheet entries. Do not derive booked hours from native Project
actual-time totals: these were verified to update on Timesheet submission.

A secondary **Booking Completeness & Integrity** report may identify missing,
duplicate, inconsistent or unclassified bookings. It is not an SLA performance
report. Its detection rules remain to be designed without introducing expected
hours or capacity targets.

### Technical candidates and security requirements

Native Timesheet Detail is the authoritative employee-hours ledger. Four proposed
custom fields are implementation candidates only, not authorization to create them:

- `custom_work_context`
- `custom_hd_customer`
- `custom_hd_ticket`
- `custom_emergency`

Native Timesheet fields continue to handle Employee, Company, Activity Type,
Project, Task, duration and description. Use a narrowly scoped technician-facing
interface; do not grant ordinary Technicians broad Projects User or HR roles.

Preserve existing Telectro Helpdesk and customer privacy controls. Enforce:

- Authenticated employee identity and technician access to their own bookings.
- Server-side ticket-reference authorization.
- Customer and Project reference consistency.
- Restricted management-report access.
- No unauthorized ticket details in lookups or reports.
- No privileged native Timesheet access through alternate APIs.

Existing Helpdesk permissions are unchanged by this specification update.

### Explicit exclusions and historical disposition

The minimum implementation excludes:

- Timesheet submission, approval workflows and coordinator approval queues.
- Expected working hours, employee capacity targets, productivity measurements
  and employee scoring.
- SLA performance calculations, stop-the-clock or jeopardy management,
  explanations for SLA breaches and supplier-delay attribution.
- Customer/contract/site time budgets.
- Profitability, financial balancing and billing workflows.
- Full Project Management and HR/payroll implementation.

Earlier requirements are retained below with these explicit dispositions:

| Historical requirement or option | Disposition for this build |
| --- | --- |
| Monthly budgets, budget remaining and budget-exceeded behavior | Deferred; booked-hour totals do not imply budget tracking |
| Approval and submission questions | Superseded by own-booking correction without approval and Draft-inclusive reporting |
| Ticket-only time logs, ticket child table or separate time-log DocType | Superseded by the native Timesheet Detail ledger across the four contexts |
| Internal work and Project linkage question | Resolved by the accepted contexts; Project Tasks remain optional |
| Billable/non-billable reporting and financial processes | Deferred; preserve native fields without introducing billing workflows |
| Site/location and contract reporting extensions | Deferred beyond the minimum customer/ticket/Project drill-down |
| Active versus waiting time, blocker fields and supplier attribution | Deferred; historical section 2 is outside this build |
| Partner time, wider staff participation and Customer-visible time | Deferred; no additional access or participation is authorized |
| Android application, automatic capture and external time tools | Deferred; historical section 3 is outside this build |

Historical monthly employee/customer totals and ticket breakdowns remain useful
booked-hours views, without capacity, productivity, SLA or budget interpretations.

### Accepted DEV feasibility evidence — do not repeat

The following are accepted prior demonstrations, not instructions to rerun tests:

- Employee/User relationship established for Bravo.
- Native Project created without Tasks.
- Native Draft Timesheet persisted.
- Correct duration and non-billable calculations.
- Native submission tested and rolled back.
- Project actual-time update on submission verified.
- Standalone HD Customer creation and rollback verified.
- HD Customer to ERPNext Customer mapping verified.
- Existing ticket authorization interfaces identified.
- Positive ticket visibility checked for Bravo.
- Timesheet Detail has no existing custom fields.

Persistent DEV Timesheet `TS-2026-00001` is Draft with 0.75 hours against
`PROJ-0001`. Project actual hours are zero following the verified submission
rollback. Submission feasibility does not add submission to the accepted scope.

### Development boundary and remaining implementation decisions

Canonical Telephony source remains inside the existing DEV backend container at
`/home/frappe/frappe-bench/apps/telephony`. The Mac repository overlay must not be
assumed synchronized. Future source synchronization uses
`bin/pull-telephony-changes.sh`, with explicit `--include-new` paths for approved
new source files; fixtures use the separate controlled fixture-export workflow.
No synchronization is part of this documentation task.

This runbook update belongs in the Mac Git repository. It authorizes no canonical
DEV code, DocType, fixture, permission, database or container changes, and no
production deployment.

Implementation design still needs review of:

- Context-specific required references and customer/Project consistency rules.
- Employee identity resolution, management scope and alternate-API containment.
- Simple booking interaction, time input and Draft grouping conventions.
- Correction audit, duplicate handling and historical deletion/archiving safeguards.
- Stable legacy/Gwizz migration keys.
- Work-first presentation and optional integrity-report detection rules.

## Approved V1 Time Booking revision — 25 November 2026

The owner accepted the B3.88A.2 source assessment and approved the business
policy recorded here. The B3.88A.5 consolidation and roadmap were accepted with
the B3.88A.5A qualifications below. This revision records business decisions
and checkpoint order. Implementation, migration, dormant production deployment,
and operational activation require their respective approvals.

> Time Booking records the work that actually took place, not the administrative events surrounding that work. Ticket lifecycle, SLA performance and actual technical effort remain independent measurements.

### Ticket lifetime and manual creation

- Eligible Technicians can record their own actual work retrospectively against
  an existing Ticket, subject to current Ticket authorization for new bookings.
  Multiple eligible Technicians may record their contributions to the same Ticket.
- Resolved is Telectro's operational completion state. Administrative closure is
  optional. Use valid resolution evidence as the inclusive upper boundary for
  completed Tickets. A reopened Ticket has one continuous lifetime, including
  any earlier resolved gap. For active Tickets, including Paused, the full work
  interval must end at or before the server's current site-local time. Future
  work is prohibited in all cases.
- Use Ticket creation as the lower boundary for Portal, Email and unverified
  origins. A Ticket with positively verified manual origin permits work wholly
  before or spanning its creation, including work prompted by monitoring. The
  Ticket must exist at submission. Keep native Ticket creation, opening,
  resolution and SLA timestamps intact.
- Identify manual origin automatically. Preserve the existing Request Source
  field's meaning, routing and edit behaviour. Reuse trusted creation metadata
  where available, with a minimal server-owned creation marker as the next
  option. Client-supplied values, copies and ordinary updates cannot establish
  manual origin. Missing Portal or Email indicators alone are insufficient.
  The Technician supplies no origin selection or additional mandatory input.
  The solution requires no separate administration workflow or broad historical
  classification. Consider a new DocType only if existing mechanisms prove
  insufficient. A.6 will establish the trusted staff create path and verify the
  provenance mechanism. Positive evidence of manual creation is sufficient for
  V1, so exhaustive classification of creation routes is unnecessary.
- Keep one work interval and count its total once. Derive its pre-creation
  portion as `max(0, min(end, ticket_creation) - start)` and show the portion to
  the Technician. Preserve the smallest stable server-owned attribution value
  needed to retain the accepted portion after reference loss. A.7 will establish
  the storage and audit mechanism. Keep the existing Activity Type, work
  description, 1,440-minute maximum and overlap safeguards. There is no extra
  investigation duration or justification field, mandatory Investigation
  Activity Type, pre-creation lookback limit, or ratio to Ticket lifetime.

### Historical maintenance, authorization and retention

- Preserve established authority over owned historical bookings after Ticket
  reassignment or resolution. A description-only correction with the same Ticket
  and unchanged interval may use the existing booking's authorization without
  revalidating that Ticket reference or interval solely because the description
  changed. Apply the same principle to description-only submitted replacement.
  Preserve Technician identity, managed provenance, ownership, revision,
  Customer consistency, privacy and correction audit. Submitted replacement
  must preserve atomicity and replay safeguards.
- Keep historical booked hours and audit evidence after Ticket or Project
  completion, archival or removal. Keep protected Ticket content and lookups
  subject to current access. Historical booking visibility and maintenance confer
  no broader Ticket read access or authority to create a new booking or select a
  different Ticket. Verify retention and privacy, including missing references,
  using the existing native safeguards and report access controls.
- Preserve existing bookings when lifecycle evidence is missing or inconsistent.
  Reject new or changed Ticket intervals when necessary evidence is unreliable.
  Modification time, SLA deadlines and unrelated fields cannot substitute for
  missing lifecycle evidence. Broad historical data repair is outside this work.
- **Outstanding for A.8.** Decide whether and under what constraints an eligible
  Technician who has lost Ticket read access can change the start time or
  duration of an existing, legitimately authorized booking against the same
  Ticket. A blanket restriction on those changes has not been approved. This
  decision leaves A.6 and A.7 preparation open to proceed under their respective
  approvals. It does not expand Ticket visibility or call for historical
  assignment reconstruction.
- Preserve Project and Task grant authorization and temporal coverage across the
  booked interval. Retain the accepted Ticket assignment-history, worker-grant,
  Assignment Capture Receipt and temporal coverage implementation. Initial V1
  Ticket booking has no dependency on assignment capture, historical assignment
  episode or worker-grant coverage, or historical-work attestation.

### Role, reporting and superseded requirements

A Coordinator is a Technician with selected additional operational privileges,
including Ticket reassignment and visibility of selected Supervisor functions
and reports. Intake organization, dispatch of all Tickets and managing
Technicians are outside the inherent responsibilities of this role. Supervisor
permissions remain explicitly scoped.

The revision supersedes the B3.88A.2 proposal to use Ticket creation as a
universal lower bound, any requirement to reconstruct individual reopened or
assigned periods for initial Ticket booking, and any requirement to rerun Ticket
authorization and lifetime checks for an unchanged reference and interval in a
description-only correction. Historical rationale and accepted evidence remain
part of the record.

Retain Draft-inclusive reporting and the existing exclusions for available-hours
reconciliation, artificial gap filling, capacity analysis, productivity scoring,
individual rankings, priority-based time analysis, HR/payroll, and booking
approval workflows. Routine Technician submission remains outside the V1 scope.
Audited maintenance of an already submitted booking is covered by the historical
correction requirements above.

### Approved checkpoint roadmap and release gates

| Checkpoint | Classification and dependency | Acceptance target |
| --- | --- | --- |
| **B3.88A.6 — Trusted manual origin** | Mandatory before activation. First independently verifiable implementation slice. | Automatic positive evidence from the verified manual create path. Portal, Email, copied, imported and unknown Tickets cannot qualify by default, payload or ordinary edit. |
| **B3.88A.7 — Ticket interval and attribution** | Mandatory before activation. Depends on A.6. | One server-side interval policy covers creation, changed Draft corrections and changed submitted replacements, with visible and stable pre-creation attribution. Prove lifecycle boundaries, concurrency, Customer consistency and unchanged Project/Task coverage. |
| **B3.88A.8 — Historical maintenance and retention** | Mandatory before activation. Preparation can run alongside A.7. Finalize the open interval-correction boundary before implementing that case. | Prove description-only maintenance after loss of Ticket read access, atomic replacement, replay, and historical hours and audit retention without protected reference disclosure. |
| **B3.88A.9 — Print Heading and fixture disposition** | Mandatory for dormant deployment. Can proceed independently of A.6–A.8. | Resolve the Print Heading discrepancy through a separately approved change. Review the 12 previously excluded DEV fixture differences against the candidate and target. Reconcile release-relevant differences and keep unrelated differences deferred. Preserve the accepted Customer mapping index and Workspace fixture scope. |
| **B3.87M.167E.2B — Full DEV migration durability** | Mandatory for dormant deployment. Blocked on A.9 and separate migration authorization. | After each of two full DEV migrations, verify Workspace anchor placement, native links, roles, widget IDs and duplicate counts, the Customer mapping index, and the `TS-2026-00017` fingerprint. Verify the approved Print Heading state, Assignment Capture Receipt first-install contract with capture off, and restoration of all 20 My Team Load roles before reopening site traffic. |
| **B3.88A.10 — Immutable dormant candidate** | Mandatory for dormant deployment. Follows fixture disposition and DEV migration durability for the selected scope. | Validate the immutable image, embedded code and fixtures, applicable inherited and Phase 2 semantic validators, and site-aware flag-off behavior. Prove booking containment through APIs and managed native insertion, separate report and Workspace access controls, preservation of normal Timesheet and Helpdesk behavior, and readiness for the runtime-to-migration window and rollback. |
| **B3.88A.11 — Operational preparation and booking activation** | Configuration can follow dormant deployment or proceed in parallel where safe. Activation requires a validated deployed candidate containing the accepted A.6–A.8 behavior and verified participant readiness. | Verify eligible User–Employee–Company links, Activity Types, Customer mappings, applicable Project/Task and Supervisor grants, and Technician workflows. The site flag opens booking to all eligible Technicians, so a restricted pilot needs a reviewed eligibility design. Document that hard disable preserves data and also disables managed history and corrections. |
| **B3.88A.12 — Structured email and routing pilot** | Separate operational rollout. Depends on approved folders, verified sender/Customer data and routing readiness. | Keep incomplete requests private and traceable, reply once per pending thread, and promote a qualifying reply into one linked Ticket using native threading and deduplication. Preserve existing mail flows outside the pilot. Ordinary customers use shared Default True Pool. Validate Pool suppression and Claim eligibility. Dedicated Teams and scoped Round Robin are justified exceptions. |

Print Heading remains a release blocker. The known reimport would drop the
unique `print_heading` index, change the module from Setup to Printing, remove
explicit naming-rule metadata, and replace `Desk User` read permission with
`All`. Both full DEV migration passes remain pending. Minimum dormant production
scope keeps managed booking and assignment capture off. Existing Helpdesk and
ordinary Timesheet paths remain available, and report and Workspace access stays
within existing role and data scope.

Customer and Project onboarding, documentation, training and management
preparation run in parallel. Use native Frappe capabilities and existing
Administrator grant workflows. Missing operational master data outside the
release scope does not gate dormant deployment. Defer unrelated fixture cleanup,
Supervisor grant browser actions (B3.87M.167D.2), correction-only deactivation,
and Ticket assignment capture cutover beyond the initial release or activation
where applicable.

---

## Historical enhancement candidates — retained context

The following original plan is preserved. Conflicts and broader requirements are
superseded or deferred according to the accepted specification above; they are
not additional requirements for the minimum Phase 2 build.

## Purpose

This document captures important post-pilot enhancement candidates for the ERPNext / Helpdesk pilot.

These items are intentionally not part of the current Boschendal pilot rollout baseline unless Telectro explicitly changes the pilot scope.

The current pilot rollout remains focused on:

1. training and onboarding material;
2. production installation;
3. production login, email, HTTPS, Customer portal, and Partner workspace proof;
4. first pilot users;
5. stable V1 request lifecycle operation.

Phase 2 items should be preserved because they may require custom fields, reports, workflow changes, mobile workflow changes, permissions, training updates, and production migration planning.

---

## Scope rule

Phase 2 enhancement candidates must not silently expand the current pilot rollout.

Before implementation, each candidate should be reviewed for:

* business priority;
* operational impact;
* required custom fields;
* required reports;
* required permissions;
* Customer visibility impact;
* Partner visibility impact;
* data migration impact;
* training impact;
* production deployment risk.

---

## 1. Technician time logging and monthly time budget reporting

### Request

Telectro management requested technician time management for the Boschendal pilot.

The requirement is to record time spent by technicians and report how that time was used against a monthly time budget.

The expected reporting need includes:

* technician;
* ticket;
* Customer / Account;
* site or location;
* date;
* time spent;
* work category;
* monthly total per technician;
* monthly total per Customer / Account;
* ticket-level breakdown of where the monthly time budget was spent.

### Initial interpretation

This should be treated as a Phase 2 operational reporting enhancement.

The current pilot already covers:

* request capture;
* routing;
* accountable ownership;
* Customer-visible updates;
* Partner collaboration;
* controlled resolution;
* coordinator and supervisor review.

Time logging adds a new measurement layer on top of the ticket lifecycle.

It should be designed deliberately rather than added casually during final rollout preparation.

### Open design questions

Before implementation, confirm:

* Should only technicians log time, or should coordinators and supervisors also log time?
* Should Partner time be captured?
* Should time be captured manually, automatically, or both?
* Should time be recorded as minutes, decimal hours, or start/stop intervals?
* Should time entries require approval?
* Should time entries be Customer-visible?
* Should time be billable / non-billable?
* Should time be linked only to HD Tickets, or also to internal work, site visits, and projects?
* Is the monthly budget per Customer, site, contract, technician, or team?
* What should happen when the monthly budget is exceeded?
* Should reporting distinguish active work from waiting time?

### Possible implementation options

Potential implementation paths include:

1. HD Ticket child table for time entries.
2. New custom DocType for ticket time logs.
3. ERPNext Timesheet integration, if suitable.
4. Lightweight mobile-friendly ticket time action.
5. Later Android/mobile workflow if browser-based entry is insufficient.

The selected approach should be based on existing ERPNext / Frappe / Helpdesk capabilities before custom code is added.

### Possible future reports

Future reports may include:

* Time spent by technician per month.
* Time spent by Customer / Account per month.
* Time spent by ticket.
* Time budget used vs remaining.
* Tickets consuming the most time.
* Active work vs waiting / blocked time.
* Partner time vs Telectro time, if Partner time is captured.
* Billable vs non-billable time, if required.

### Pilot decision

Do not include this in the current rollout baseline unless explicitly re-scoped.

Treat technician time logging and monthly budget reporting as a likely first post-pilot upgrade candidate.

---

## 2. Waiting on equipment / stock / supplier dependency classification

### Request

Telectro management raised that some faults or installations cannot progress because required equipment may be supplied by another party or may be outside Telectro’s direct control.

This creates a reporting issue.

A ticket may appear open, stale, or unresolved even though the reason is a legitimate external dependency.

### Initial interpretation

The current pilot already has process guidance for stale and blocked tickets.

However, Phase 2 may need a more reportable ticket-level classification for why a ticket is waiting.

### Possible future field

A future HD Ticket field may be required.

Possible field names:

* `Waiting Reason`
* `Blocker Type`
* `Dependency Type`
* `External Dependency`
* `Progress Blocker`

Possible values:

* Not waiting
* Waiting on Customer
* Waiting on Partner
* Waiting on Supplier
* Waiting on Equipment
* Waiting on Stock
* Waiting on Site Access
* Waiting on Internal Decision
* Waiting on Scheduled Visit
* Other

### Reporting value

This would help Telectro distinguish between:

* active technician work;
* neglected work;
* legitimate waiting state;
* Customer-caused delay;
* Partner-caused delay;
* supplier or stock delay;
* equipment dependency;
* internal decision delay.

### Design caution

This should not become a vague replacement for clear ticket notes.

If a waiting/blocker field is added, the ticket should still require clear internal or Customer-visible communication explaining the practical next step.

### Pilot decision

Do not add this field during the current rollout unless it becomes essential for go-live.

Capture it as a Phase 2 enhancement candidate.

---

## 3. Android or mobile time logging investigation

### Request

Telectro asked whether an Android application could be used as an interim solution for technician time logging.

### Initial interpretation

This should be researched separately.

Introducing an external Android tool may create duplicate capture, reconciliation overhead, and process split between Helpdesk tickets and time reporting.

A browser-based mobile-friendly ERPNext / Helpdesk workflow may be simpler if it can satisfy the operational need.

### Investigation questions

Before choosing an interim tool, confirm:

* Can technicians log time against a ticket reference?
* Can time data be exported cleanly?
* Can time be grouped by technician, Customer, ticket, and month?
* Can the process work with weak mobile connectivity?
* Does each technician need a separate installed app?
* Does management need live dashboards or only monthly reporting?
* How much manual reconciliation would be needed?
* Would a small ERPNext / Helpdesk enhancement be safer than introducing a separate app?
* Can the tool support auditability and correction of incorrect entries?

### Pilot decision

Research only after training material and production installation are under control.

Do not select or implement an Android interim tool during the current rollout slice.

---

## Recommended priority

### Current rollout priority

Keep current effort focused on:

1. onboarding pack;
2. role guides;
3. Activity Process Guides;
4. production install;
5. production proof;
6. first pilot onboarding.

### First post-pilot candidate

Technician time logging and monthly time budget reporting should be treated as the first serious post-pilot enhancement candidate.

It is important, but it should be designed properly because it affects data model, reporting, technician workflow, supervisor review, and possibly Customer/account reporting.
