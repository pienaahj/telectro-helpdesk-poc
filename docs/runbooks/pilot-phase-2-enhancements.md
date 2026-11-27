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

The [Customer identity decision](customer-location-and-organisation-model.md#customer-identity-decision)
records the implemented Ticket mapping and the functional booking inheritance
and reporting requirements that must pass before activation.

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

#### REP-01–06 management reporting acceptance register

The owner approved management reporting on actual recorded time. Pierre’s
business acceptance follows the Supervisor browser check.

| ID | Business requirement | DEV implementation and acceptance check |
| --- | --- | --- |
| REP-01 | See which Technicians did what work and how much time they recorded. | Technician Breakdown groups by Company, Employee, Work Context, saved Customer and permitted references. Narrow using the same filters and switch to Booking Detail for individual entries. |
| REP-02 | Start with work or Customer and identify the contributing Technicians. | Customer and Work Context breakdowns show contributing Employees and Companies. Customer attribution distinguishes listed, unlisted, unattributed and not applicable. |
| REP-03 | Break down Projects, work references, Service Areas and activities. | Project / Reference, Service Area and Activity views use the permission-checked projection. Restricted and missing historical references retain their hours under separate labels. |
| REP-04 | Inspect authorized individual bookings and descriptions. | Booking Detail shows recorded and report-counted intervals, work metadata and a spreadsheet-safe Timesheet Detail description. A restricted, missing or unverified linked reference blanks the associated description. |
| REP-05 | Reconcile every view against the same actual booked time. | The same managed Draft and Submitted population feeds every view. Each clipped slice contributes to one row per view, and the native total row sums that partition. Cancelled and withdrawn work is excluded. Emergency and pre-creation are portions of booked time. |
| REP-06 | Verify actual Supervisor grants, scope, browser drill-down and exports. | Use the existing Supervisor Reporting Grant and native report and CSV/Excel paths. Verify roster and Customer limits and denial for an ordinary Technician, Coordinator without the Supervisor role and unauthorized user. Owner browser and functional acceptance are recorded. Pierre’s feedback remains a separate gate. |

Saved operational Customer values drive grouping. The existing Customer
authorization also applies to exports. Reference filters match exact authorized
display identities and offer no unrestricted master-data suggestions. The
existing Ops Workspace report link remains the entry point.

The 26 November owner decision retains this report and register as the first
pillar of the [approved management intelligence specification](#approved-management-intelligence-specification--26-november-2026).

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

The 26 November approval adds the narrow Customer Labour Cost Analysis
exception described below. It authorizes operational exports and local Excel
analysis with manual financial inputs. The original accounting, billing,
payroll and full-profitability exclusions remain in force.

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
- **A.8A — Owner approved on 26 November 2026 (Africa/Johannesburg).** An
  eligible Technician may correct the start time or duration of their own
  legitimate historical booking against its saved Ticket after losing Ticket
  read access. The corrected end must be at or before both the applicable A.7
  lifecycle upper bound and the server-owned creation timestamp of the original
  logical booking. Repeated Draft corrections and submitted replacements
  preserve that boundary. Current Ticket access permits ordinary corrections
  under the existing A.7 rules. The decision preserves historical maintenance
  independently of live reference authority, with no correction age limit or
  reconstruction of assignment history.
- Restricted lifecycle validation follows ownership, managed provenance and
  revision checks and uses only the saved Ticket. Missing or unreliable
  lifecycle evidence blocks a changed interval. Description maintenance
  preserves the saved work and Customer identity, including a historical blank,
  and its attribution. New bookings and changed references require current
  authorization. Project and Task interval changes still require full grant
  coverage.
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
| **B3.88A.8 — Historical maintenance and retention** | Mandatory before activation. Owner approved A.8A on 26 November 2026. | Prove description and bounded interval corrections after loss of Ticket read access, immutable original creation evidence, atomic replacement, replay, and historical hours and audit retention without protected reference disclosure. |
| **REP-01–06 — Supervisor Booked Hours** | Internal functional closure recorded. Existing DEV and export evidence retained. | Record Pierre’s business acceptance separately. |
| **DASH-01–10 — Technician Work Overview** | Internal owner acceptance closed at B3.88REP.2C. Management usability remains part of operational activation. An otherwise-authorized dormant deployment can proceed independently. | Retain Supervisor Booked Hours reconciliation and owner browser evidence. Obtain Pierre’s feedback separately. |
| **COST-01–09 — Customer Labour Cost Analysis** | Internal acceptance closed on 27 November 2026. Owner Excel and management presentation acceptance passed. | Complete Customer and Current Project onboarding and confirm Pierre's exact User and separately approved reporting grants before operational use. Pierre's acceptance using actual business data remains pending. |
| **UI-01–12 — Consolidated Technician UI improvements** | A.2.1 and A.2.2 owner acceptance closed. A.2.4 contextual Work Origin technically verified in DEV. | Obtain A.2.4 owner browser acceptance. A.2.3 Customer and Service Area report selectors remain separately scoped. |
| **B3.88A.9 — Print Heading and fixture disposition** | Mandatory for dormant deployment. Can proceed independently of A.6–A.8. | Resolve the Print Heading discrepancy through a separately approved change. Review the 12 previously excluded DEV fixture differences against the candidate and target. Reconcile release-relevant differences and keep unrelated differences deferred. Preserve the accepted Customer mapping index and Workspace fixture scope. |
| **B3.87M.167E.2B — Full DEV migration durability** | Mandatory for dormant deployment. Blocked on A.9 and separate migration authorization. | After each of two full DEV migrations, verify Workspace anchor placement, native links, roles, widget IDs and duplicate counts, the Customer mapping index, and the `TS-2026-00017` fingerprint. Verify the approved Print Heading state, Assignment Capture Receipt first-install contract with capture off, and restoration of all 20 My Team Load roles before reopening site traffic. |
| **B3.88A.10 — Immutable dormant candidate** | Mandatory for dormant deployment. Follows fixture disposition and DEV migration durability for the selected scope. | Validate the immutable image, embedded code and fixtures, applicable inherited and Phase 2 semantic validators, and site-aware flag-off behavior. Prove booking containment through APIs and managed native insertion, separate report and Workspace access controls, preservation of normal Timesheet and Helpdesk behavior, and readiness for the runtime-to-migration window and rollback. |
| **B3.88A.11 — Operational preparation and booking activation** | Configuration can follow dormant deployment or proceed in parallel where safe. Activation requires a validated deployed candidate containing the accepted A.6–A.8 behavior and verified participant readiness. Plan for DASH management-usability acceptance at activation. | Verify eligible User–Employee–Company links, Activity Types, Customer mappings, applicable Project/Task and Supervisor grants, and Technician workflows. The site flag opens booking to all eligible Technicians, so a restricted pilot needs a reviewed eligibility design. Document that hard disable preserves data and also disables managed history and corrections. |
| **B3.88A.12 — Structured email and routing pilot** | Separate operational rollout. Depends on approved folders, verified sender/Customer data and routing readiness. | Keep incomplete requests private and traceable, reply once per pending thread, and promote a qualifying reply into one linked Ticket using native threading and deduplication. Preserve existing mail flows outside the pilot. Ordinary customers use shared Default True Pool. Validate Pool suppression and Claim eligibility. Dedicated Teams and scoped Round Robin are justified exceptions. |

Print Heading remains a release blocker. The known reimport would drop the
unique `print_heading` index, change the module from Setup to Printing, remove
explicit naming-rule metadata, and replace `Desk User` read permission with
`All`. Both full DEV migration passes remain pending. Minimum dormant production
scope keeps managed booking and assignment capture off. Existing Helpdesk and
ordinary Timesheet paths remain available, and report and Workspace access stays
within existing role and data scope.

**Project onboarding dependency — 26 November 2026.** The owner received
Telectro’s current `New_Project_Plan_Layout.xlsx` planning template. It covers
Project, Account, Client, Project Number, Project Owner and Telectro Invoice,
an action plan with due dates, assigned Technicians and completion dates,
travel kilometres and time, onsite and offsite labour hours, hardware,
third-party suppliers, connectivity, and Technician and Manager sign-off.
The current Project list was promised by close of business Friday,
27 November 2026. Keep the current import template until the actual list has
been received and assessed. This is an onboarding dependency for minimum
Project-based Time Booking. DASH delivery proceeds independently. Full
Project management, procurement, financial accounting and travel-cost
functionality remain outside the approved onboarding scope.

Customer and Project onboarding, documentation, training and management
preparation run in parallel. Use native Frappe capabilities and existing
Administrator grant workflows. Missing operational master data outside the
release scope does not gate dormant deployment. Defer unrelated fixture cleanup,
Supervisor grant browser actions (B3.87M.167D.2), correction-only deactivation,
and Ticket assignment capture cutover beyond the initial release or activation
where applicable.

---

## Approved management intelligence specification — 26 November 2026

The owner approved **B3.88REP.2** on Thursday, 26 November 2026. This
extends the Phase 2 business specification with three complementary pillars.
Management needs to see where recorded work was spent, inspect the contributing
entries and assess the commercial implications. Clear visual presentation and
practical navigation are functional acceptance requirements. The owner approved
the visual and interactive direction demonstrated in ChatGPT.

### Shared reporting authority and population

All three pillars use the native Timesheet ledger and the same authorized
booking population. Apply existing Supervisor Reporting Grants, Company and
Customer restrictions, saved historical Customer identity, and server-side
reference and description redaction. Reuse site-local date clipping and exact
aggregation. Include Draft and Submitted bookings, exclude Cancelled and
withdrawn bookings, and count replacements once. Emergency and pre-creation
work remain subsets of booked time. Preserve the existing reporting service,
authorization model and Helpdesk privacy throughout.

### Pillar 1 — REP-01–06 Supervisor Booked Hours

Retain Daily Summary, Technician Breakdown, Customer Breakdown, Work Context
Breakdown, Project / Reference Breakdown, Service Area Breakdown, Activity
Breakdown, and Booking Detail. Preserve comprehensive filters, authorized
descriptions, detail navigation, and Excel and CSV exports. The dashboard links
to the report for detailed analysis while preserving its existing capabilities.

The DEV implementation and technical evidence at
`d77d2b3338a63220f6e4a935d8a97e40eca19aad` remain accepted evidence for
the [REP-01–06 register](#rep-0106-management-reporting-acceptance-register).
Owner browser and functional acceptance were recorded on 26 November 2026.
Independent inspection of the owner’s downloaded filtered Excel export
confirmed TS-2026-00017, Boschendal and a numeric 0.250 booked hours.
The previously verified native CSV and Excel paths remain accepted evidence.
Pierre’s personal business acceptance remains a separate gate.

### Pillar 2 — DASH-01–10 Technician Work Overview

| ID | Approved requirement and acceptance check |
| --- | --- |
| DASH-01 | Show useful information on open using a sensible default period. Display actual recorded booked time with meaningful Technician and Customer summaries within scope. Management can start with the overview before filtering. Live activity inference is outside scope. |
| DASH-02 | Show Technician names and readable hours and minutes. Preserve stable Employee and Company identities and exact underlying values. |
| DASH-03 | Show visual distributions by Technician, Customer and Work Context so managers can see where work time was spent. Employee rankings and performance scores remain excluded. |
| DASH-04 | Let management explore by Technician, Customer, Work Context, Project, Service Area, Activity Type and permitted work reference, including Snapfix. Reveal detail progressively using familiar labels. |
| DASH-05 | Expand or drill into individual authorized work entries and show the full permitted description. Keep reference and description redaction and make detail readable without unnecessary horizontal scrolling. |
| DASH-06 | Offer Today, This Week, Last Week, This Month and Custom presets. Use the site timezone and show the dates actually selected. |
| DASH-07 | Open Supervisor Booked Hours with the applicable date range and active filters carried forward. Preserve all existing report and export capabilities. |
| DASH-08 | Reconcile dashboard totals and drill-down to Supervisor Booked Hours for the same scope and period. Aggregate precise underlying durations before display rounding. Count Emergency and pre-creation time within booked time. |
| DASH-09 | Reuse the existing authorized reporting population and projection. Enforce Supervisor, Company, Customer and reference restrictions on the server for summaries, selectors, detail and response data. |
| DASH-10 | In owner browser acceptance, demonstrate that management can readily determine each Technician’s recorded work, time spent supporting Boschendal, work performed on Projects, what a Technician did for a Customer, and where technical effort was spent. These tasks must be usable without knowledge of Timesheets, Employee identifiers or database reference types. Obtain Pierre’s feedback separately. |

**Owner acceptance recorded — 26 November 2026 (B3.88REP.2B).** The owner
passed the functional and management-usability checks on the actual DEV
dashboard and said, “All in all this is very impressive and WOW to me.”
Acceptance covers day-level Custom selection, all seven exploration modes,
expandable descriptions, restricted Project redaction and the handover to
Supervisor Booked Hours.

**Final internal closure — 26 November 2026 (B3.88REP.2C).** The owner’s
final browser retest accepted all six presentation refinements at
`ce8ca4b04254fdcbf593205619787a897c770d0f`. The full-period view retained
48 minutes and eight entries. Selecting Snapfix showed one 15-minute entry.
The restricted Project still contributed its one minute with its identity
and description withheld. The accepted design is frozen. Further
enhancements should be driven by operational experience or Pierre’s feedback.

Representative owner evaluation with multiple Technicians remains deferred
under the Bravo-only DEV grant. The controlled multi-Technician technical
evidence remains accepted. The abbreviated native Desk title on narrow
mobile screens is an accepted limitation. Pierre’s personal feedback
remains pending as a separate business item.

DEV registers the native `technician-work-overview` Page with the existing
Supervisor Governance role. Put **Technician Work Overview** first in the
Ops Workspace **Time Booking Reports** card and retain **Supervisor Booked
Hours** immediately after it. A targeted DEV installation uses
`frappe.reload_doc("ftelephony", "page", "technician_work_overview", force=True)`
and a one-link update to that card. Refresh the native Page domain cache and
affected Supervisor Page and boot caches, then verify both links as a
restricted Supervisor. The Workspace fixture carries the same link for the
authorized release process.

### Pillar 3 — COST-01–09 Customer Labour Cost Analysis

The approved commercial analysis compares recorded technical labour with
Customer account revenue for the same reporting period. It supports Customer
comparison, support contract review and analysis of labour contribution.

| ID | Approved requirement and acceptance check |
| --- | --- |
| COST-01 | Show one summary row per authorized Customer with recorded work during the period. Include permitted Helpdesk, Project and Customer Support work, standalone and unlisted Customers, and use the saved operational identity. Leave missing historical identities unattributed. |
| COST-02 | Show contributing Technician hours for each Customer and support individual hourly labour rates. Key the calculation by stable Employee and Company identity and use human-readable names for display. |
| COST-03 | Export authorized Technician identities and booked hours with blank hourly labour cost input cells for management to fill in Excel. Supply no estimated costs or salaries. ERPNext rate storage is outside the approved scope. |
| COST-04 | Provide one blank revenue input per Customer and label the reporting period. Recommend revenue excluding VAT. Blank revenue is unknown and explicit zero is a valid entry. Revenue retrieval, inference and ERPNext storage are outside scope. |
| COST-05 | Prefer three worksheets named **Technician Rates**, **Customer Labour Breakdown** and **Customer Financial Summary**. Populate authorized operational data automatically and leave financial inputs blank. Generate trusted formulas for labour cost, effective hourly revenue, revenue less labour cost, labour cost as a percentage of revenue, and labour contribution margin. Leave calculated amounts blank until required inputs are supplied. Missing rates represent unknown costs. Handle zero revenue and hours safely and keep calculable values numeric. |
| COST-06 | Compare and sort Customers by booked hours, labour cost, revenue, labour contribution in Rand, labour contribution margin percentage and effective hourly revenue. Show Rand and percentage contribution distinctly and label revenue less labour cost as labour contribution. Other direct costs and overheads are outside that measure. A future manual Other Direct Costs input remains a candidate. |
| COST-07 | Separately reconcile Customer-attributed, Internal and unattributed historical work to all authorized booked time and keep Emergency within that total. Leave Internal and unattributed time unallocated to Customer accounts. Identify the export’s scope and label a restricted Supervisor’s results as scoped labour figures. |
| COST-08 | Use the existing authorized population and verify Supervisor roster, Company and Customer restrictions, aggregation by Technician and Customer, Cancelled and replacement treatment, exact hours reconciliation, numeric cells, blank inputs, missing rates, formulas, and zero denominators. Protect spreadsheet text from formula execution, limit formulas to generated calculation cells, and verify protection of descriptions and references and absence of financial write-back. Actual owner workbook acceptance is required. |
| COST-09 | Enforce the owner's 26 November 2026 confidential commercial authorization decision. Limit access to Pierre's exact approved enabled System User with the Commercial Reporting role and existing Supervisor reporting authority, plus Administrator during explicitly enabled, bounded DEV testing. Reevaluate authorization for Desk discovery, Workspace links, direct Page requests, period validation and workbook generation. Classify exported workbooks as management confidential and serve them with private, no-store cache control. This is a mandatory gate for COST acceptance and activation. |

#### COST DEV implementation

Open **Ops Workspace → Time Booking Reports → Customer Labour Cost Analysis**.
The native Desk page defaults to **This Month** for Pierre and displays the
inclusive site dates before download. The export rechecks his identity,
commercial role, Supervisor reporting authority, active grants and applicable
Company, Employee and Customer restrictions. Its three-sheet
workbook opens on **Customer Financial Summary**. Blue input cells accept
manual values in Excel. **Technician Rates** and **Customer Labour
Breakdown** provide the supporting operational hours.

Each saved listed Customer has one revenue input across the Companies in
scope. Where a Customer spans Companies, the workbook also shows each
Customer/Company’s hours and labour cost without allocating account revenue
across Companies. Unlisted Customer names are grouped within their recorded
section and Company and remain distinct from listed identities with the same
name. The reconciliation includes Internal and unattributed work without
charging those hours to Customers.

The standard `customer-labour-cost-analysis` Page uses
`TELECTRO-POC Role - Commercial Reporting`. Its existing Ops Workspace link
follows **Supervisor Booked Hours**. Site-specific onboarding sets
`telectro_cost_pierre_user` to the exact approved ERPNext User identifier
after independent confirmation, assigns the commercial role to that User,
and establishes the appropriate Supervisor Reporting Grants and User
Permissions separately. Leave the identity unset until the owner confirms
it. Keep this setting in the individual site's configuration. Other
Supervisors retain access to the existing reporting features under their
current grants.

#### COST controlled DEV workbook acceptance

The Administrator test switch `telectro_cost_admin_dev_test` is off by
default. For the owner test on the verified DEV `frontend` site, set the
site-specific value to integer `1` with
`bench --site frontend set-config -p telectro_cost_admin_dev_test 1`.
The exception also requires developer mode, the local DEV database host
`db`, the Phase 2 booking feature flag and the exact eligible Bravo
Technician identity (`HR-EMP-00001`, Telectro (Demo)). Both the period
endpoint and workbook enforce 20–26 November 2026 as the outer date bounds.
Administrator runs as Administrator against that DEV population.
Remove the switch after owner testing with
`bench --site frontend set-config telectro_cost_admin_dev_test None`.

In DEV Desk, sign in as **Administrator** and open **Ops Workspace → Time
Booking Reports → Customer Labour Cost Analysis**. Confirm **Custom**,
**20 November 2026** through **26 November 2026**, then download and open the
workbook in Excel. Check the confidentiality notice and the reconciliation
of **48 minutes (0.800 hours)**, made up of **47 Boschendal minutes**,
**1 unattributed minute** and **0 Internal minutes**.

Confirm the inputs start blank. On **Technician Rates**, enter **R600** in
**E9**, then enter **R1,000 excluding VAT** in **F9** on **Customer
Financial Summary**. Expected Boschendal results are **R470 labour cost**,
**R530 labour contribution**, **53% contribution margin**, **47% labour
cost** and **R1,276.60 revenue per booked hour**. The reconciliation shows
**R10 unattributed labour** and **R480 total labour cost**. Keep populated
financial inputs in the local workbook.

Focused DEV verification passed with a temporary approved identity and the
bounded Administrator exception. Other Supervisors and users assigned the
commercial role in error were denied. The live Workspace, Desk discovery,
direct Page and API paths rejected unauthorized requests. A tab opened before
role revocation rejected its next workbook request. A Boschendal Customer
restriction reduced the temporary approved user's export from 48 to 47
minutes. The Administrator browser export retained the accepted 48-minute
reconciliation and all 21 formulas, with the confidentiality notice on all
three worksheets. Existing REP and DASH access was verified for the
Supervisor control. Pierre's actual account remains an onboarding dependency.

#### COST final internal closure

**Final internal closure — 27 November 2026 (A.1).** The owner accepted
the actual Excel workbook and its management presentation and usability.
“Yes, it looks polished and should be simple enough to use.” The owner
previously accepted the 48-minute reconciliation and the financial results
above using the fictional R600 hourly rate and R1,000 account revenue.
Internal labour cost was R0. Clearing the Technician rate correctly blanked
the dependent financial results. The accepted workbook and confidentiality
implementation are recorded in `03ed0c89603dca04284cfe630cd2085658d08435`
and `41e7be61b82ff8c03ea0c6bd37265dc4bb46e46e`, respectively.

**COST-09 containment.** After the Administrator exception was removed, the
owner observed that the COST Workspace link was absent and both the period
API and workbook download API returned HTTP 403. The 27 November A.0 DEV
read-only check found both `telectro_cost_admin_dev_test` and
`telectro_cost_pierre_user` absent from persisted site configuration,
persisted bench configuration and effective Frappe configuration on
`frontend`. Neither key has an explicit value. Administrator test access is
disabled. Pierre's commercial identity and reporting grants remain
unconfigured.

**Operational activation.** The owner reported demonstrating the workbook
to Pierre on 26 November and explaining its use and onboarding dependencies.
Pierre's initial business reception was positive. His operational acceptance
using actual business data remains pending. Operational use requires creation
and verified mappings of authoritative Customer identities, loading of
approved Current Projects, appropriate Technician Project/Task authorization,
approved Technician and Employee identities, and approved Supervisor
Reporting Grants and User Permissions. Confirm Pierre's exact approved
enabled System User, configure that identity and assign the dedicated
Commercial Reporting role through controlled onboarding. Handle workbooks as
management confidential. These dependencies apply to operational activation.
An otherwise-approved dormant deployment remains subject to its existing
release gates.

### Financial scope exception and implementation direction

The earlier commercial-analysis exclusion has one explicit exception.
Authorized operational labour data may be exported with blank financial
inputs for local Excel calculations and Customer comparison. Financial inputs
and calculations stay in the workbook. Payroll integration, stored salaries
or financial labour rates, ERPNext revenue capture, accounting transactions,
automatic billing, full profitability calculation, automatic overhead
allocation, productivity scoring and financial write-back remain outside
the approved scope.

Prefer a native Frappe Desk page in the existing Telephony app and reuse the
reporting service. Inspect the native export path first. A focused custom
multi-sheet workbook exporter is approved in principle if native exports
cannot meet COST-05 and COST-08. The design remains subject to focused
technical inspection. A new application, database, container service or
frontend framework requires a demonstrated need.

### Delivery and release boundaries

The approved Phase 2 roadmap retains REP formal closure, the DASH and COST
workstreams, consolidated Technician UI work, A.9 migration disposition,
two-pass DEV migration, an immutable dormant production candidate,
operational preparation and activation, and the separate A.12 structured
email intake and templates rollout. Dashboard management usability is
intended for operational activation. An otherwise-authorized dormant
infrastructure deployment can proceed independently of presentation work.
Existing release gates and approvals continue to apply.

DASH-01–10 internal acceptance is closed. COST-01–09 Customer Labour
Cost Analysis is implemented under B3.88REP.3 and its confidential
authorization decision B3.88REP.3A.
COST-01–09 internal acceptance is closed at A.1. Reuse the native Timesheet ledger,
Supervisor Booked Hours, the accepted Technician Work Overview and their
shared authorized reporting foundation. Preserve Supervisor Reporting
Grants, saved historical Customer identity, reference and description
redaction, exact duration aggregation and site-local date clipping. Include
Draft and Submitted bookings, exclude Cancelled and withdrawn work, and
count replacements once. Carry forward the accepted evidence for these
contracts.

---

## Consolidated Technician UI acceptance

**A.2.1 owner closure (UI-01–03).** The owner completed all nine DEV
browser checks and explicitly accepted the presentation at
`e8983cf6fbab9a8c9e5659fa65f2124cdedb110f`. The global **Book Time**
launcher has a 10 px gap after the ERPNext icon. The second action sits
below the Technician Workspace's **Time Booking** heading and above its
reports. Both open **My Time Bookings** using the same booking
authorization. Existing Workspace links and block IDs were preserved.

**A.2.2 DEV technical verification (UI-04–07).** All four work contexts
start with **Start Date and Time** and **Duration (minutes)**, followed
by context and work details, then **Description**. The native picker,
Now action and keyboard entry were retained. DEV displays **South African
Time (SAST)** and previews whole-minute durations and site-local end
times, including the date across midnight. Saved bookings display hours
and minutes and distinguish exact fractional pre-creation time, confirmed
zero, and unknown. Pre-creation applies to Helpdesk Ticket work and is
included in total booked time.

| Reference | Technical evidence |
| --- | --- |
| UI-04 | DEV Ticket #739 derived Boschendal and Other as read-only values and cleared both when the Ticket was removed. The **Helpdesk Ticket** label retains the stored `Helpdesk` value. The listed Customer selector, unlisted Customer requirement and Project Customer derivation keep their existing rules. |
| UI-05 | The native booking Customer selector uses field-level `only_select`. DEV autocomplete found Boschendal without offering Customer creation. The Frappe Advanced Search dialog can expose a create action, so it is omitted by this native setting. The unlisted field explains when to use it. |
| UI-06 | Native required-field feedback remains in place. Invalid duration and future start feedback identify the affected input and retain entered values. DEV Project and Task choices respected the completed work interval. Revised intervals rechecked existing selections. Empty and failed lookups showed distinct guidance. Browser testing exercised inline retry with a simulated 403 and no permission popup. An invalid server request returned HTTP 422. Both full correction and precise saved-reference forms were opened without saving. |
| UI-07 | The duration preview covers singular and plural forms, and an overnight preview includes the next date. Exact fractional seconds remain visible in saved Helpdesk pre-creation details. |

The browser loaded Desk asset revision `2026-11-27-6`. The focused
JavaScript tests covered stale Project and Task responses, exact scoped
restoration, and existing A.8 expected-error handling.

**A.2.2 owner closure.** The owner verified all 15 browser checklist items
and explicitly accepted the revised form presentation and usability at
`335a0671c17646f20ace358c3533a034dd7f219a`.

**A.2.4 contextual Work Origin.** The server derives **Not applicable** for
new Helpdesk Ticket, Project and Internal bookings and discards any supplied
Snapfix reference or Other origin description for those contexts. The
Technician only selects Work Origin for Customer Support. **Direct / Ad-hoc**,
**Snapfix** and **Other** remain the available choices. Snapfix requires its
reference and Other requires its description. **Emergency / Unplanned**
remains an explicit required choice in every context.

Historical classifications, related metadata and replacement lineage are
preserved. Full corrections in the original context carry forward hidden
origin metadata, and an unknown origin can remain blank only where the
locked saved row already has a blank origin in that context. The saved
reference correction path retains existing metadata and authorization.
The Select fixture adds one option. Applying that option to the individual
DEV Custom Field required no full migration. The existing detailed reports
filter **Not applicable** explicitly, retain the historical choices, and
keep a blank filter as **all origins**. A blank value on a saved row
continues to mean unknown.

DEV browser checks covered all four contexts, conditional fields, the
native mandatory dialog and clearing stale values while retaining the
description. Rollback-only DEV verification exercised creation in every
context, a saved-reference correction, Technician and Supervisor report
filtering, and native Supervisor CSV and Excel exports. The browser loaded
Desk asset revision `2026-11-27-7`. **A.2.4 owner browser acceptance is
pending.** A.2.3 remains separate and includes UI-09 and UI-10.

### Technician Time Booking Terminology and Quick Reference Guide

Prepare the guide and screenshots after UI acceptance. Cover why time is
booked, both **Book Time** entry points, start date and time, duration,
direct keyboard entry, and each Work Context. Explain Helpdesk Ticket,
Customer Support, listed and unlisted Customers, Project and Task, and
Internal work. Include Service Area, Activity Type, Work Origin,
Emergency / Unplanned, meaningful descriptions, correcting saved work,
and reviewing personal booked hours. Use the approved classifications.
Explain that Work Origin is required for Customer Support. **Direct /
Ad-hoc** is one of its choices. Other contexts receive the system-derived
**Not applicable** value. **Emergency / Unplanned** is a separate
classification that Technicians choose explicitly in every context.

### B3.88A.12 future Ticket Intake Method

Management wants the percentage of Tickets created through each intake
mechanism. Start with Email, Manual and Portal. Snapfix, WhatsApp and other
integrations are future categories. The Helpdesk Ticket owns the value and
derives it from its trusted creation mechanism. Count each Ticket once,
independently of Technician bookings.

Request Source identifies the requesting party. Inspect native Helpdesk
intake metadata before introducing a new Custom Field. Preserve
`custom_request_source` and `custom_telectro_manual_origin` under their
existing contracts. A.12 will scope implementation and reporting separately.
Historical intake classification requires trustworthy evidence.

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
