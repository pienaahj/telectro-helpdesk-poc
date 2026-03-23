# Mail Health Runbook (Pilot)

Goal: avoid silent failures in pilot email intake by providing quick health checks and a deterministic proof flow grounded in the current poller and proof helpers.

Use this runbook when:

- checking whether pilot mail intake is alive
- separating poller-health issues from ticket-intake issues
- validating breadcrumbs and scheduler state
- proving whether a controlled inbound test mail was handled correctly

Use this alongside:

- **Bench Verification Playbook** for proof discipline
- **Email Ticket Intake Runbook** for current intake contract
- **Email Reference** for mail-container/network/mailbox details

---

## What “healthy” looks like

A healthy pilot mail path currently means all of the following are true:

- `Scheduled Job Type` exists and is enabled for:
  - `telephony.jobs.pull_pilot_inboxes.run`
- recent scheduler/job activity is present and not dominated by repeated exceptions
- poller breadcrumbs show recent execution and sensible state
- Email Accounts used by pilot intake are enabled for incoming mail
- a controlled inbound test mail produces:
  - a `Communication`, and typically
  - a linked `HD Ticket`
- inbound proof is validated from `Communication` first, then ticket state

---

## Current preferred proof tools

The preferred current proof path is:

```python
import importlib
import telephony.scripts.job_status_pull_pilot_inboxes as s
import telephony.scripts.proof_pull_pilot_inboxes as p

importlib.reload(s)
importlib.reload(p)

s.run()
p.run()
```

These two scripts together provide the strongest current operator-facing proof:

### `job_status_pull_pilot_inboxes.py`

- quick job health
- pilot inbox configuration summary
- staleness verdict
- key poller breadcrumbs

### `proof_pull_pilot_inboxes.py`

- Stage A / intake breadcrumbs
- pull-poller breadcrumbs
- latest ticket sanity output
- quick verdict section

---

## Quick health check

### 1) Scheduled Job Type

In the UI:

1. open **Scheduled Job Type**
2. find method:
   - `telephony.jobs.pull_pilot_inboxes.run`
3. confirm:
   - enabled / not stopped
   - frequency is as expected for pilot
   - recent execution timestamps are advancing

### 2) Scheduled Job Log

Check for recent runs of the pilot poller and confirm they are completing.

Healthy signs:

- repeated `Complete` entries
- no repeating failure pattern
- timestamps advancing as expected

### 3) Error Log

Check for repeated exceptions around expected run times.

Healthy signs:

- no recurring poller errors
- no fresh traceback loop tied to pilot intake

### 4) Pilot Email Account sanity

Current pilot accounts expected by the poller:

- `Faults`
- `Routing`
- `PABX`
- `Helpdesk`

Confirm each has:

- `enable_incoming = 1`
- expected email address
- `email_sync_option = UNSEEN`

The quick helper already prints this:

```python
import importlib
import telephony.scripts.job_status_pull_pilot_inboxes as s

importlib.reload(s)
s.run()
```

---

## Deterministic proof flow

### Step 1 — Preflight job health

Run:

```python
import importlib
import telephony.scripts.job_status_pull_pilot_inboxes as s

importlib.reload(s)
s.run()
```

This gives:

- pilot inbox config summary
- staleness-based health verdict
- current key poller breadcrumbs

Interpretation:

- `OK` means the poller has run recently and `last_ok` is fresh
- `WARN` usually means stale or incomplete evidence, not necessarily failure
- `ERR` means missing or too-old success, or `last_err` is set

### Step 2 — Inspect richer breadcrumbs and latest ticket sanity

Run:

```python
import importlib
import telephony.scripts.proof_pull_pilot_inboxes as p

importlib.reload(p)
p.run()
```

This gives:

- Stage A / intake breadcrumbs
- pull-poller breadcrumbs
- latest `HD Ticket` sanity list
- quick verdict fields such as:
  - `poller_last_ok`
  - `poller_last_err`
  - `last_skip_meta`
  - `last_nonzero_snapshot`

### Step 3 — Controlled smoke mail

Send a controlled test mail to one pilot mailbox.

Prefer:

- clear sender
- clear subject
- easy-to-find unique marker in subject/body

After scheduler pickup or manual run, verify from `Communication` first.

### Step 4 — Prove outcome from `Communication`

Use `Communication` as the authoritative inbound proof anchor.

Check:

- communication exists
- sender is correct
- subject is correct
- linked reference is correct
- linked reference points to the expected `HD Ticket`

Only then confirm ticket-level business fields.

---

## Recommended verification order for inbound mail

When proving inbound behavior, use this order:

1. poller/job health
2. `Communication`
3. linked `HD Ticket`
4. ticket business fields
5. Stage A breadcrumbs, if relevant

This avoids false conclusions caused by stale UI, browser, or bench assumptions.

---

## Breadcrumb semantics that matter

### Poller keyspace

Base prefix:

```text
telephony:pull_pilot_inboxes:*
```

Important keys:

- `fingerprint`
  - confirms which code build / logic marker is live

- `last_run`
  - last time the job executed

- `last_start`
  - last time execution actually began after lock acquisition

- `last_ok`
  - last successful completion timestamp

- `last_err`
  - last recorded fatal error string

- `last_skip`
  - last time the job skipped, usually due to lock contention

- `last_comm`
  - most recent `Communication` produced by the poller

- `last_ticket`
  - most recent linked `HD Ticket` found from the resulting `Communication`

- `last_mail_meta`
  - last processed message metadata

- `last_skip_meta`
  - most recent skipped message metadata, including reasons such as:
    - `blocked`
    - `dedupe`

- `per_account`
  - latest run snapshot for all configured pilot inboxes

- `last_per_account_nonzero`
  - last meaningful non-idle per-account snapshot
  - preserves the last interesting state even after later zero-mail runs

### Critical semantic distinction

- `per_account` = latest run snapshot
- `last_per_account_nonzero` = last meaningful run snapshot

Do not read `per_account` as historical truth.

### Stage A keyspace

Base prefix:

```text
telephony:stage_a:*
```

These breadcrumbs are event-driven.

Important operational truth:

- Stage A breadcrumbs appear when actual intake mapping logic runs
- a zero-mail poller run should not populate Stage A breadcrumbs

---

## Current pilot truths

These are currently verified and should be treated as the pilot contract unless deliberately changed:

- `custom_customer` is the effective inbound customer field for pilot intake
- `customer` is currently not the active pilot customer field on this path
- `custom_site_group` is the current campus/site field in use
- `Communication` is the safest authoritative proof point for inbound-mail verification
- poller dedupe is identity-based re-ingest protection only
- dedupe is not business-level duplicate suppression

---

## Noise handling and mailbox hygiene

Current pilot posture:

### Preferred

Use server-side mailbox filtering/rules for obvious bounce and internal-task-notification noise.

### Code-level fallback

The poller blocklist prevents ticket creation from known blocked noise.

### If rules are unavailable

- use periodic manual mailbox cleanup
- rely on poller breadcrumbs and job logs for health verification

Known pilot boundary:

- broader business-level duplicate suppression is intentionally out of scope for pilot

---

## Secondary lightweight helper

A simpler helper still exists:

```python
import importlib
import telephony.scripts.proof_mail_health as h

importlib.reload(h)
h.run()
```

This is useful for:

- quick Scheduled Job Type presence check
- recent Error Log mentions
- best-effort breadcrumb key visibility probe

This helper is still useful, but it is no longer the preferred full proof path.

---

## When things look wrong

### If `last_ok` is fresh but no new ticket appeared

Check in this order:

1. `last_skip_meta`
2. `last_mail_meta`
3. `Communication`
4. Stage A breadcrumbs
5. latest `HD Ticket` list

This usually separates:

- blocked noise
- dedupe skip
- processed communication without expected business outcome
- stale UI assumptions

### If Stage A breadcrumbs look missing

Do not assume failure immediately.

Remember:

- Stage A breadcrumbs are event-driven
- zero-mail runs do not prove intake mapping
- poller health and Stage A proof are separate concerns

### If bench results look inconsistent

Assume session staleness before assuming business logic failure.

Use:

- fresh bench session
- one-shot proof queries
- `importlib.reload(...)` for script modules during active iteration

---

## Minimal day-to-day operator sequence

For fast daily verification:

```python
import importlib
import telephony.scripts.job_status_pull_pilot_inboxes as s
import telephony.scripts.proof_pull_pilot_inboxes as p

importlib.reload(s)
importlib.reload(p)

s.run()
p.run()
```

If needed, follow with a controlled smoke mail and verify via `Communication`.

---

## Result expectation

A good runbook outcome is not “a ticket always appears instantly.”

A good runbook outcome is:

- the poller path is provably healthy
- message handling can be explained
- skipped messages have visible reasons
- inbound business outcomes are verified from authoritative evidence

---

## SEEN behaviour and pilot intake

With IMAP + `UNSEEN`, messages are marked `\SEEN` at retrieve time in the Frappe receive pipeline.

Operational implication:

- blocked, skipped, and errored messages may not reappear automatically
- breadcrumbs and logs become the proof mechanism after fetch
- mailbox hygiene and observability matter more than retry-via-unseen assumptions

## Result expectation

A good runbook outcome is not “a ticket always appears instantly.”

A good runbook outcome is:

- the poller path is provably healthy
- message handling can be explained
- skipped messages have visible reasons
- inbound business outcomes are verified from authoritative evidence

---

## SEEN behaviour and pilot intake

With IMAP + `UNSEEN`, messages are marked `\SEEN` at retrieve time in the Frappe receive pipeline.

Operational implication:

- blocked, skipped, and errored messages may not reappear automatically
- breadcrumbs and logs become the proof mechanism after fetch
- mailbox hygiene and observability matter more than retry-via-unseen assumptions
