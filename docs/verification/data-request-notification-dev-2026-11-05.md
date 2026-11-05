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

Commit: c439a41a147fb81b57f622ca6dccc9f54039ccf0

Published scope:
- Data Request arrival planner dependency recovery
- Ten-minute escalation foundation
- Activation-gated escalation scheduler registration
- Transactional in-app Notification Log creation
- Transactional native Email Queue creation
- Email Queue status reconciliation
- Combined single-intent notification dispatcher
- Permanent delivery regressions

DEV-only operational worker work is NOT included in this commit.

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
| Total | 189 | Previously verified PASS |

These are results of individual verified test runs,
not a claim of one aggregate 189-test execution.

The final three suites (54 tests) are DEV-only pending Git recovery.

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

## 6. Activation safeguards

Escalation activation key:
`telectro_data_request_escalation_start_at`

Notification delivery activation key:
`telectro_data_request_notification_delivery_start_at`

Both mechanisms must fail closed when their respective
activation key is absent.

Historical backlog must not be indiscriminately notified.

Working-hours versus elapsed-time policy must be confirmed
before production activation.

## 7. Remaining development and verification

- Real concurrent worker safety and interrupted recovery
- Batch worker and scheduler integration
- Durable error classification and operational reporting
- Controlled scheduler activation verification
- Coordinator War Room and Supervisor reporting
- Customer portal status-transition guard
- Synchronize operational worker source/tests into Git
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
