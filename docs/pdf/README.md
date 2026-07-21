# PDF publishing

This directory contains the reproducible Vivliostyle publishing setup for the
Telectro ERPNext / Helpdesk pilot documentation.

## Current publication

Source:

```text
../user-guides/activity-process-guides.md
```

Generated output:

```text
dist/activity-process-guides.pdf
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

## Preview

Run the authoritative paginated preview:

```bash
npm run preview
```

This renders all pages and should be used when checking:

- final page count;
- table-of-contents page references;
- chapter page breaks;
- running headers and footers;
- final pagination.

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

## Build the PDF

Run:

```bash
npm run build
```

The generated PDF is written to:

```text
dist/activity-process-guides.pdf
```

## Current publication rules

The publication currently uses:

- A4 pages;
- top-level Activity Process Guides starting on new pages;
- a generated contents page containing the 22 numbered top-level guides;
- clickable contents links;
- PDF bookmarks;
- running document and activity headings;
- numbered page footers;
- controlled heading, paragraph, list, code-block, and table pagination.

The source Markdown remains the canonical document. Pagination and publication
layout belong in:

```text
activity-process-guides.css
```

Publication structure and output settings belong in:

```text
vivliostyle.config.js
```

## Final verification

Before distributing a generated PDF, verify:

1. the PDF page count matches the full Vivliostyle preview;
2. all contents entries have resolved page numbers;
3. contents links navigate to the correct guide;
4. the PDF bookmark outline is present;
5. representative early, middle, and late pages have no clipped content;
6. the final printed page number matches the PDF page count;
7. full-text search works;
8. the generated PDF does not appear in `git status`.

The initial verified Activity Process Guides publication contained 203 pages.
The page count may change when the source document or stylesheet changes.