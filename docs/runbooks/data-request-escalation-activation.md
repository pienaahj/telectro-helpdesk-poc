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

## Rollback

If production escalation must be stopped, unset `telectro_data_request_escalation_start_at` using Frappe's parsed Python `None` value.

Example syntax for the `bench set-config` command:

`bench --site <site-name> set-config telectro_data_request_escalation_start_at None --parse`

Do not use lowercase JSON `null` with `--parse`.

Disabling escalation capture prevents new escalation intents but does not cancel already created intents or notifications.

If delivery must also be stopped, assess the effect on existing Data Request arrival notifications before changing the separate notification-delivery setting.

Retain all historical notification and audit evidence.
