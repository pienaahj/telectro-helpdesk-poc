# ERPNext / Helpdesk Pilot Activity Process Guides

## Purpose

These Activity Process Guides document the real day-to-day workflows that are too detailed for the role-based Welcome Guides.

The Welcome Guides explain the basic orientation:

- where each role starts;
- which workspace or portal they use;
- what each role is responsible for;
- what each role should and should not do.

The Activity Process Guides explain the actual operational steps for common activities.

They are intended to prevent users from having to discover non-obvious workflows by trial and error.

## How this guide fits with the other pilot docs

This guide is the user-facing process layer.

Related documents:

- `docs/user-guides/pilot-welcome-guides.md`
  - role-based orientation for Telectro, Partner, and Customer users.
- `docs/runbooks/ticket-evidence-v1.md`
  - canonical technical/operational model for private ticket evidence.
- `docs/runbooks/customer-ticket-lifecycle-v1.md`
  - canonical customer ticket lifecycle and Customer portal visibility model.
- `docs/runbooks/ticket-assignment-contract.md`
  - canonical assignment, claim, release, and handoff model.

Avoid duplicating those documents here.

This guide should describe what the user must do in the UI and what they must verify afterwards.

## Process guide format

Each activity should use this structure:

1. Purpose
2. Audience
3. When to use it
4. Before you start
5. Step-by-step process
6. Verification
7. Common mistakes
8. Screenshot checklist
9. Related docs

---

# 1. Add a Customer-visible update with photo/document evidence

## Purpose

Use this process when Telectro needs to send a Customer-visible ticket update and include supporting evidence such as a photo, PDF, quote, worksheet, or other document.

This is a deliberately controlled two-step process:

1. attach the evidence to the HD Ticket first;
2. then select that already-attached evidence inside the Customer-visible update dialog.

This is important because attaching a file to the ticket and sending a Customer-visible update are not the same action.

## Audience

Primary users:

- Telectro Technician
- Telectro Coordinator
- Telectro Ops / Supervisor

Secondary users:

- any internal Telectro user who is allowed to update Customer tickets.

This process is not for Partner users or Customer users.

## When to use this process

Use this process when:

- the Customer must receive an update;
- the update needs to include evidence;
- the evidence should be visible/downloadable from the Customer-facing ticket view;
- the evidence supports work progress, clarification, or completion.

Typical examples:

- site photo after inspection;
- photo of completed work;
- signed job card;
- quote or supporting PDF;
- screenshot or diagnostic result that is safe for the Customer;
- completion evidence for a resolved Customer ticket.

## Before you start

Confirm the following before sending anything Customer-visible:

- You are on the correct HD Ticket.
- The ticket is a Customer-related ticket.
- The update is safe for the Customer to read.
- The selected file is safe for the Customer to see.
- The file does not contain internal-only comments, private notes, unrelated Customer information, passwords, supplier-only information, or Telectro-only operational discussion.
- You know which file should be sent with the update.

Important:

- Do not assume that every file attached to the ticket is Customer-visible.
- Do not assume that attaching a file to the ticket automatically sends it to the Customer.
- The Customer-visible update must deliberately select the correct already-attached file.

## Step-by-step process

### Step 1 — Open the correct ticket

Open the relevant HD Ticket from the correct Telectro workspace or report.

Useful starting points may include:

- Technician workspace current work list;
- Coordinator current work or review queue;
- Ops / Supervisor oversight reports;
- direct HD Ticket link.

Before continuing, confirm that the ticket number, subject, Customer/account, and location context are the expected ones.

### Step 2 — Attach the evidence to the ticket first

Use the ticket evidence / attachment area to add the file to the HD Ticket.

Depending on the available UI surface, this may be done by:

- uploading a supported file;
- taking a photo through the ticket evidence dialog;
- attaching an existing document to the ticket.

After upload, confirm that the file appears as ticket evidence or as an attached file on the ticket.

This step only attaches the evidence to the ticket.

It does not, by itself, send the evidence to the Customer.

### Step 3 — Confirm the uploaded evidence is the correct file

Before opening the Customer-visible update dialog, check:

- the filename;
- the file type;
- whether the file opens/downloads correctly;
- whether the content is safe for Customer visibility;
- whether it is attached to the correct ticket.

This is the best point to catch mistakes.

### Step 4 — Open the Customer-visible update action

Open the Telectro-side Customer-visible update action/dialog.

The exact label may depend on the current UI wording, but this is the action used to send an update that appears to the Customer.

Do not use an internal note if the Customer is meant to see the message.

Do not use a Customer-visible update if the information is internal-only.

### Step 5 — Write the Customer-visible message

Write the update in plain, Customer-safe language.

A good Customer-visible update should:

- explain what was done or found;
- avoid internal shorthand where possible;
- avoid blame or speculation;
- be short enough to read quickly;
- mention the evidence only if it helps the Customer understand the update.

Example wording style:

- “We inspected the PABX cabinet and found the loose patch lead shown in the attached photo. The connection has been reseated and we are monitoring the line.”
- “The attached photo shows the completed installation at the reception desk. Please let us know if anything further is required.”
- “We have attached the supporting document for the quoted replacement part.”

### Step 6 — Select the already-attached evidence file

Inside the Customer-visible update dialog, select the evidence file that was attached to the ticket in Step 2.

This is the non-obvious part of the workflow:

- first attach the file to the ticket;
- then select that attached file inside the Customer-visible update dialog.

The dialog should not be treated as the original upload point.

It is the point where Telectro deliberately chooses which ticket evidence is included with this Customer-visible communication.

### Step 7 — Submit the update

Submit/send the Customer-visible update.

Wait for the dialog to close or for the ticket to refresh.

Do not immediately assume the process succeeded until the timeline and/or Customer-facing result has been checked.

### Step 8 — Verify the internal ticket timeline

After submitting, verify the HD Ticket timeline.

Confirm that:

- the Customer-visible communication appears in the timeline;
- the message text is correct;
- the selected evidence file is linked or attached as expected;
- no wrong file was selected;
- no internal-only information was accidentally sent.

If something is wrong, escalate immediately before the Customer relies on the information.

### Step 9 — Verify the Customer-facing result when required

When the update is important, sensitive, or part of a training/proof flow, also verify the Customer portal result.

Confirm that the Customer can see the expected update and attachment.

Check:

- the latest update area, if applicable;
- the activity/timeline area;
- the attachment link/download behaviour;
- whether the Customer-facing wording is clear.

This is especially important for completion evidence or resolution communication.

## Verification checklist

The process is complete only when all relevant checks pass:

- The evidence was attached to the correct HD Ticket.
- The correct evidence file was selected in the Customer-visible update dialog.
- The Customer-visible message was submitted successfully.
- The ticket timeline shows the expected Customer-visible communication.
- The selected evidence appears with the communication as expected.
- The Customer portal shows the update/evidence when Customer-facing verification is required.
- No private/internal-only information was exposed to the Customer.

## Common mistakes

### Mistake: Opening the Customer-visible update dialog before attaching the file

Problem:

- The evidence may not be available to select.

Correct approach:

- Close the dialog.
- Attach the evidence to the ticket first.
- Reopen the Customer-visible update dialog.
- Select the already-attached file.

### Mistake: Assuming all ticket attachments are automatically sent to the Customer

Problem:

- Ticket evidence and Customer-visible communication are separate concepts.

Correct approach:

- Treat Customer-visible evidence selection as a deliberate action.
- Select only the file that should accompany the Customer-visible update.

### Mistake: Selecting the wrong attached file

Problem:

- The Customer may receive the wrong evidence or private information.

Correct approach:

- Check the filename and content before submitting.
- If filenames are unclear, open/download the file first and confirm the content.

### Mistake: Putting internal notes into a Customer-visible update

Problem:

- Internal operational detail may become visible to the Customer.

Correct approach:

- Use internal notes for Telectro-only information.
- Use Customer-visible updates only for information that is safe and useful for the Customer.

### Mistake: Skipping verification

Problem:

- The user may believe the Customer received the correct update when the timeline or Customer portal does not show the expected result.

Correct approach:

- Always check the ticket timeline.
- Check the Customer portal when the update is important or when proving the workflow.

## Do

- Attach evidence to the ticket first.
- Confirm the evidence is attached to the correct ticket.
- Confirm the evidence is Customer-safe.
- Write Customer-visible updates in clear plain language.
- Select the intended already-attached evidence file inside the update dialog.
- Verify the timeline after submitting.
- Verify the Customer portal result when needed.

## Do not

- Do not assume the update dialog is the original file upload step.
- Do not assume ticket evidence is automatically sent to the Customer.
- Do not attach internal-only evidence to a Customer-visible update.
- Do not include passwords, private notes, unrelated Customer information, or internal Telectro discussion.
- Do not skip timeline verification.
- Do not use Customer-visible updates for Telectro-only coordination.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. HD Ticket opened with ticket number and context visible.
2. Ticket evidence / attachment area before upload.
3. Evidence upload or Take Photo action.
4. Uploaded evidence visible on the ticket.
5. Customer-visible update dialog opened.
6. Evidence selector inside the Customer-visible update dialog.
7. Correct evidence selected.
8. Ticket timeline after submission.
9. Customer portal view showing the update/evidence, when applicable.

Avoid duplicating these screenshots in every Welcome Guide.

The Welcome Guides should link to this process instead of carrying all these steps.

## Related docs

- `docs/runbooks/ticket-evidence-v1.md`
- `docs/runbooks/customer-ticket-lifecycle-v1.md`
- `docs/user-guides/pilot-welcome-guides.md`

---

# 2. Activity Process Guide backlog

The following process guides are candidates for this document as the pilot training pack matures.

## Internal Telectro ticket execution

Planned guides:

- Claim a ticket
- Release a ticket
- Handoff / share ticket context
- Add an internal note
- Add a Customer-visible update without evidence
- Extend Customer-visible evidence update guide after production screenshots are captured
- Resolve a Customer ticket
- Attach Customer-facing completion evidence

## Coordinator and Supervisor control

Planned guides:

- Check unclaimed tickets
- Check aging and at-risk tickets
- Check first-response risk
- Review current work
- Review Partner acceptance queue
- Review Partner work completion queue
- Intervene on a stale or blocked ticket

## Partner collaboration

Planned guides:

- Request Partner acceptance
- Review Partner acceptance
- Partner submits work done
- Review Partner completed work
- Send rework back to Partner
- Archive or close Partner-side work after Telectro review

## Customer portal

Planned guides:

- Customer logs a support request
- Customer adds follow-up information
- Customer views latest update
- Customer downloads Customer-visible evidence
- Customer checks resolved ticket outcome

---

# 3. Maintenance rule

Keep Activity Process Guides practical.

When updating this document:

- describe what the user does;
- include what the user must verify;
- link back to canonical runbooks for implementation detail;
- avoid duplicating technical contracts from runbooks;
- avoid turning Welcome Guides into long process manuals;
- keep screenshots in Obsidian unless they are deliberately added to the repo.
