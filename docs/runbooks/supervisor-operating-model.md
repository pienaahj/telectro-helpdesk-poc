# Supervisor Operating Model — Pilot

## Purpose

The supervisor function in the pilot supports **queue health, team awareness, and timely intervention**.

It is not a mechanical scoring function and it is not intended to replace technician ownership. Its purpose is to help the supervisor see where work is sitting, where attention may be needed, and where load balancing or coaching may improve service flow.

The supervisor view should help answer four practical questions:

- What work is currently unclaimed or back in the pool?
- What work appears to be aging, stuck, or at risk?
- Who is currently carrying active work?
- Where is imbalance, overload, or underload emerging across the team?

### Supervisor responsibilities

The supervisor is responsible for monitoring the operational state of both the queue and the team.

This includes:

- monitoring pool and unclaimed work
- monitoring aging or stuck tickets
- monitoring tickets released back to the pool
- monitoring current workload distribution across technicians
- identifying overload, underload, or imbalance
- using service indicators to support coaching and intervention, not to mechanically judge performance

That distinction matters. The reporting layer should remain managerial and constructive. It should support good operational decisions, not reduce the team to simplistic productivity scoring.

### Supervisor role

The supervisor role covers both **queue oversight** and **team-state oversight**.

In practice, this means the supervisor needs visibility into:

- unclaimed work that still needs ownership
- active work that may be aging or drifting
- tickets released back into the pool
- current technician workload
- visible imbalance across the team
- selected service indicators that suggest attention may be needed

These indicators are intended for **operational awareness, coaching, and intervention**. They are not intended to function as a simplistic performance score.

### Intervention model

The normal operating model remains **technician ownership**.

A supervisor should generally allow the assigned technician to carry and progress their own work unless there is a clear operational reason to step in.

Supervisor intervention is appropriate when:

- work remains unclaimed for too long
- a ticket is aging without visible progress
- a ticket has been released back to the pool and needs renewed ownership
- technician workload appears materially imbalanced
- a technician is overloaded or unavailable
- a ticket appears to need escalation or coordination outside the normal flow

Supervisor action should normally be light-touch first:

1. review the queue and team state
2. identify the item or technician needing attention
3. prompt, coach, or clarify where appropriate
4. re-route or escalate only when justified

The aim is to preserve technician ownership wherever possible and use supervisor intervention as an exception path rather than the default mode of operation.

### Claim / release / escalation in practice

For the pilot, the intended working model is:

- technicians claim work from the pool
- technicians carry ownership of claimed work
- technicians may release work back to the pool when justified
- supervisors monitor the effect of those movements on queue health and team balance
- supervisor reassignment or escalation is an exception path used when ownership, progress, or service flow requires intervention

This keeps the technician flow simple while still giving the supervisor enough operational visibility to manage the queue responsibly.

### Controlled Handoff and accountability audit

When a supervisor or coordinator needs to transfer ticket ownership, the approved path is **Controlled Handoff**.

Controlled Handoff should be used when:

- the current owner is unavailable
- the ticket needs a different accountable owner
- workload balancing requires ownership transfer
- escalation or coordination requires a clear accountable owner change

Controlled Handoff is not a contributor mechanism. It transfers accountable ownership from one owner, or the true pool, to one new accountable owner.

Every successful Controlled Handoff records a durable audit row showing:

```text
ticket
changed on
changed by
from user
to user
reason
source
```

### Supervisor workspace

The `TELECTRO-POC Ops` supervisor workspace is the operational shell for supervisor use.

Current state:

- queue-health cards retained
- active unclaimed quick list corrected
- admin shortcuts removed to keep admin concerns separate
- supervisor report links added and rendering correctly

This workspace is intended to be the supervisor’s practical starting point for monitoring queue health and team state.

### Supervisor reports

#### `Supervisor Team Snapshot`

`Supervisor Team Snapshot` tells the supervisor **who is carrying load**.

It is intended to provide a quick team-level view of:

- who is currently carrying work
- how much active work each technician is carrying
- where aging sits within that owned work
- which technicians may need balancing, support, or intervention

This is the supervisor’s **team-state overview** report.

#### `Active Tickets by Technician`

`Active Tickets by Technician` tells the supervisor **what that load actually is**.

For each currently owned active ticket, it shows:

- who owns the ticket
- which ticket it is
- what the subject is
- what status it is in
- how old or stale it appears
- which items may deserve attention first

This is a **detail drill-down report**, not a KPI report.

Its purpose is to help the supervisor move from summary to specifics.

#### `Aging and At-Risk Tickets`

`Aging and At-Risk Tickets` tells the supervisor **which active owned tickets most likely need intervention attention**.

This report is intended to show:

- only active owned tickets
- only tickets older than the chosen threshold
- oldest or stalest items first
- technician visible on every row
- a practical intervention-oriented list for supervisor follow-up

This is the supervisor’s **attention list** rather than a general workload list.

#### `TELECTRO Assignment Handoff Audit`

`TELECTRO Assignment Handoff Audit` tells the supervisor **who changed accountable ownership, from whom, to whom, when, and why**.

This report is intended to support governance around supervisor/coordinator intervention.

It shows Controlled Handoff audit rows, including:

- ticket
- ticket subject
- changed on
- changed by
- from user
- to user
- reason
- source

This is a governance and accountability report, not a productivity score.

### Reporting intent

The supervisor reports work together:

- `Supervisor Team Snapshot` shows **who is carrying load**
- `Active Tickets by Technician` shows **what that load consists of**
- `Aging and At-Risk Tickets` shows **which owned items may need intervention first**
- `TELECTRO Assignment Handoff Audit` shows **who transferred accountable ownership, when, and why**

Together they support a supervisor workflow of:

1. scan the team
2. inspect the detail
3. intervene where needed

### Operating principle

The supervisor layer should support:

- visibility
- balance
- intervention
- coaching
- service protection

It should not become a simplistic performance scoreboard.

The pilot should use these indicators to improve operational awareness and decision-making first. Stronger SLA-style or comparative measures can be added later once the team flow and queue behaviour are better understood.
