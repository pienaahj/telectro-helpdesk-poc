# Data Request Notification Delivery — DEV Verification Ledger

Date: 2026-11-05
Project: ERPNext Pilot / Telectro Helpdesk
Environment: DEV, Frappe site `frontend`
Branch: `feat/2026-11-04-data-request-10min-escalation`
Draft PR: https://github.com/pienaahj/telectro-helpdesk-poc/pull/415

## 1. Purpose

Preserve accepted DEV verification evidence for the Data Request
ten-minute Coordinator escalation and notification delivery work.

Do not repeat proven development investigations during production
deployment without concrete evidence that their assumptions changed.

This ledger records observed results from the development session.
It is not a substitute for the production release runbook.

## 2. Published source checkpoint

Current published HEAD: `21fb00170f2b97f8d11afa9dc98cbd7041ba3b9f`

Published scope:
- Data Request arrival planner dependency recovery
- Ten-minute escalation foundation
- Activation-gated escalation scheduler registration
- Transactional in-app Notification Log creation
- Transactional native Email Queue creation
- Email Queue status reconciliation
- Combined single-intent notification dispatcher
- Permanent delivery regressions
- Activation-gated one-minute notification delivery scheduler

Foundational notification delivery was published in `c439a41`.
The selection, retry policy and transactional worker were
subsequently published in `d518644`.
Batch delivery, sanitized operational reporting and durable
unhandled-failure backoff were recovered from canonical DEV
and published in `f1e460b`.
All six recovered file SHA-256 identities matched DEV.
The scheduler hook, entry point and permanent scheduler regressions
were recovered from canonical DEV with matching SHA-256 identities,
then published in `21fb001` (ESC.134A–134E).

## 3. Permanent regression evidence

| Suite | Tests | Result |
|---|---:|---|
| Escalation foundation | 54 | PASS |
| Notification authorization | 10 | PASS |
| In-app recording | 14 | PASS |
| Email queueing | 19 | PASS |
| Email reconciliation | 18 | PASS |
| Combined dispatcher | 20 | PASS |
| Candidate selection | 16 | PASS |
| Worker retry policy | 19 | PASS |
| Transactional worker | 19 | PASS |
| Notification batch | 31 | PASS |
| Operational reporting | 14 | PASS |
| Unhandled-failure backoff | 15 | PASS |
| Scheduler entry point and hooks | 12 | PASS |
| Total | 261 | Previously verified PASS |

These are results of individual verified test runs,
not a claim of one aggregate 261-test execution.

The selection, worker policy and transactional worker suites (54 tests) were recovered and published in commit `d518644`.
The batch, reporting and unhandled-failure suites (60 tests) are now recovered and published in `f1e460b`.
The 12 scheduler integration regressions passed in ESC.132
and were published in `21fb001`.

## 4. MariaDB integration proofs

### ESC.69 — In-app notification

- Authorized DEV Coordinator: PASS
- Real Notification Log created: PASS
- Intent reference persisted: PASS
- Repeated delivery reused Notification Log: PASS
- Transaction rollback: PASS
- Intent and Notification Log absent afterward: PASS
- Email sending prohibited during test: PASS

### ESC.72 — Native Email Queue

- Native Email Queue creation: PASS
- Reference to internal Notification Intent: PASS
- Queue reuse without duplication: PASS
- No HD Ticket Communication created: PASS
- No intent Communication created: PASS
- Transaction rollback: PASS
- Intent and Email Queue absent afterward: PASS
- Immediate SMTP sending prohibited: PASS

### ESC.77 — Combined dispatcher

- In-app and email record creation: PASS
- Both record identities persisted: PASS
- Overall Processing state: PASS
- Repeated dispatch reused both identities: PASS
- No duplicate notification or queue: PASS
- Communication privacy: PASS
- Transaction rollback and cleanup: PASS

### ESC.90 — Transactional worker

- Persistent activation disabled: PASS
- Authorized DEV Coordinator fixture: PASS
- Worker reached intercepted commit boundary: PASS
- Both notification channels persisted in transaction: PASS
- Processing state and five-minute poll: PASS
- Failure attempt count remained zero: PASS
- Email remained Not Sent: PASS
- Transaction rollback and cleanup: PASS
- Activation configuration unchanged: PASS

ESC.90 used an intercepted commit.
It does NOT prove a durable committed worker transaction.

### ESC.94 — Durable failure recovery

- Real DEV MariaDB transactions: PASS
- Persistent notification delivery activation disabled: PASS
- Isolated test intent committed before worker execution: PASS
- Injected dispatcher failure handled: PASS
- Partial database write rolled back: PASS
- Failure metadata committed separately: PASS
- Intent transitioned to Retry: PASS
- Failed attempt count incremented to one: PASS
- One-minute retry deadline persisted: PASS
- Failure state survived subsequent transaction rollback: PASS
- No Notification Log or Email Queue created: PASS
- Temporary intent removed: PASS
- Persistent activation unchanged: PASS

Evidence marker: `ESC_94_DURABLE_FAILURE_RECOVERY=PASS`

This proves actual worker rollback and durable failure recording.
It does not prove concurrent worker execution.

### ESC.95 — Row-lock serialization

- Two independent MariaDB sessions established: PASS
- First session acquired exclusive intent row lock: PASS
- Second session blocked by the existing lock: PASS
- First session committed Complete state: PASS
- Second session observed the committed state: PASS
- Worker rejected redispatch of completed intent: PASS
- No notification dispatch occurred: PASS
- Temporary intent removed: PASS
- Persistent activation unchanged: PASS

Evidence marker: `ESC_95_ROW_LOCK_SERIALIZATION=PASS`

This proves MariaDB row-lock serialization and the worker's
completed-state recheck. It does not prove simultaneous
end-to-end execution of two worker processes or interrupted
worker recovery.

### ESC.103B — Simultaneous worker execution

- Two independent DEV MariaDB worker connections: PASS
- First worker held the intent row lock: PASS
- Second worker attempted processing concurrently: PASS
- First worker committed its Processing result: PASS
- Second worker rejected redispatch: PASS
- Exactly one controlled dispatch invocation: PASS
- Five-minute polling deadline persisted: PASS
- No email or Notification Log created: PASS
- Temporary fixture removed: PASS
- Persistent activation unchanged: PASS

Evidence marker: `ESC_103B_SIMULTANEOUS_WORKERS=PASS`

This proves overlapping worker execution, row-lock serialization,
and single-dispatch behaviour with a controlled dispatcher.

### ESC.104 — Interrupted worker recovery

- Two independent DEV MariaDB worker connections: PASS
- First worker made an uncommitted partial write: PASS
- Second worker waited for the same intent lock: PASS
- First worker interrupted using SystemExit: PASS
- First transaction rolled back: PASS
- Second worker recovered the intent: PASS
- Uncommitted partial write did not survive: PASS
- Recovery result committed: PASS
- Retry budget remained unchanged: PASS
- Five-minute polling deadline persisted: PASS
- Temporary fixture removed: PASS

Evidence marker: `ESC_104_INTERRUPTED_WORKER_RECOVERY=PASS`

This simulates interruption followed by explicit connection cleanup.
It is not an operating-system kill test.

### ESC.105 — Committed stale Processing recovery

- Previously committed Processing fixture: PASS
- Intent excluded before recovery threshold: PASS
- Stale intent selected after recovery threshold: PASS
- Worker recovered the intent: PASS
- Recovery state committed durably: PASS
- Five-minute polling rescheduled: PASS
- Retry budget unchanged: PASS
- Premature redispatch prevented: PASS
- Next polling deadline respected: PASS
- No notification or email created: PASS
- Temporary fixture removed: PASS
- Persistent activation unchanged: PASS

Evidence marker: `ESC_105_STALE_PROCESSING_RECOVERY=PASS`

This proves recovery of an already committed stale Processing
intent using real selection and worker database operations with
a controlled dispatcher.

### ESC.111 — MariaDB batch failure isolation

- Two isolated eligible notification intents: PASS
- First dispatcher failure handled as Retry: PASS
- First intent's partial InnoDB write rolled back: PASS
- One-minute retry deadline persisted: PASS
- Second intent independently entered Processing: PASS
- Second intent's commit survived transaction reset: PASS
- Second intent's retry budget unchanged: PASS
- No delivery records created: PASS
- Both temporary fixtures removed: PASS
- Persistent activation unchanged: PASS

Evidence marker: `ESC_111_BATCH_MARIADB_ISOLATION=PASS`

### ESC.115D — MyISAM reporting transaction isolation

- Native Error Log storage engine MyISAM: CONFIRMED
- Notification Intent storage engine InnoDB: CONFIRMED
- Sanitized Error Log persisted without explicit commit: PASS
- Unrelated uncommitted InnoDB change rolled back: PASS
- MyISAM Error Log survived rollback: PASS
- Exactly one sanitized Error Log persisted: PASS
- All temporary records removed: PASS
- Persistent activation unchanged: PASS

Evidence marker: `ESC_115D_REPORTING_TRANSACTION_ISOLATION=PASS`

The earlier ESC.115 test was invalid because it expected MyISAM
Error Log inserts to roll back. ESC.115D is the corrected proof.
Production must verify its native table storage engine before
relying on the same persistence semantics.

### ESC.118 — Integrated batch error reporting

- Two isolated eligible notification intents: PASS
- Unhandled worker exception induced: PASS
- Batch rolled back before reporting: PASS
- Exactly one sanitized MyISAM Error Log created: PASS
- Error Log identity included in batch outcome: PASS
- Failed intent's partial InnoDB write absent: PASS
- Second intent's Processing transaction committed: PASS
- Error Log survived transaction reset: PASS
- No email or Notification Log created: PASS
- All temporary fixtures removed: PASS
- Persistent activation unchanged: PASS

Evidence marker: `ESC_118_BATCH_REPORTING_MARIADB=PASS`

ESC.118 established the original unhandled-error reporting
behaviour before durable backoff was introduced.
The repeated-failure gap was subsequently addressed and
verified in ESC.122–126.

### ESC.126 — Integrated durable unhandled-failure backoff

- Two isolated eligible DEV notification intents: PASS
- First worker's unhandled exception injected: PASS
- Batch rollback preceded sanitized reporting: PASS
- Actual durable backoff helper invoked: PASS
- Failed intent transitioned to Retry: PASS
- Failed attempt count incremented to one: PASS
- One-minute retry deadline committed durably: PASS
- Incomplete InnoDB write discarded: PASS
- Second intent independently entered Processing: PASS
- Second intent's five-minute polling deadline committed: PASS
- Exactly one sanitized MyISAM Error Log persisted: PASS
- Error Log survived subsequent transaction reset: PASS
- No Notification Log or Email Queue created: PASS
- Both intent fixtures and Error Log removed: PASS
- Persistent activation remained disabled: PASS

Evidence marker: `ESC_126_DURABLE_BACKOFF_MARIADB=PASS`

ESC.126 initially encountered stale Python module objects in the
interactive Bench console. ESC.126B established that canonical DEV
source contained the function while the loaded worker did not.
ESC.126C reloaded worker and then batch, verifying function
identities without modifying source or database state.
The subsequently executed ESC.126 integration proof passed.

This is the thirteenth accepted DEV MariaDB integration checkpoint.
It proves the integrated path with controlled candidate selection
and notification dispatch; it does not prove live SMTP delivery.

## 5. Implemented policy

- Escalation due after ten elapsed minutes from ticket creation
- First-completion timestamp stops outstanding escalation
- Operational escalation remains independent of notification delivery
- Arrival recipients: eligible Data Provisioning team members
- Escalation recipients: authorized Coordinator Ops users
- Recipient authorization rechecked at delivery
- Notification Log type: Alert
- Email Queue associated with internal intent, not HD Ticket
- Existing Email Queue reused; no automatic replacement
- Pending email: five-minute status polling
- Failed processing: 1, 2, 4, 8-minute retry delays
- Fifth unsuccessful attempt: terminal Failed
- Revoked authorization: terminal Failed
- Routine queue polling does not consume retry attempts
- Unhandled batch failure: rollback before sanitized reporting
- Native MyISAM Error Log persists without committing InnoDB work
- Unhandled failure backoff reuses the existing retry policy
- Row-locked eligibility recheck prevents overwriting progress
- Reporting or backoff persistence failures propagate

## 6. Activation safeguards

Escalation activation key:
`telectro_data_request_escalation_start_at`

Notification delivery activation key:
`telectro_data_request_notification_delivery_start_at`

Both mechanisms must fail closed when their respective
activation key is absent.

Historical backlog must not be indiscriminately notified.
Production must independently verify the native Error Log
storage engine before relying on MyISAM persistence.

Working-hours versus elapsed-time policy must be confirmed
before production activation.

## 7. Remaining development and verification

- Controlled DEV scheduler execution verification
- Real ten-minute Coordinator escalation lifecycle proof
- Production Scheduled Job Type synchronization and release verification
- Final operational error classification and monitoring
- Controlled scheduler activation verification
- Coordinator War Room: outstanding and escalated Data Request
  visibility, live age and refresh-independent updates
- Coordinator workspace: add entry points to the escalation
  War Room and dedicated escalation report
- Supervisor workspace: add access to the same dedicated
  escalation report for governance and oversight
- Dedicated Data Request escalation report: implement,
  establish columns and filters, and verify access permissions
- Verify Coordinator notification authority remains independent
  of Supervisor workspace/report visibility
- Customer portal status-transition guard
- Complete PR review and required release gates

## 8. Production release rules

Production release remains ON HOLD.

Follow:
`docs/runbooks/production-runtime-release.md`

The existing runbook and its human Phase 2 approval gate
are authoritative. Do not improvise or skip release phases.

Production validation should establish deployed identity,
schema/migration correctness, configuration, runtime health,
permissions, notification safety, and operational acceptance.

DEV functional proofs are retained; production-specific
deployment evidence must still be collected.

No demo tickets should be created in production merely
to reproduce DEV integration experiments.

## 9. Evidence limitations

This document summarizes observed session output.
The interactive ESC.69/72/77/90 console transcripts
are preserved in the development conversation, not yet
as separately archived machine-generated evidence files.

No SMTP delivery to a real recipient has been proven.
No production activation has occurred.

## 10. Scheduler integration and DEV registration

### ESC.131B–133 — Scheduler source and runtime

- Existing one-minute cron expression retained: `*/1 * * * *`
- Inbox polling, escalation and notification jobs each appear once: PASS
- Notification entry point delegates to bounded delivery batch: PASS
- Twelve permanent scheduler regressions: PASS (ESC.132)
- Effective Frappe hook resolution: PASS (ESC.133)
- Disabled activation returns a disabled result without dispatch: PASS
- Notification delivery activation remains unset: PASS

ESC.133 verifies effective Frappe hooks and direct entry-point
resolution. It does not prove actual scheduler tick execution.

### ESC.134A–134E — Canonical source recovery

- Dry-run exact scope: three scheduler files, PASS
- Mac-to-DEV SHA-256 identity for all three files: PASS
- Exactly one modified tracked file and two new files: PASS
- No unrelated source or fixture changes: PASS
- Staged diff and commit scope: PASS
- Published commit: `21fb00170f2b97f8d11afa9dc98cbd7041ba3b9f`
- Remote Git identity and clean working tree: PASS

### ESC.135–138A — Scheduler diagnostics and native contract

- Effective hooks contain all three one-minute jobs: PASS
- Existing inbox Scheduled Job Type initially present: PASS
- Escalation and notification Scheduled Job Type initially missing
- DEV scheduler disabled and inactive: confirmed by `bench doctor`
- Two workers reported online; this does not prove scheduler execution
- Native `sync_jobs()` implementation inspected
- Native synchronization reloads the Scheduled Job Type DocType,
  inserts or updates defined jobs, then clears ordinary undefined jobs
- Targeted native `insert_single_event()` inspected as an alternative

No full migration or broad job synchronization was executed
during this DEV registration correction.

### ESC.139–140A — Targeted database registration

- DEV site: `frontend`
- Initial Scheduled Job Type records: 92
- Existing 92 records preserved unchanged: PASS
- Escalation job registered as one-minute Cron: PASS
- Notification delivery job registered as one-minute Cron: PASS
- Transaction committed successfully: PASS
- Fresh-console persistence verification: PASS
- Total persisted Scheduled Job Type records: 94
- All three relevant jobs registered once, not stopped: PASS
- DEV scheduler remained disabled: PASS
- Notification delivery activation remained disabled: PASS

The targeted registration is DEV database state, not a
production deployment artifact. Production must reconcile
scheduler registration through the authorized release process.

### Outstanding operational acceptance

- Real scheduler tick/worker execution has not been proven.
- Real ten-minute Coordinator escalation lifecycle has not
  yet been proven end-to-end.
- Coordinator War Room escalation visibility and live-age
  updates remain unproven.
- Coordinator and Supervisor workspace additions remain open.
- The separate escalation report shared by those workspaces
  is not implemented or accepted.
- Report filters, columns, permissions and presentation still
  require definition and acceptance.
- Coordinator notification recipients must remain governed by
  Coordinator Ops authorization, independently of workspace
  and Supervisor report visibility.
- DEV scheduler is intentionally disabled.
- Notification delivery activation remains disabled.
- No live SMTP delivery has been proven.
- Production migration, scheduling and operational health
  require separate runbook-controlled evidence.
- Confirm elapsed-time versus working-hours policy before
  enabling escalation in production.

Production remains ON HOLD. Draft PR #415 remains unmerged.
The committed production release runbook and its Phase 2
human approval gate remain authoritative.

## 11. Escalation MariaDB integration

### ESC.145B — Ten-minute decision boundary and idempotency

- Real DEV MariaDB HD Ticket row and row-locking path: PASS
- Isolated negative numeric BIGINT fixture: PASS
- Actual Coordinator recipient resolver returned four users: PASS
- At 9 minutes 59 seconds: no escalation intents, PASS
- At exactly ten minutes: four escalation intents, PASS
- Escalation recipients matched authorized Coordinators: PASS
- Repeated capture produced no duplicate intents: PASS
- Temporary ticket and intents rolled back: PASS
- Original ticket and intent counts restored: PASS
- Activation configuration unchanged: PASS

Evidence marker: `ESC_145B_ESCALATION_INTEGRATION=PASS`

This is the fourteenth accepted DEV MariaDB integration
checkpoint. Controlled timestamps were used; real elapsed
wall-clock time and background scheduler execution were not
established.

### ESC.146 — Completion suppression

- Isolated on-time completion at five minutes: PASS
- Isolated late completion at ten minutes five seconds: PASS
- Both policy completion states correctly identified: PASS
- No escalation intents created for either completed ticket: PASS
- Temporary fixtures removed by transaction rollback: PASS
- Original database counts restored: PASS
- DEV scheduler remained disabled: PASS
- Escalation and notification activation remained disabled: PASS

Evidence marker: `ESC_146_COMPLETION_SUPPRESSION=PASS`

This is the fifteenth accepted DEV MariaDB integration
checkpoint. Completion timestamps were supplied directly
in isolated test fixtures. Normal ticket-save completion
auditing was not exercised by this integration test.

### Current acceptance boundary

- Permanent regressions: 261 previously verified PASS
- DEV MariaDB integration checkpoints: 15 accepted
- Real ten-minute wall-clock observation: outstanding
- Background scheduler tick and worker execution: outstanding
- Production deployment and operational acceptance: outstanding
- No SMTP delivery was invoked by these tests

Production remains ON HOLD. Draft PR #415 remains unmerged.

## 12. Native scheduled-job worker execution

### ESC.150–152 — Native execution contract and preflight

- Frappe ScheduledJobType execution path inspected: PASS
- Native queue execution and status logging inspected: PASS
- Notification delivery job registered once: PASS
- One-minute Cron configuration: PASS
- Target RQ queue: default
- Scheduled Job Log enabled: create_log = 1
- Job not already queued: PASS
- Global DEV scheduler disabled: PASS
- Escalation and delivery activation disabled: PASS

### ESC.153A — Native RQ enqueue

- Exactly one notification delivery job enqueued: PASS
- Explicit force=True used; no global scheduler activation
- RQ job identity:
  `scheduled_job::telephony.jobs.data_request_notification_delivery.run`
- Both activation settings remained disabled: PASS
- Enqueue acceptance did not assume worker completion

Evidence marker: `ESC_153A_NATIVE_JOB_ENQUEUED=PASS`

### ESC.153B — Persisted worker completion

- Fresh DEV Bench console verification: PASS
- Scheduled Job Log identity: `78pp7e7s3s`
- Persisted execution status: Complete
- Recorded execution time: 2026-11-05 17:10:58
- Native worker execution: PASS
- Persisted successful execution log: PASS
- Existing Data Request tickets: 1, unchanged
- Existing notification intents: 1, unchanged
- Existing escalation intents: 0, unchanged
- Escalation activation remained disabled: PASS
- Notification delivery activation remained disabled: PASS
- Global DEV scheduler remained disabled: PASS

Evidence marker: `ESC_153B_WORKER_OUTCOME_INSPECTED=PASS`

This proves native RQ worker execution of the registered
activation-disabled notification delivery job.

It does not prove automatic periodic cron dispatch,
an activated delivery batch, real SMTP delivery,
or real ten-minute wall-clock Coordinator escalation.

### Outstanding operational acceptance

- Automatic periodic cron dispatch remains unproven.
- Real ten-minute elapsed-time escalation remains unproven.
- Normal ticket-save completion auditing was not exercised
  by the isolated ESC.146 completion-suppression fixture.
- Coordinator War Room, Coordinator/Supervisor workspace
  additions and shared escalation report remain outstanding.
- Production scheduler configuration and runtime verification
  must follow the authorized release runbook.

Permanent regressions: 261 previously verified PASS.
DEV MariaDB integration checkpoints: 15 accepted.
Native RQ execution: verified separately.

Production remains ON HOLD. Draft PR #415 remains unmerged.
