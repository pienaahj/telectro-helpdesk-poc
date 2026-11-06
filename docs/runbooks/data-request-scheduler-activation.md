# ERPNext Pilot — Production Scheduler Configuration and Activation Note

- **Captured:** 2026-11-06 (Africa/Johannesburg)
- **Status:** Evidence-backed DEV diagnosis; **NOT** production validation or approval
- **Change control:** Production **ON HOLD**
- **Authoritative release procedure:** `docs/runbooks/production-runtime-release.md` (all phase gates, including explicit Phase 2 human review, remain mandatory)
- **Related delivery:** Draft PR #415, `feat/2026-11-04-data-request-10min-escalation`, published HEAD `de160214c0417907ee67df9d0a60e1b9d2dbe91d` at capture time.

## Purpose

Preserve the exact scheduling dependency discovered in DEV so that a later production release does **not** assume running Compose services and registered cron hooks mean Data Request escalation will occur automatically. This document is a readiness note, **not** authorization to activate the scheduler or release the application.

## Evidence already accepted — do not repeat

| Checkpoint | Evidence and observed result |
|---|---|
| ESC.248A | Actual `HD Ticket.save()` Data Request first-completion timestamp persisted; later edit/reopen/re-resolution preserved it; manual change rejected. Non-audit post-save hooks and external effects isolated; transaction rolled back; 324-ticket DEV baseline restored. |
| Prior escalation acceptance | Native worker processed a truly elapsed >10-minute Data Request and generated the expected four Coordinator escalation intents once; no emails sent. **Worker logic accepted; automatic scheduler invocation still unproved.** |
| ESC.249 | Effective Frappe cron `*/1 * * * *` contains `telephony.jobs.pull_pilot_inboxes.run`, `telephony.jobs.data_request_escalation.run` and `telephony.jobs.data_request_notification_delivery.run`, each observed once where checked. Both Data Request `Scheduled Job Type` records exist with `stopped=0`, `frequency=Cron`, `cron_format=*/1 * * * *`. Escalation `last_execution=None`; notification-delivery historical timestamp `2026-11-05 17:10:58.610523` (not sufficient evidence of automatic dispatch). |
| ESC.250 | Installed Frappe scheduler source checks `maintenance_mode`, `pause_scheduler`, `disable_scheduler` (site config) and `System Settings.enable_scheduler`. The original attempt to read `System Settings.disable_scheduler` was invalid; that field does not exist. |
| ESC.251 | On DEV site `frontend`, `System Settings.enable_scheduler=0`; `is_scheduler_disabled(verbose=False)=True`; `is_scheduler_inactive(verbose=False)=True`. Explicit **configuration blocker** to automatic dispatch. No settings changed. |
| ESC.252 | DEV Compose `scheduler`, `queue-short`, `queue-long` containers all running (`Up 15 hours` at inspection). This establishes process presence, **not successful job dispatch**. |
| ESC.253 | `frappe.utils.scheduler.enqueue_events_for_site(site)` calls `is_scheduler_inactive()` and returns immediately if true; it only calls `enqueue_events(site=site)` when active. Scheduler logs displayed no entries in the inspected tail; absence of logs is not proof of failure. |
| ESC.254 | `enqueue_events(site)` checks `schedule_jobs_based_on_activity()` then iterates enabled `Scheduled Job Type` records (`stopped=0`), calls each `job_type.enqueue()`, with `CroniterBadCronError` handling. `ScheduledJobType.enqueue()` checks due time (`is_event_due()`) and `is_job_in_queue()` before enqueue. No configuration changes or jobs executed by inspection. |
| ESC.255 | In the DEV UI, the **Scheduled Job Type** forms exist for both Data Request methods, show **Stopped unchecked**, **Frequency Cron**, `*/1 * * * *`, and expose a **Scheduled Job Log** connection. Escalation showed no Last Execution or linked log; delivery showed a Last Execution of 2026-11-05 17:10:58 SAST and one linked log. The displayed Next Execution values were on 5 November 2026 and thus stale when inspected on 6 November, consistent with the disabled DEV scheduler. |
| ESC.256 | The DEV **Scheduled Job Log** list, filtered to delivery, showed **one Complete record** (`78pp7e7s3s`), and the escalation job had no records in its corresponding list. The UI states logs are retained for **7 days** by default and the retention policy is configurable via **Log Settings**. The log was not inspected in detail; **Complete does not prove email delivery or automatic (vs. manual) invocation**. |

## Exact scheduler mechanics observed in installed DEV Frappe

### Site eligibility (pre-dispatch)

`apps/frappe/frappe/utils/scheduler.py`:

```python
# Relevant excerpt observed in ESC.253
frappe.init(site=site)
frappe.connect()
if is_scheduler_inactive():
    return
enqueue_events(site=site)
```

The inactive check accounts for:

1. `frappe.conf.maintenance_mode`;
2. `frappe.conf.pause_scheduler`;
3. `frappe.conf.disable_scheduler`;
4. `System Settings.enable_scheduler` (the actual Single DocType field).

**DEV verified:** Only the last check was the identified blocker (`enable_scheduler=0`). **Production state unknown.**

### Job dispatch (after site eligibility)

`enqueue_events(site)` checks `schedule_jobs_based_on_activity()` and, if permitted, queries all `Scheduled Job Type` rows with `stopped=0`. It attempts `job_type.enqueue()` for each. This is **not** limited to Data Request jobs. The job itself checks whether it is due and whether already in queue.

The activity check is cached, calls `is_dormant()` and allows normal scheduling for a non-Frappe-Cloud site or in developer mode, based on the observed source. Production must still be checked in its own installed version.

### Job execution is a separate stage

Registration → site eligibility → due/queue check → enqueue → worker picks up job → job execution → evidence of outcome. **Do not conflate these stages.** A scheduled-job `last_execution` timestamp alone may not establish that a job was invoked automatically rather than manually.

## ESC.255–256 — Scheduler administration UI evidence

Read-only observations from the DEV Frappe Desk, provided as screenshots on 2026-11-06:

1. Global Desk search **Scheduled Job Type** → open the existing `data_request_escalation.run` and `data_request_notification_delivery.run` records. This is the appropriate **job administration** UI; an empty **Scheduler Event** list does not mean the hook-registered jobs are absent.
2. Both jobs showed **Stopped unchecked**, `Frequency = Cron`, and `Cron Format = */1 * * * *`. This is registration/configuration evidence, **not** execution evidence.
3. Escalation showed no prior **Last Execution** and no linked **Scheduled Job Log**. Its form displayed a Next Execution of **2026-11-05 16:18 SAST** (past at inspection). The delivery form displayed Last Execution **2026-11-05 17:10:58 SAST**, Next Execution **2026-11-05 17:11 SAST**, and **1** linked log.
4. Open **Scheduled Job Log** from the connection to inspect history. The delivery log list showed one entry for `data_request_notification_delivery.run`, **Status = Complete**, **ID = `78pp7e7s3s`**. The escalation list was empty. The detail of the completed log was **not inspected**, so its initiator, detailed timings, and outcome beyond `Complete` remain unknown.
5. The UI advertises **7-day Scheduled Job Log retention**, adjustable in **Log Settings**. Production logging/retention requirements should be explicitly evaluated; logs may disappear before an incident investigation.
6. The Scheduled Job Type form prominently exposes **Execute** and **Save** actions. **Do not click Execute** merely to inspect a job: it is a manual execution path and does not establish automatic scheduler dispatch; it could trigger delivery or other side effects. Do not change **Stopped** or cron fields during inspection. Likewise, the Scheduled Job Log list exposes an **Add** button; creating synthetic logs is not operational proof.
7. An empty **Scheduler Event** list is not a blocker for hook-registered jobs. Distinguish `Scheduler Event` from `Scheduled Job Type` and `Scheduled Job Log` when preparing production operating instructions.

**Caveat:** These are observed DEV UI states on screenshots, **not** production readings, an assertion about a real automatic tick, proof of SMTP delivery, or permission to enable scheduling.

### Suggested production evidence sequence (only after runbook authorization)

- Screenshot the **Scheduled Job Type** of each approved job, showing method, cron, Stopped, Last/Next Execution and local timezone.
- Cross-check **System Settings.enable_scheduler** plus site configuration and scheduler process state; a Next Execution value can remain visible even when the scheduler is inactive.
- Observe and preserve a **new** Scheduled Job Log resulting from a known permitted **automatic tick**, plus queue/worker evidence and corresponding business-state result. Do not count a manually pressed **Execute** action as automatic acceptance.
- Check the applicable retention period and export operational evidence to the release evidence location under the authoritative runbook, subject to privacy controls.

## Production release gate: required pre-activation inspection

**Do not perform these checks as a substitute for any release-runbook phase.** When production release activity is authorized, collect read-only evidence from the deployed **production** site and production containers:

- Confirm running release image, Git/release identity, approved PR/commit and completed release-runbook prerequisites.
- Confirm production site name and correct runtime context before any command; do not assume DEV site `frontend` or DEV Compose service names apply in production.
- Inspect `System Settings.enable_scheduler` with the correct field, and read `frappe.conf.maintenance_mode`, `pause_scheduler`, `disable_scheduler`.
- Inspect `is_scheduler_disabled(verbose=False)` and `is_scheduler_inactive(verbose=False)` using the installed deployed Frappe API, only if functions match the inspected version.
- Verify exact registered hooks and `Scheduled Job Type` records, `stopped`, cron expression, due/last execution state and any queued-job status. Check for duplicates or stale records.
- Inspect production scheduler service, short/long queue workers, Redis connectivity and job-processing evidence without altering their state.
- Inventory **all** other enabled scheduled jobs and externally connected effects, especially pilot inbox polling, outbound notification delivery, assignment and customer communications.
- Confirm SMTP transport/routing is resolved and separately accepted before permitting real customer/Coordinator messages. Do not assume successful intent creation means email was delivered.
- Agree a written activation/rollback and observation plan in the human review gate before changing scheduler settings.

Read-only Frappe checks used successfully in DEV (adapt **only** after confirming the site and version):

```python
import frappe
from frappe.utils import cint
from frappe.utils.scheduler import (
    is_scheduler_disabled,
    is_scheduler_inactive,
)

print('enable_scheduler=', cint(
    frappe.db.get_single_value('System Settings', 'enable_scheduler')
))
for key in ('maintenance_mode', 'pause_scheduler', 'disable_scheduler'):
    print(key, frappe.conf.get(key))
print('scheduler_disabled=', is_scheduler_disabled(verbose=False))
print('scheduler_inactive=', is_scheduler_inactive(verbose=False))

cron = (frappe.get_hooks('scheduler_events') or {}).get('cron') or {}
for path in ( 'telephony.jobs.pull_pilot_inboxes.run',
              'telephony.jobs.data_request_escalation.run',
              'telephony.jobs.data_request_notification_delivery.run'):
    print('cron_occurrences', path, (cron.get('*/1 * * * *') or []).count(path))
```

This snippet reads state only. It **does not** prove that a scheduler tick has dispatched and completed a job. Do not run production activation commands from this note.

## Activation: controlled future procedure, **not yet approved**

**Gate 1 — Explicit authorization.** Follow `docs/runbooks/production-runtime-release.md`, including Phase 2 human review and all required evidence. Obtain explicit agreement on when and how scheduling and notification delivery may start. Do not initiate production activation before those approvals.

**Gate 2 — Scope and side effects.** Account for the fact that enabling the site scheduler can dispatch **all eligible enabled scheduled jobs**, not only Data Request escalation. Establish safe controls for inbox polling and notification delivery, and verify the actual impact of each control before changing anything. Do not globally disable legitimate unrelated production scheduling without a reviewed plan.

**Gate 3 — Configuration.** Identify the exact supported production-version procedure for enabling the scheduler (the installed Frappe implementation uses `System Settings.enable_scheduler`); verify its command/API syntax before use. Preserve prior values and rollback instructions. **No enabling command is authorized by this note.**

**Gate 4 — Post-activation evidence.** After authorized activation, separately prove scheduler tick, eligible job enqueue, queue worker pickup, and job completion for the Data Request escalation job. Verify the expected periodic cadence, failures/retries and duplicate protection without inventing production customer/demo tickets. Observe real operational cases or a specifically approved non-customer test strategy.

**Gate 5 — Business behaviour.** Correlate scheduled-job execution with Data Request first-completion suppression, >10-minute escalation and idempotent Coordinator intents. Preserve privacy/recipient boundaries. Where configured recipients differ from the DEV fixture, validate the production recipient mapping rather than assuming four recipients.

**Gate 6 — Delivery.** Separately prove SMTP network reachability, outbound email delivery, sender identity and failure handling before declaring customer-facing notification delivery accepted.

**Gate 7 — Closure.** Capture release evidence under the runbook, prove system health and clean production operational state, and obtain the runbook's completion/approval markers.

## Pending questions — do not infer answers from DEV

1. What is the actual production `System Settings.enable_scheduler` value and effective `is_scheduler_inactive()` result?
2. What other enabled production scheduled jobs would run immediately on activation, and what external actions could they trigger?
3. Are the production scheduler, Redis and queue workers actually dispatching and completing scheduled tasks under the deployed release?
4. What specifically prevents unexpected inbox ingestion/outbound notification delivery during controlled validation?
5. What production-safe evidence will demonstrate automatic scheduler tick → enqueue → worker execution without demo tickets?
6. Is SMTP network access and the real email delivery path approved and proven?
7. What exact release-runbook gate and responsible human approve scheduler activation and rollback?

## State following ESC.256

- **DEV:** scheduler explicitly disabled (`System Settings.enable_scheduler=0`); no scheduler activation or job dispatch performed during these inspections.
- **Application logic:** escalation worker and native first-completion audit accepted by prior tests.
- **Automatic tick / queue dispatch:** outstanding, **not** accepted.
- **Production:** no scheduler status inspection from production yet; release/activation **ON HOLD**.
- **Documentation follow-up:** Review and integrate this note into a focused, committed production runbook update at the appropriate PR/release slice. Do not treat a local note as a committed operational procedure.
- **UI evidence:** ESC.255–256 confirmed job administration via **Scheduled Job Type** and one completed historical delivery **Scheduled Job Log**; no escalation log and no automatic tick verified. Seven-day log retention should be considered for production evidence preservation.
