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

The Customer extraction contract belongs in:

```text
extract-customer-activity-guide.mjs
```

The master and Customer publications currently share the same proven
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

Page counts may change when the canonical source document or shared stylesheet
changes. Any changed publication should be rebuilt and reverified before
distribution.
