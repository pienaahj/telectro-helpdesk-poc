# Ticket Evidence V1

## Purpose

Ticket Evidence is the pilot model for attaching field photos, supporting documents, quotes, notes, and related proof to an HD Ticket.

The goal is not full document management. The goal is ticket-level operational evidence that can be safely uploaded, viewed, and downloaded from the relevant workflow surfaces.

## Current V1 model

Evidence files are stored as private Frappe `File` records attached to the related `HD Ticket`.

Files are not exposed through raw `/private/files/...` links in the Partner-safe or internal Ticket Evidence flows. Instead, users interact through controlled upload, list, and download endpoints.

## Supported V1 upload formats

The current V1 allow-list is intentionally conservative:

- JPG / JPEG
- PNG
- PDF
- DOC / DOCX
- XLS / XLSX
- TXT

Maximum size:

- 10 MB per file

Unsupported mobile-native formats are intentionally not promised in V1:

- WEBP
- HEIC / HEIF
- DNG / Apple ProRAW

Reason:

- native Frappe/File validation currently rejects real WEBP uploads
- mobile-native photo formats vary by device and browser
- upload acceptance should stay aligned with what Frappe can safely store

## Photo capture path

For field photos, the preferred V1 path is **Take Photo** from the Ticket Evidence UI.

The browser camera capture flow normalises captured photos to PNG before upload.

This avoids the common problem where existing device photos may be stored as unsupported mobile-native formats.

Current capture surfaces:

- Internal HD Ticket Ticket Evidence dialog
- Partner-safe ticket evidence upload dialog

Captured photos are uploaded as private PNG files attached to the HD Ticket.

Example filename patterns:

- `ticket-evidence-photo-YYYYMMDDHHMMSS.png`
- `partner-ticket-evidence-photo-YYYYMMDDHHMMSS.png`

## Internal evidence flow

Internal users with the correct ticket access can use the internal Ticket Evidence dialog on HD Ticket.

Current internal capabilities:

- list evidence attached to the ticket
- download evidence through controlled internal endpoint
- upload selected supported files
- take photo and upload captured PNG evidence

Internal uploads add timeline comments using this pattern:

```text
Telectro uploaded evidence: <filename>
```

## Partner evidence flow

Partner users use the Partner-safe ticket page.

Current Partner capabilities:

- list evidence attached to accessible Partner tickets
- download evidence through controlled Partner endpoint
- upload selected supported files
- take photo and upload captured PNG evidence

Partner uploads add timeline comments using this pattern:

```text
Partner uploaded evidence: <filename>
```

Partner access remains constrained by Partner-safe ticket access rules.

## Partner Request creation-time evidence

Partner Request supports attaching evidence during request creation.

The request is created first. Evidence files are then uploaded to the created HD Ticket through the Partner-safe evidence upload endpoint.

If evidence upload fails after ticket creation, the user is directed to open the Partner Ticket and add the evidence there.

## Access and security principles

Evidence V1 follows these principles:

- files are private
- files are attached to the HD Ticket
- user must have access to the ticket
- download endpoints verify the file is attached to the requested ticket
- Partner users cannot use internal upload endpoints
- Partner users interact through Partner-safe pages and endpoints
- raw private file URLs are not the workflow surface

## Proven pilot ticket

HD Ticket `783` is the current strongest evidence proof ticket.

Known proven behaviours on ticket `783`:

- internal selected-file upload created private evidence
- internal Take Photo created private PNG evidence
- Partner selected-file upload created private evidence
- Partner Take Photo created private PNG evidence
- Partner and Telectro/internal evidence views stayed in sync
- timeline comments were added for evidence uploads
- Partner user was blocked from internal upload endpoint

Example proven captured files:

- `ticket-evidence-photo-20260513101149.png`
- `ticket-evidence-photo-20260513101137.png`
- `ticket-evidence-photo-20260513102341.png`
- `partner-ticket-evidence-photo-20260513110738.png`

## Known limitations

Current V1 does not include:

- evidence deletion/removal
- download audit logging
- evidence categories
- evidence context metadata
- customer-safe upload model
- email/WhatsApp intake automation
- preview support for all file types
- direct support for WEBP / HEIC / HEIF / DNG / ProRAW

## Future direction

Likely next improvements:

- Customer Site evidence upload model
- evidence metadata such as category/context/source
- download/open audit trail
- optional preview rules for browser-safe formats
- controlled email/WhatsApp evidence intake
- revisit mobile-native formats only if Frappe/File validation and storage policy can support them safely

