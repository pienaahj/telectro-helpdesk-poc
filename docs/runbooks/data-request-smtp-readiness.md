# Data Request — SMTP and Notification Delivery Readiness

- **Evidence captured:** 2026-11-06 (Africa/Johannesburg)
- **Status:** DEV source and configuration inspection complete; production acceptance outstanding
- **Release authority:** `docs/runbooks/production-runtime-release.md`
- **Related readiness note:** `docs/runbooks/data-request-scheduler-activation.md`
- **Change:** Draft PR #415 (`feat/2026-11-04-data-request-10min-escalation`)

## Purpose and boundaries

Preserve the accepted DEV evidence for the Data Request notification delivery path, identify the risks of actual outbound email, and specify production pre-activation checks. This document does **not** authorize deployment, scheduler activation, outbound notification activation, SMTP reconfiguration, or a production test send.

The production release runbook remains authoritative, including the explicit **Phase 2 human-review gate** and subsequent phase order. Scheduler execution and notification delivery are **separate operational activation decisions**. Enabling the Frappe site scheduler may also run other registered jobs, including pilot inbox polling; do not enable it merely to test notification delivery.

## Accepted DEV evidence (do not repeat without a concrete reason)

| Check | Finding |
|---|---|
| ESC.265 | `telephony.jobs.data_request_notification_delivery.run()` delegates to the bounded batch processor; the entry point itself does not send mail. |
| ESC.266 | Batch maximum is 100; `dry_run=True` returns after selection without invoking individual workers. Processing errors are isolated, with rollback and durable failure handling on the live path. |
| ESC.267 | Selector is read-only and separately gated by `frappe.conf.telectro_data_request_notification_delivery_start_at`. Missing setting disables selection; a future timestamp yields `not_due`. Only intents created on or after activation and no later than current time can qualify. |
| ESC.268 | Individual worker rechecks eligibility under `SELECT ... FOR UPDATE`, owns commit/rollback, and persists retry/backoff after eligible failures. |
| ESC.269 | Dispatcher records/reuses an in-app Notification Log, creates or reconciles the referenced Email Queue, and refuses duplicate queue creation. `Queued` maps to intent `Processing`, not `Complete`. |
| ESC.270 | `frappe.sendmail(..., delayed=True)` is used for a single authorized internal recipient; `communication=None`, with Email Queue linked to the notification intent. Queueing is not proof of SMTP delivery. |
| ESC.271 | Ten DEV Email Accounts, nine outgoing-enabled. `Routing` is default outgoing. All inspected accounts specify `mail:587` with their TLS/SSL options disabled. Neither `disable_email_sending` nor `mute_emails` was set in site configuration. |
| ESC.272 | DEV Docker Mailserver image `mailserver/docker-mailserver:14.0.0` running and healthy. Backend DNS resolved `mail` and backend TCP connected to `mail:587`. |
| ESC.273 | SMTP `EHLO` succeeded (`250`). AUTH advertised before TLS; STARTTLS **not** advertised. No authentication or message submission attempted. |
| ESC.274 | Postfix global and submission `smtpd_tls_security_level=none`; submission SASL authentication enabled; TLS-only authentication not enabled; no TLS certificate file configured. |
| ESC.275 | No global Postfix `relayhost`; `default_transport=smtp`, `smtp_tls_security_level=none`, `smtp_sasl_auth_enable=no`, and `relay_transport=relay`. No external route or delivery was exercised. |

## Activation and delivery semantics

The notification selector uses the site-local, timezone-naive configuration key:

```text
telectro_data_request_notification_delivery_start_at
```

- **Absent:** notification delivery selection disabled, even if the scheduler is running.
- **In the future:** selection returns `not_due`.
- **Reached:** only eligible intents with `creation >= activation` and `creation <= now` are candidates, up to 100 per batch.
- **Eligible delivery states:** `Pending`, due `Retry`, and recoverable `Processing` (including a five-minute stale-processing fallback when no next-attempt time is recorded).
- **Recheck:** the worker verifies activation and eligibility again under its row lock.
- **Historical data:** intents created before the activation timestamp are excluded; choose and record the production activation timestamp deliberately. Do not assume the historical backlog will be sent.

The observed source implements a staged path:

1. Data Request Notification Intent is recorded.
2. When separately activated and due, the worker processes the intent and records/reuses the internal Notification Log.
3. `frappe.sendmail(delayed=True)` creates a Frappe Email Queue record, without requesting immediate SMTP sending.
4. A separate native email-sending mechanism may subsequently process the queue. **Once queued, sending is not controlled solely by the Data Request activation timestamp.**
5. Reconciliation maps Email Queue `Not Sent`/`Sending` to `Queued`, `Sent` to `Sent`, and `Error`/`Partially Sent` to `Failed`. The intent reaches `Complete` only after reconciliation reports `Sent`.

A Frappe queue status of `Sent` is not proof that the destination mailbox received the message.

## DEV Email Queue inventory

Read-only query at ESC.271:

| Native Email Queue status | Rows |
|---|---:|
| Sent | 13 |
| Not Sent | 2 |
| Error | 1 |

No existing records were retried or modified. These records were not attributed to the Data Request feature and do not prove external delivery.

## DEV SMTP endpoint and security observations

The configured hostname `mail` resolves inside Docker to the running **Docker Mailserver 14.0.0**, not a harmless mail-catching stub. DEV has a real mail delivery implementation and must be treated as potentially capable of sending external email.

- **Submission endpoint:** `mail:587`; container's host mapping is `1587->587`.
- **Connection:** backend-to-mail TCP connectivity and EHLO proved.
- **SMTP TLS:** STARTTLS not advertised; Postfix explicitly has TLS security `none` for submission.
- **SMTP authentication:** advertised before TLS; submission SASL enabled. Credentials and actual authentication were **not tested**.
- **Outbound routing:** no global upstream `relayhost`; standard SMTP delivery transport selected; outbound TLS not required and outbound SASL authentication disabled. Per-destination routing and actual external connectivity remain unverified.

**Security restriction:** do not submit real SMTP credentials across this observed unencrypted DEV submission path. Do not copy these DEV TLS settings into production. Actual production SMTP settings must be inspected independently.

## Production pre-activation checklist

1. Follow the committed production runtime release runbook, preserving the Phase 2 human approval gate and all release phases. Review the separate scheduler activation note.
2. Inspect production site scheduler status, job registrations, queue workers, and **all** enabled scheduled jobs/side effects before deciding whether to activate the scheduler. Container uptime alone is not scheduler-dispatch proof.
3. Inspect actual production Email Account configuration, SMTP endpoint, sender identity, authentication method, TLS settings, outbound network and firewall policy **without exposing credentials**.
4. Require secure SMTP submission (appropriate certificate validation, encryption and authentication) before sending live messages. If external SMTP submission is unreachable, resolve its network route or firewall policy separately; internal `mail:587` DEV reachability is not evidence for production.
5. Confirm the authorized internal Coordinator recipients for Data Request arrival and ten-minute escalation, and validate role/permission and customer-data containment.
6. Inspect native production Email Queue inventory and pending/error items before allowing the mail sender to run. Avoid unexpected old-queue dispatches.
7. Explicitly approve and record a site-local notification-delivery activation timestamp. Document the pre-activation-intent exclusion boundary.
8. Plan a controlled, approved recipient and test message, isolated from customer notifications, with a documented stop/rollback plan. Do not manufacture production demo tickets.
9. Distinguish acceptance evidence for (a) intent creation, (b) Notification Log/Email Queue, (c) authenticated and encrypted SMTP submission, (d) mail-system acceptance, and (e) mailbox receipt. Inspect failure handling without replaying accepted DEV regression suites unnecessarily.
10. Under an authorized release window, prove actual scheduler tick → job enqueue → worker execution, followed by controlled email queue handling and operational monitoring. Capture evidence and perform the release runbook's closure requirements.

## Outstanding production acceptance

- Production scheduler state and complete enabled-job side-effect review.
- Authorized automatic scheduler tick, enqueue, and native worker execution.
- Actual production SMTP endpoint, network path, authentication and secure TLS verification.
- Controlled runtime creation/reconciliation of a queued notification and native email sending.
- SMTP acceptance and verified receipt at an authorized test mailbox.
- Human approval, rollback readiness and final operational closure through the authoritative release runbook.

## Release control

Accepted DEV source inspections **ESC.265–275** are preserved here and need not be rerun without concrete contrary evidence. They are not substitutes for production-specific operational evidence.

**Production remains ON HOLD.**
