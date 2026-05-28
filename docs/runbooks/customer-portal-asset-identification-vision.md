# Customer Portal Asset Identification Vision

## Purpose

The Customer portal should primarily help Customer-side ticket reporters identify the affected location, asset, or equipment as accurately as possible.

The portal is not just a simplified ticket form. Its main value is to help the Customer communicate useful operational context to Telectro technicians before work starts.

The intended outcome is:

```text
Customer reports a fault or request
↓
Customer identifies the affected place / asset / equipment as closely as possible
↓
Telectro receives a ticket with structured operational context
↓
Technicians spend less time clarifying where or what the issue relates to
↓
Ticket history becomes useful by Customer, Campus, Fault Point, Asset, and Equipment reference
```

## Primary design principle

The Customer portal should be treated as an asset-identification product first, and a ticket-status product second.

The portal should help answer:

```text
Where is the issue?
What is affected?
Which equipment, circuit, SIM, tag, or asset reference may be involved?
What evidence can the Customer provide?
What does Telectro need to act without unnecessary back-and-forth?
```

Ticket status, outstanding tickets, and Customer-visible updates are still important, but they should support the main purpose of accurate fault/request identification.

## Current V1 foundation

The current Customer Intake V1 foundation already supports the first version of this model.

Relevant ticket fields include:

```text
HD Ticket.customer
HD Ticket.custom_site_group
HD Ticket.custom_fault_category
HD Ticket.custom_site
HD Ticket.custom_fault_asset
HD Ticket.custom_service_area
HD Ticket.custom_equipment_ref
HD Ticket.via_customer_portal
```

Current proven behaviour:

- Customer Website Users are contained to their linked Customer organisation.
- Customer-created tickets flow through the native Helpdesk Customer portal.
- Customer portal tickets are server-side anchored to the Customer Campus where possible.
- Customer users can select a Customer-scoped Fault Point through a controlled picker.
- The picker does not expose an unrestricted raw Frappe Link field.
- Selected Fault Point values are saved into `custom_site`, `custom_fault_asset`, and `custom_fault_category`.
- Customer evidence/attachments can be stored as private files attached to the HD Ticket.
- Customer-visible updates can be sent through deliberate Telectro-side actions.

## Current implemented Customer location context

As of the 2026-05-29 Customer portal asset-identification train, the Customer portal now supports a stronger end-to-end location/context flow.

### Customer new-ticket flow

The Customer new-ticket page now supports:

```text
Service Area selection
Equipment / Circuit / SIM / Tag reference capture
Customer-scoped Fault Point search
Selected Fault Point summary card
Coordinate availability indicator
External "View on map" link for the selected point
Improved no-results recovery guidance
```

The Fault Point picker remains Customer-scoped and server-controlled. It does not expose an unrestricted raw Frappe Link field to Customer users.

The selected Fault Point summary card confirms the Customer's selected operational context before submission:

```text
Selected Fault Point
Fault Point
Category
Campus
Map availability / View on map
```

When a selected Fault Point has coordinates, the Customer can open the selected point externally in OpenStreetMap. This is deliberately implemented as an external map link for V1 rather than an embedded Customer map.

### Customer ticket detail flow

After submission, the Customer ticket detail view now shows the submitted location context on both desktop and mobile.

The Customer-visible location context includes:

```text
Fault Point
Category
Equipment Ref
View on map
```

The detail view resolves the saved `custom_site` Location ID into the friendly `Location.location_name` through a Customer-safe backend endpoint.

This avoids showing raw internal Location IDs such as:

```text
kmz8ddf58f32e1ddb2988ba7b71
```

and instead shows Customer-meaningful labels such as:

```text
Buildings: Bakery
```

The generic Customer detail field lists now suppress duplicate location-context fields once those values are represented in the dedicated Location details panel.

### Current guardrails

The implemented model preserves the following guardrails:

```text
Customer lookup remains backend-scoped.
Raw Location Link fields are not exposed to Customer users.
Fault-like non-email tickets still require a structured Fault Point.
The map feature uses only the selected point coordinates.
No embedded map dependency has been added.
No unrestricted Customer browsing of Location data has been introduced.
```

### Proven example

Proof ticket `817` demonstrated the current flow:

```text
Customer: Boschendal
Customer user: customer2@boschendal.co.za
Fault Category: Buildings
Fault Point: Buildings: Bakery
Equipment Ref: COORDINATE-PROOF-20260529
Location: kmz8ddf58f32e1ddb2988ba7b71
Latitude: -33.885257694
Longitude: 18.96524681
```

The Customer new-ticket page, desktop ticket detail sidebar, and mobile ticket detail view all display the Customer-safe location context.

## Asset identification model

The portal should make a clear distinction between the following concepts.

### Customer

The organisation raising the ticket.

Example:

```text
Boschendal
```

### Campus / Site Group

The Customer-side campus or broad operating area.

In V1 this is represented by:

```text
HD Ticket.custom_site_group
```

Example:

```text
Boschendal
```

### Fault Category

The type of Customer-visible point being selected.

Examples:

```text
Buildings
Network Nodes
Residents
Other
```

In V1 this is represented by:

```text
HD Ticket.custom_fault_category
```

### Fault Point

The Customer-friendly point where the issue is observed.

Examples:

```text
Buildings: Bakery
Network Nodes: Cabinet 3
Residents: Unit 14
Other: Gate entrance
```

In V1 this is represented by:

```text
HD Ticket.custom_site
```

### Fault Asset

The operational asset Telectro should treat as impacted.

In V1 this may be the same selected Location as the Fault Point.

In future this may diverge.

Example future model:

```text
Fault Point: Buildings: Bakery
Fault Asset: Router / ONT / Switch / Access Point serving Bakery
```

In V1 this is represented by:

```text
HD Ticket.custom_fault_asset
```

### Equipment Ref

A free-text reference supplied by the Customer when they know a concrete equipment, circuit, SIM, serial, tag, or asset identifier.

Examples:

```text
Serial number
Circuit number
SIM ICCID
Asset tag
Router label
Equipment sticker
```

In V1 this is represented by:

```text
HD Ticket.custom_equipment_ref
```

This should be exposed to the Customer portal as an optional field because it provides high operational value without requiring a complete equipment master-data model.

Recommended Customer-facing label:

```text
Equipment / Circuit / SIM / Tag reference
```

Recommended helper text:

```text
Enter any serial number, circuit number, SIM ICCID, asset tag, or equipment label visible on the affected equipment.
```

## Long-range vision

The long-range Customer portal should guide reporters through identifying the affected operational object as accurately as possible.

Target direction:

```text
Customer selects or is scoped to Customer / Campus
↓
Portal shows Customer-scoped places, assets, or equipment
↓
Customer identifies the affected point through search and/or spatial view
↓
Portal optionally links known equipment behind that point
↓
Customer adds Equipment Ref and evidence if available
↓
Ticket stores structured operational references
↓
Technician sees location, asset, equipment reference, evidence, and ticket history
```

The ideal future state is that a ticket can be linked to as much relevant operational context as possible:

```text
Customer
Campus
Fault Category
Fault Point
Fault Asset
Equipment
Equipment Ref
Evidence
Previous ticket history
Resolution history
```

## Spatial direction

A spatial or map-assisted view is a desirable long-term enhancement because it can make the Customer portal feel practical and intuitive.

This should be approached incrementally.

Recommended progression:

```text
Search picker
↓
Selected Fault Point summary card
↓
Selected point map preview
↓
Internal map proof of Customer-scoped Location data
↓
Customer-facing map-assisted picker
↓
Asset/equipment overlays
```

The first Customer-facing spatial improvement does not need to be a full map picker.

A small selected-point preview may already add value:

```text
Selected Fault Point

Buildings: Bakery
Category: Buildings
Campus: Boschendal

Coordinates available
```

Later, the portal can support:

```text
Category filtering
Nearby points
Click-to-select map points
Equipment overlays
Ticket history by point
```

## Near-term implementation slices

The slices below started as the near-term plan. Several have now been completed or partially completed during the 2026-05-29 Customer portal asset-identification train. Future edits should either mark these as completed or move the remaining work into a backlog section.

### Slice 1: Re-prove current Fault Point picker

Purpose:

```text
Confirm the Customer Fault Point picker still works correctly after KMZ Location cleanup.
```

Proof target:

```text
Customer user: customer2@boschendal.co.za
Search term: Bakery
Expected label: Buildings: Bakery
Expected Location: coordinate-backed KMZ Location row
```

Success condition:

```text
Customer portal creates a ticket with correct custom_site and custom_fault_asset values.
```

### Slice 2: Dry-run remaining KMZ cleanup buckets

Purpose:

```text
Check whether Network Nodes, Other, and Residents have the same duplicate-style Location pattern as Buildings.
```

Guardrail:

```text
Dry-run first.
Do not commit cleanup unless the same safe pattern is confirmed.
```

### Slice 3: Expose Equipment Ref to Customer portal

Purpose:

```text
Allow Customer reporters to provide serial, circuit, tag, ICCID, or other visible equipment references.
```

Behaviour:

```text
Optional field
Free text
Saved into HD Ticket.custom_equipment_ref
Visible to internal Telectro users
Visible on Customer ticket detail where appropriate
```

Non-goal:

```text
Do not build unrestricted equipment lookup yet.
Do not require complete equipment master data.
Do not make Equipment Ref mandatory.
```

### Slice 4: Add selected Fault Point summary card

Purpose:

```text
Show the Customer a clear confirmation of the selected affected point before ticket submission.
```

Example:

```text
Selected Fault Point
Buildings: Bakery
Category: Buildings
Campus: Boschendal
```

### Slice 5: Add fallback when the Customer cannot find the point

Purpose:

```text
Prevent Customers from selecting an incorrect point only because the correct one is missing or hard to find.
```

Possible behaviour:

```text
Customer selects "I cannot find the affected point"
Customer provides free-text location/equipment details
Customer uploads evidence
Ticket is still created with safe structured data where available
```

### Slice 6: Prove coordinate/map viability internally

Purpose:

```text
Validate whether the current Location coordinate data can support a map preview or map-assisted picker.
```

Start internal-only.

Check:

```text
Coordinate availability
Category coverage
Customer scoping
Data quality
Map rendering approach
```

### Slice 7: Add selected point map preview

Purpose:

```text
Show a small Customer-safe map preview after a Fault Point is selected.
```

Guardrail:

```text
Only show the selected Customer-scoped point initially.
Do not expose unrestricted Location browsing.
```

### Slice 8: Improve Customer ticket list and detail context

Purpose:

```text
Help Customers track outstanding tickets and understand progress.
```

Useful fields:

```text
Ticket ID
Subject
Status
Fault Point
Equipment Ref
Last Customer-visible update
Created date
Resolution summary
```

## V1 non-goals

The following are deliberately out of scope for the first Customer portal asset-identification pass:

```text
Full custom Customer portal replacement
Unrestricted Location Link fields
Unrestricted equipment lookup
Customer-visible internal Location tree
Customer-visible internal comments
Customer access to unrelated Customer data
Full GIS/map picker before data proof
Complete equipment master-data model
Mandatory Equipment Ref
Links / Areas category exposure without safety proof
```

## Design guardrails

- Use the native Helpdesk Customer portal foundation unless a hard blocker appears.
- Keep Customer users scoped to their linked Customer organisation.
- Use controlled endpoints for Customer-scoped lookup.
- Avoid exposing raw Desk/Frappe Link behaviour to Customer users.
- Prefer incremental UI improvements over a large rewrite.
- Verify existing code and data before augmenting behaviour.
- Keep asset/location/equipment identification central to portal decisions.
- Treat evidence, updates, and status as supporting context around the affected asset.

## Success definition

The Customer portal is successful when a Customer reporter can create a ticket that tells Telectro:

```text
Who reported it
Which Customer and Campus it belongs to
What kind of fault/request it is
Where the issue is observed
What asset or point is likely affected
Which equipment/circuit/SIM/tag may be involved
What evidence supports the report
What the Customer has already communicated
```

The better this context is at ticket creation time, the less operational clarification Telectro technicians need before acting.
