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

Current published HEAD: `f1e460b9076cd6d5a91ffa966efbc8dfd0b58cb8`

Published scope:
- Data Request arrival planner dependency recovery
- Ten-minute escalation foundation
- Activation-gated escalation scheduler registration
- Transactional in-app Notification Log creation
- Transactional native Email Queue creation
- Email Queue status reconciliation
- Combined single-intent notification dispatcher
- Permanent delivery regressions

Foundational notification delivery was published in `c439a41`.
The selection, retry policy and transactional worker were
subsequently published in `d518644`.
Batch delivery, sanitized operational reporting and durable
unhandled-failure backoff were recovered from canonical DEV
and published in `f1e460b`.
All six recovered file SHA-256 identities matched DEV.

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
| Total | 249 | Previously verified PASS |

These are results of individual verified test runs,
not a claim of one aggregate 249-test execution.

The selection, worker policy and transactional worker suites (54 tests) were recovered and published in commit `d518644`.
The batch, reporting and unhandled-failure suites (60 tests) are now recovered and published in `f1e460b`.

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

- Activation-gated batch scheduler integration
- Final operational error classification and monitoring
- Controlled scheduler activation verification
- Coordinator War Room and Supervisor reporting
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
