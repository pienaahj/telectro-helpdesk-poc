# Notification V1 Operating Model

## Purpose

Notification V1 defines the first controlled notification layer for the ERPNext Pilot.

The goal is to give users small, action-required nudges when a workflow state needs their attention, without replacing the reports and workspaces that remain the operational source of truth.

## Operating principle

Reports and workspaces remain the primary way to manage operational work.

Notifications are only used as supporting alerts for specific action-required workflow transitions.

Notification V1 is intentionally narrow:

- in-app `Notification Log` alerts only
- `type = Alert`
- no Email Queue changes
- no assignment changes
- no ToDo changes
- no routing changes
- no workflow-state changes

## What Notification V1 does

Notification V1 creates in-app alerts for selected workflow events where a specific user needs to take action.

The alert is linked back to the related `HD Ticket`.

The intended use is:

- draw attention to a ticket that needs action
- support users who may not constantly watch every queue
- preserve reports and workspaces as the reliable queue-management layer

## What Notification V1 does not do

Notification V1 does not promise:

- email delivery
- mobile push notifications
- browser push notifications
- generic activity notifications
- notifications for every timeline comment
- notifications for every field change
- notifications for every assignment side effect

This avoids creating noisy or misleading alerts during the pilot.

## Recipient rules

### Internal / Telectro-facing notifications

| Event | Recipient |
| --- | --- |
| Controlled Handoff completed | Receiving technician |
| Partner acceptance submitted | Current Telectro assignee from `_assign` |
| Partner acceptance rework requested by Partner | Current Telectro assignee from `_assign` |
| Partner work completed | HD Ticket owner |

### Partner-facing notifications

| Event | Recipient |
| --- | --- |
| Partner acceptance requested by Telectro | Partner ticket owner |
| Partner work rework requested by Telectro | Partner assignee from `_assign` |

## Workflow events that notify

Notification V1 covers these action-required events:

- Controlled Handoff receiver must take ownership of the handed-off ticket.
- Partner must review a Partner acceptance request from Telectro.
- Telectro must review Partner acceptance submitted by Partner.
- Telectro must respond when Partner requests acceptance rework.
- Telectro must review Partner work completed by Partner.
- Partner must respond when Telectro requests Partner work rework.

## Workflow events intentionally silent

The following are intentionally silent in V1:

- review-only actions
- evidence uploads
- generic timeline comments
- generic field changes
- debug comments
- assignment canonicalisation side effects
- native assignment events that Frappe already handles
- email delivery

## Relationship to reports and workspaces

Notifications are not the queue.

The operational queue remains visible through:

- Partner workspace cards
- Telectro / Ops / Coordinator workspaces
- current-work reports
- Partner workflow reports
- review and rework queues
- supervisor and coordinator views

This distinction is important for the pilot because reports and workspaces are easier to audit, explain, and govern than relying on notification behaviour alone.

## Pilot expectation-setting

For Telectro users, the safe explanation is:

> The system now creates in-app alerts for selected workflow actions that need attention. These alerts are helpful nudges, but the reports and workspaces remain the official place to manage the queue.

For Partner users, the safe explanation is:

> Partner users receive in-app alerts for specific Partner-side actions, such as when Telectro requests acceptance or when rework is required. The Partner workspace and Partner ticket pages remain the main place to work from.

## Known watch items

The following should be monitored during pilot use:

- whether Partner users notice in-app alerts clearly enough
- whether Telectro users notice in-app alerts clearly enough
- whether the notification bell behaviour is sufficient
- duplicate `Assignment Completed` comments during some Partner flows
- assignment/canonicalisation noise
- old pilot tickets with stale state confusing proof checks
- missing-recipient edge cases

## Future options

Possible later slices:

- recipient fallback rules when no Telectro assignee exists
- recipient fallback rules when the ticket owner is not an internal user
- coordinator or supervisor fallback alerts
- email notifications for selected high-value events
- mobile/browser push investigation
- notification visibility improvements in workspaces
- notification cleanup / deduplication if noise appears
