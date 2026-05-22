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

## Customer Location Link-field containment discovery

A follow-up discovery checked whether native Helpdesk customer portal should expose the Telectro Location Link fields:

```text
custom_site_group = Campus
custom_site = Fault Point
```

The customer proof user remained a contained Website User:

```text
User: test@boschendal.co.za
roles: Customer, All, Guest
user_type: Website User
```

Location permissions for the customer user were:

```text
read = False
create = False
write = False
delete = False
```

A permission-aware Location list check as the customer failed:

```text
frappe.get_list("Location") as customer -> PermissionError
```

This is the safe default because the Location tree contains a mixed hierarchy of campus/group records and detailed child fault points.

The relevant native Helpdesk portal field methods were inspected:

```python
def get_visible_custom_fields():
    return frappe.db.get_all(
        "HD Ticket Template Field",
        {"parent": "Default", "hide_from_customer": 0},
        pluck="fieldname",
    )


def get_customer_portal_fields(doctype, fields):
    visible_custom_fields = get_visible_custom_fields()
    customer_portal_fields = [
        "name",
        "subject",
        "status",
        "priority",
        "response_by",
        "resolution_by",
        "creation",
        *visible_custom_fields,
    ]
    fields = [field for field in fields if field.get("value") in customer_portal_fields]
    return fields
```

Finding:

```text
Native Helpdesk only allowlists fields from HD Ticket Template Field.
It does not itself add customer-specific Location filtering or containment.
```

Decision:

```text
Do not expose custom_site_group or custom_site directly on the customer portal yet.
```

Recommended phased approach:

```text
Phase 1:
Keep customer portal intake limited to Service Area, which is already proven as a safe Select field.

Phase 2:
Design a controlled customer-safe Location lookup that derives allowed Location records from the customer organisation / HD Customer / Contact relationship.

Phase 3:
Only expose Campus/Fault Point after proving the lookup cannot leak unrelated Location records.
```

Conclusion:

```text
Customer-visible Location Link fields need a separate containment design. The native customer portal field-template mechanism is safe for fixed Select fields like Service Area, but Location Link fields should remain hidden until customer-scoped lookup/filtering is implemented and proven.
```
