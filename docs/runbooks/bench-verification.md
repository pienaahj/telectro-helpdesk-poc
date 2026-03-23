# Bench Verification Playbook (Pilot)

Goal: verify pilot behavior from current code and committed facts, without being misled by stale bench state, stale browser state, or guessed assumptions.

Use this playbook:

- before changing behavior
- before claiming proof
- when results feel contradictory
- when inbound mail behavior, breadcrumbs, or ticket outcomes need to be verified from current reality

---

## Why this exists

A recurring pilot problem is not only buggy logic. It is also misleading verification state, for example:

- stale bench session state
- stale module imports
- stale browser/UI state
- proof attempts based on guessed IDs instead of facts
- breadcrumbs read out of context

This playbook exists to reduce false debugging trails and improve proof quality.

---

## Core rules

### 1) Verify existing behavior before augmenting it

Do not start by editing.

Start by proving:

- what code is actually installed
- what data is actually committed
- what breadcrumbs are actually present
- what the system actually did

### 2) Prefer factual anchors over inferred outcomes

Use the strongest available proof anchor first.

Current preferred inbound proof hierarchy:

1. `Communication`
2. linked `HD Ticket`
3. ticket business fields
4. breadcrumbs
5. UI impressions

### 3) Query by facts, not guessed IDs

Prefer:

- known sender
- known subject
- known communication name
- latest records by creation
- exact field names verified from meta / DB truth

Avoid:

- “it was probably ticket 688”
- “the browser still shows old state so it must have failed”

### 4) Treat staleness as a default risk

If results feel contradictory, assume staleness first:

- stale bench session
- stale module import
- stale browser state
- stale breadcrumbs context

---

## Preferred working method

Order of preference:

1. inspect/edit in-container with VSCode Dev Containers / Container extension
2. use `bench console`
3. use shell / `docker compose exec` / heredocs only as last resort

Why:

- correct site/app context matters
- bench console is the safest place for proof queries
- shell shortcuts are useful but easier to get subtly wrong

---

## Bench session rules

### Use fresh sessions for important proof

A fresh bench session is usually safer than reusing a long-lived one.

Use a fresh session when:

- verifying a just-changed script
- verifying a just-changed job
- results contradict the UI
- results contradict earlier bench output

### Reload modules during active iteration

When iterating on Python proof helpers:

```python
import importlib
import telephony.scripts.job_status_pull_pilot_inboxes as s
import telephony.scripts.proof_pull_pilot_inboxes as p

importlib.reload(s)
importlib.reload(p)
```

Do not assume bench has reloaded changed modules automatically.

### Do not mutate `frappe.local.*` as a “cache reset” habit

Avoid using internal context mutation as a routine debugging technique.

That tends to create more uncertainty than clarity.

---

## Current verified pilot truths

These are currently verified and should be treated as proof anchors:

- `custom_customer` is the active pilot inbound customer field
- `customer` is currently not the effective inbound customer field on this path
- `custom_site_group` is the campus/site field in use
- `Communication` is the safest authoritative inbound proof anchor
- poller dedupe is identity-based only
- semantic/business duplicate suppression is intentionally out of scope for pilot

---

## Standard proof flow for inbound test mail

### Step 1 — Confirm poller health

Run:

```python
import importlib
import telephony.scripts.job_status_pull_pilot_inboxes as s

importlib.reload(s)
s.run()
```

Confirm:

- pilot inbox config looks correct
- `last_ok` is fresh
- no active `last_err` problem
- verdict is sensible

### Step 2 — Inspect richer breadcrumbs

Run:

```python
import importlib
import telephony.scripts.proof_pull_pilot_inboxes as p

importlib.reload(p)
p.run()
```

Inspect:

- `last_mail_meta`
- `last_skip_meta`
- `last_comm`
- `last_ticket`
- `per_account`
- `last_per_account_nonzero`

### Step 3 — Find the `Communication`

For inbound proof, start with the communication created by the mail path.

Confirm:

- sender
- subject
- creation time
- reference linkage

### Step 4 — Confirm linked ticket state

Only after the `Communication` is proven should you confirm:

- `custom_customer`
- `raised_by`
- `custom_site_group`
- `agent_group`
- `status`

### Step 5 — Use Stage A breadcrumbs only in context

Remember:

- Stage A breadcrumbs are event-driven
- zero-mail runs do not populate them
- missing Stage A breadcrumbs do not automatically mean poller failure

---

## Verification hierarchy by use case

### A) Inbound mail proof

Preferred order:

1. prove poller health
2. find the resulting `Communication`
3. confirm linked `HD Ticket`
4. confirm ticket business fields
5. inspect Stage A breadcrumbs if needed

Why:

- `Communication` is the most reliable inbound proof anchor currently in this pilot

### B) Poller health proof

Preferred order:

1. `Scheduled Job Type`
2. `Scheduled Job Log`
3. poller breadcrumb keyspace
4. quick status helper
5. richer proof helper

Recommended scripts:

```python
import importlib
import telephony.scripts.job_status_pull_pilot_inboxes as s
import telephony.scripts.proof_pull_pilot_inboxes as p

importlib.reload(s)
importlib.reload(p)

s.run()
p.run()
```

### C) Field truth / schema truth

If uncertain whether a field is real, populated, or queryable:

- use `meta.get_valid_columns()`
- inspect actual DB-backed fields
- prefer schema truth over UI assumptions

This is especially important when differentiating between:

- real DB columns
- derived / virtual / display fields
- fields that exist but are not the pilot-active path

---

## Poller breadcrumb interpretation

Poller keyspace base:

```text
telephony:pull_pilot_inboxes:*
```

Important meanings:

- `per_account`
  - latest run snapshot only

- `last_per_account_nonzero`
  - preserved last meaningful snapshot
  - useful after later idle runs

- `last_skip_meta`
  - explains most recent skip reason
  - useful for blocked noise and dedupe interpretation

- `last_err`
  - error signal, but not always the whole story
  - always check whether later success has occurred

---

## Stage A breadcrumb interpretation

Stage A keyspace base:

```text
telephony:stage_a:*
```

Use these breadcrumbs to understand intake mapping behavior, not generic poller liveness.

Keep the separation clean:

- poller health proof:
  - `telephony:pull_pilot_inboxes:*`

- intake mapping proof:
  - `Communication`
  - ticket outcome
  - `telephony:stage_a:*` when mail actually processed

That separation matters.

---

## Anti-patterns

Avoid these mistakes:

- trusting old browser state over fresh bench queries
- assuming bench has reloaded changed Python modules
- proving inbound behavior from ticket guesses instead of `Communication`
- treating `per_account` as historical truth
- treating missing Stage A breadcrumbs as generic poller failure
- trying to “fix” uncertainty by mutating `frappe.local.*`
- expanding scope before verifying the current slice

---

## Good proof habits

Prefer these habits:

- use fresh bench sessions for critical proof
- use one-shot factual queries
- reload script modules during active iteration
- verify from authoritative anchors first
- separate poller-liveness proof from business-outcome proof
- record concrete proof notes as you go

---

## Minimal daily-use pattern

For routine pilot mail verification:

```python
import importlib
import telephony.scripts.job_status_pull_pilot_inboxes as s
import telephony.scripts.proof_pull_pilot_inboxes as p

importlib.reload(s)
importlib.reload(p)

s.run()
p.run()
```

Then, if needed:

- send controlled smoke mail
- verify from `Communication`
- confirm resulting ticket business fields

---

## What “done” looks like for a proof task

A proof task is done when you can clearly state:

- what was tested
- which source of truth was used
- what evidence was observed
- what remained unchanged
- what conclusion is safe to make

Not when the UI happened to look right once.

---

## Condensed reminder

When in doubt:

- fresh bench
- reload modules
- prove poller health first
- prove inbound from `Communication`
- only then interpret ticket fields
- treat breadcrumbs according to their actual semantics


Not when the UI happened to look right once.

---

## Condensed reminder

When in doubt:

- fresh bench
- reload modules
- prove poller health first
- prove inbound from `Communication`
- only then interpret ticket fields
- treat breadcrumbs according to their actual semantics
