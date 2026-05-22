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

## Customer containment proof

A follow-up containment check was performed with the proof customer user:

```text
User: test@boschendal.co.za
user_type: Website User
effective roles: Customer, All, Guest
```

The user had the intended HD Ticket permission shape:

```text
read = True
create = True
write = True
delete = False
```

Browser route checks:

```text
/helpdesk/my-tickets        allowed
/helpdesk/my-tickets/798    allowed
/app                        blocked / not permitted
/app/telectro-poc-ops       blocked / not permitted
/app/telectro-poc-tech      blocked / not permitted
/app/report                 blocked / not permitted
/app/hd-ticket              blocked / not permitted
```

Permission-aware bench proof used `frappe.get_list()` as the customer user:

```text
row_count: 1
visible ticket: 798
```

The customer user could see only their own native customer-created ticket:

```text
HD Ticket: 798
raised_by = test@boschendal.co.za
owner = test@boschendal.co.za
contact = Customer
custom_request_source = Customer
custom_service_area = Other
status = Open
```

Important testing note:

```text
frappe.get_all() bypasses normal list permissions and is not valid for customer containment proof.
Use frappe.get_list() or browser/API behaviour when proving portal visibility.
```

Conclusion:

```text
Native Helpdesk customer portal containment is viable for a Customer Website User with safe HD Ticket read/create/write and no delete permission.
```

## Customer organisation linkage proof

A follow-up proof confirmed how native Helpdesk resolves the `HD Ticket.customer` field for customer portal tickets.

Helpdesk does not resolve `HD Ticket.customer` from ERPNext `Customer` directly. It uses:

```text
Contact → Dynamic Link → HD Customer
```

The proof customer contact initially had no Dynamic Links:

```text
Contact: Customer
email_id: test@boschendal.co.za
Dynamic Links: []
HD Customers: none
```

After creating HD Customer `Boschendal` and linking Contact `Customer` to it through a Dynamic Link, Helpdesk customer resolution returned:

```text
get_customer("Customer") = ["Boschendal"]
get_customer("test@boschendal.co.za") = ["Boschendal"]
```

A new native customer portal ticket then resolved the organisation correctly:

```text
HD Ticket: 799
owner = test@boschendal.co.za
raised_by = test@boschendal.co.za
contact = Customer
customer = Boschendal
subject = Subject: Native customer portal organisation linkage proof
priority = Medium
ticket_type = Faults
agent_group = Helpdesk Team
via_customer_portal = 1
custom_request_source = Customer
custom_service_area = Other
_assign = ["hendrik@local.test"]
```

Important notes:

```text
- Existing ticket 798 remained customer = None because it was created before the Contact → HD Customer link existed.
- New native portal tickets created after the link correctly set customer = Boschendal.
- The native customer portal Close action can be mistaken for closing the view; this is a UX risk to revisit before production use.
```

Conclusion:

```text
Native Helpdesk customer portal can support organisation-aware customer intake once customer Contacts are linked to HD Customer records.
```

## Customer portal field capture proof

A follow-up proof confirmed that native Helpdesk customer portal fields can expose selected Telectro custom fields through `HD Ticket Template Field`.

Initial discovery showed that the Default template existed but had no configured template fields:

```text
HD Ticket Template: Default
Default HD Ticket Template Field row_count: 0
get_visible_custom_fields() = []
```

The installed `HD Ticket Template Field` child table is intentionally small and only controls inclusion/visibility behaviour:

```text
fieldname
url_method
required
hide_from_customer
placeholder
```

The first safe field tested was `custom_service_area` because it is a simple `Select` field on `HD Ticket`, not a customer-facing Link field.

The Default template was configured with:

```text
fieldname = custom_service_area
required = 1
hide_from_customer = 0
placeholder = Select the affected service area
```

After the change, Helpdesk reported:

```text
get_visible_custom_fields() = ["custom_service_area"]
```

A new native customer portal ticket then captured the selected service area correctly:

```text
HD Ticket: 800
owner = test@boschendal.co.za
raised_by = test@boschendal.co.za
contact = Customer
customer = Boschendal
subject = Testing Customer cerated ticket with Service Area visible
status = Open
priority = Medium
ticket_type = Faults
agent_group = Routing
via_customer_portal = 1
custom_request_source = Customer
custom_service_area = Routing
_assign = ["tech.alfa@local.test"]
```

This also proved that the existing Telectro routing logic consumed the customer-selected Service Area:

```text
custom_service_area = Routing
agent_group = Routing
_assign = ["tech.alfa@local.test"]
```

Important notes:

```text
- `custom_service_area` is a good first customer-visible field because it is a Select field with fixed options.
- `custom_site_group` and `custom_site` should not be exposed yet without a separate Link-field containment proof.
- Customer-facing Link fields to Location may require additional permissions, filtering, or a safer controlled lookup model.
```

Conclusion:

```text
Native Helpdesk customer portal can support customer-visible Telectro field capture through HD Ticket Template Field. Service Area is now proven as a safe first field and integrates with the existing routing flow.
```
