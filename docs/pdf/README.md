# PDF publishing

This directory contains the reproducible Vivliostyle publishing setup for the
Telectro ERPNext / Helpdesk pilot documentation.

## Publications

### Canonical Activity Process Guides

Canonical source:

```text
../user-guides/activity-process-guides.md
```

Generated output:

```text
dist/activity-process-guides.pdf
```

This is the canonical master Activity Process Guide publication.

The current verified master publication contains 23 numbered top-level
activities.

### Customer Activity Process Guide

The Customer Activity Process Guide is a derived publication generated from
canonical Activities 5–9 in:

```text
../user-guides/activity-process-guides.md
```

The Customer edition renumbers those activities from 1–5 for publication.

Generated intermediate Markdown:

```text
dist/customer-activity-process-guide.md
```

Generated PDF:

```text
dist/customer-activity-process-guide.pdf
```

The generated Customer Markdown is not a second canonical process source and
must not be edited directly.

Customer-facing process changes must be made in the canonical Activity Process
Guides first and then regenerated through the Customer extraction process.

### Partner Activity Process Guide

The Partner Activity Process Guide is a derived publication generated from
three Partner-facing activities in:

```text
../user-guides/activity-process-guides.md
```

The Partner publication uses this deliberate operational ordering:

```text
Canonical Activity 21 -> Partner Activity 1
Canonical Activity 10 -> Partner Activity 2
Canonical Activity 11 -> Partner Activity 3
```

This produces:

```text
1. Partner logs a Partner-originated service request
2. Partner responds to an acceptance request
3. Partner submits work done
```

The order is intentional.

It presents the Partner-originated request and Partner Acceptance workflow
before the separate Telectro-assigned Partner Work Completion workflow.

Generated intermediate Markdown:

```text
dist/partner-activity-process-guide.md
```

Generated PDF:

```text
dist/partner-activity-process-guide.pdf
```

The generated Partner Markdown is not a second canonical process source and
must not be edited directly.

Partner-facing process changes must be made in the canonical Activity Process
Guides first and then regenerated through the Partner extraction process.

The Partner extractor permits no publication-only activity-body transforms.
After removal of the canonical H1 and `Related docs` section, each generated
Partner activity body must remain identical to its canonical source body.

### Activity Process Guides Visual Supplement

Canonical visual source:

```text
../user-guides/activity-process-guides-visual-supplement.md
```

Shared controlled screenshot library:

```text
../user-guides/activity-process-guides-visuals/
```

Generated PDF:

```text
dist/activity-process-guides-visual-supplement.pdf
```

The Master Visual Supplement is explanatory rather than canonical process text.

The canonical Activity Process Guides remain the process source of truth. The
Visual Supplement provides selected Production screenshots only where visual
recognition materially improves understanding.

The current verified Master Visual Supplement contains:

```text
29 controlled screenshot assets
28 screenshots used in the Master publication
22 pages
```

`visual-22-partner-work-request-rework-dialog.png` remains in the controlled
asset library but is deliberately not repeated in the Master publication
because the current DOC-05 visual covers the same interaction.

### Customer Activity Process Guides Visual Supplement

The Customer Visual Supplement is derived from selected Customer-safe visuals
in the Master Visual Supplement.

Generated intermediate Markdown:

```text
dist/customer-activity-process-guides-visual-supplement.md
```

Generated PDF:

```text
dist/customer-activity-process-guides-visual-supplement.pdf
```

The generated Customer Markdown is not a second visual source and must not be
edited directly.

The Customer extractor:

* validates the expected Master Customer chapter boundary;
* proves each selected Master image and source caption exists exactly once;
* selects only the two Customer-safe visuals required by the publication;
* excludes internal Telectro ticket and evidence-management controls;
* rewrites image paths only for the generated `dist/` publication context;
* fails rather than guessing if the expected Master structure changes.

The current verified Customer Visual Supplement contains:

```text
2 selected screenshots
2 numbered visual chapters
4 pages
```

### Partner Activity Process Guides Visual Supplement

The Partner Visual Supplement is derived from selected Partner-safe visuals in
Master chapters 3 and 4.

Generated intermediate Markdown:

```text
dist/partner-activity-process-guides-visual-supplement.md
```

Generated PDF:

```text
dist/partner-activity-process-guides-visual-supplement.pdf
```

The generated Partner Markdown is not a second visual source and must not be
edited directly.

The Partner extractor:

* validates the Master Partner Acceptance, Partner Work Completion, and
  maintenance chapter boundaries;
* proves each selected Master image and source caption exists exactly once;
* preserves the separation between Partner Acceptance and Partner Work
  Completion;
* selects six Partner Acceptance visuals and two Partner Work visuals;
* excludes Telectro-only review dialogs, queues, and final-review screens;
* rewrites image paths only for the generated `dist/` publication context;
* fails rather than guessing if the expected Master structure changes.

The current verified Partner Visual Supplement contains:

```text
8 selected screenshots
2 numbered visual chapters
8 pages
```

The generated `dist/` directory is intentionally excluded from Git.

## Requirements

The publishing setup was verified with:

```text
Node.js v22.20.0
npm 11.6.1
Vivliostyle CLI 11.1.0
Vivliostyle Core 2.44.1
```

Install the locked dependencies from this directory:

```bash
npm ci
```

## Canonical master preview

Run the authoritative paginated preview:

```bash
npm run preview
```

This renders all pages and should be used when checking:

* final page count;
* table-of-contents page references;
* chapter page breaks;
* running headers and footers;
* final pagination.

Run the quicker development preview:

```bash
npm run preview:quick
```

Quick preview renders pages progressively. Its page total, toolbar position,
and table-of-contents page references may be incomplete or approximate until
the relevant pages have been rendered.

Do not use quick preview as the final pagination proof.

Stop either preview with:

```text
Ctrl+C
```

## Build the canonical master PDF

Run:

```bash
npm run build
```

The generated PDF is written to:

```text
dist/activity-process-guides.pdf
```

## Customer publication

### Extract the Customer guide

Run:

```bash
npm run customer:extract
```

This:

* reads canonical Activities 5–9 from
  `../user-guides/activity-process-guides.md`;
* validates the expected canonical section structure;
* removes publication-inappropriate `Related docs` sections;
* renumbers the five Customer activities from 1–5;
* applies the controlled publication-only Customer wording transform;
* verifies body parity against the canonical source;
* fails rather than guessing if the expected source structure changes;
* writes the generated Customer Markdown to
  `dist/customer-activity-process-guide.md`.

### Preview the Customer guide

Run:

```bash
npm run customer:preview
```

This regenerates the Customer Markdown before starting the authoritative
Vivliostyle preview.

Use the full preview to verify:

* final Customer page count;
* the five-entry Customer contents page;
* resolved contents page references;
* activity page breaks;
* running headers and footers;
* final pagination;
* absence of clipping or broken layout.

### Build the Customer PDF

Run:

```bash
npm run customer:build
```

This regenerates the Customer Markdown first and then builds:

```text
dist/customer-activity-process-guide.pdf
```

The current verified Customer Activity Process Guide publication contains:

```text
5 numbered activities
45 pages
```

## Partner publication

### Extract the Partner guide

Run:

```bash
npm run partner:extract
```

This:

* reads canonical Activities 21, 10, and 11 from
  `../user-guides/activity-process-guides.md`;
* validates each activity against its exact canonical H1 and closing boundary;
* publishes the activities in the deliberate order 21 -> 10 -> 11;
* renumbers them as Partner Activities 1–3;
* removes publication-inappropriate `Related docs` sections;
* rejects stale numbered `Activity N` references;
* verifies exact body parity against the canonical source;
* permits no Partner publication-only body transforms;
* fails rather than guessing if the expected canonical structure changes;
* writes the generated Partner Markdown to
  `dist/partner-activity-process-guide.md`.

The publication mapping is:

```text
Canonical 21 -> Partner 1
Canonical 10 -> Partner 2
Canonical 11 -> Partner 3
```

### Preview the Partner guide

Run:

```bash
npm run partner:preview
```

This regenerates the Partner Markdown before starting the authoritative
Vivliostyle preview.

Use the full preview to verify:

* final Partner page count;
* the three-entry Partner contents page;
* resolved contents page references;
* activity page breaks;
* running headers and footers;
* final pagination;
* absence of clipping or broken layout;
* clear separation between Partner Acceptance and Partner Work Completion.

### Build the Partner PDF

Run:

```bash
npm run partner:build
```

This regenerates the Partner Markdown first and then builds:

```text
dist/partner-activity-process-guide.pdf
```

The current verified Partner Activity Process Guide publication contains:

```text
3 numbered activities
33 pages
```

## Visual Supplement publications

### Preview and build the Master Visual Supplement

Run the authoritative paginated preview:

```bash
npm run visual:preview
```

Build the Master Visual Supplement PDF:

```bash
npm run visual:build
```

The generated PDF is written to:

```text
dist/activity-process-guides-visual-supplement.pdf
```

The Master Visual Supplement is built directly from the tracked visual source
and shared screenshot library. No generated intermediate Markdown is required.

### Customer Visual Supplement

Extract the Customer-facing visual subset:

```bash
npm run customer-visual:extract
```

This validates the expected Master Customer chapter, selects the approved
Customer-safe visuals, rewrites their image paths for the generated publication
context, and writes:

```text
dist/customer-activity-process-guides-visual-supplement.md
```

Run the authoritative paginated preview:

```bash
npm run customer-visual:preview
```

Build the Customer Visual Supplement PDF:

```bash
npm run customer-visual:build
```

The build command always regenerates the Customer Markdown before building:

```text
dist/customer-activity-process-guides-visual-supplement.pdf
```

### Partner Visual Supplement

Extract the Partner-facing visual subset:

```bash
npm run partner-visual:extract
```

This validates the expected Master Partner workflow boundaries, preserves the
separation between Partner Acceptance and Partner Work Completion, selects only
the approved Partner-safe visuals, rewrites their image paths for the generated
publication context, and writes:

```text
dist/partner-activity-process-guides-visual-supplement.md
```

Run the authoritative paginated preview:

```bash
npm run partner-visual:preview
```

Build the Partner Visual Supplement PDF:

```bash
npm run partner-visual:build
```

The build command always regenerates the Partner Markdown before building:

```text
dist/partner-activity-process-guides-visual-supplement.pdf
```

The generated Customer and Partner Visual Supplement Markdown files are build
artifacts. Do not edit them directly or treat them as independent publication
sources.

## Current publication rules

The publications currently use:

* A4 pages;
* top-level Activity Process Guides starting on new pages;
* generated contents pages;
* clickable contents links;
* PDF bookmarks;
* running document and activity headings;
* numbered page footers;
* controlled heading, paragraph, list, code-block, and table pagination.

The canonical Activity Process Guides publication contains 23 numbered
top-level guides.

The Customer publication contains five numbered Customer activities derived
from canonical Activities 5–9.

The Partner publication contains three numbered Partner activities derived
from canonical Activities 21, 10, and 11.

The Partner publication deliberately presents canonical Activity 21 first so
that Partner request creation appears before the later Partner Acceptance
response process.

Partner Acceptance and Partner Work Completion remain separate workflow trains
throughout the Partner publication.

The canonical source Markdown remains:

```text
../user-guides/activity-process-guides.md
```

Pagination and publication layout belong in:

```text
activity-process-guides.css
```

The canonical master publication structure and output settings belong in:

```text
vivliostyle.config.js
```

The Customer publication structure and output settings belong in:

```text
vivliostyle.customer.config.js
```

The Partner publication structure and output settings belong in:

```text
vivliostyle.partner.config.js
```

The Customer extraction contract belongs in:

```text
extract-customer-activity-guide.mjs
```

The Partner extraction contract belongs in:

```text
extract-partner-activity-guide.mjs
```

The master, Customer, and Partner publications currently share the same proven
stylesheet.

## Final verification

Before distributing a generated PDF, verify:

1. the PDF page count matches the full Vivliostyle preview;
2. all contents entries have resolved page numbers;
3. contents links navigate to the correct guide;
4. the PDF bookmark outline is present;
5. representative early, middle, and late pages have no clipped content;
6. the final printed page number matches the PDF page count;
7. full-text search works;
8. the generated Markdown and PDF do not appear in `git status`.

For the Customer publication, also verify:

1. the contents page contains exactly five numbered Customer activities;
2. Customer Activities 1–5 each begin on their own page;
3. no `Related docs` section appears in the generated Customer guide;
4. no stale numbered reference such as `Activity 6` or `Activity 9` remains;
5. the Customer publication remains derived from canonical Activities 5–9.

For the Partner publication, also verify:

1. the contents page contains exactly three numbered Partner activities;
2. Partner Activities 1–3 each begin on their own page;
3. the publication mapping is exactly
   `21 -> 1`, `10 -> 2`, and `11 -> 3`;
4. no `Related docs` section appears in the generated Partner guide;
5. no stale numbered `Activity N` reference remains;
6. canonical Activity 12 does not leak into the Partner publication;
7. canonical Activity 22 does not leak into the Partner publication;
8. the three Partner activity bodies retain exact canonical body parity;
9. Partner Acceptance and Partner Work Completion remain clearly separate
   workflow trains.

## Verified publication baselines

Current verified canonical master:

```text
23 numbered activities
209 pages
```

Current verified Customer publication:

```text
5 numbered activities
45 pages
```

Current verified Partner publication:

```text
3 numbered activities
33 pages
```

Page counts may change when the canonical source document or shared stylesheet
changes. Any changed publication should be rebuilt and reverified before
distribution.
