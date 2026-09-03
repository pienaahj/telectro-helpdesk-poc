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

## Production Campus and Location Onboarding Procedure

This section records the reusable procedure for introducing a new Customer
campus and its Location hierarchy into production.

The Boschendal production promotion on 2026-09-03 is the first accepted
reference implementation.

### Core principle

Importing Location records and making those Locations available to a Customer
portal user are two separate operations.

```text
Location dataset promotion
        +
Customer → Campus resolution
        =
Customer-visible Fault Point locations
```

A successfully imported Location hierarchy does not automatically become
visible to a Customer portal user.

The portal remains server-scoped to the Campus resolved for that Customer.

### 1. Required Location topology

Customer campuses must be group Locations directly below:

```text
Pilot Sites
```

Example:

```text
Pilot Sites
├─ Existing Customer Campus
└─ New Customer Campus
   ├─ New Customer Campus - Areas
   ├─ New Customer Campus - Buildings
   ├─ New Customer Campus - Links
   ├─ New Customer Campus - Network Nodes
   ├─ New Customer Campus - Other
   └─ New Customer Campus - Residents
```

The top-level Campus and category buckets are group Locations.

Actual Fault Points and assets are leaf Locations beneath the relevant
category.

### 2. Location has no active/enabled switch

Do not look for an `active`, `enabled`, `disabled`, or `status` field on
`Location` when a newly imported campus does not appear in the Customer portal.

The accepted DEV comparison showed:

```text
LOCATION_STATE_FIELDS=[]
```

Visibility is controlled by Customer-to-Campus resolution, not by activating
individual Location rows.

Diagnostic rule:

```text
Locations exist in production
+
portal shows another Campus
=
inspect Customer → Campus mapping
```

Do not modify or re-import Location rows merely because the Customer portal is
still showing another Campus.

### 3. Prepare and validate Location data in DEV

Refine the source Location dataset in DEV before production promotion.

The production release must preserve:

- canonical Location IDs;
- customer-facing Location labels;
- parent hierarchy;
- group/leaf semantics;
- geometry type;
- coordinates where applicable.

The final release should be deterministic and accepted in DEV before production
promotion.

For the Boschendal reference release:

```text
Root rows:       1
Category groups: 6
Leaf locations: 262
Total:           269
```

Production promotion must use the exact accepted staged artifacts rather than
re-exporting or rebuilding the data on the production host.

### 4. Production prerequisite

Before import, confirm that:

```text
Pilot Sites
```

exists in production and is a group Location.

Also inspect the existing `Pilot Sites` subtree so that the pre-import baseline
is known.

For the Boschendal production promotion, the pre-import subtree was:

```text
Pilot Sites
└─ TELECTRO PILOT TEST CAMPUS
   └─ TELECTRO PILOT TEST CAMPUS - Buildings
      └─ Buildings: Pilot Test Point
```

Do not create or alter unrelated existing Customer campuses during the import.

### 5. Production release safety boundary

Before any Location mutation:

1. identify the exact accepted release artifacts;
2. verify their SHA-256 hashes;
3. verify logical CSV row counts using CSV parsing rather than physical line
   counts;
4. place the artifacts inside the backend's controlled read-only import
   boundary;
5. prove the backend can read the exact artifacts and reproduce the accepted
   hashes;
6. parse the release through the repository-controlled importer;
7. execute the importer dry-run;
8. prove the dry-run caused no database mutation;
9. take a fresh production backup with files;
10. verify the exact backup artifacts exist and are non-empty.

Only after all of these gates pass may the committed import run.

The Boschendal reference release used:

```text
stage-00-root.csv
SHA256=6b00263603e2bde0b61f8ce101d5dabb8fcc9346e02c96ac544dad56c65cee70

stage-01-groups.csv
SHA256=de5f727a90c1e1f940db1e168e599e467a0c90e56da023aa5bf9a4d9928f2d7f

stage-02-locations.csv
SHA256=2d18ed5b54a54398dcc2b3d5aa5898f4a26d63617ab4cb32e02c70f0a9892570
```

The logical row contract was:

```text
STAGE_COUNTS=[1, 6, 262]
TOTAL_RELEASE_ROWS=269
```

The production dry-run must prove both acceptance and no mutation.

For Boschendal:

```text
RUN_RESULT={
    'ok': True,
    'dry_run': True,
    'row_count': 269,
    'stage_counts': [1, 6, 262]
}

LOCATION_COUNT_BEFORE=4
LOCATION_COUNT_AFTER=4

BOSCHENDAL_LOCATION_RELEASE_V1_PROD_PREFLIGHT_COMPLETE=YES
```

A fresh backup must be taken after the dry-run and before the committed import.

The Boschendal reference backup was created with:

```text
./bin/prod-bench.sh --site erp.telectro.co.za backup --with-files
```

and produced four independently verified artifacts:

```text
site_config_backup.json
database.sql.gz
files.tar
private-files.tar
```

### 6. Import exactly once

The generic Location release importer owns the production transaction:

```text
telephony.scripts.import_location_release
```

The committed import must follow this ownership boundary:

```text
validate release
→ validate production target
→ apply staged rows
→ run repository postflight
→ commit on success

any failure
→ rollback
```

Do not manually insert release rows around the importer.

Do not blindly retry a committed Location release.

Immediately before calling the committed import, confirm that the production
state still matches the expected pre-import boundary.

If the expected release IDs or final Location count are already present, stop.
Inspect the persisted state before attempting another write.

The Boschendal production promotion demonstrated this safeguard.

The expected count boundary was:

```text
Original production Locations: 4
Boschendal release rows:        269
Expected final total:           273
```

A subsequent guarded invocation encountered:

```text
LOCATION_COUNT_BEFORE_COMMIT=273
```

and stopped before calling the importer again.

This was the correct behaviour.

The presence of `273` Locations did not indicate a failed or partial release.
It indicated that the release had already been committed and therefore must not
be replayed.

Do not use a Location-name prefix such as:

```text
name LIKE 'Boschendal%'
```

to determine whether the full release exists.

Canonical Location IDs may intentionally differ from their customer-facing
Location labels.

For the Boschendal release, only the root and six category group IDs begin with
`Boschendal`; the 262 leaf rows retain canonical IDs.

Exact release-ID comparison is the authoritative test.

### 7. Independent fresh-session acceptance

After the committed import, open a fresh Production Bench Console session.

Do not treat successful output from the transaction-owning session as the final
production acceptance proof.

Using the exact accepted staged artifacts, independently reconstruct the set of
expected release IDs and compare it with the persisted production `Location`
rows.

Verify:

```text
expected release ID count
existing release ID count
missing release ID count
total production Location count
repository postflight result
target Campus root
target Campus parent
target Campus group state
```

For the Boschendal production release, the fresh-session proof returned:

```text
EXPECTED_RELEASE_ID_COUNT=269
TOTAL_LOCATION_COUNT=273
EXISTING_RELEASE_ID_COUNT=269
MISSING_RELEASE_ID_COUNT=0
MISSING_RELEASE_IDS=[]

POSTFLIGHT_RESULT={
    'verified_count': 269,
    'stage_counts': [1, 6, 262]
}

BOSCHENDAL_EXACT_269_RELEASE_IDENTITIES=PASS
BOSCHENDAL_REPOSITORY_POSTFLIGHT=PASS
BOSCHENDAL_COMMITTED_RELEASE_FRESH_SESSION_PERSISTENCE=PASS
```

The persisted Boschendal root was:

```text
name=Boschendal
location_name=Boschendal
parent_location=Pilot Sites
is_group=1
```

The release modification window was after the fresh pre-import backup, providing
an additional temporal boundary between rollback state and imported state.

### 8. Preserve the existing Location baseline

A new Campus import must not replace or semantically damage existing campuses
under `Pilot Sites`.

After the Boschendal import, production contained:

```text
Pilot Sites
├─ TELECTRO PILOT TEST CAMPUS
│  └─ TELECTRO PILOT TEST CAMPUS - Buildings
│     └─ Buildings: Pilot Test Point
└─ Boschendal
   ├─ Boschendal - Areas
   ├─ Boschendal - Buildings
   ├─ Boschendal - Links
   ├─ Boschendal - Network Nodes
   ├─ Boschendal - Other
   └─ Boschendal - Residents
```

The accepted hierarchy proof returned:

```text
EXISTING_PILOT_LOCATION_BASELINE_PRESERVED=YES
BOSCHENDAL_CATEGORY_HIERARCHY=PASS
BOSCHENDAL_LOCATION_RELEASE_V1_SERVER_ACCEPTANCE=PASS
```

Nested-set values such as `lft` and `rgt` will legitimately change when a new
subtree is inserted.

Therefore preservation means retaining the existing semantic hierarchy and
records, not retaining their previous nested-set numbers.

At this point the Location dataset promotion is complete.

Do not continue changing the Location tree merely because a Customer portal user
still resolves to another Campus.

### 9. Customer Campus resolution

Location promotion and Customer Campus resolution are separate acceptance layers.

The Customer portal Fault Point picker first resolves one allowed Campus for the
logged-in Customer Website User.

It then searches only inside:

```text
<Allowed Campus> - <Selected Category>
```

For example:

```text
Boschendal - Buildings
Boschendal - Network Nodes
Boschendal - Links
Boschendal - Areas
Boschendal - Other
Boschendal - Residents
```

Therefore, if a Customer portal user sees the wrong Location hierarchy after a
successful production import, inspect the Customer-to-Campus resolution path
before changing any Location records.

### 10. Native Customer organisation path

The preferred Customer Website User model is:

```text
Named Customer Website User
→ matching Contact
→ Dynamic Link
→ HD Customer
→ allowed Campus
```

A working Boschendal DEV example was:

```text
customer2@boschendal.co.za
→ Contact: Customer 2 Boschendal-Boschendal
→ Dynamic Link: HD Customer = Boschendal
→ RESOLVED_HD_CUSTOMERS=['Boschendal']
→ RESOLVED_ALLOWED_CAMPUS=Boschendal
```

In this working DEV case:

```text
HD Customer Boschendal exists = YES
ERPNext Customer Boschendal exists = NO
```

The Campus still resolves correctly because `Boschendal` is also a group
`Location` directly below:

```text
Pilot Sites
```

This is the normal native Helpdesk Customer-organisation path.

A real Customer Website User does not require a matching ERPNext `Customer`
record merely to resolve its Campus when the linked `HD Customer` itself matches
the top-level Campus Location.

### 11. ERPNext Customer default-campus precedence

There is a second supported resolution path.

If the linked `HD Customer` name also exists as an ERPNext `Customer`, the
ERPNext Customer's:

```text
custom_default_campus
```

takes precedence over the direct HD Customer-name fallback.

The controlled production test Customer demonstrated this path:

```text
Website User:
  pilot.customer@telectro.co.za

Contact:
  Pilot Customer

HD Customer:
  TELECTRO PILOT TEST CUSTOMER

ERPNext Customer:
  TELECTRO PILOT TEST CUSTOMER
```

Its original state was:

```text
custom_default_campus=TELECTRO PILOT TEST CAMPUS
RESOLVED_ALLOWED_CAMPUS=TELECTRO PILOT TEST CAMPUS
```

After the controlled Campus change:

```text
custom_default_campus=Boschendal
RESOLVED_ALLOWED_CAMPUS=Boschendal
```

This changed only the Customer's Campus anchor.

It did not require changes to:

- the Website User identity;
- the email address;
- the Contact;
- the HD Customer relationship;
- roles or permissions;
- the imported Location hierarchy.

### 12. Controlled test-user technique

Before real Customer users and real Customer email addresses exist, use an
existing controlled Customer Website User for production acceptance.

Do not create fake identities that resemble real Customer users solely to prove
Campus or Location behaviour.

The preferred controlled-test pattern is:

```text
existing test Website User
→ existing Contact
→ existing HD Customer
→ existing matching ERPNext Customer
→ set custom_default_campus to target Campus
→ verify resolver
→ perform browser acceptance
```

Before changing the Campus, record:

```text
Customer
Website User
current custom_default_campus
current resolved allowed Campus
target Location
target parent
target is_group state
```

The target Campus must exist as:

```text
parent_location=Pilot Sites
is_group=1
```

After the change, independently verify:

```text
DEFAULT_CAMPUS_AFTER=<Target Campus>
RESOLVED_ALLOWED_CAMPUS_AFTER=<Target Campus>
```

Only then proceed to Customer portal browser testing.

This technique is suitable for reusable acceptance testing across future
Customer campuses because it isolates the variable under test:

```text
Customer Campus assignment
```

while preserving the test user's established authentication, Contact,
organisation relationship, and permissions.

### 13. Do not confuse test configuration with real Customer onboarding

The controlled test-user technique is an acceptance mechanism.

It is not the final production onboarding model for real Customer personnel.

Real Customer onboarding should still use:

```text
Named Customer Website User
→ matching Contact
→ Dynamic Link to the correct HD Customer
→ Customer role only
→ Customer portal access
```

Each real Customer-side person should have an individual Website User so that:

```text
organisation visibility is shared
+
user identity remains individually auditable
```

Do not reuse the controlled test account as a shared operational Customer login.

### 14. Customer Portal browser acceptance

After the Customer resolver returns the intended Campus, perform browser
acceptance through the actual Customer portal.

Open:

```text
/helpdesk/my-tickets/new
```

Use the controlled Customer Website User whose Campus resolution was just
verified.

Acceptance requires:

1. the page loads successfully;
2. Service Area is available;
3. Severity is available;
4. Fault Point remains optional;
5. all supported Location categories are available;
6. selecting a category returns Locations from the allowed Campus;
7. another Customer's Location subtree is not exposed;
8. customer-facing Location labels are readable;
9. raw canonical Location IDs are not exposed as the primary Customer label;
10. selecting a Location displays the correct Campus;
11. point and non-point Location semantics remain correct.

The supported Customer-facing categories are:

```text
Buildings
Network Nodes
Links
Areas
Other
Residents
```

For a Buildings proof, returned rows must belong beneath:

```text
<Target Campus> - Buildings
```

A selected point should display:

```text
Category: Buildings
Campus: <Target Campus>
```

### 15. Boschendal production browser reference proof

On 2026-09-03, the controlled production Customer was configured to resolve:

```text
RESOLVED_ALLOWED_CAMPUS=Boschendal
```

The production Customer portal then returned real imported Boschendal Building
Locations rather than the synthetic Pilot Test Point.

Visible examples included:

```text
Buildings: (Wireless) Cow Shed
Buildings: (Wireless) Mount Vineyard Cottage
Buildings: (Wireless) Vineyard Cottage
Buildings: Accommodation FOH
Buildings: Baker Cottage
Buildings: Baker House
```

These results were scoped beneath:

```text
Boschendal - Buildings
```

This proved the complete read-side chain:

```text
accepted production Location dataset
→ Customer Campus resolution
→ server-scoped Customer lookup
→ Customer-visible Boschendal Locations
```

The production screenshot captured during this proof should be retained with the
Customer onboarding/browser-acceptance evidence.

### 16. Controlled test configuration after acceptance

If `custom_default_campus` was changed only temporarily for a specific acceptance
test, explicitly decide whether to restore it.

Do not leave the decision implicit.

Two valid outcomes are:

```text
A. Restore the controlled test Customer to its original synthetic Campus

or

B. Retain the controlled test Customer on the new Campus for continued
   acceptance testing
```

If restoring, record the original value before mutation and verify after the
restoration that both:

```text
custom_default_campus
RESOLVED_ALLOWED_CAMPUS
```

again equal the intended original Campus.

If retaining the new Campus, record that decision so a future operator does not
mistake the changed test configuration for production Customer master data.

### 17. Reusable new-Customer / new-Campus checklist

For every future Customer Campus and Location onboarding:

```text
[ ] Refine Location data in DEV
[ ] Confirm Customer-facing labels and canonical IDs
[ ] Accept deterministic staged release artifacts
[ ] Record accepted artifact SHA-256 hashes
[ ] Confirm logical staged row counts
[ ] Confirm target Campus root and category groups
[ ] Verify production Pilot Sites prerequisite
[ ] Inspect existing Pilot Sites baseline
[ ] Stage exact artifacts through the controlled import boundary
[ ] Verify backend-visible artifact hashes
[ ] Parse release with repository-controlled importer
[ ] Run production dry-run
[ ] Prove dry-run caused no mutation
[ ] Take fresh pre-import backup with files
[ ] Verify exact backup artifacts
[ ] Reconfirm production pre-import boundary
[ ] Execute committed import exactly once
[ ] Never blindly retry after uncertain commit state
[ ] Perform fresh-session exact release-ID proof
[ ] Run repository postflight independently
[ ] Confirm existing Location hierarchy remains semantically intact
[ ] Confirm new Campus is a group directly under Pilot Sites
[ ] Create/configure the correct HD Customer organisation
[ ] Link named Customer Website Users through Contacts
[ ] Verify Customer roles and containment
[ ] Resolve Customer user to intended Campus
[ ] Prove another Customer's Campus is not exposed
[ ] Browser-test each required Location category
[ ] Verify point Location selection
[ ] Verify Links/Areas non-point behaviour where required
[ ] Capture Customer-facing acceptance screenshots
[ ] Record controlled-test Campus restoration/retention decision
[ ] Only then mark Customer Location onboarding production-ready
```

### 18. Operational troubleshooting boundary

Always keep these three questions separate:

```text
1. Did the Location dataset reach production correctly?

2. Does the Customer resolve to the correct Campus?

3. Does the Customer portal expose only the correct Campus subtree?
```

Use the failure boundary to decide where to investigate.

```text
Question 1 fails
→ investigate release artifacts/import/postflight

Question 1 passes
Question 2 fails
→ investigate User/Contact/HD Customer/default-Campus resolution

Questions 1 and 2 pass
Question 3 fails
→ investigate Customer portal lookup/containment logic
```

A failure in one layer must not automatically trigger mutations in another
layer.

In particular:

```text
correct Location import
+
wrong Customer Campus
```

must not trigger a Location re-import.

Likewise:

```text
correct Customer Campus
+
incorrect browser results
```

must not trigger Customer master-data changes until the server-scoped lookup
path has been inspected.

This separation is the reusable operational contract for future Customer Campus
and Location onboarding.

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
