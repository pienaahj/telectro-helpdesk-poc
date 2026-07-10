# Pilot Phase 2 Enhancements

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
