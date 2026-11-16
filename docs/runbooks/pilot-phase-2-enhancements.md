# Pilot Phase 2 Enhancements

## Accepted Phase 2 specification — 16 November 2026

**Status: business scope approved for development planning; implementation and production deployment remain unauthorized.**

### Business requirement and acceptance criterion

Pierre's authoritative requirement is:

> I would like to know what my technicians are busy with and how much time they spend on it.

This is the primary acceptance criterion. Telectro needs lightweight employee
time booking suited to a small, informally operated business. Evaluate every
feature against this requirement. The booking interface must be simple and quick.

This section defines the accepted functional scope and takes precedence over
conflicting historical candidates below. The original material is retained for
traceability. Phase 2 remains separate from the current pilot baseline and the
current production correction release.

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
