# Customer Location and Organisation Model — V1 Checkpoint

Date: 2026-06-01  
Project: TELECTRO ERPNext / Helpdesk Pilot  
Scope: Customer portal intake, customer organisation context, location/fault-point selection, and future routing implications.

## Purpose

This document records the current Customer portal location and organisation model after the Customer Fault Point discovery, non-point location picker, and customer organisation context normalisation slices.

The goal is to avoid losing the important model decisions made during implementation.

The key principle is:

```text
Customer organisation, commercial customer, campus, service area, location, coverage, and routing ownership are related but separate concepts.
```

Do not collapse these into one field or one fake service area.

## Current Customer Portal Intake Model

Native Helpdesk Customer portal tickets use Helpdesk's own customer organisation field:

```text
HD Ticket.customer
```

For the current Boschendal proof, this is:

```text
customer = Boschendal
```

The Telectro/internal customer field is:

```text
HD Ticket.custom_customer
```

This field links to ERPNext `Customer`.

For ticket `820`, the important proof state was:

```text
customer = Boschendal
custom_customer = blank
HD Customer exists = Boschendal
ERPNext Customer exists = None
```

Therefore, the pilot deliberately does not copy `customer` into `custom_customer`.

That would be invalid unless a matching ERPNext `Customer` exists or an explicit mapping has been configured.

## Why `custom_customer` Remains Blank for Customer Portal Tickets

The field `custom_customer` links to the ERPNext `Customer` DocType.

The native Customer portal organisation currently resolves to Helpdesk `HD Customer`.

Example:

```text
Native Customer portal organisation:
  HD Customer = Boschendal

Telectro/internal ERPNext customer field:
  custom_customer -> ERPNext Customer
```

In current local data, `Boschendal` exists as an `HD Customer`, not as an ERPNext `Customer`.

There is an ERPNext Customer record such as:

```text
Customer B - Customer Owned
```

with:

```text
Default Campus = Boschendal
```

But this is not the same as saying:

```text
ERPNext Customer = Boschendal
```

So the correct current behaviour is:

```text
customer = Boschendal
custom_customer = blank
```

## Read-Side Normalisation

Because Customer portal tickets use `customer` and internal/Telectro tickets may use `custom_customer`, read-side code should resolve customer organisation like this:

```python
ticket.get("custom_customer") or ticket.get("customer")
```

This is now used for service coverage context and internal Fault Location display.

This keeps Customer portal tickets valid while allowing internal views/helpers to show the organisation context.

## Do Not Auto-Populate `custom_customer` Yet

Do not blindly set:

```python
custom_customer = customer
```

This is unsafe because `customer` may refer to an `HD Customer`, while `custom_customer` expects an ERPNext `Customer`.

For Boschendal, that would attempt to write a non-existent ERPNext Customer value.

Future work needs an explicit mapping decision.

## Possible Future Mapping Model

A future production-safe model may need an explicit relationship:

```text
HD Customer / portal organisation
  maps to
ERPNext Customer / commercial customer
```

Example:

```text
HD Customer:
  Boschendal

ERPNext Customer:
  Customer B - Customer Owned

Campus:
  Boschendal
```

Possible implementation options:

### Option A — Mapping field on HD Customer

Add a custom field on `HD Customer`:

```text
custom_erpnext_customer -> Link Customer
```

Then configure:

```text
HD Customer Boschendal
  custom_erpnext_customer = Customer B - Customer Owned
```

Customer portal ticket creation could then safely populate:

```text
custom_customer = mapped ERPNext Customer
```

only when the mapping exists.

### Option B — Resolve through Contact / Dynamic Link

If the portal user's Contact links to both an `HD Customer` and an ERPNext `Customer`, the system could resolve the ERPNext Customer through the Contact.

This avoids adding a new mapping field, but may be less explicit and harder to reason about for multi-branch customers.

### Current Decision

No mapping is implemented yet.

The current pilot uses read-side fallback only.

## Location Model

Customer portal tickets can optionally include location context.

The Customer portal location picker is Customer-safe and server-scoped. It does not expose raw unrestricted Location links.

Current category behaviour:

```text
Buildings      -> Point
Network Nodes  -> Point
Other          -> Point
Residents      -> Point
Links          -> LineString
Areas          -> Polygon
```

The backend lookup is scoped by:

```text
logged-in Customer user
-> allowed Customer organisation
-> allowed Campus
-> selected category bucket
-> category-specific geometry type
```

## Point Location Selection

For point categories:

```text
Buildings
Network Nodes
Other
Residents
```

a selected location is saved as both:

```text
custom_site = selected Location
custom_fault_asset = selected Location
custom_fault_category = selected category
```

This reflects that the selected record is both the fault point and the selected asset context.

Proof ticket `818` showed a mapped Building selection saving correctly:

```text
custom_site_group = Boschendal
custom_fault_category = Buildings
custom_site = selected Building Location
custom_fault_asset = selected Building Location
custom_equipment_ref = EQN-12345-TEST
via_customer_portal = 1
raised_by = customer2@boschendal.co.za
```

## Optional Fault Point Behaviour

Fault Point remains optional for Customer portal tickets.

This is intentional.

Some valid Customer faults may not have an associated mapped Location yet. In those cases, the Customer can still submit the ticket using the subject, description, and equipment/circuit/SIM/tag reference.

Proof ticket `819` showed a ticket created without selecting Fault Point:

```text
customer = Boschendal
custom_site_group = Boschendal
custom_fault_category = blank
custom_site = blank
custom_fault_asset = blank
custom_service_area = Faults
custom_equipment_ref = TEST-123-FAULT-POINT
via_customer_portal = 1
raised_by = customer2@boschendal.co.za
status = Open
```

This behaviour must be preserved.

## Non-Point Location Selection

Links and Areas are non-point geometry types.

They are treated as asset-driven context, not ordinary Fault Points.

For non-point categories:

```text
Links -> LineString
Areas -> Polygon
```

a selected record is saved as:

```text
custom_fault_asset = selected Link/Area Location
custom_fault_category = Links or Areas
custom_site = blank
```

This matches the existing internal model where Links/Areas are asset-driven and should not be forced into the point-based `custom_site` field.

Proof ticket `820` showed a Link selection saving correctly:

```text
customer = Boschendal
custom_customer = blank
custom_site_group = Boschendal
custom_fault_category = Links
custom_site = blank
custom_fault_asset = Links: Wireless Connection
custom_service_area = Faults
custom_equipment_ref = LOCATION-NEW-12345
via_customer_portal = 1
raised_by = customer2@boschendal.co.za
status = Open
```

The selected asset had:

```text
location_name = Links: Wireless Connection
custom_kmz_geometry_type = LineString
```

Area lookup also worked and displayed correctly on the map.

## Internal Fault Location Display

Internal HD Ticket view now displays resolved fault location context.

For Customer portal tickets, this display should show the organisation using read-side fallback:

```text
custom_customer or customer
```

For ticket `820`, internal location context returned:

```text
customer = Boschendal
campus = Boschendal
category = Links
fault_point = None
fault_asset = Links: Wireless Connection
primary_location = Links: Wireless Connection
service_area = Faults
```

This is the correct display model for a non-point Link ticket.

## Service Coverage Context

`service_coverage.get_ticket_context()` now falls back from `custom_customer` to `customer`.

For ticket `820`, the context resolved as:

```text
ticket = 820
customer = Boschendal
campus = Boschendal
service_area = Faults
```

Coverage rows returned `0` in the local proof.

That is treated as missing coverage configuration/data, not a failure to resolve ticket context.

## Boschendal Service Coverage Proof

A local proof row was created to confirm that native Customer portal tickets can match TELECTRO Service Coverage without requiring `custom_customer`.

Proof row:

```text
TELECTRO Service Coverage: TSC-2026-00003
enabled = 1
coverage_scope = Campus
customer = blank
campus = Boschendal
service_area = Faults
user = hendrik@local.test
coverage_role = Primary
priority = 10
notes = Local proof row for Customer portal Boschendal Faults coverage.
```

Ticket `820` resolved coverage context as:

```text
ticket = 820
customer = Boschendal
campus = Boschendal
service_area = Faults
```

`get_matching_coverage_rows_for_ticket("820")` returned:

```text
coverage rows count = 1
matched row = TSC-2026-00003
coverage_scope = Campus
campus = Boschendal
service_area = Faults
user = hendrik@local.test
coverage_role = Primary
_match_rank = 2
```

This proves that Customer portal tickets can participate in coverage matching through Campus + Service Area scope.

The result intentionally does not use Customer/Campus scope yet because `TELECTRO Service Coverage.customer` links to ERPNext `Customer`, while native Customer portal tickets currently provide Helpdesk `HD Customer` through `HD Ticket.customer`.

Current V1 interpretation:

```text
Customer portal organisation:
  HD Ticket.customer = Boschendal

Coverage match:
  Campus = Boschendal
  Service Area = Faults
```

Until explicit HD Customer -> ERPNext Customer mapping is decided, Boschendal-specific Customer portal coverage can be represented with Campus + Service Area rows.

## Important Architecture Principle

Do not use fake Service Areas to represent customer responsibility.

For example, avoid creating service areas like:

```text
Boschendal Coordinator
```

That mixes two separate concepts:

```text
Service taxonomy
```

with:

```text
Customer responsibility / ownership mapping
```

Service Area should describe the nature of work or operational domain, for example:

```text
Faults
Internet Connection
PABX
CCTV
Quotes & Site Surveys
```

Customer responsibility should be modelled separately.

## Responsibility / Coverage Model

Future routing should be based on explicit coverage/responsibility rules, not overloaded Service Area labels.

Preferred conceptual model:

```text
Customer / Campus / Service Area
  -> Primary / Eligible / Backup users
  -> optional preferred coordinator / default owner
```

This keeps the model flexible enough for both simple and complex customers.

Example simple customer:

```text
Customer organisation:
  Boschendal

Campus:
  Boschendal

Service Area:
  Faults

Coverage:
  Primary coordinator or technician group to be decided
```

Example future complex customer:

```text
Customer organisation:
  Emerald Life

Campuses / branches:
  50+ branches

Coverage:
  May vary by branch, region, service area, preferred technician, or coordinator
```

This is why customer organisation, campus, service area, and ownership/routing must stay separate.

## Current Open Decisions

### 1. HD Customer to ERPNext Customer mapping

Need to decide whether to add an explicit mapping from Helpdesk `HD Customer` to ERPNext `Customer`.

Possible direction:

```text
HD Customer.custom_erpnext_customer -> Customer
```

### 2. Customer/Campus/Service Area coverage responsibility

Need to define production coverage rows for customer/campus/service-area combinations.

This should drive visibility, team load, routing, and escalation later.

### 3. Default coordinator / preferred owner routing

Need to decide whether certain customers or campuses have a preferred coordinator/default accountable owner.

This should be a responsibility/routing rule, not a fake Service Area.

### 4. Multi-branch proof

Need a future proof case using an Emerald Life-style topology with many branches.

This should validate that the model supports:

```text
one customer organisation
many campuses/branches
different coverage by branch/service area
```

## Current Decisions Preserved

- Customer portal tickets may use native `HD Ticket.customer`.
- `custom_customer` must not be populated unless a valid ERPNext Customer mapping exists.
- Internal display/read helpers should use `custom_customer or customer`.
- Fault Point remains optional for Customer portal intake.
- Point locations populate both `custom_site` and `custom_fault_asset`.
- Links/Areas populate `custom_fault_asset` only and leave `custom_site` blank.
- Service Area must remain a work taxonomy, not a customer ownership shortcut.
- Responsibility and routing should be handled by explicit coverage/routing policy.
