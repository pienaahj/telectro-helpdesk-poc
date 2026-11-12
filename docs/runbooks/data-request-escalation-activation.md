# Data Request — Coordinator Escalation Activation

## Purpose

Activate the existing ten-minute Data Request escalation mechanism for exactly three designated recipients:

- `sean@telectro.co.za`
- `pierre@telectro.co.za`
- `christo@telectro.co.za`

Escalation occurs when a Data Request remains without recorded first completion ten elapsed minutes after ticket creation. Claiming or assigning the ticket does not stop the escalation clock.

Escalation is independent of Helpdesk SLA policies.

## Required production release

The site-configurable recipient implementation must be merged and deployed before configuring or activating escalation.

Follow `docs/runbooks/production-runtime-release.md` as the authoritative production release procedure.

The runbook's Phase 2 human review gate and all other required release gates must be satisfied. This document does not authorize deployment or activation.

## Production configuration

Site: `erp.telectro.co.za`

### 1. Escalation recipients

Configuration key:

`telectro_data_request_escalation_recipients`

Required value:

```json
[
  "sean@telectro.co.za",
  "pierre@telectro.co.za",
  "christo@telectro.co.za"
]
```

The recipient resolver uses this explicit list only. It does not automatically include other Coordinator-role members.

Each recipient must be an enabled System User with a valid email address and permission to read the Data Request.

Verify all three accounts before activation. Missing or unauthorized accounts are excluded from recipient resolution.

### 2. Escalation activation

Configuration key:

`telectro_data_request_escalation_start_at`

Keep unset until explicitly authorized.

At activation, set to the approved site-local timestamp in `YYYY-MM-DD HH:MM:SS` format, without a timezone suffix.

Only tickets created at or after this timestamp are considered for escalation.

Older tickets are excluded.

### 3. Notification delivery

Configuration key:

`telectro_data_request_notification_delivery_start_at`

Production notification delivery was previously activated independently of escalation.

Verify its existing value and operational health. Do not reset its activation timestamp unnecessarily.

The delivery pipeline processes eligible arrival and escalation intents.

### 4. Scheduler health

Verify that the production scheduler is enabled and operational.

Confirm that these jobs are registered and active:

- `telephony.jobs.data_request_escalation.run`
- `telephony.jobs.data_request_notification_delivery.run`

Both are registered through Frappe scheduler hooks.

Scheduler activation affects other scheduled jobs and requires appropriate operational approval.

## Activation procedure

After the approved production release:

1. Record the existing configuration and release identity.
2. Confirm that the expected application image and source revision are running.
3. Confirm all three designated recipients are eligible to read Data Requests.
4. Confirm notification delivery is active and operational.
5. Confirm the scheduler is running and its workers are healthy.
6. Configure the explicit three-person recipient list.
7. Verify the effective resolved recipients are exactly Sean, Pierre and Christo.
8. Set the approved escalation activation timestamp.
9. Verify the configuration and monitor escalation processing.
10. Preserve the evidence using the established production release procedure.

Do not create operational test tickets or involve the Emerald Life Customer without separate approval.

## Expected behaviour

A Data Request that remains incomplete ten minutes after creation becomes eligible for escalation on the next scheduled processing cycle.

Each eligible recipient receives a separately identifiable escalation intent.

The normal notification pipeline creates an in-app alert and queues an email.

Deterministic intent identities prevent duplicate intents for the same ticket, event and recipient.

If the ticket is completed before escalation intent capture, no new escalation notification is generated, even if completion occurred late.

## DEV acceptance evidence — 10 November 2026

Test ticket: **HD Ticket #962**

- Created: 19:37:46 SAST
- Ten-minute threshold: 19:47:46 SAST
- Automatic escalation intent created: 19:55:04 SAST
- Sole DEV recipient: `hendrik@local.test`
- Intent: `TDRN-ee886e97b8c7a13c2a499df137033000b08acd3a`
- Notification Log: `5312ro2v16`
- Email Queue: `5342b30g2q`
- Email Queue status: `Sent`
- In-app notification visually confirmed after browser refresh
- Recipient regression suite: 13/13 PASS

The DEV scheduler was initially disabled and was enabled after the ticket exceeded ten minutes. Therefore this test proves automatic escalation and delivery, but **does not establish normal scheduling latency from the deadline**.

An Email Queue status of `Sent` is evidence of Frappe's sending status, not independent confirmation of mailbox receipt.

## DEV closure state

At completion of testing:

- `telectro_data_request_escalation_start_at` = `None`
- `telectro_data_request_notification_delivery_start_at` = `None`
- `telectro_data_request_escalation_recipients` = `["hendrik@local.test"]`
- DEV site scheduler remains enabled

## Production acceptance — 12 November 2026

### Scope and outcome

**Site:** `erp.telectro.co.za`
**Release:** `20261111-3cca9a2`
**Test ticket:** HD Ticket `#76`
**Result:** **PASS — automatic ten-minute escalation and three-recipient email delivery.**

This section records actual production behaviour observed on 12 November 2026.
It supersedes earlier readiness statements describing production escalation
as inactive or operationally unproven. Historical DEV findings remain valid.

The controlled test was performed using an authorized Emerald Life customer
portal account. The Data Provisioning team was informed and intentionally
left the test ticket incomplete until escalation occurred.

No manual escalation job was invoked.

### Production activation

Escalation was activated at **2026-11-12 10:27:29 SAST**.

Effective production configuration:

- `telectro_data_request_escalation_start_at`:
  `2026-11-12 10:27:29`
- `telectro_data_request_escalation_recipients`:
  `["sean@telectro.co.za","pierre@telectro.co.za","christo@telectro.co.za"]`
- `telectro_data_request_notification_delivery_start_at`:
  `2026-11-10 13:25:07`

All three recipient accounts were verified as enabled System Users.
The production scheduler and queue workers had already been enabled
and verified under the production runtime release procedure.

The escalation activation timestamp excludes tickets created before
activation. No historical Data Requests were retroactively escalated.

**Production activation evidence:**

`/opt/telectro/erpnext/staging/20261111-3cca9a2/data-request-escalation-activation.txt`

SHA-256:

`7eedc05193c38e7d5bb8f529c22554262d7d3ff419bfe1e673b88629f082831c`

### Controlled production test — HD Ticket #76

The customer portal successfully created ticket `#76` with:

- Subject: `This is a test ticket`
- Creation: `2026-11-12 10:34:04.554836` SAST
- Customer: Emerald Life
- Service Area: `Data Request`
- Ticket Type: `Service Request`
- Priority: `High`
- Assigned team: `Data Provisioning`
- Initial status: `Open`
- First completion timestamp: `None`

The ticket was created after escalation activation and remained
incomplete beyond the ten-minute threshold.

### Automatic escalation timeline

| Event | Production time (SAST) |
|---|---|
| Ticket creation | 10:34:04 |
| Ten-minute threshold | 10:44:04 |
| Automatic escalation scheduler execution | 10:44:49 |
| Three escalation intents created | 10:44:49 |
| Native Email Queue records last modified | 10:46:51 |
| Intent delivery reconciliation completed | 10:51:49 |

The escalation scheduler executed automatically on its normal
one-minute cron cadence.

Exactly three escalation intents were created approximately
45 seconds after the ten-minute threshold.

The recipients matched the approved configuration:

- `sean@telectro.co.za`
- `pierre@telectro.co.za`
- `christo@telectro.co.za`

No additional recipient or duplicate escalation intent was observed
in the ticket-specific inspection.

The Data Request Escalation Report independently identified
ticket `#76` as overdue while it was Open and assigned to
Data Provisioning.

### Notification delivery and mailbox acceptance

| Recipient | Intent delivery | Native Email Queue | Independent mailbox receipt |
|---|---|---|---|
| Sean | Complete / Sent | Sent | Confirmed at 10:47 SAST |
| Pierre | Complete / Sent | Sent | Confirmed |
| Christo | Complete / Sent | Sent | Confirmed |

For each recipient, production inspection verified:

- Exactly one escalation intent for ticket `#76`
- `delivery_state=Complete`
- `email_state=Sent`
- Linked native Email Queue with status `Sent`
- Linked Notification Log
- `next_attempt_on=None`

At the earlier 10:48 inspection, the intents still reported
`Processing / Queued` although native email delivery had progressed.

The automatic notification-delivery scheduler subsequently reconciled
all three records to `Complete / Sent` at approximately 10:51:49.

All three designated recipients independently confirmed actual receipt
of their escalation emails.

This establishes mailbox delivery beyond Frappe's native
Email Queue `Sent` status.

### Final test-ticket state

Ticket `#76` was subsequently **Resolved** through the
normal operational workflow.

The final Helpdesk screenshot confirms:

- Status: `Resolved`
- Ticket Type: `Service Request`
- Service Area: `Data Request`

Historical escalation intents, Notification Logs and Email Queue records
are retained as operational audit evidence.

### Acceptance markers

```text
RELEASE_ID=20261111-3cca9a2
PRODUCTION_ACCEPTANCE_DATE=2026-11-12
DATA_REQUEST_ESCALATION_ACTIVATED=PASS
PRODUCTION_TEST_TICKET=76
CUSTOMER_PORTAL_DATA_REQUEST_CREATION=PASS
DATA_REQUEST_CLASSIFICATION=PASS
AUTOMATIC_TEN_MINUTE_ESCALATION=PASS
ESCALATION_INTENTS=3_OF_3
ESCALATION_RECIPIENTS=3_OF_3
ESCALATION_REPORT_OVERDUE=PASS
NOTIFICATION_LOGS_LINKED=3_OF_3
NATIVE_EMAIL_QUEUE_SENT=3_OF_3
INTENT_DELIVERY_COMPLETE=3_OF_3
INDEPENDENT_MAILBOX_CONFIRMATIONS=3_OF_3
TEST_TICKET_RESOLVED=PASS
DATA_REQUEST_PRODUCTION_ESCALATION_ACCEPTANCE=PASS
```

### Related customer submission incident

Earlier on 12 November, a customer portal Data Request submission
returned HTTP 417 with:

`frappe.exceptions.ValidationError: Data Requests must be Service Requests.`

The exception originated in
`telephony/data_request_intake.py`,
within `prepare_data_request_insert()`.

A subsequent genuine Emerald Life Data Request, ticket `#74`,
was successfully created and fulfilled, with customer activity,
technician response, attachment and resolution.

An outdated browser session is a possible explanation for the
earlier rejection, but this was **not conclusively established**.

No emergency production source correction or rollback was performed.

If the rejection recurs, investigate the submitted Ticket Type,
portal application version and request context before changing
the intake validation guard.

### Continuing production state and release boundary

**Data Request escalation remains activated in production**, using
the three explicitly configured recipients.

The successful acceptance test does not authorize additional
recipient changes, scheduler configuration changes, notification
replay or new production test tickets.

Production runtime recovery checkpoints R1–R5 passed.

Formal Phase 23 final-state evidence and Phase 24 operational
release closure remain outstanding under:

`docs/runbooks/production-runtime-release.md`

**Do not repeat the successful production escalation test merely
to complete documentation.**

## Rollback

If production escalation must be stopped, unset `telectro_data_request_escalation_start_at` using Frappe's parsed Python `None` value.

Example syntax for the `bench set-config` command:

`bench --site <site-name> set-config telectro_data_request_escalation_start_at None --parse`

Do not use lowercase JSON `null` with `--parse`.

Disabling escalation capture prevents new escalation intents but does not cancel already created intents or notifications.

If delivery must also be stopped, assess the effect on existing Data Request arrival notifications before changing the separate notification-delivery setting.

Retain all historical notification and audit evidence.
