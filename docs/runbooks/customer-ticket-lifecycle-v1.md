# Customer Ticket Lifecycle V1

## Purpose

This document captures the intended Customer ticket lifecycle for the Telectro ERPNext / Helpdesk pilot.

The Customer Intake discovery proved that the native Helpdesk customer portal can be used as the Customer Web Intake foundation. Customers can create tickets, select Service Area, upload private attachment evidence, and remain contained to customer-safe portal surfaces.

The remaining gap is not ticket intake. The remaining gap is customer-facing lifecycle visibility after the ticket has been submitted.

## Confirmed Telectro decision

Telectro does not require formal Customer sign-off in the portal before closing a Customer ticket.

The confirmed operational process is:

```text
Telectro consults directly with the Customer.
Telectro confirms that the work is accepted through that direct interaction.
Telectro records the outcome.
Telectro closes or resolves the ticket internally.
```

The Customer should not need to press an approve/reject/sign-off button in the portal.

## Important distinction from Partner workflow

Customer workflow should not copy the Partner acceptance/rework train.

Do not add Customer equivalents of:

```text
Customer Acceptance Requested
Accepted by Customer
Customer Rework Required
Customer Acceptance Review Queue
Customer accept/reject portal buttons
Partner-style Customer work/acceptance state machine
```

Partner workflow is more formal because a Partner may perform work, receive assigned work, complete work, request Telectro review, or participate in a formal acceptance train.

Customer workflow is different.

The Customer needs:

```text
clear status visibility
customer-visible progress updates
a clear resolution/work-done outcome
safe attachment/evidence visibility where appropriate
a simple route for follow-up if the Customer still has a concern
```

Closure remains a Telectro-controlled action.

## Customer Ticket Lifecycle V1 shape

Recommended V1 lifecycle:

```text
1. Customer submits ticket through the native Helpdesk customer portal.
2. Ticket is routed internally by Telectro using Service Area and routing rules.
3. Telectro works the ticket internally.
4. Telectro consults directly with the Customer where needed.
5. Telectro confirms acceptance through direct Customer communication.
6. Telectro records a customer-facing resolution/work-done summary.
7. Telectro resolves or closes the ticket.
8. Customer portal shows the resolution outcome and current/closed status.
```

## Customer portal should show

The Customer portal should make the ticket state understandable without exposing internal operational noise.

V1 customer-visible fields should include:

```text
Ticket number
Subject
Status
Priority, if useful
Service Area
Created date
Last updated date
Latest customer-visible update
Resolution/work-done summary
Resolved or closed date, where applicable
Customer-submitted attachments
Telectro-shared evidence/attachments, if explicitly allowed
```

The portal should avoid showing:

```text
internal assignment details
internal routing/debug comments
private Telectro-only notes
internal governance/reassignment actions
raw private file URLs
Partner-specific acceptance/work states
```

## Telectro-side finalisation requirement

When Telectro resolves a Customer ticket, the operator should capture enough information for both audit and Customer visibility.

Recommended finalisation inputs:

```text
Customer consultation note
Work done / resolution summary
Customer-visible closure note
Internal-only note, if needed
Resolution date
Optional evidence or attachment reference
```

The customer-visible closure note should be deliberate and clean. It should not rely on arbitrary internal timeline comments.

## Follow-up after closure

V1 does not require formal Customer sign-off.

If the Customer still has a concern after closure, the preferred V1 options are:

```text
Customer replies through the existing communication path, if email/reply handling is active.
Customer adds a follow-up comment, if the native portal supports this safely.
Telectro opens or links a follow-up ticket, if the issue is new or materially different.
```

Avoid adding a complex Customer rework/acceptance state machine unless Telectro explicitly requests it later.

## Attachment and evidence principle

Customer and Telectro evidence should remain private File records attached to the HD Ticket.

Customer-facing file access should be controlled.

Do not expose raw `/private/files/...` URLs as the intended access model.

Recommended V1 approach:

```text
Customer-submitted files remain visible to the Customer where native portal permissions allow.
Telectro-shared evidence should be exposed only if deliberately marked or routed through a controlled customer-safe mechanism.
Internal-only evidence remains internal.
```

## Minimum implementation direction

Recommended implementation sequence:

```text
1. Inspect native Helpdesk customer portal support for customer-visible comments, status, and resolution display.
2. Decide whether the native customer ticket detail page can be lightly extended.
3. If native extension is too limited, create a controlled customer-safe ticket detail page.
4. Add or reuse a Telectro-side customer-visible resolution/closure note.
5. Ensure internal comments/debug/routing noise is not shown to Customers.
6. Ensure resolved/closed Customer tickets show a clear outcome in the portal.
```

## Open decisions

```text
- Whether to extend the native Helpdesk customer ticket detail page or build a controlled customer-safe detail page.
- Where to store the customer-visible resolution/work-done summary.
- Whether Customer follow-up after closure should reopen the same ticket, add a comment, or create/link a follow-up ticket.
- Whether Telectro-shared evidence needs a formal visibility flag.
- Whether Customer closed/resolved tickets need a separate archive/list view.
- Whether email replies should be the preferred Customer follow-up channel once incoming email is enabled.
```

## Current decision

```text
Do not build formal Customer sign-off for V1.
Do not copy the Partner acceptance/rework state machine to Customer tickets.
Do provide clearer customer-visible progress and resolution outcome.
Telectro remains responsible for closing Customer tickets after direct Customer consultation confirms acceptance.
```

