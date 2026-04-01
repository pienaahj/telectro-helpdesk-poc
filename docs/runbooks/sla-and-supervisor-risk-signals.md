# SLA and Supervisor Risk Signals

## Purpose

Document where Helpdesk SLA timing is configured in the pilot, what current assumptions are in effect, and how supervisor-facing risk signals should interpret those fields.

This runbook exists to separate:

- **system SLA targets** configured in Helpdesk
- **supervisor warning/risk signals** derived from those targets for operational visibility

These are related, but they are **not the same thing**.

---

## Scope

This runbook covers:

- where the current SLA is configured
- how `Response By` and `Resolution By` are derived
- what current pilot SLA assumptions appear to be
- what remains provisional pending Telectro confirmation
- how future supervisor risk views should interpret those fields

This runbook does **not** define Telectro’s final operational SLA policy.  
Those values must ultimately come from Telectro’s actual working practice and agreed support model.

---

## Current source of truth

Current ticket SLA timing is driven from the Helpdesk SLA configuration:

- **Module / DocType:** `HD Service Level Agreement`
- **Current record in use:** `Default`

Observed from the UI:

- `Default SLA` is enabled
- the record is enabled
- it defines priority-based first response and resolution targets
- it also defines working hours and a holiday list

This means the values shown on an `HD Ticket` under the **SLA** tab are not arbitrary.  
They are derived from the active SLA configuration in Helpdesk.

---

## Where to change it

To review or change the current SLA timing:

- open **Helpdesk**
- navigate to **HD Service Level Agreement**
- open the record **`Default`**

Relevant areas in that record:

### Response and Resolution

Priority rows define the configured targets for:

- **First Response Time**
- **Resolution Time**

### Working Hours

Working-hour windows and holiday list affect how the deadlines are calculated.

### Default SLA

The current record is marked as the default SLA, so new tickets may inherit it unless another SLA-selection rule overrides it.

---

## Current observed pilot configuration

The current `Default` SLA appears to be configured as follows:

### Priority targets

- **Low**
  - First Response Time: `24h`
  - Resolution Time: `72h`
- **Medium**
  - First Response Time: `8h`
  - Resolution Time: `24h`
- **High**
  - First Response Time: `1h`
  - Resolution Time: `4h`
- **Urgent**
  - First Response Time: `30m`
  - Resolution Time: `2h`

### Default priority

- **Medium**

### Resolution timing

- **Apply SLA for Resolution Time** is enabled

### Working hours

- Holiday List: `Default`
- Working days observed: Monday–Friday
- Working hours observed: `10:00` to `18:00`

---

## Ticket fields affected

On `HD Ticket`, the SLA-related fields currently observed include:

- `sla`
- `response_by`
- `resolution_by`
- `agreement_status`

These should be treated as follows:

### `sla`

The SLA record applied to the ticket.

### `response_by`

The system-derived target datetime by which the first response is due.

### `resolution_by`

The system-derived target datetime by which the ticket should be resolved.

### `agreement_status`

The current SLA lifecycle/status shown by Helpdesk (for example `First Response Due`).

---

## Important distinction: SLA target vs supervisor warning signal

This is the key operational distinction.

### System SLA target

The **actual due target** is defined by Helpdesk SLA configuration and stamped onto the ticket as:

- `response_by`
- `resolution_by`

These fields are the system truth for the current pilot configuration.

### Supervisor warning / risk signal

A supervisor risk signal is a **monitoring/reporting interpretation** of those target fields.

Examples:

- target already passed
- target due within the next 24 hours
- target approaching breach within a chosen warning window

These warning windows are **not automatically the SLA itself**.  
They are an operational overlay used to help supervisors intervene early.

---

## Current pilot assumptions

At present, the pilot should assume:

- tickets are using the Helpdesk SLA configuration from `HD Service Level Agreement: Default`
- `response_by` and `resolution_by` are the correct fields to use for supervisor timing visibility
- the current configured timing values are **provisional pilot assumptions**
- the final business meaning of those timings must be confirmed with Telectro

This means:

- the system wiring is valid
- the fields are useful
- the exact numbers may still change later

---

## Current known limitation

The current pilot does **not yet** treat the current SLA timing values as final Telectro-approved operational policy.

Therefore:

- build reports off the **derived ticket fields**
- document the current SLA configuration
- avoid claiming the timing thresholds are final business truth until Telectro confirms them

---

## Recommended supervisor signal model

The preferred supervisor pattern is to separate:

### First Response

- **First Response At Risk**
- **First Response Missed**

### Resolution

- **Resolution At Risk**
- **Resolution Missed**

This keeps the operational meaning clear:

- **At Risk** = still potentially recoverable
- **Missed** = already slipped and now requires recovery/escalation

Supervisor-facing intervention should generally give more visual weight to **At Risk** than **Missed**, because that is where action can still prevent a breach.

---

## Recommended implementation order

### First slice

Implement supervisor reporting from:

- `response_by`

Start with:

- **First Response At Risk**
- **First Response Missed**

### Later slice

Mirror the same pattern using:

- `resolution_by`

For:

- **Resolution At Risk**
- **Resolution Missed**

---

## Defining “At Risk”

“At Risk” is not the same thing as the SLA target.

It is a warning window **before** the target.

Examples of possible future definitions:

- due within next 2 hours
- due within next 4 hours
- due within next working day
- due within next 24 hours

The exact warning window must be treated as a configurable/reporting assumption until Telectro confirms what is operationally useful.

### Current recommendation

Until Telectro confirms the preferred warning window:

- document the chosen report threshold explicitly
- label it as a **pilot reporting assumption**
- avoid presenting it as if it is a contractual SLA rule

---

## Verification steps

### Verify current SLA record

1. Open **Helpdesk > HD Service Level Agreement**
2. Open record **`Default`**
3. Confirm:
   - record is enabled
   - `Default SLA` is checked
   - priority rows match expected values
   - working hours and holiday list are set as expected

### Verify ticket fields

Open a recent `HD Ticket` and confirm the **SLA** tab shows:

- SLA
- SLA Status
- Response By
- Resolution By

### Verify active ticket population in bench console

Example proof query:

```python
import frappe

rows = frappe.db.sql("""
    SELECT
        COUNT(*) AS total_active,
        SUM(CASE WHEN response_by IS NOT NULL THEN 1 ELSE 0 END) AS with_response_by,
        SUM(CASE WHEN resolution_by IS NOT NULL THEN 1 ELSE 0 END) AS with_resolution_by
    FROM `tabHD Ticket`
    WHERE status IN ('Open', 'Replied')
""", as_dict=True)

print(rows[0])
```

Expected outcome:

- active tickets should have populated SLA target fields if the SLA is being applied correctly

---

## Change management note

If Telectro later confirms different operational timings, update:

1. the relevant `HD Service Level Agreement` record(s)
2. this runbook
3. any supervisor reports whose warning windows are based on pilot assumptions

Do **not** silently leave reports using stale warning assumptions after SLA configuration changes.

---

## Summary

### System truth

- SLA timing is currently configured in `HD Service Level Agreement`
- current pilot appears to use record `Default`
- `response_by` and `resolution_by` are the correct derived timing fields on `HD Ticket`

### Operational truth

- supervisor risk signals should be built from those derived fields
- “At Risk” and “Missed” should be treated as separate supervisor views

### Governance truth

- current configured timings are usable for pilot structure
- final thresholds and business interpretation still require Telectro confirmation


1. the relevant `HD Service Level Agreement` record(s)
2. this runbook
3. any supervisor reports whose warning windows are based on pilot assumptions

Do **not** silently leave reports using stale warning assumptions after SLA configuration changes.

---

## Summary

### System truth

- SLA timing is currently configured in `HD Service Level Agreement`
- current pilot appears to use record `Default`
- `response_by` and `resolution_by` are the correct derived timing fields on `HD Ticket`

### Operational truth

- supervisor risk signals should be built from those derived fields
- “At Risk” and “Missed” should be treated as separate supervisor views

### Governance truth

- current configured timings are usable for pilot structure
- final thresholds and business interpretation still require Telectro confirmation
