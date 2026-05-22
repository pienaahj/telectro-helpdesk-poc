# Customer Portal Discovery

## Outcome

Native Frappe Helpdesk customer portal was proven viable as the base for Customer Web Intake.

A clean Customer Website User was able to log in, open the native Helpdesk customer portal, create a ticket, and view the created ticket.

Proof ticket:

```text
HD Ticket: 798
owner = test@boschendal.co.za
raised_by = test@boschendal.co.za
contact = Customer
customer = None
subject = This is a test ticket creation.
status = Open
priority = Medium
ticket_type = Faults
agent_group = Helpdesk Team
via_customer_portal = 1
custom_request_source = Customer
custom_customer = None
custom_service_area = Other
_assign = ["hendrik@local.test"]
```

## Confirmed

```text
- /helpdesk loads native Helpdesk SPA.
- Agent/Admin users see the Helpdesk agent interface.
- Customer Website Users can reach /helpdesk/my-tickets/new once permissions are corrected.
- Native ticket creation flows through HD Ticket lifecycle.
- Telectro hooks still run on native customer-created tickets.
- custom_request_source is set to Customer.
- custom_service_area falls back to Other.
- Routing/assignment still happens.
- Customer can view their submitted ticket through the native portal.
```

## Local blockers found

```text
1. HD Ticket Custom DocPerm blocked customer create/write.
2. Helpdesk Contact role has desk_access = 1 and forces System User / Desk User, so it is not suitable for contained customer portal users.
3. Customer role with Website User is the cleaner customer account model.
4. Helpdesk customer article search expects Redis Search / FT.SEARCH. The local Redis service does not support it.
5. Native Helpdesk SPA attempted to call telephony.api.is_call_integration_enabled, but the endpoint was missing.
```

## Working local customer model

```text
User:
- user_type = Website User
- roles = Customer
- no Helpdesk Contact
- no Desk User
- no Agent / Agent Manager / System Manager
- no TELECTRO internal or Partner roles

HD Ticket permission:
- Customer read/create/write = 1
- delete = 0
```

## Important note on Helpdesk Contact

```text
Helpdesk Contact has desk_access = 1.
Adding it to a customer user converts the user back to System User / Desk User.
For this pilot, do not use Helpdesk Contact for contained Customer Web Intake unless this is deliberately changed.
```

## Native portal gaps still to solve

```text
- Link Contact to HD Customer / organisation so customer is not None.
- Decide how to expose customer/site/service area selection.
- Decide whether customer intake uses native ticket template fields or a thin wrapper.
- Decide whether attachments/evidence are enabled in native portal or handled through controlled Telectro evidence endpoints.
- Decide whether to provide Redis Stack / RediSearch or suppress Knowledge Base article suggestions for pilot.
- Add safe telephony call integration status endpoint if the Helpdesk SPA expects it.
```

## Current recommendation

Do not build a custom Customer Intake page yet.

Use native Helpdesk Customer Portal as the base, then add only the minimum Telectro-specific alignment needed for:

```text
- customer identity / organisation linkage
- service area / site capture
- evidence upload policy
- safe permissions
- production-ready Redis/search decision
```

