# Ticket Status and Workspace Baseline

## Purpose

This note records the pilot baseline established on **2026-03-13** after routing and assignment behavior had stabilized sufficiently to support a cleaner operational working model.

The goal was to:

- establish a clearer ticket-status baseline
- remove stale pilot clutter from normal operator flow
- preserve a visible distinction between:
  - active work
  - genuine completed work
  - retained stale pilot history

---

## Operational trust boundary

The routing / assignment trust boundary is **2026-03-12**.

### Meaning

- tickets created **on or after 2026-03-12** are treated as part of the current reliable pilot baseline for routing / assignment validation
- tickets created **before 2026-03-12** are treated as **pre-baseline pilot records**

Pre-baseline records may still exist for reference, but they are **not** considered trustworthy operational history for validating the current routing / assignment contract.

---

## Status model

The intended pilot meaning of ticket statuses is:

### Open

Active operational work.

### Resolved

Genuine operational tickets completed through the normal flow.

### Closed

Reserved for real terminal operational use where applicable.

### Archived

Retained stale or non-operational historical pilot records.

### Important distinction

`Archived` is intentionally separate from `Resolved`.

This prevents stale pilot residue from being mixed into genuine completed operational history.

---

## Cleanup decision taken

Pre-2026-03-12 stale pilot tickets were removed from normal active flow and retained under **Archived**.

This decision was taken because older pilot tickets had survived multiple changes to routing and assignment behavior and no longer represented trustworthy operational records.

Keeping them mixed into active or resolved working surfaces created:

- unnecessary noise
- weaker reporting clarity
- harder proofing of the current pilot contract

---

## Workspace intent

The `TELECTRO-POC Tech` workspace now follows this operational intent:

- **+ Log Ticket** opens `HD Ticket` filtered to `Status = Open`
- **Resolved Tickets** provides intentional access to genuine completed operational work
- **Unclaimed (War Room)** remains a primary entry point for pool / claim flow
- **Archived** is not part of the normal tech working path

### Practical effect

The primary operator path stays focused on active work, while completed and historical records remain deliberately accessible without cluttering day-to-day execution.

---

## Reporting rule

Unless a report explicitly needs archive history, **Archived tickets should be excluded by default** from operational reporting.

Operational reporting should normally distinguish between:

- active work (`Open`)
- genuine completed work (`Resolved` / `Closed`)
- retained stale pilot residue (`Archived`)

This keeps reporting aligned with the operational trust boundary.

---

## Rationale

The pilot accumulated a significant number of stale tickets before routing and assignment behavior stabilized.

Those records were useful only as retained pilot history, not as trustworthy current operational data.

Introducing **Archived** creates a clean separation between:

- current live work
- genuine completed operational work
- retained stale pilot residue

This avoids future ambiguity where reporting or workspace views would otherwise have to separate real completed tickets from cleanup residue by ad hoc filtering or interpretation.

---

## Future direction

Future reporting and workspace design should continue to preserve this distinction.

In particular:

- operator-facing entry paths should prefer active working views
- completed operational history should remain intentionally accessible
- archived pilot residue should remain available, but outside the normal operator flow

---

## Note

This baseline is a pilot hygiene decision as much as a status decision.

Its purpose is to keep:

- daily work clearer
- proofing cleaner
- reports easier to interpret
- old pilot residue from being mistaken for current operational truth
n.

Its purpose is to keep:

- daily work clearer
- proofing cleaner
- reports easier to interpret
- old pilot residue from being mistaken for current operational truth
