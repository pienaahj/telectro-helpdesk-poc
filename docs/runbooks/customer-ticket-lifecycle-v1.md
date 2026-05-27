# Customer Ticket Lifecycle V1

## Purpose

This document captures the intended Customer ticket lifecycle for the Telectro ERPNext / Helpdesk pilot.

The Customer Intake discovery proved that the native Helpdesk customer portal can be used as the Customer Web Intake foundation. Customers can create tickets, select Service Area, upload private attachment evidence, and remain contained to customer-safe portal surfaces.

The original gap was not ticket intake. The original gap was customer-facing lifecycle visibility after the ticket had been submitted.

That gap is now sufficiently proven for V1 deployment: Customers can view ticket status, add follow-up updates, see customer-visible Telectro Communications, and see Resolved tickets in the portal. Remaining work is mainly operational polish and Telectro-side workflow convenience, not a blocker to the V1 Customer Intake model.

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

## Current implementation proof

As of 2026-05-26, Customer Ticket Lifecycle V1 has been proven through the native Helpdesk customer portal.

Confirmed behaviour:

```text
Customer can create a ticket through the native Helpdesk customer portal.
Customer can select Service Area during ticket creation.
Service Area is saved on the HD Ticket and consumed by routing.
Customer can upload private attachment evidence during ticket creation.
Customer can view their own tickets through the Customer portal.
Customer can add follow-up updates through the Customer ticket detail page.
Customer follow-up updates are stored as Communication records.
Internal Comments are not Customer-visible.
Customer portal users cannot close Customer tickets directly.
The native Customer portal Close action is hidden for V1.
A backend guard blocks Customer / Website users from setting Customer tickets to Closed.
Internal / Telectro users can still resolve or close Customer tickets.
Resolved Customer tickets remain visible in the Customer ticket list.
Resolved status and fulfilled response / resolution indicators are visible to the Customer.
Customer Knowledge Base and article suggestion affordances are suppressed for V1.
```

Proof tickets from the deployability slice:

```text
802 - Customer lifecycle proof:
      Customer creation, private evidence, Customer follow-up, Telectro customer-visible Communication,
      Customer close prevention, internal finalisation, Resolved detail/list visibility.

803 - Customer portal V1 polish proof:
      Customer portal still worked after hiding Knowledge Base/article suggestion affordances;
      Service Area routing still worked.

804 - Customer update affordance proof:
      Customer ticket detail showed a clear Add update action;
      Customer-side ticket view and sidebar remained usable.
```

Current V1 position:

```text
Customer Intake V1 is deployable as a native Helpdesk customer portal flow with Telectro-specific guardrails and light UI polish.

Customer ticket completion is Telectro-controlled.
Customer-facing progress and outcome updates must be sent as Communication / Email Reply, not internal Comment.
Resolved is the preferred Customer-facing completion state for V1.
Closed remains an internal/administrative state and is not Customer-controlled.
```

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
7. Telectro resolves the ticket for V1.
8. Customer portal shows the resolution outcome and Resolved status.
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

## Follow-up after resolution

V1 does not require formal Customer sign-off.

The proven Customer follow-up path is:

```text
Customer opens their ticket in the native Customer portal.
Customer uses the Add update action on the ticket detail page.
Customer submits extra information, photos, or feedback.
The update is stored as a Communication and remains visible in the ticket activity.
```

For V1, Customer follow-up is intended for active or resolved ticket communication. The Customer should not close the ticket directly from the portal.

If the Customer still has a concern after Telectro has resolved the issue, the preferred V1 options are:

```text
Customer adds a follow-up update through the portal, where the ticket remains available.
Customer replies through email, once incoming email handling is active and proven.
Telectro reopens, follows up, or links a new ticket if the issue is new or materially different.
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

## Open decisions and backlog

```text
- Add a clearer Telectro-side Customer Resolution action so operators do not rely on hidden status fields.
- Decide where to store a structured customer-visible resolution/work-done summary if Communication alone is not enough.
- Decide whether Customer follow-up after Resolved should reopen the same ticket, remain as Communication, or create/link a follow-up ticket.
- Decide whether Telectro-shared evidence needs a formal visibility flag.
- Decide whether Customer resolved tickets need a separate archive/list view later.
- Decide whether email replies should become the preferred Customer follow-up channel once incoming email is enabled.
- Keep customer Location / Campus Link fields deferred until safe customer-scoped lookup/filtering is implemented and proven.
```

## Current decision

```text
Do not build formal Customer sign-off for V1.
Do not copy the Partner acceptance/rework state machine to Customer tickets.
Do provide clearer customer-visible progress and resolution outcome.
Telectro remains responsible for closing Customer tickets after direct Customer consultation confirms acceptance.
```

## Customer organisation-level visibility

Customer Intake V1 supports multiple named Customer Website Users linked to the same Customer organisation.

The intended model is:

```text
Customer Website User
→ Contact
→ Dynamic Link
→ HD Customer
→ HD Ticket.customer
```

Customer users are contained by Customer organisation, not only by individual ticket ownership. This means multiple customer-side contacts for the same organisation can see and participate in that organisation’s tickets while preserving individual audit identity.

For example, two Boschendal users can both access Boschendal portal tickets:

- `test@boschendal.co.za`
- `customer2@boschendal.co.za`

Both users resolve to `HD Customer = Boschendal`.

Permission-aware proof showed:

- both users could see the same Boschendal ticket set;
- `customer2@boschendal.co.za` saw zero non-Boschendal tickets;
- `customer2@boschendal.co.za` created ticket 809;
- ticket 809 was linked to `customer = Boschendal`;
- ticket 809 had `owner`, `raised_by`, and `contact` tied to `customer2@boschendal.co.za`;
- `customer2@boschendal.co.za` uploaded private evidence file `Customer portal test file.xlsx`;
- `test@boschendal.co.za` could view ticket 809 and add a Customer update;
- both Customer updates were recorded as separate Communications with the correct sender identity;
- both Customer users and Telectro could see the ticket/update path.

This avoids shared logins while allowing customer-side staff to cover one another’s tickets.

## Follow-on: Customer Location/Campus scoped filtering

The Customer organisation resolver introduced for Customer ticket visibility is also the foundation for Customer Location/Campus filtering.

Before exposing Customer-side Location/Campus fields, the next slice must prove that lookup/search results are scoped by the current Customer user’s linked `HD Customer`.

Required proof:

- Boschendal Customer users can see/select only Boschendal locations;
- a Boschendal Customer user cannot search/select another Customer’s locations;
- filtering is enforced server-side, not only by browser UI filters;
- unrestricted Link-field exposure is avoided.

