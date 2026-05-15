# Pilot Outstanding Issues and Timeline

## Purpose

This document tracks the remaining ERPNext Pilot issues, expected order of work, and rough timeline.

The goal is to keep pilot scope clear:

- protect demo-critical flows
- avoid mixing unrelated workflow changes
- keep technical debt visible
- separate urgent pilot issues from later polish

---

## Current state

The pilot now has working foundations for:

- Partner-safe ticket request and ticket detail flows
- Partner acceptance and rework flow
- Partner work completion and review flow
- Ticket Evidence V1 upload/list/download/camera capture
- Notification V1 in-app alerts for selected action-required workflow states
- Partner-safe notification routing
- Explicit creator take-ownership option for internal manual tickets
- Current-work and team-load visibility through reports/workspaces

Reports and workspaces remain the primary operational source of truth.

Notifications are supporting nudges only.

---

## Timeline view

### Immediate / demo-safe

These items should be prioritised before further broad workflow expansion.

#### 1. Stabilise workspace landing behaviour

Status: outstanding

Problem:

- Internal and Partner landing behaviour can become inconsistent after route-guard or workspace changes.
- Partner route containment must remain strict.
- Internal users should land on the correct Tech / Coordinator / Ops workspace based on role.

Target outcome:

- Partner users land on `TELECTRO-POC Partner`.
- Tech users land on `TELECTRO-POC Tech`.
- Coordinator users land on `TELECTRO-POC Coordinator`.
- Supervisor/Ops users land on `TELECTRO-POC Ops`.
- No Partner user should land on raw HD Ticket list/report/workspace surfaces.

Suggested next slice:

- Re-test current landing behaviour by role.
- Capture actual route outcomes.
- Fix only proven broken redirects.

---

#### 2. Continue assignment/timeline noise cleanup discovery

Status: discovery started

Findings so far:

- Fresh creator take-ownership assignment is clean.
- Normal routing assignment is clean.
- Older Partner transition tickets show noisy timeline sequences when assignment changes from Telectro owner to Partner queue.
- Noise is layered:
  - native Frappe `Assigned` comments
  - native `Assignment Completed` comments
  - TELECTRO explicit `Info` comments from assignment normalisation
  - historical repair/setup actions
- `TELECTRO_RULE_DEBUG` comments are not currently active in inspected tickets.

Target outcome:

- Do not suppress native assignment comments globally.
- Avoid unnecessary assignment mutation when the final owner is already correct.
- For Partner fulfilment transitions, prefer one clear workflow signal where possible.
- Keep assignment state correct before optimising timeline appearance.

Suggested next slice:

- Pick one current reproducible noisy transition.
- Prove exact function/hook responsible.
- Patch only if semantics are not affected.

---

#### 3. Verify My Team Load operating fit

Status: implemented

Reason:

- A Telectro technician requested visibility of team load so technicians can help one another.
- This is a team-awareness and peer-support report, not only a supervisor governance report.

Current outcome:

- `My Team Load` report shows current active load by owner / pool.
- Uses Open ToDo as the canonical assignment source.
- Shows total open tickets, pool count, and Partner queue items.
- Anchored for internal use.

Target outcome:

- Confirm the report appears in the intended Tech / Coordinator / Ops workspaces.
- Confirm technicians understand it as a peer-support view.
- Confirm counts are useful and not misleading.

Suggested next slice:

- Validate report from Tech user.
- Validate report from Coordinator user.
- Validate report from Supervisor/Ops user.
- Consider minor label changes only if users misunderstand the purpose.

---

## Near-term pilot backlog

### 4. Customer Site evidence upload model

Status: outstanding

Reason:

- Ticket Evidence V1 currently supports evidence against HD Tickets.
- The next practical model is evidence against customer/site context where useful.

Target outcome:

- Define whether evidence belongs to:
  - HD Ticket only
  - Customer Site / Location
  - both via ticket context
- Avoid turning ticket evidence into a full document-management system.

Suggested order:

1. Define data model.
2. Define internal upload/list/download path.
3. Define Partner-safe exposure, if needed.
4. Add audit/context comments only where useful.

---

### 5. Evidence metadata / category / context

Status: outstanding

Reason:

- Current evidence upload works, but files are mostly just attached files plus comments.
- Telectro may later need better context around why a file was uploaded.

Possible fields:

- evidence category
- uploaded by actor type
- evidence note
- workflow step
- visible to Partner flag
- related site/fault asset

Suggested approach:

- Keep V1 evidence simple.
- Add metadata only when a real workflow need is proven.

---

### 6. Download audit logging

Status: optional / later

Reason:

- Controlled download endpoints exist.
- Audit logging could help prove who accessed private evidence.

Target outcome:

- Record download events only for controlled endpoints.
- Avoid noisy audit rows for every internal browser preview unless explicitly needed.

---

### 7. Optional evidence deletion/removal policy

Status: optional / later

Reason:

- Evidence deletion/removal can become governance-sensitive.
- Current priority is upload/view/download.

Target outcome:

- Define who may remove evidence.
- Preserve audit trail.
- Avoid silent deletion of pilot proof.

---

## Partner containment backlog

### 8. Partner report access tightening for multi-user Partner accounts

Status: future hardening

Reason:

- Current Partner access is suitable for pilot-style Partner users.
- If multiple Partner users/accounts are used under the same Partner organisation, visibility rules may need refinement.

Target outcome:

- Decide whether Partner users see:
  - only tickets they own
  - all tickets for their Partner organisation
  - only tickets assigned to their Partner queue
- Implement explicit model rather than relying on owner alone.

---

### 9. Partner-safe history visibility

Status: optional

Reason:

- Partner ticket detail currently surfaces selected latest notes.
- Some use cases may need broader Partner-visible ticket history.

Target outcome:

- Expose useful history without leaking internal-only timeline entries.
- Keep raw HD Ticket timeline hidden from Partner users.

---

## Notification backlog

### 10. Recipient fallback rules

Status: future hardening

Current V1 is narrow and proven.

Potential future cases:

- no Telectro assignee exists
- ticket owner is not an internal user
- Partner assignee is missing
- Coordinator/Ops should receive fallback alerts

Suggested approach:

- Do not add broad fallback notifications until a real missed-action case is proven.
- Reports/workspaces remain the source of truth.

---

### 11. Email / mobile / browser push

Status: explicitly out of scope for V1

Current position:

- Notification V1 is in-app `Notification Log` only.
- Email Queue is not part of V1.
- Mobile/browser push is not promised.

Suggested approach:

- Only add email for high-value events if Telectro explicitly needs it.
- Avoid notification noise.

---

## Later polish / technical debt

### 12. Duplicate helper cleanup in `partner_create.py`

Status: later cleanup

Known examples:

- duplicated helper patterns
- duplicate note-key style areas
- evidence helper consolidation opportunities

Suggested approach:

- Do not refactor during active workflow changes.
- Only clean when tests/proof flows are stable.

---

### 13. Workspace fixture noise management

Status: ongoing

Reason:

- Workspace changes can export broad fixture noise.
- Route/landing behaviour can regress after workspace edits.

Suggested approach:

- Keep workspace PRs small.
- Inspect fixture diffs carefully.
- Use restore scripts where appropriate.
- Validate landing after route/workspace PRs.

---

## Working principles

- One slice at a time.
- Verify existing code before augmenting.
- Prefer in-container edits with VSCode Dev Containers.
- Use bench console for proof.
- Pull changed files back to host before Git diff/commit.
- Avoid changing assignment semantics unless the exact before/after behaviour is proven.
- Keep Partner containment stricter than internal convenience.
- Reports/workspaces are the source of truth; notifications are nudges.
