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

# 2. Claim, release, and handoff ticket ownership

## Purpose

Use this process when Telectro needs to keep ticket ownership clear and auditable.

In the pilot, assignment means accountable ownership.

It does not mean general collaboration, casual visibility, or “everyone who might help”.

The normal pilot ownership actions are:

- **Claim** — take ownership from the true pool;
- **Release** — return your own ticket to the true pool with a reason;
- **Controlled Handoff** — supervisor/coordinator transfer of accountability to one new owner.

Do not use generic direct Assign/Unassign as the normal reassignment path.

The controlled actions exist to prevent duplicate ownership, stale assignments, and unclear responsibility.

## Audience

Primary users:

- Telectro Technician
- Telectro Coordinator
- Telectro Ops / Supervisor

Typical responsibility split:

- technicians normally claim or release work that is theirs to act on;
- coordinators and supervisors use Controlled Handoff when accountability must move deliberately;
- ops/supervisors monitor whether work has a clear owner and next action.

## When to use these processes

Use controlled ownership actions when:

- a ticket is unclaimed and someone must take responsibility;
- a ticket was incorrectly assigned to you;
- you cannot continue and the ticket must return to the pool;
- a coordinator or supervisor needs to transfer accountability to a specific person;
- a stale or blocked ticket needs a clear next owner;
- the current owner is no longer the right person to drive the ticket.

Do not use these actions to hide work, avoid responsibility, or create informal multi-owner states.

## Important ownership concepts

### Assigned to me

A ticket assigned to you is your accountable work.

You are expected to either:

- work it;
- update it;
- resolve it when appropriate;
- release it with a reason if it should not sit with you;
- ask a coordinator/supervisor to hand it off if accountability must move to a specific person.

### Shared with me

A ticket shared with you gives you visibility or involvement.

It does not necessarily make you the accountable owner.

Shared tickets are useful when:

- you are helping another technician;
- you are being consulted;
- you are preparing to take over work;
- a coordinator/supervisor wants you to see the ticket context.

If you must become the accountable owner, use the correct controlled ownership action rather than treating visibility as ownership.

### True pool / unclaimed work

A true pool ticket has no accountable individual owner.

This is operationally useful only when the ticket is genuinely waiting to be claimed or routed.

Unclaimed work should not be ignored.

Coordinators and supervisors should monitor unclaimed work because it can become operational risk.

### Controlled Handoff

Controlled Handoff is the approved way for a coordinator or supervisor to move accountability to a specific new owner.

Controlled Handoff should:

- move the ticket to one accountable owner;
- avoid adding a second assignee;
- require a reason;
- leave an audit trail;
- make the next owner/action clear.

## Process A — Claim a ticket

### Purpose

Claim a ticket when it is unclaimed or in the true pool and you are the correct person to take accountability for it.

Claiming a ticket means:

- you become the accountable owner;
- it should appear in your assigned/current work;
- you are responsible for the next action.

### Before you claim

Confirm:

- the ticket is actually unclaimed or available to claim;
- the ticket belongs to a service area or work type you can handle;
- you understand the customer request;
- you have checked the fault location or relevant ticket context;
- you are prepared to take the next action.

Do not claim a ticket simply to remove it from a queue if you cannot act on it.

### Step-by-step process

1. Open the relevant workspace or report.
2. Find the unclaimed ticket or ticket available to claim.
3. Open the ticket.
4. Read the Customer Request or original ticket context.
5. Review location, service area, severity, and any existing activity.
6. Confirm that you are the right person to take ownership.
7. Use the pilot-safe **Claim** action.
8. Wait for the ticket to update.
9. Confirm that the ticket now shows you as the accountable owner or appears in your assigned/current work.
10. Add the next appropriate update, note, or work action.

### Verification

After claiming, confirm:

- the ticket no longer appears as unclaimed;
- the ticket appears in your current/assigned work;
- the ticket has one clear accountable owner;
- the timeline or assignment state reflects the ownership change where visible;
- the next action is clear.

### Common mistakes

#### Mistake: Claiming work you cannot action

Problem:

- The ticket leaves the pool but still does not move forward.

Correct approach:

- Only claim when you can take the next meaningful action.
- If you are unsure, ask a coordinator/supervisor before claiming.

#### Mistake: Treating shared visibility as ownership

Problem:

- You may assume you own the ticket when you only have visibility.

Correct approach:

- Check whether the ticket is actually assigned to you.
- Use Claim or Controlled Handoff if ownership must change.

#### Mistake: Claiming a ticket that needs supervisor/coordinator routing

Problem:

- The wrong person may take ownership and delay the ticket.

Correct approach:

- Leave unclear ownership decisions to the coordinator/supervisor.
- Use comments or escalation if the ticket needs routing clarification.

## Process B — Release a ticket

### Purpose

Release a ticket when it is assigned to you but should not remain your accountable work.

Releasing returns the ticket to the true pool with a reason.

Use Release when the ticket should become available for correct routing or claiming again.

### When to release

Release may be appropriate when:

- the ticket was incorrectly assigned to you;
- the work belongs to another area or skill set;
- you cannot continue and no specific next owner is known;
- the ticket needs coordinator review before being reassigned;
- the ticket should return to the pool rather than being handed to a named person.

Do not release a ticket just to avoid work.

If you know exactly who should own the ticket next, ask for or use Controlled Handoff instead, depending on your role.

### Before you release

Confirm:

- the ticket is currently assigned to you;
- you have read the customer request and ticket context;
- you understand why you are releasing it;
- your reason is clear enough for the next person;
- the ticket is not being left without critical context.

If useful, add an internal note before release so the next owner understands what happened.

### Step-by-step process

1. Open the ticket assigned to you.
2. Confirm that it should not remain your accountable work.
3. Check whether the correct next action is Release or Controlled Handoff.
4. Use the pilot-safe **Release** action.
5. Enter a clear reason.
6. Submit the release.
7. Wait for the ticket to update.
8. Confirm that the ticket is no longer assigned to you.
9. Confirm that the ticket is visible in the correct unclaimed/pool/coordinator view where applicable.

### Good release reasons

Good release reasons are specific and useful.

Examples:

- “Incorrectly assigned to PABX; appears to be Internet Connection fault.”
- “Customer location is outside my current route; returning for coordinator scheduling.”
- “Requires coordinator review before next assignment.”
- “I cannot proceed because the fault point is unclear; returning for triage.”

Poor release reasons:

- “Not mine.”
- “Busy.”
- “Wrong.”
- “Please check.”

### Verification

After releasing, confirm:

- the ticket is no longer assigned to you;
- it appears as unclaimed/pool work where expected;
- the reason is visible enough for the next person;
- the ticket has not gained a duplicate or stale owner;
- any urgent context has been captured before release.

### Common mistakes

#### Mistake: Releasing when a specific next owner is known

Problem:

- The ticket goes back to the pool even though the correct next owner is already clear.

Correct approach:

- Use Controlled Handoff when accountability should move to a specific person.

#### Mistake: Releasing without a useful reason

Problem:

- The coordinator or next owner has to rediscover the issue.

Correct approach:

- Write a short, specific reason that explains why the ticket is being returned.

#### Mistake: Releasing urgent work without warning

Problem:

- The ticket may sit unclaimed while urgent work is delayed.

Correct approach:

- Add context and notify/escalate through the appropriate operational path when urgency matters.

## Process C — Controlled Handoff

### Purpose

Use Controlled Handoff when a coordinator or supervisor must transfer ticket accountability to a specific new owner.

Controlled Handoff is not casual sharing.

It is the deliberate transfer of accountable ownership.

### When to use Controlled Handoff

Use Controlled Handoff when:

- the current owner should no longer own the ticket;
- a specific next owner is known;
- a supervisor/coordinator is intervening in stale or blocked work;
- work must move from one technician to another;
- a ticket needs a clear accountable owner after review;
- the pool is not the right destination because the next owner is already known.

### Before handoff

Confirm:

- the ticket is the correct ticket;
- the current ownership state is understood;
- the new owner is the correct accountable person;
- the reason for the handoff is clear;
- important ticket context is already visible or added as an internal note;
- the handoff will not create a duplicate or informal second owner.

### Step-by-step process

1. Open the ticket.
2. Review the Customer Request and latest activity.
3. Review current owner/assignment state.
4. Decide who should become the next accountable owner.
5. Open the **Controlled Handoff** action.
6. Select the new owner.
7. Enter a clear reason for the handoff.
8. Submit the handoff.
9. Wait for the ticket to update.
10. Confirm that the ticket has one clear accountable owner.
11. Confirm that the handoff reason appears in the ticket activity/audit trail where available.
12. Confirm that the new owner can see the ticket in their current/assigned work.

### Good handoff reasons

Good handoff reasons explain why accountability moved.

Examples:

- “Moving to Bravo because this is now confirmed as SIM-related work.”
- “Moving to Charlie for PABX follow-up after initial routing review.”
- “Coordinator reassignment: Alfa unavailable for site visit today.”
- “Supervisor intervention: stale ticket needs dedicated owner.”

Poor handoff reasons:

- “Please handle.”
- “Changed.”
- “As discussed.”
- “Take over.”

### Verification

After Controlled Handoff, confirm:

- the previous owner is no longer the accountable owner;
- the new owner is the only accountable owner;
- the ticket appears in the new owner’s current/assigned work;
- the reason is recorded;
- no generic multi-assignee state was created;
- the timeline/audit trail shows the handoff where available.

### Common mistakes

#### Mistake: Using generic Assign/Unassign instead of Controlled Handoff

Problem:

- Generic assignment can create drift-prone or multi-assignee states that do not match the pilot model.

Correct approach:

- Use the pilot-safe Controlled Handoff action for accountability transfer.

#### Mistake: Handing off without context

Problem:

- The new owner receives accountability but does not know what to do next.

Correct approach:

- Add a clear handoff reason.
- Add an internal note first if the ticket needs more context.

#### Mistake: Handing off to create visibility only

Problem:

- Handoff changes accountable ownership when simple visibility may have been enough.

Correct approach:

- Use sharing/context visibility when someone only needs to assist or observe.
- Use Controlled Handoff only when accountability must move.

## Do

- Use Claim for true pool/unclaimed work you can own.
- Use Release when your ticket should return to the pool with a reason.
- Use Controlled Handoff when accountability must move to a specific new owner.
- Write clear reasons for release and handoff actions.
- Check the ticket after ownership changes.
- Keep one clear accountable owner for owned tickets.
- Add internal context before release/handoff when the next person needs it.

## Do not

- Do not use generic Assign/Unassign as the normal pilot ownership path.
- Do not create informal multi-owner states.
- Do not claim work you cannot action.
- Do not release work without a useful reason.
- Do not hand off a ticket just to give someone visibility.
- Do not leave urgent released work without appropriate operational escalation.
- Do not treat `Shared with me` as the same as `Assigned to me`.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. `My Current Work` showing assigned and shared tickets.
2. Unclaimed/pool ticket list or report.
3. Ticket detail showing current owner/assignment context.
4. Claim action.
5. Ticket after Claim showing the new owner/current work state.
6. Release action with reason field.
7. Ticket after Release showing it is no longer assigned to the releasing user.
8. Controlled Handoff action.
9. Controlled Handoff new owner and reason fields.
10. Ticket after handoff showing the new accountable owner.
11. Handoff timeline/audit evidence where available.

## Related docs

- `docs/runbooks/ticket-assignment-contract.md`
- `docs/runbooks/supervisor-operating-model.md`
- `docs/user-guides/pilot-welcome-guides.md`

# 3. Internal notes and Customer-visible updates

## Purpose

Use this process when Telectro needs to decide whether ticket information should stay internal or be visible to the Customer.

This is one of the most important pilot boundaries.

Internal notes and Customer-visible updates are not interchangeable.

Use:

- **Internal note** when the information should stay inside Telectro;
- **Customer-visible update** when the Customer should see the message in the Customer portal;
- **Customer-visible update with evidence** when the Customer should see both the message and a deliberately selected supporting file.

The Customer portal should show useful progress and outcome information.

It should not expose internal Telectro coordination, routing, assignment, debugging, or governance detail.

## Audience

Primary users:

- Telectro Technician
- Telectro Coordinator
- Telectro Ops / Supervisor

Secondary users:

- any internal Telectro user who writes ticket updates;
- anyone reviewing Customer-facing ticket quality.

This process is not for Partner users or Customer users.

## Core rule

Before adding any note or update, decide who the information is for.

Ask:

1. Is this for Telectro only?
2. Is this safe and useful for the Customer?
3. Is this a progress or outcome update the Customer should see?
4. Does this contain operational detail that should stay internal?
5. Does this need evidence attached?
6. Could this message confuse, alarm, or expose information to the Customer unnecessarily?

If the answer is “Customer should not see this”, use an internal note.

If the answer is “Customer should see this”, use a Customer-visible update.

## Important distinction

### Internal note

Use an internal note for information that should stay inside Telectro.

Internal notes are appropriate for:

- technician coordination;
- scheduling constraints;
- internal investigation notes;
- routing uncertainty;
- assignment/handoff context;
- supervisor/coordinator observations;
- partner management discussion;
- operational risk notes;
- internal troubleshooting detail;
- information that may be useful later but should not appear in the Customer portal.

Internal notes should help Telectro run the ticket.

They should not be relied on as Customer communication.

### Customer-visible update

Use a Customer-visible update when the Customer should see the progress or outcome.

Customer-visible updates are appropriate for:

- acknowledging progress;
- asking the Customer for useful information;
- explaining what Telectro found;
- explaining what Telectro did;
- giving a clear next step;
- confirming that work is complete;
- sharing a safe evidence reference;
- providing resolution or closure wording.

Customer-visible updates should be written in clear, plain language.

They should be deliberate and clean.

### Customer-visible update with evidence

Use the separate evidence process when the Customer-visible update needs a file, photo, or document.

That workflow is:

1. attach the evidence to the HD Ticket first;
2. confirm the evidence is correct and Customer-safe;
3. open the Customer-visible update dialog;
4. select the already-attached evidence;
5. submit the update;
6. verify the timeline and Customer-facing result.

See:

- `# 1. Add a Customer-visible update with photo/document evidence`

## Process A — Add an internal note

### Purpose

Add an internal note when Telectro needs to record useful ticket information that should not be shown to the Customer.

The goal is to preserve operational context without leaking internal discussion into the Customer portal.

### When to use an internal note

Use an internal note when:

- the information is for Telectro only;
- the note explains internal routing or triage;
- the note supports handoff, release, or supervisor review;
- the note records investigation detail;
- the note explains why a ticket is blocked;
- the note captures risk, uncertainty, or dependency;
- the note contains operational wording that is not appropriate for the Customer;
- the Customer does not need the detail to understand the ticket progress.

### Before you add an internal note

Confirm:

- you are on the correct ticket;
- the note is useful to Telectro;
- the note does not need to be sent to the Customer;
- the note is factual and professional;
- the note gives enough context for the next Telectro user;
- the note does not replace a Customer-visible update that the Customer actually needs.

Internal does not mean careless.

Internal notes should still be readable, factual, and useful.

### Step-by-step process

1. Open the relevant HD Ticket.
2. Read the Customer Request and latest activity.
3. Decide that the information should stay internal.
4. Open the internal note/comment action.
5. Write the note clearly.
6. Include the reason, context, blocker, or next step.
7. Submit the note.
8. Confirm the note appears in the internal ticket timeline/activity.
9. Confirm it was not sent as a Customer-visible update.
10. Continue with the next ticket action if needed.

### Good internal note examples

Good internal notes are specific and useful.

Examples:

- “Customer says the fault only occurs after load shedding. Please check UPS/power path before replacing equipment.”
- “Released back to pool because this appears to be an Internet Connection fault, not PABX.”
- “Waiting for site access confirmation from reception before scheduling technician.”
- “Partner feedback is incomplete; coordinator should request clearer completion evidence.”
- “Supervisor note: first response is at risk if no Customer-visible update is sent today.”

### Poor internal note examples

Poor internal notes create confusion or are too vague.

Examples:

- “Check.”
- “Still broken.”
- “Customer angry.”
- “Not mine.”
- “See WhatsApp.”
- “Discussed with Robbie.”

If outside context matters, summarise the relevant point inside the ticket.

### Verification

After adding an internal note, confirm:

- the note appears on the internal ticket activity/timeline;
- the wording is clear enough for the next Telectro user;
- no Customer-visible update was accidentally sent;
- the ticket still has a clear next action;
- urgent Customer-facing communication has not been forgotten.

### Common mistakes

#### Mistake: Using an internal note when the Customer needs an update

Problem:

- Telectro has recorded the information internally, but the Customer still sees no progress.

Correct approach:

- Use a Customer-visible update when the Customer needs to know progress, next steps, or outcome.

#### Mistake: Writing vague internal notes

Problem:

- The next user has to rediscover the context.

Correct approach:

- Include the reason, finding, blocker, or next action.

#### Mistake: Treating internal notes as private casual chat

Problem:

- Internal notes still form part of the ticket record and should remain professional.

Correct approach:

- Keep internal notes factual, concise, and useful.

## Process B — Add a Customer-visible update without evidence

### Purpose

Add a Customer-visible update when Telectro needs to communicate ticket progress, clarification, or outcome to the Customer, and no supporting file needs to be sent.

This is the normal Customer-facing progress update process.

Use the evidence process only when a Customer-visible file/photo/document must be included.

### When to use a Customer-visible update

Use a Customer-visible update when:

- the Customer needs to know that work has started;
- the Customer needs a progress update;
- Telectro needs more information from the Customer;
- Telectro has identified the likely cause;
- Telectro has completed a step;
- Telectro needs to explain the next action;
- the ticket is waiting on Customer input;
- Telectro is resolving the ticket and needs a clear Customer-facing outcome note.

### Before you send a Customer-visible update

Confirm:

- you are on the correct ticket;
- the ticket is Customer-related;
- the message is safe for the Customer;
- the message is clear and useful;
- the message does not include internal-only information;
- the message does not blame another party unnecessarily;
- the message does not expose passwords, supplier/internal detail, routing/debug notes, or internal governance discussion;
- no evidence file is required for this update.

If evidence is required, use the Customer-visible evidence update process instead.

### Step-by-step process

1. Open the relevant HD Ticket.
2. Read the Customer Request and latest activity.
3. Decide that the Customer should see this update.
4. Confirm that no evidence file is required.
5. Open the Customer-visible update action/dialog.
6. Write the message in clear Customer-safe wording.
7. Review the message before submitting.
8. Submit/send the update.
9. Confirm the update appears in the ticket timeline/activity as a Customer-visible communication.
10. When needed, verify that the update appears in the Customer portal Latest update or activity area.

### Good Customer-visible update examples

Good Customer-visible updates are clear, calm, and useful.

Examples:

- “We have received the request and are checking the affected service point.”
- “A technician has inspected the cabinet and found a loose patch lead. The connection has been reseated and we are monitoring the line.”
- “We need the room number or nearest equipment label before we can dispatch the correct technician.”
- “The SIM has been tested and the issue appears to be network coverage at the site. We are escalating this for further review.”
- “The work has been completed and the service is currently testing correctly.”

### Poor Customer-visible update examples

Poor Customer-visible updates expose too much internal detail or are not useful.

Examples:

- “Assigned to Bravo because Alfa is busy.”
- “Looks like routing messed this one up.”
- “Partner did not do this properly.”
- “Internal note: supervisor to check SLA.”
- “Waiting on Robbie.”
- “Fixed.”

### Verification

After sending a Customer-visible update, confirm:

- the update appears in the ticket activity/timeline;
- the wording is correct;
- the update is Customer-safe;
- the Customer portal shows the update when verification is required;
- the Customer has a clear understanding of progress or next steps;
- no internal-only note was accidentally sent.

### Common mistakes

#### Mistake: Sending internal coordination as a Customer-visible update

Problem:

- The Customer sees internal routing, assignment, or governance discussion.

Correct approach:

- Use internal notes for Telectro coordination.
- Only send Customer-visible wording that is useful to the Customer.

#### Mistake: Writing an update that is too vague

Problem:

- The Customer sees activity but still does not understand what is happening.

Correct approach:

- Include the practical progress, finding, question, or next step.

#### Mistake: Forgetting to verify the Customer-facing result

Problem:

- Telectro assumes the Customer can see the update, but the portal or timeline may not show what was expected.

Correct approach:

- Verify the ticket timeline.
- Verify the Customer portal when the update is important or part of a proof/training flow.

## Decision guide

Use this quick decision guide before writing.

### Use an internal note when

- the message is for Telectro only;
- it explains routing, assignment, or handoff context;
- it includes internal investigation details;
- it mentions internal risk, SLA review, or governance;
- it includes operational uncertainty that the Customer does not need;
- it would confuse the Customer;
- it would expose internal process detail.

### Use a Customer-visible update when

- the Customer needs a progress update;
- the Customer needs to answer a question;
- the Customer needs to know what was found;
- the Customer needs to know what was done;
- the Customer needs to know the next step;
- the Customer needs a resolution/outcome summary;
- the wording is safe, clean, and useful.

### Use a Customer-visible update with evidence when

- the Customer should see the message; and
- the Customer should receive a specific supporting file, photo, or document.

Do not attach evidence casually.

Only deliberately selected Customer-visible evidence should be exposed to the Customer.

## Do

- Decide the audience before writing.
- Use internal notes for Telectro-only context.
- Use Customer-visible updates for Customer-facing progress and outcomes.
- Keep Customer-visible wording clear and professional.
- Include the next step when it helps the Customer.
- Verify the timeline after submitting.
- Verify the Customer portal when the update is important.
- Use the separate evidence process when a Customer-visible file must be included.

## Do not

- Do not expose internal notes as Customer-visible updates.
- Do not use internal notes as a substitute for Customer communication.
- Do not include assignment, routing, debugging, governance, or supervisor detail in Customer-visible messages.
- Do not blame technicians, partners, suppliers, or the Customer in Customer-visible wording.
- Do not send unclear one-word updates.
- Do not attach evidence unless it has been deliberately selected for Customer visibility.
- Do not assume that every timeline entry is visible to the Customer.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Ticket detail showing Customer Request and activity.
2. Internal note/comment action.
3. Internal note being written.
4. Internal ticket timeline after internal note submission.
5. Customer-visible update action/dialog.
6. Customer-visible update being written.
7. Ticket timeline after Customer-visible update submission.
8. Customer portal Latest update card.
9. Customer portal activity/timeline showing the Customer-visible update.
10. Example contrast between internal note and Customer-visible update, if safe to show in training data.

## Related docs

- `docs/runbooks/customer-ticket-lifecycle-v1.md`
- `docs/runbooks/ticket-evidence-v1.md`
- `docs/user-guides/pilot-welcome-guides.md`

# 4. Resolve a Customer ticket

## Purpose

Use this process when Telectro has completed the work on a Customer ticket and needs to record a clear Customer-visible resolution outcome.

This is the normal Telectro-side completion action for Customer tickets in the pilot.

Resolving a Customer ticket means:

- Telectro has confirmed the work outcome through the normal direct Customer service process;
- the ticket is updated to `Resolved`;
- a Customer-visible resolution update is sent;
- optional Customer-facing completion evidence can be shared;
- the Customer portal shows the resolved outcome.

This is not a formal Customer portal sign-off process.

The Customer does not approve, reject, or close the ticket from the portal as part of the normal V1 workflow.

## Audience

Primary users:

- Telectro Technician
- Telectro Coordinator
- Telectro Ops / Supervisor

Typical responsibility split:

- technicians normally resolve Customer tickets after the work outcome has been confirmed;
- coordinators may help confirm that the correct Customer-visible wording and completion evidence are used;
- supervisors may review resolved tickets for process quality, SLA risk, or training proof.

This process is not for Partner users or Customer users.

## When to use this process

Use this process when:

- the work on a Customer ticket is complete;
- Telectro has confirmed the outcome through direct Customer interaction or the normal service process;
- the Customer should see a clear resolution or work-done summary;
- the ticket should move to `Resolved`;
- any Customer-facing completion evidence has been selected deliberately.

Typical examples:

- a reported service fault has been corrected;
- a technician has completed the site work;
- a replacement or repair has been completed;
- the Customer has been informed of the outcome;
- Telectro has enough information to record the resolution clearly.

## When not to use this process

Do not resolve a Customer ticket when:

- the work outcome has not been confirmed;
- the ticket still needs technician action;
- the ticket is waiting for Customer information;
- the ticket is waiting for Partner or Supplier action;
- the message should only be an internal note;
- the Customer only needs a progress update, not a resolution;
- the correct action is Partner review, Partner rework, or Customer follow-up.

Use `Add Customer Update` instead when the Customer needs progress information but the ticket should remain active.

Use an internal note when the information should stay inside Telectro.

## Important distinction

### Customer ticket resolution

Customer ticket resolution is Telectro-controlled.

The Customer portal shows useful progress and resolved outcome information, but it is not a formal approval/rework workflow.

Telectro should confirm the work outcome through the normal direct Customer service process and then resolve the ticket internally.

### Partner completion review

Partner completion is different.

Partner work may require Partner acceptance, Partner work submission, Telectro review, and possible rework.

Do not copy the Partner acceptance/rework process onto Customer tickets.

Customer tickets should have:

- clear Customer-visible progress updates;
- clear Customer-visible resolution wording;
- safe Customer-facing completion evidence where needed;
- a simple Customer follow-up route if the Customer still has a concern.

## Before you start

Confirm the following before resolving the ticket:

- You are on the correct HD Ticket.
- The ticket is a Customer ticket.
- The work outcome has been confirmed.
- The ticket should move to `Resolved`.
- The Customer-visible resolution wording is ready.
- The wording is safe for the Customer.
- Any completion evidence has already been attached to the HD Ticket.
- Any selected evidence is safe for Customer visibility.
- No internal-only information will be exposed.
- The ticket does not still require Partner, Supplier, Customer, or technician action.

If completion evidence is required, attach it to the ticket before opening the `Resolve Customer Ticket` dialog.

The resolution dialog lets you select an already-attached file.

It is not the original evidence upload step.

## Step-by-step process

### Step 1 — Open the correct Customer ticket

Open the relevant HD Ticket from the correct Telectro workspace or report.

Useful starting points may include:

- Technician workspace current work list;
- Coordinator current work or review queue;
- Ops / Supervisor oversight reports;
- direct HD Ticket link.

Before continuing, confirm that the ticket number, subject, Customer/account, and location context are the expected ones.

### Step 2 — Review the Customer Request and latest activity

Read the Customer Request, latest Customer-visible updates, internal notes, and relevant activity.

Confirm:

- what the Customer originally reported;
- what work was done;
- whether the Customer has provided follow-up information;
- whether the latest internal context changes the resolution wording;
- whether there are any unresolved blockers.

Do not resolve the ticket from a report row alone.

Open the ticket and review the context first.

### Step 3 — Confirm the work outcome

Confirm that the work is complete and accepted through the normal direct Customer service process.

This may happen through:

- direct discussion with the Customer;
- technician confirmation after site work;
- coordinator confirmation;
- normal service call or operational process;
- other approved Telectro communication.

The Customer does not need to press an approve/reject/sign-off button in the portal.

### Step 4 — Attach completion evidence first, if needed

If the Customer should receive completion evidence, attach the file to the HD Ticket before resolving.

Completion evidence may include:

- photo of completed work;
- signed job card;
- completion sheet;
- test result;
- report;
- safe supporting document.

After upload, confirm:

- the file is attached to the correct ticket;
- the file opens/downloads correctly;
- the content is safe for Customer visibility;
- the filename is recognisable enough to select correctly.

Skip this step if no Customer-facing completion evidence is required.

### Step 5 — Open the Resolve Customer Ticket action

Open the `Resolve Customer Ticket` action from the ticket.

The action opens a dialog titled `Resolve Customer Ticket`.

The dialog requires:

- `Customer-visible resolution update`

The dialog may also allow:

- `Completion evidence file`

The primary action is:

- `Send update and resolve`

### Step 6 — Write the Customer-visible resolution update

Write a clear, Customer-safe resolution update.

A good resolution update should:

- say what was completed or corrected;
- avoid internal routing or assignment detail;
- avoid blame;
- avoid unclear shorthand;
- avoid internal-only troubleshooting notes;
- mention any attached completion evidence if it helps the Customer.

Good examples:

- “The loose patch lead in the PABX cabinet has been reseated and the line is currently testing correctly.”
- “The installation at reception has been completed. The attached photo shows the final installation position.”
- “The SIM was tested and replaced. The affected device is now connecting correctly.”
- “The connection has been restored after replacing the damaged cable at the cabinet.”

Poor examples:

- “Fixed.”
- “Assigned to Bravo and done.”
- “Partner caused the issue.”
- “Internal note: SLA was at risk.”
- “Customer says okay.”
- “See WhatsApp.”

If outside confirmation matters, summarise the relevant outcome in the ticket instead of relying on external context.

### Step 7 — Select completion evidence, if required

If completion evidence should be visible to the Customer, select the correct already-attached file in the `Completion evidence file` field.

Only select evidence that should be Customer-facing.

Do not select:

- internal-only notes;
- screenshots containing credentials;
- supplier-only documents;
- unrelated Customer documents;
- private Telectro operational material;
- rough working photos that should not be shared.

If the file is not available in the selector, close the dialog and attach the file to the ticket first.

### Step 8 — Send update and resolve

Review the resolution note and selected evidence one final time.

Then use `Send update and resolve`.

Wait for the dialog to close or for the ticket to refresh.

Do not assume the process has succeeded until the ticket state and timeline have been checked.

### Step 9 — Verify the internal ticket result

After submission, verify the ticket internally.

Confirm:

- the ticket status is now `Resolved`;
- the resolution wording is recorded;
- the Customer-visible resolution communication appears in the activity/timeline;
- any completion evidence is linked to the resolution communication as expected;
- an internal audit entry exists where visible;
- no incorrect file was shared;
- no internal-only wording was sent to the Customer.

### Step 10 — Verify the Customer-facing result when required

For training, proof, important tickets, or completion evidence, also verify the Customer portal result.

Confirm that the Customer can see:

- the ticket in resolved state;
- the Customer-visible resolution update;
- the attached completion evidence, if selected;
- the evidence download/open behaviour, if applicable.

This is especially important during pilot onboarding and screenshot collection.

## Verification checklist

The process is complete only when the relevant checks pass:

- The correct Customer ticket was opened.
- The work outcome was confirmed through the normal direct Customer service process.
- The ticket was resolved using `Resolve Customer Ticket`.
- The Customer-visible resolution update was clear and safe.
- The ticket status changed to `Resolved`.
- The ticket timeline/activity shows the Customer-visible resolution communication.
- Completion evidence was selected only if deliberately intended for Customer visibility.
- Selected completion evidence is visible/downloadable to the Customer when required.
- Internal-only notes, routing detail, or private evidence were not exposed.
- The Customer portal result was verified when required.

## Common mistakes

### Mistake: Resolving before the outcome is confirmed

Problem:

- The ticket may show as resolved even though the work is not actually complete.

Correct approach:

- Confirm the work outcome through the normal direct Customer service process first.
- Use a Customer-visible progress update if the Customer needs information before resolution.

### Mistake: Treating Customer resolution as formal portal sign-off

Problem:

- Users may wait for a Customer approval/reject action that is not part of the V1 Customer workflow.

Correct approach:

- Telectro confirms the outcome directly and resolves the ticket internally.
- The Customer portal shows the result, but it is not the approval mechanism.

### Mistake: Writing a vague resolution note

Problem:

- The Customer sees a resolved ticket but does not understand what was done.

Correct approach:

- Write a short, clear work-done or resolution summary.

### Mistake: Including internal coordination detail

Problem:

- The Customer sees Telectro routing, assignment, SLA, Partner, or internal troubleshooting detail.

Correct approach:

- Keep Customer-visible resolution wording focused on the Customer-facing outcome.
- Put internal detail in an internal note when needed.

### Mistake: Selecting the wrong completion evidence

Problem:

- The Customer may receive the wrong file or private information.

Correct approach:

- Attach and verify the file before resolving.
- Check filename and content before selecting it in the resolution dialog.

### Mistake: Assuming completion evidence is uploaded inside the resolution dialog

Problem:

- The file may not be available to select.

Correct approach:

- Attach the file to the HD Ticket first.
- Then select the already-attached file in the `Completion evidence file` field.

### Mistake: Skipping Customer portal verification during training/proof

Problem:

- Telectro may believe the Customer can see the resolved outcome or evidence when the portal result has not been confirmed.

Correct approach:

- Verify the Customer portal for training, smoke proof, important tickets, and evidence-sharing flows.

## Do

- Confirm the work outcome before resolving.
- Use `Resolve Customer Ticket` for Customer ticket completion.
- Write a clear Customer-visible resolution update.
- Attach completion evidence to the ticket before resolving, if evidence is needed.
- Select only Customer-safe completion evidence.
- Verify the ticket status after resolving.
- Verify the Customer-visible communication after resolving.
- Verify the Customer portal result when required.
- Use internal notes for internal-only completion context.

## Do not

- Do not wait for formal Customer portal sign-off.
- Do not copy Partner acceptance/rework workflow onto Customer tickets.
- Do not resolve tickets that still need active work.
- Do not use vague resolution wording such as “Fixed”.
- Do not expose assignment, routing, SLA, governance, or internal debugging detail.
- Do not select files that are not safe for Customer visibility.
- Do not assume the resolution dialog uploads the evidence file.
- Do not skip verification for completion evidence.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Customer ticket opened with ticket number and context visible.
2. Customer Request card before resolution.
3. Fault Location card before resolution.
4. Completion evidence attached to the HD Ticket, if applicable.
5. `Resolve Customer Ticket` action.
6. `Resolve Customer Ticket` dialog.
7. `Customer-visible resolution update` field.
8. `Completion evidence file` selector.
9. `Send update and resolve` primary action.
10. Ticket after resolution showing `Resolved` status.
11. Ticket activity/timeline showing the Customer-visible resolution communication.
12. Customer portal showing resolved status.
13. Customer portal showing the resolution update.
14. Customer portal showing completion evidence/download, if applicable.

## Related docs

- `docs/runbooks/customer-ticket-lifecycle-v1.md`
- `docs/runbooks/ticket-evidence-v1.md`
- `docs/user-guides/pilot-welcome-guides.md`

# 5. Customer logs a support request

## Purpose

Use this process when a Customer user needs to log a new support request through the Customer portal.

The Customer portal is the Customer-facing starting point for support requests.

A good support request should help Telectro understand:

- what needs attention;
- where the issue is located;
- which service, fault point, asset, equipment label, circuit, SIM, room, or area is affected;
- what symptoms the Customer is seeing;
- whether photos or evidence are available.

The goal is not to make the Customer diagnose the fault.

The goal is to give Telectro enough clear starting information to route, investigate, and act.

## Audience

Primary users:

- Customer portal users

Secondary users:

- Telectro Technician
- Telectro Coordinator
- Telectro Ops / Supervisor

Internal Telectro users may use this guide during training, onboarding, or Customer support.

This process is not for Partner users.

Partner users should use the Partner workflow instead.

## When to use this process

Use this process when:

- the Customer needs to report a new support issue;
- the issue is not already logged;
- the Customer can describe what is wrong;
- the Customer can identify the affected location, asset, equipment, or service well enough for Telectro to start;
- the Customer wants to attach photos, labels, access notes, or other evidence at the start.

Typical examples:

- a phone, PABX, SIM, CCTV, link, or internet service is not working;
- a specific site, room, cabinet, link, area, or device needs attention;
- the Customer has a photo or label that will help Telectro identify the affected point;
- the Customer needs Telectro to investigate a new issue.

## When not to use this process

Do not log a new support request when:

- the same issue is already logged;
- the Customer only needs to add more information to an existing ticket;
- the Customer wants to reply to a Telectro update on an existing ticket;
- the issue is only a follow-up to a ticket that is already open or recently resolved.

Use `Add information` on the existing ticket instead of creating a duplicate request.

A duplicate request should only be logged when there is a clear reason, such as a genuinely separate issue or a new fault after the previous one was completed.

## Important concepts

### Support Requests

`Support Requests` is the Customer portal area where the Customer can see their logged requests.

Use it to:

- view existing requests;
- open a request again;
- check progress;
- add more information;
- log a new support request.

### Log a Support Request

`Log a Support Request` starts a new request.

Use it only when a new issue needs to be reported.

### Fault Point

`Fault Point` helps Telectro understand where the issue is located.

In the current Customer portal flow, Fault Point is optional.

Customers should choose the closest recognised point, asset, link, or area when they can.

If the exact point is not available or the Customer is unsure, the Customer should still submit the request and describe the location clearly in the details.

### Category

The Fault Point area includes a Category selector.

The current category options include:

- Buildings
- Network Nodes
- Links
- Areas
- Other
- Residents

The Category helps narrow the available fault point search results.

### Search

The Search field lets the Customer search within the selected category.

Customers can search for a recognisable location name, such as a building, room, cabinet, reception area, link, area, or known label.

### Selected Fault Point / Selected Fault Asset

After the Customer selects a result, the portal shows a selected summary.

Depending on the selected category and geometry, the summary may refer to:

- `Selected Fault Point`
- `Selected Fault Asset`

This selected context is sent to Telectro with the ticket.

### Subject

The subject is the short title of the support request.

It should be brief and specific.

### Detailed explanation

The detailed explanation is where the Customer describes the issue.

It should include symptoms, location clues, equipment labels, access notes, and anything Telectro should know before investigating.

### Attachments

Customers can attach photos or evidence while creating the request.

Useful attachments include:

- photos of equipment labels;
- screenshots;
- fault lights;
- site photos;
- access notes;
- signed documents;
- supporting evidence.

Do not attach passwords, unrelated Customer information, or private documents that are not needed for the support request.

## Before you start

Before logging a new support request, the Customer should check:

- whether the same issue is already listed under `Support Requests`;
- whether the existing ticket can be updated with `Add information`;
- what is affected;
- where the issue is located;
- whether a photo, equipment label, access note, or other evidence would help;
- whether the issue needs urgent wording in the description.

If the issue already exists, open the existing ticket and use `Add information`.

## Step-by-step process

### Step 1 — Open Support Requests

Log in as a Customer portal user.

Open `Support Requests`.

This shows the Customer’s support request list.

Before creating a new request, check whether the same issue is already listed.

### Step 2 — Start a new support request

Select `Log a Support Request`.

This opens the new support request page.

The page may show Customer branding and a short instruction such as telling Telectro what needs attention and where it is located.

### Step 3 — Choose a Fault Point category, if useful

In the `Fault Point` area, review the selected Category.

Choose the category that best matches the affected location or asset.

Examples:

- use `Buildings` for a room, building, office, reception, or similar fixed location;
- use `Network Nodes` for cabinets, nodes, or technical network points;
- use `Links` when the affected item is a link rather than a single point;
- use `Areas` when the issue affects a broader mapped area;
- use `Other` when the exact category is not clear.

If unsure, choose the closest likely category and explain the uncertainty in the detailed explanation.

### Step 4 — Search for the closest affected location

Use the Search field to find the closest affected location, point, asset, link, or area.

If results appear, select the closest recognised option.

If no matching result appears:

- try a shorter search term;
- search for a nearby known location;
- choose the closest point you recognise; or
- leave the Fault Point blank and explain the exact location in the detailed explanation.

Fault Point is helpful, but it should not prevent the Customer from submitting a valid request.

### Step 5 — Confirm the selected Fault Point or Fault Asset

If a result is selected, check the selected summary before submitting.

Confirm:

- the selected name looks correct;
- the category looks correct;
- the campus/location context looks correct;
- the map link is useful if available.

If the wrong point was selected, clear it and search again.

### Step 6 — Add a short subject

Enter a short, clear subject.

Good examples:

- “Reception phone not ringing”
- “Internet down at Bakery office”
- “CCTV camera offline at main gate”
- “SIM device not connecting”
- “Link unstable near cellar”

Poor examples:

- “Help”
- “Broken”
- “Problem”
- “Urgent”
- “Please fix”

The subject should help Telectro identify the request quickly from a list.

### Step 7 — Add a detailed explanation

Enter a clear detailed explanation.

Include useful details such as:

- what is not working;
- when the issue started;
- whether it is constant or intermittent;
- which users, rooms, devices, or areas are affected;
- any equipment label, SIM number, circuit reference, extension, cabinet, or device name;
- what has already been checked;
- who Telectro can contact or where access can be arranged.

Good example:

```text
The reception phone is not ringing for incoming calls. Outgoing calls still work. The issue started this morning after load shedding. The phone is at the main reception desk. The equipment label on the handset is PABX-REC-02.
```

Good example when the Fault Point is unknown:

```text
We could not find the exact fault point in the list. The issue is at the small office behind the tasting room. The nearest known location is the reception area. I have attached a photo of the room and the equipment label.
```

### Step 8 — Attach photos or evidence, if helpful

Attach photos or evidence when it will help Telectro understand the request.

Useful examples:

- photo of the affected device;
- photo of an equipment label;
- screenshot of an error;
- photo of warning lights;
- access instruction or contact note;
- document that supports the request.

Before submitting, confirm the attachment is relevant and safe to share.

### Step 9 — Submit the request

Review the request before submitting.

Confirm:

- the subject is clear;
- the detailed explanation contains enough information;
- the selected Fault Point or Fault Asset is correct, if one was selected;
- the attachments are correct, if any were added.

Select `Submit`.

### Step 10 — Verify the submitted ticket

After submission, the portal should open the new ticket detail page.

Confirm:

- the ticket was created;
- the ticket number is visible;
- the subject and description are correct;
- the selected Fault Point or Fault Asset context appears where expected;
- any uploaded attachments are present;
- the ticket appears in `Support Requests`.

If the ticket does not open or something looks wrong, record what happened and contact Telectro through the agreed support channel.

## Verification checklist

The process is complete when:

- The Customer checked that the issue was not already logged.
- `Log a Support Request` was used for a new issue.
- The subject is clear.
- The detailed explanation is useful.
- A Fault Point or Fault Asset was selected when one was known.
- The request was still submitted when no exact Fault Point was available.
- Photos or evidence were attached when helpful.
- The request submitted successfully.
- The new ticket opened after submission.
- The ticket appears in `Support Requests`.

## Common mistakes

### Mistake: Logging a duplicate request

Problem:

- Telectro may receive two tickets for the same issue, which can split updates and confuse ownership.

Correct approach:

- Check `Support Requests` first.
- Use `Add information` on the existing ticket when the issue is already logged.

### Mistake: Waiting because the exact Fault Point is not listed

Problem:

- The Customer may delay reporting the issue.

Correct approach:

- Select the closest known point if possible.
- If no useful point is available, leave Fault Point blank and describe the exact location in the detailed explanation.

### Mistake: Choosing a random Fault Point

Problem:

- Telectro may be routed to the wrong location.

Correct approach:

- Choose the closest known point only when it is genuinely helpful.
- If unsure, explain the uncertainty in the detailed explanation.

### Mistake: Using a vague subject

Problem:

- Telectro cannot quickly understand the issue from the request list.

Correct approach:

- Use a short subject that names the affected service, place, or symptom.

### Mistake: Leaving out access or equipment details

Problem:

- Telectro may need to ask for more information before acting.

Correct approach:

- Include room, cabinet, equipment label, access notes, contact person, or other practical details when available.

### Mistake: Attaching unclear or unrelated photos

Problem:

- Attachments may not help Telectro understand the problem.

Correct approach:

- Attach clear, relevant photos or documents.
- Add a short explanation in the description if the photo needs context.

## Do

- Check existing `Support Requests` first.
- Use `Log a Support Request` for new issues.
- Select the closest Fault Point or Fault Asset when known.
- Submit the request even when no exact Fault Point is available.
- Use a short, clear subject.
- Give enough detail for Telectro to start.
- Attach photos or evidence where helpful.
- Use `Add information` on the existing ticket for follow-up details.

## Do not

- Do not log duplicate requests for the same issue unless there is a clear reason.
- Do not choose a random Fault Point.
- Do not delay reporting just because the exact point is not listed.
- Do not use one-word subjects such as “Help” or “Broken”.
- Do not attach passwords, unrelated documents, or private information that is not needed for the request.
- Do not expect Customer portal sign-off or closure actions as part of the normal Customer workflow.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. `Support Requests` list.
2. `Log a Support Request` button.
3. New support request page header.
4. `Fault Point` area.
5. Category selector.
6. Search field.
7. Fault Point search results.
8. Selected Fault Point or Selected Fault Asset summary.
9. Map link, if available.
10. Subject field.
11. Detailed explanation editor.
12. Attachment upload in the editor.
13. `Submit` button.
14. New ticket detail page after submission.
15. Ticket visible in `Support Requests`.
16. `Add information` action on an existing ticket, as the alternative to duplicate creation.

## Related docs

- `docs/runbooks/customer-location-and-organisation-model.md`
- `docs/runbooks/customer-ticket-lifecycle-v1.md`
- `docs/user-guides/pilot-welcome-guides.md`

# 6. Customer adds follow-up information

## Purpose

Use this process when a Customer user needs to add more information to an existing support request.

This is the normal Customer portal follow-up action.

Customers should use this process when the issue is already logged and they need to send Telectro more detail, photos, labels, access notes, corrected location information, or feedback.

This avoids creating duplicate support requests for the same issue.

## Audience

Primary users:

- Customer portal users

Secondary users:

- Telectro Technician
- Telectro Coordinator
- Telectro Ops / Supervisor

Internal Telectro users may use this guide during training, onboarding, or when helping a Customer understand how to update an existing request.

This process is not for Partner users.

Partner users should use the Partner workflow instead.

## When to use this process

Use this process when:

- the support request already exists;
- the Customer has more information to add;
- Telectro has asked for more detail;
- the Customer wants to send photos, labels, access notes, or extra location information;
- the Customer wants to clarify symptoms;
- the Customer wants to add contact availability;
- the Customer still has a concern after a ticket has been resolved;
- the Customer needs to respond to a Customer-visible update from Telectro.

Typical examples:

- “The fault is now affecting the boardroom as well.”
- “Here is a photo of the equipment label.”
- “The correct room is the small office behind reception.”
- “The technician can access the cabinet after 14:00.”
- “The issue came back after load shedding.”
- “The service is still unstable after the ticket was marked resolved.”

## When not to use this process

Do not use `Add information` when:

- the issue is completely new and unrelated to the existing ticket;
- the Customer needs to log a separate support request;
- the Customer is trying to formally approve or reject work;
- the Customer is trying to close the ticket;
- the message contains private information that should not be attached to the support request;
- the message is intended for internal Telectro notes.

Use `Log a Support Request` for a genuinely new issue.

Use `Add information` for follow-up on an existing issue.

## Important concepts

### Support Requests

`Support Requests` is the Customer portal area where the Customer can view existing requests.

Use it to open the relevant ticket before adding more information.

### Add information

`Add information` opens the Customer follow-up editor on the ticket detail page.

Use it to send Telectro more details on the existing ticket.

### Add more information

The follow-up area may show the heading `Add more information`.

This is the area where the Customer can enter a follow-up message.

### Attachments

Customers can attach photos or evidence when adding information.

Useful attachments include:

- photos of equipment labels;
- screenshots;
- fault lights;
- site photos;
- access notes;
- corrected location photos;
- supporting documents.

Attachments should be relevant to the existing ticket.

### Send

`Send` submits the Customer follow-up.

The follow-up is stored on the ticket and should appear in the ticket activity.

### Active and resolved tickets

Customer follow-up is intended for active or resolved ticket communication.

If the Customer still has a concern after Telectro has resolved the ticket, they can add follow-up information on the existing ticket while the ticket remains available.

Telectro can then decide whether to follow up, reopen, or link/create a new ticket if the issue is new or materially different.

The Customer portal is not a formal approval/rejection workflow.

The Customer should not close the ticket directly as part of the normal V1 process.

## Before you start

Before adding follow-up information, the Customer should confirm:

- they are logged in as the correct Customer user;
- they are looking at the correct support request;
- the information belongs on this existing ticket;
- the update is clear enough for Telectro to act on;
- any photos or attachments are relevant;
- the update does not contain passwords or unrelated private information.

If the issue is new and unrelated, log a new support request instead.

## Step-by-step process

### Step 1 — Open Support Requests

Log in as a Customer portal user.

Open `Support Requests`.

Find the existing support request that needs more information.

### Step 2 — Open the correct ticket

Open the ticket from the support request list.

Before continuing, confirm:

- the ticket number is correct;
- the subject matches the issue;
- the visible request/update history matches the issue;
- this is not a different or unrelated fault.

Do not add information to the wrong ticket.

### Step 3 — Review the latest visible update

Read the latest visible update and activity before writing.

Check whether:

- Telectro has asked for specific information;
- Telectro has already explained the next step;
- the ticket has been resolved;
- the follow-up is still related to the same issue.

If Telectro asked for a specific detail, answer that request clearly.

### Step 4 — Select Add information

Select `Add information`.

The follow-up editor should open or become active.

The editor may show guidance such as:

- photos;
- equipment labels;
- access notes;
- extra location details.

### Step 5 — Write the follow-up message

Write a clear message that explains what Telectro needs to know.

A good follow-up message should include:

- what changed;
- what is still wrong;
- where the issue is located;
- which equipment or service is affected;
- any access or contact detail;
- what the attachment shows, if a file is attached.

Good examples:

```text
The fault is still happening after the router restart. It affects the office behind reception. I have attached a photo of the equipment label.
```

```text
The technician can access the cabinet today between 14:00 and 16:00. Please ask for Johan at reception.
```

```text
The exact fault point is not listed. The issue is at the small office behind the tasting room. I attached a photo of the door and equipment label.
```

```text
The service worked after the visit but failed again after load shedding at about 18:30.
```

Poor examples:

```text
Still broken.
```

```text
Please check.
```

```text
Urgent.
```

```text
Same problem.
```

If the update is short, it should still say what is wrong and where.

### Step 6 — Attach photos or evidence, if helpful

Attach photos or evidence when it helps explain the follow-up.

Useful examples:

- equipment label photo;
- cabinet or device photo;
- screenshot of an error;
- photo showing warning lights;
- access instruction document;
- updated location photo.

Before sending, confirm that the attachment:

- belongs to this ticket;
- is clear enough to help;
- does not expose passwords;
- does not include unrelated Customer or private information.

Skip this step if no attachment is needed.

### Step 7 — Send the follow-up

Review the message and attachments.

Select `Send`.

Wait for the ticket to update.

Do not assume the update was sent until it appears on the ticket.

### Step 8 — Verify the ticket activity

After sending, verify that the follow-up appears in the ticket activity.

Confirm:

- the message appears on the correct ticket;
- the wording is correct;
- any attachment is present;
- the attachment opens/downloads where expected;
- the latest visible activity makes sense.

If the update does not appear, try refreshing the ticket or contact Telectro through the agreed support channel.

### Step 9 — Avoid duplicate tickets

After sending follow-up information, do not create another new support request for the same issue unless there is a clear reason.

Continue using the existing ticket for related information.

Create a new support request only when:

- the issue is separate;
- the affected service/location is materially different;
- Telectro asks for a new request;
- the previous ticket is no longer the right place for the new issue.

## Verification checklist

The process is complete when:

- The Customer opened the correct existing support request.
- The latest visible update was reviewed.
- `Add information` was used instead of creating a duplicate ticket.
- The follow-up message was clear and relevant.
- Photos or evidence were attached only when helpful.
- `Send` was used to submit the update.
- The follow-up appeared in the ticket activity.
- Any attachment appeared with the update where expected.
- No unrelated private information was attached.
- No duplicate support request was created for the same issue.

## Common mistakes

### Mistake: Logging a duplicate request instead of adding information

Problem:

- Telectro may receive multiple tickets for the same issue, which can split updates and confuse ownership.

Correct approach:

- Open the existing ticket.
- Use `Add information`.

### Mistake: Adding information to the wrong ticket

Problem:

- Telectro may investigate the wrong issue or location.

Correct approach:

- Check the ticket number, subject, and visible activity before sending the update.

### Mistake: Sending a vague follow-up

Problem:

- Telectro still does not know what changed or what action is needed.

Correct approach:

- Explain what is wrong, where it is happening, and what the attachment shows.

### Mistake: Treating follow-up as formal approval or rejection

Problem:

- The Customer portal is not a formal sign-off workflow.

Correct approach:

- Use follow-up to provide information, photos, feedback, or concerns.
- Telectro remains responsible for deciding whether to follow up, reopen, link, or create another ticket.

### Mistake: Attaching unclear or unrelated files

Problem:

- Telectro may not be able to use the attachment or may receive unnecessary private information.

Correct approach:

- Attach only relevant, clear, safe files.

### Mistake: Expecting the Customer to close the ticket

Problem:

- Customer closure is not part of the normal V1 Customer workflow.

Correct approach:

- Add follow-up information if something still needs attention.
- Telectro resolves/closes through the Telectro-side process.

## Do

- Use `Add information` on the existing ticket for related follow-up.
- Read the latest visible update before replying.
- Write a clear message.
- Include location, equipment, access, or contact details when useful.
- Attach photos or evidence where helpful.
- Verify the follow-up appears in the ticket activity.
- Continue using the same ticket for the same issue.
- Use a new support request only for a genuinely separate issue.

## Do not

- Do not log duplicate support requests for the same issue.
- Do not add information to the wrong ticket.
- Do not send one-word follow-ups without context.
- Do not attach passwords or unrelated private information.
- Do not use Customer follow-up as formal approval/rejection.
- Do not expect to close the ticket from the Customer portal.
- Do not use this process for Partner workflow actions.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. `Support Requests` list with an existing ticket.
2. Customer ticket detail page.
3. Latest update card or visible activity before follow-up.
4. `Add information` action.
5. `Add more information` editor area.
6. Editor placeholder showing photos/labels/access/location guidance.
7. Attachment added to the editor.
8. `Send` button.
9. Ticket activity after follow-up submission.
10. Attachment visible in the ticket activity, if applicable.
11. Existing ticket after follow-up, showing why a duplicate request was not needed.

## Related docs

- `docs/runbooks/customer-ticket-lifecycle-v1.md`
- `docs/user-guides/pilot-welcome-guides.md`
- `docs/user-guides/activity-process-guides.md#5-customer-logs-a-support-request`

# 7. Customer views latest update

## Purpose

Use this process when a Customer user wants to check what Telectro has said or done on an existing support request.

The `Latest update` card gives the Customer a quick view of the most recent Customer-visible update on the ticket.

This helps Customers see progress without needing to understand Telectro’s internal workflow, assignments, handoffs, Partner reviews, internal notes, or operational comments.

The goal is to help the Customer answer:

* Has Telectro responded?
* What is the latest Customer-visible update?
* What should I do next?
* Do I need to add more information?
* Has the ticket been resolved?

## Audience

Primary users:

* Customer portal users

Secondary users:

* Telectro Technician
* Telectro Coordinator
* Telectro Ops / Supervisor

Internal Telectro users may use this guide during training, onboarding, or when helping a Customer understand what they can see in the Customer portal.

This process is not for Partner users.

Partner users should use the Partner workflow instead.

## When to use this process

Use this process when:

* the Customer wants to check progress on an existing request;
* Telectro has sent a Customer-visible update;
* Telectro has resolved a Customer ticket with a Customer-visible resolution update;
* the Customer wants to confirm the latest visible information before adding follow-up;
* the Customer wants to check whether an attachment, evidence item, or update is visible;
* the Customer wants to understand whether the ticket needs a response from them.

Typical examples:

* “I want to see whether Telectro has replied.”
* “I want to check the latest update before phoning.”
* “I want to confirm what Telectro said after the site visit.”
* “I want to check whether the ticket has been resolved.”
* “I want to know whether I should add more information.”

## When not to use this process

Do not use this process when:

* the Customer needs to log a new support request;
* the Customer needs to send new information to Telectro;
* the Customer needs to attach photos or evidence;
* the Customer wants to formally approve or reject work;
* the Customer expects to see internal Telectro notes, assignments, debug comments, or Partner workflow detail.

Use `Log a Support Request` for a new issue.

Use `Add information` when the Customer needs to send more detail on an existing ticket.

The Customer portal is not a formal sign-off or internal operations portal.

## Important concepts

### Support Requests

`Support Requests` is the Customer portal area where the Customer can see their logged requests.

Use it to open the existing ticket before checking the latest update.

### Request details

`Request details` shows the original Customer request where available.

This is the Customer’s starting message or original logged request.

It helps the Customer compare the latest update against what was originally reported.

### Latest update

`Latest update` shows the most recent Customer-visible update from the ticket activity.

It is intended to show the newest Customer-facing communication after the original request.

If there has not yet been a later Customer-visible update, the `Latest update` card may not appear.

### Customer-visible activity

Customer-visible activity is the ticket activity that the Customer is allowed to see.

It can include:

* the original Customer request;
* Customer follow-up information;
* Telectro Customer-visible updates;
* Telectro Customer-visible resolution updates;
* Customer-visible attachments where deliberately exposed.

### Internal Telectro notes

Internal Telectro notes are not shown to the Customer.

Customers should not expect to see:

* internal routing notes;
* assignment comments;
* technician-only notes;
* coordinator/supervisor governance notes;
* Partner workflow states;
* debug comments;
* private operational discussion.

If the Customer needs to know something, Telectro should send a deliberate Customer-visible update.

### Add information

`Add information` is the Customer response path.

Use it when the Customer has more detail, photos, access notes, corrected location information, or feedback to send after reading the latest update.

## Before you start

Before checking the latest update, the Customer should confirm:

* they are logged in as the correct Customer user;
* they are opening the correct support request;
* they know what issue they are checking;
* they understand that only Customer-visible information will appear;
* they understand that internal Telectro notes are not shown in the Customer portal.

## Step-by-step process

### Step 1 — Open Support Requests

Log in as a Customer portal user.

Open `Support Requests`.

This shows the Customer’s logged support requests.

### Step 2 — Open the correct ticket

Open the support request that needs to be checked.

Before reading the update, confirm:

* the ticket number is correct;
* the subject matches the issue;
* the visible request details match the issue;
* this is not a different or unrelated ticket.

### Step 3 — Check the ticket status

Look at the ticket status or status area where available.

The status helps the Customer understand whether the ticket is still active, resolved, or closed.

Status alone may not explain the full situation.

Read the latest visible update as well.

### Step 4 — Read the Request details

Read `Request details` where shown.

This confirms the original Customer request.

Use it to remember:

* what was reported;
* where the issue was located;
* what details or evidence were originally supplied;
* whether the latest update is responding to the same issue.

### Step 5 — Read the Latest update card

Find the `Latest update` card.

Read the update carefully.

The latest update may include:

* acknowledgement of the request;
* progress information;
* a request for more detail;
* site visit information;
* next steps;
* resolution wording;
* completion outcome;
* reference to Customer-visible evidence.

If the `Latest update` card is not visible, it may mean there is no later Customer-visible update after the original request yet.

In that case, check the visible activity/timeline for available Customer-visible communication.

### Step 6 — Review the visible activity if needed

If more context is needed, review the visible ticket activity.

Use the activity to understand:

* what the Customer originally logged;
* whether the Customer already added follow-up information;
* what Telectro has sent to the Customer;
* whether the latest update is part of a longer conversation.

Do not expect internal Telectro notes to appear.

Only Customer-visible communication should be visible in the Customer portal.

### Step 7 — Decide whether a response is needed

After reading the latest update, decide whether the Customer needs to respond.

A response may be needed when:

* Telectro asks for more information;
* the Customer has new symptoms to report;
* the Customer needs to correct a location or equipment detail;
* the Customer needs to attach a photo or label;
* the Customer still has a concern after resolution;
* the issue has returned after being marked resolved.

If a response is needed, use `Add information`.

Do not log a duplicate support request for the same issue.

### Step 8 — Use Add information if follow-up is needed

Select `Add information` on the existing ticket.

Send a clear follow-up message.

Attach photos or evidence where helpful.

Use the existing ticket for related follow-up so that Telectro can keep the conversation and work history together.

### Step 9 — Do not look for internal notes

Customers should not try to find internal Telectro notes in the Customer portal.

Internal notes are intentionally hidden.

If the Customer needs an explanation, they should ask through `Add information` or the agreed support channel.

Telectro should then provide a clear Customer-visible update if appropriate.

## Verification checklist

The process is complete when:

* The Customer opened `Support Requests`.
* The Customer opened the correct ticket.
* The Customer checked the ticket status.
* The Customer reviewed `Request details` where available.
* The Customer read the `Latest update` card where available.
* The Customer reviewed visible activity if more context was needed.
* The Customer understood that internal Telectro notes are not shown.
* The Customer used `Add information` when a response or clarification was needed.
* No duplicate support request was created for the same issue.

## Common mistakes

### Mistake: Expecting to see internal Telectro notes

Problem:

* Customers may think information is missing because they cannot see internal operational notes.

Correct approach:

* Customers should only expect to see Customer-visible information.
* Telectro must send a deliberate Customer-visible update when the Customer needs to know something.

### Mistake: Treating Latest update as the whole ticket history

Problem:

* The Latest update card shows the newest Customer-visible update, not necessarily the full conversation.

Correct approach:

* Read the visible activity/timeline when more context is needed.

### Mistake: Logging a duplicate request after reading an update

Problem:

* Duplicate requests can split the work history and confuse ownership.

Correct approach:

* Use `Add information` on the existing ticket when the follow-up belongs to the same issue.

### Mistake: Assuming no Latest update means no ticket exists

Problem:

* A ticket may exist even if there is no later Customer-visible update yet.

Correct approach:

* Confirm the ticket is visible in `Support Requests`.
* Check the request details and visible activity.
* Use `Add information` only if the Customer needs to add useful detail.

### Mistake: Using the Customer portal as a formal sign-off system

Problem:

* The V1 Customer portal is not a formal approval/rejection workflow.

Correct approach:

* Read the latest update for progress or outcome.
* Use `Add information` if there is a concern.
* Telectro remains responsible for resolution/closure through the Telectro-side process.

### Mistake: Missing a request for information

Problem:

* Telectro may be waiting for the Customer to provide access notes, photos, labels, or corrected location details.

Correct approach:

* Read the latest update carefully.
* If Telectro asks for detail, respond through `Add information`.

## Do

* Open the correct ticket from `Support Requests`.
* Read the ticket status and latest visible update together.
* Use `Request details` to compare the latest update with the original issue.
* Review the visible activity/timeline when more context is needed.
* Use `Add information` to respond on the same ticket.
* Expect Customer-visible updates only.
* Ask for clarification if the latest update is unclear.

## Do not

* Do not expect to see internal Telectro notes.
* Do not log a duplicate request for the same issue.
* Do not treat `Latest update` as a formal approval/rejection step.
* Do not assume the full internal work history is visible.
* Do not use this process to submit new issue details; use `Log a Support Request` for a genuinely new issue.
* Do not close tickets as part of the normal Customer V1 workflow.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. `Support Requests` list.
2. Customer ticket detail page.
3. Ticket status area.
4. `Request details` card.
5. `Latest update` card.
6. Visible activity/timeline.
7. Example Customer-visible Telectro update.
8. Example resolved ticket outcome.
9. `Add information` action as the response path.
10. Example where no later `Latest update` is shown yet, if useful for training.

## Related docs

* `docs/runbooks/customer-ticket-lifecycle-v1.md`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/user-guides/activity-process-guides.md#3-internal-notes-and-customer-visible-updates`
* `docs/user-guides/activity-process-guides.md#6-customer-adds-follow-up-information`

# 8. Customer downloads Customer-visible evidence

## Purpose

Use this process when a Customer user needs to open or download evidence that Telectro has deliberately made Customer-visible on a support request.

Customer-visible evidence may include completion proof, photos, documents, or supporting files that Telectro has intentionally shared with the Customer.

This process is important because ticket evidence and Customer-visible evidence are not the same thing.

Not every file attached to a ticket is visible to the Customer.

The Customer should only expect to see evidence that is Customer-visible or that the Customer originally submitted through the Customer portal.

## Audience

Primary users:

* Customer portal users

Secondary users:

* Telectro Technician
* Telectro Coordinator
* Telectro Ops / Supervisor

Internal Telectro users may use this guide during training, onboarding, or when helping a Customer find evidence on an existing request.

This process is not for Partner users.

Partner users should use the Partner workflow instead.

## When to use this process

Use this process when:

* Telectro has sent a Customer-visible update with evidence;
* Telectro has resolved a Customer ticket and attached Customer-facing completion evidence;
* the Customer needs to open a photo, PDF, document, or other file shared on the ticket;
* the Customer needs to verify proof of work or completion;
* the Customer wants to check an attachment they submitted earlier;
* Telectro has told the Customer that evidence is available on the ticket.

Typical examples:

* “Please download the completion photo from the ticket.”
* “The resolution update says the completion document is attached.”
* “I want to check the photo I uploaded when I logged the request.”
* “Telectro said the signed completion evidence is available.”
* “I need to confirm which document was shared with the resolution update.”

## When not to use this process

Do not use this process when:

* the Customer needs to upload a new file;
* the Customer needs to add more information to the ticket;
* the Customer expects to see all internal ticket files;
* the Customer expects to see Partner-only files;
* the Customer expects to see technician working files;
* the Customer needs a file that was not deliberately shared with them;
* the issue is new and unrelated to the existing ticket.

Use `Add information` when the Customer needs to send more detail or attach a new file.

Use `Log a Support Request` when the Customer needs to report a new issue.

## Important concepts

### Customer-visible evidence

Customer-visible evidence is evidence that the Customer is allowed to see.

It may be attached to a Customer-visible update or resolution communication.

Customer-visible evidence should be deliberate, safe, and relevant.

### Completion evidence

Completion evidence is evidence attached when Telectro resolves a Customer ticket.

It may include a completion photo, proof-of-work document, signed document, or other file that supports the resolution outcome.

Completion evidence is optional.

Not every resolved ticket needs completion evidence.

### Customer-submitted attachments

Customer-submitted attachments are files the Customer uploaded when creating a support request or adding follow-up information.

These may remain visible to the Customer where the native Customer portal shows them.

Examples include:

* photos of equipment labels;
* screenshots;
* access notes;
* site photos;
* supporting documents.

### Internal evidence

Internal evidence is evidence used by Telectro, technicians, coordinators, supervisors, or Partners for operational work.

Internal evidence is not automatically visible to the Customer.

Examples include:

* technician working photos;
* internal diagnostic notes;
* Partner-only documents;
* supplier information;
* governance notes;
* private operational files;
* documents containing unrelated Customer or Telectro information.

### Controlled download

Customer-facing evidence should be opened or downloaded through the Customer portal’s intended controlled access path.

The Customer should not rely on raw `/private/files/...` links as the access model.

The correct behaviour is that the portal only exposes evidence that belongs to the relevant Customer ticket and has been shared through a Customer-facing communication or allowed Customer portal attachment path.

## Before you start

Before downloading evidence, the Customer should confirm:

* they are logged in as the correct Customer user;
* they have opened the correct support request;
* the update or resolution mentions evidence, if evidence is expected;
* the file appears in the Customer-visible ticket activity or attachment area;
* the file name looks relevant;
* the file belongs to the ticket they are viewing.

If the expected evidence is not visible, the Customer should use `Add information` or the agreed support channel to ask Telectro for help.

## Step-by-step process

### Step 1 — Open Support Requests

Log in as a Customer portal user.

Open `Support Requests`.

This shows the Customer’s logged support requests.

### Step 2 — Open the correct ticket

Open the support request that contains the evidence.

Before downloading anything, confirm:

* the ticket number is correct;
* the subject matches the issue;
* the visible request details match the issue;
* this is not a different or unrelated ticket.

### Step 3 — Read the latest visible update

Read the `Latest update` card or visible ticket activity.

Look for wording that mentions evidence, attachments, completion proof, photos, documents, or a file.

Examples:

* “The completion photo is attached.”
* “The signed completion document has been attached.”
* “Please see the attached evidence.”
* “Completion evidence is available on the ticket.”

### Step 4 — Find the evidence in the visible activity

Look in the Customer-visible ticket activity for the relevant file or attachment.

The evidence may appear near:

* the Customer-visible update;
* the resolution update;
* the Customer’s original request;
* the Customer’s follow-up information;
* the visible activity/timeline.

If more than one file is visible, use the update wording and file name to choose the correct one.

### Step 5 — Open or download the file

Open or download the visible evidence file.

Depending on the browser and file type, the file may:

* open in the browser;
* download to the computer;
* ask for permission to download;
* open in a separate viewer.

Confirm the downloaded or opened file is the expected evidence.

### Step 6 — Verify the file content

After opening or downloading the file, confirm:

* the file opens successfully;
* the file belongs to the correct ticket;
* the file matches the update or resolution wording;
* the file is readable;
* the file is the expected photo, PDF, document, or evidence item.

If the wrong file was downloaded, return to the ticket and check the visible update and filename again.

### Step 7 — If the expected evidence is missing

If the Customer expected evidence but cannot see it, do not create a duplicate support request.

Use `Add information` on the same ticket and ask Telectro for help.

Good example:

* “The resolution update mentions completion evidence, but I cannot see the attachment on the ticket. Please confirm whether the file has been shared.”

Telectro can then check whether the correct file was deliberately selected and shared as Customer-visible evidence.

### Step 8 — Keep the file safe

Downloaded evidence may contain operational or Customer-specific information.

The Customer should store it appropriately and avoid forwarding it outside the intended business context.

Do not upload the downloaded file to unrelated systems unless that is part of the Customer’s internal process.

## Verification checklist

The process is complete when:

* The Customer opened the correct support request.
* The Customer reviewed the latest visible update or ticket activity.
* The expected evidence was visible in the Customer-facing ticket view.
* The Customer opened or downloaded the file.
* The file opened successfully.
* The file content matched the expected evidence.
* The Customer did not expect internal-only ticket evidence to be visible.
* The Customer used `Add information` if expected evidence was missing.

## Common mistakes

### Mistake: Assuming all ticket attachments are Customer-visible

Problem:

* A ticket can contain internal evidence, Partner evidence, or technician files that are not meant for the Customer.

Correct approach:

* Customers should only expect Customer-visible evidence or their own Customer-submitted attachments.
* Telectro must deliberately share evidence when the Customer should see it.

### Mistake: Looking for raw private file links

Problem:

* Raw `/private/files/...` links are not the intended Customer evidence access model.

Correct approach:

* Use the Customer portal’s visible file/download behaviour.
* Ask Telectro if expected evidence is not visible.

### Mistake: Downloading evidence from the wrong ticket

Problem:

* The Customer may rely on the wrong document or photo.

Correct approach:

* Confirm the ticket number, subject, update wording, and filename before using the file.

### Mistake: Treating missing evidence as a new issue

Problem:

* Creating a duplicate support request splits the conversation and work history.

Correct approach:

* Use `Add information` on the same ticket to ask Telectro to check the missing evidence.

### Mistake: Expecting Partner or internal files to be visible

Problem:

* Partner-only and internal operational evidence may contain information that should not be exposed to the Customer.

Correct approach:

* Only Customer-visible evidence should appear in the Customer portal.

### Mistake: Assuming every resolved ticket has completion evidence

Problem:

* Completion evidence is optional and depends on the type of work and Telectro’s process.

Correct approach:

* Read the resolution update.
* Download evidence only when evidence was actually shared.

## Do

* Open the correct ticket from `Support Requests`.
* Read the latest visible update before downloading.
* Download only files visible in the Customer-facing ticket view.
* Confirm the file belongs to the correct ticket.
* Confirm the file content matches the expected evidence.
* Use `Add information` if expected evidence is missing.
* Remember that Customer-visible evidence is selective.

## Do not

* Do not expect all ticket attachments to be visible.
* Do not expect internal Telectro evidence to be visible.
* Do not expect Partner-only evidence to be visible.
* Do not rely on raw `/private/files/...` links.
* Do not create a duplicate ticket just because evidence is missing.
* Do not forward downloaded evidence outside the intended business context unless appropriate.
* Do not use this process to upload new evidence; use `Add information` for that.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. `Support Requests` list.
2. Customer ticket detail page.
3. `Latest update` card mentioning evidence.
4. Visible activity/timeline showing Customer-visible evidence.
5. Evidence filename/link in the Customer portal.
6. Browser download/open behaviour.
7. Downloaded/opened evidence file.
8. Example resolved ticket with completion evidence.
9. Example Customer-submitted attachment visible in activity.
10. `Add information` action for asking Telectro when expected evidence is missing.

## Related docs

* `docs/runbooks/ticket-evidence-v1.md`
* `docs/runbooks/customer-ticket-lifecycle-v1.md`
* `docs/runbooks/pilot-outstanding-issues-timeline.md`
* `docs/user-guides/activity-process-guides.md#1-add-a-customer-visible-update-with-photodocument-evidence`
* `docs/user-guides/activity-process-guides.md#4-resolve-a-customer-ticket`
* `docs/user-guides/activity-process-guides.md#7-customer-views-latest-update`

# 9. Customer checks resolved ticket outcome

## Purpose

Use this process when a Customer user needs to check the outcome of a support request that Telectro has marked as resolved.

A resolved Customer ticket should show the Customer what Telectro has communicated as the work outcome.

The Customer should be able to check:

* the ticket status;
* the latest Customer-visible resolution update;
* any Customer-visible completion evidence;
* whether the issue appears resolved from their side;
* whether they need to add follow-up information.

This process is not a formal approval, rejection, or sign-off workflow.

For V1, Telectro controls ticket resolution from the Telectro side after confirming the work outcome through the normal service process.

## Audience

Primary users:

* Customer portal users

Secondary users:

* Telectro Technician
* Telectro Coordinator
* Telectro Ops / Supervisor

Internal Telectro users may use this guide during training, onboarding, or when helping a Customer understand what a resolved ticket means.

This process is not for Partner users.

Partner users should use the Partner workflow instead.

## When to use this process

Use this process when:

* a Customer ticket shows as `Resolved`;
* Telectro has sent a Customer-visible resolution update;
* the Customer wants to understand what work was done;
* the Customer wants to check whether completion evidence was shared;
* the Customer wants to confirm whether the issue is resolved from their side;
* the Customer still has a concern after the ticket was marked resolved.

Typical examples:

* “The ticket says Resolved. What did Telectro do?”
* “I want to check the resolution note.”
* “I need to download the completion evidence.”
* “The issue is still happening after the ticket was resolved.”
* “The issue came back after load shedding.”
* “The resolved update is unclear, and I need to ask for clarification.”

## When not to use this process

Do not use this process when:

* the Customer needs to log a new unrelated support request;
* the Customer needs to send new information before reviewing the resolved outcome;
* the ticket is still active and has not been resolved;
* the Customer wants to formally approve or reject work through the portal;
* the Customer expects to close the ticket themselves;
* the Customer expects to see internal Telectro notes or operational history.

Use `Customer views latest update` to check progress on an active ticket.

Use `Add information` if the Customer has a concern or more detail to send on the resolved ticket.

Use `Log a Support Request` only when the issue is genuinely new or unrelated.

## Important concepts

### Resolved

`Resolved` means Telectro has marked the ticket as completed from the Telectro side.

It should normally be accompanied by a Customer-visible resolution update that explains the outcome in clear Customer-facing wording.

### Resolution update

The resolution update is the Customer-visible message that explains the work outcome.

It should help the Customer understand:

* what was done;
* what was restored or completed;
* whether any evidence is attached;
* what to do if the issue continues.

### Completion evidence

Completion evidence is optional Customer-visible evidence shared with the resolved ticket.

It may include:

* a completion photo;
* proof-of-work document;
* signed document;
* worksheet;
* other supporting file.

Not every resolved ticket has completion evidence.

If evidence was shared, it should be visible/downloadable through the Customer-facing ticket view.

### Add information after resolution

If the Customer still has a concern after resolution, they should use `Add information` on the same ticket.

This lets Telectro see the concern in the context of the original request and resolution.

Telectro can then decide whether to:

* follow up on the same ticket;
* reopen the issue operationally;
* link a follow-up ticket;
* create a new ticket if the issue is materially different.

### No formal Customer portal sign-off

The V1 Customer portal is not a formal sign-off workflow.

The Customer does not need to press an approve, reject, sign-off, or close button as part of the normal process.

The Customer should use `Add information` if something still needs attention.

## Before you start

Before checking the resolved outcome, the Customer should confirm:

* they are logged in as the correct Customer user;
* they have opened the correct support request;
* the ticket subject and number match the issue;
* the ticket status shows `Resolved` or the latest update says the work has been completed;
* they understand that internal Telectro notes are not shown in the Customer portal.

## Step-by-step process

### Step 1 — Open Support Requests

Log in as a Customer portal user.

Open `Support Requests`.

Find the support request that has been resolved.

### Step 2 — Open the correct ticket

Open the ticket.

Before reviewing the outcome, confirm:

* the ticket number is correct;
* the subject matches the issue;
* the location or fault details match the issue;
* the visible request details match what was originally reported.

Do not review or respond on the wrong ticket.

### Step 3 — Check the ticket status

Look at the ticket status.

If the status shows `Resolved`, Telectro has marked the ticket as completed from the Telectro side.

Status is important, but it is not the whole outcome.

Always read the latest Customer-visible update as well.

### Step 4 — Read the resolution update

Read the `Latest update` card or the visible ticket activity.

Look for the Customer-visible resolution update.

A useful resolution update should explain the outcome in plain language.

It may include:

* what work was done;
* what was checked;
* what was restored;
* what remains for the Customer to know;
* whether completion evidence is attached;
* what to do if the issue returns.

### Step 5 — Check completion evidence, if present

If the resolution update mentions evidence, look for the visible evidence file in the Customer-facing ticket activity.

Open or download the file if needed.

Confirm:

* the evidence belongs to the correct ticket;
* the file opens successfully;
* the file matches the resolution wording;
* the evidence is useful and readable.

If evidence is expected but not visible, use `Add information` to ask Telectro to check it.

### Step 6 — Check whether the issue is resolved from the Customer side

After reading the resolution update, check the real-world issue where possible.

Examples:

* confirm the phone rings;
* confirm the link is stable;
* confirm the internet service works;
* confirm the CCTV camera is online;
* confirm the SIM/device connects;
* confirm the affected location or equipment is working as expected.

If the Customer cannot personally test the issue, they should check with the relevant site contact or user if possible.

### Step 7 — If everything is acceptable

If the issue appears resolved and the update is clear, no Customer portal action is normally required.

The Customer does not need to close the ticket from the portal.

The Customer may keep the ticket for reference and return later if needed.

### Step 8 — If something is still wrong

If the issue is not resolved, or the Customer has a concern, use `Add information` on the same ticket.

Good examples:

```text
The ticket was marked resolved, but the reception phone is still not ringing for incoming calls. Outgoing calls work. Please check again.
```

```text
The link worked after the visit but became unstable again after load shedding at about 18:30.
```

```text
The resolution update mentions completion evidence, but I cannot see the attachment on the ticket. Please confirm whether it was shared.
```

```text
The CCTV camera is online now, but the image is still blurred. I attached a screenshot.
```

Do not create a duplicate support request for the same issue unless there is a clear reason.

### Step 9 — If the issue is new or materially different

If the issue is not the same as the resolved ticket, log a new support request.

Examples of a new or materially different issue:

* a different service is affected;
* a different location is affected;
* the original fault is resolved but a new fault has appeared;
* Telectro asks the Customer to log a new request;
* the old ticket is no longer the right place for the new problem.

When unsure, use `Add information` on the resolved ticket and ask Telectro whether a new request is needed.

## Verification checklist

The process is complete when:

* The Customer opened the correct support request.
* The Customer checked the ticket status.
* The Customer read the Customer-visible resolution update.
* The Customer checked completion evidence if it was mentioned.
* The Customer understood that resolved status is not formal Customer sign-off.
* The Customer confirmed whether the issue appears resolved from their side.
* The Customer used `Add information` if something still needed attention.
* The Customer did not create a duplicate request for the same issue.
* The Customer logged a new support request only if the issue was genuinely new or materially different.

## Common mistakes

### Mistake: Treating resolved status as formal Customer approval

Problem:

* The Customer may think they approved the work or need to press an approval button.

Correct approach:

* `Resolved` is Telectro’s completion state.
* The Customer portal is not a formal approve/reject/sign-off workflow.
* Use `Add information` if there is a concern.

### Mistake: Expecting to close the ticket from the Customer portal

Problem:

* Customer closure is not part of the normal V1 Customer workflow.

Correct approach:

* Review the resolved outcome.
* Add information if needed.
* Let Telectro manage resolution and closure through the Telectro-side process.

### Mistake: Reading only the status and not the resolution update

Problem:

* The Customer may miss important outcome details or next steps.

Correct approach:

* Check status and read the latest Customer-visible update together.

### Mistake: Creating a duplicate ticket for the same unresolved issue

Problem:

* Duplicate tickets split the work history and can confuse Telectro’s ownership and follow-up.

Correct approach:

* Use `Add information` on the same ticket when the issue is still related.

### Mistake: Expecting every resolved ticket to include evidence

Problem:

* Completion evidence is optional.

Correct approach:

* Read the resolution update.
* Download evidence only when it was shared or mentioned.
* Ask through `Add information` if expected evidence is missing.

### Mistake: Adding follow-up to the wrong resolved ticket

Problem:

* Telectro may investigate the wrong issue or location.

Correct approach:

* Confirm the ticket number, subject, location, and visible activity before sending follow-up.

## Do

* Open the correct ticket from `Support Requests`.
* Check the status.
* Read the Customer-visible resolution update.
* Check Customer-visible completion evidence if present.
* Test or confirm the issue from the Customer side where possible.
* Use `Add information` if the issue continues or the update is unclear.
* Keep related follow-up on the same ticket.
* Log a new request only for a genuinely new or materially different issue.

## Do not

* Do not treat `Resolved` as formal Customer approval.
* Do not expect an approve/reject/sign-off button.
* Do not expect to close the ticket from the Customer portal.
* Do not ignore the resolution update.
* Do not create a duplicate request for the same unresolved issue.
* Do not expect internal Telectro notes to be visible.
* Do not expect every resolved ticket to have completion evidence.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. `Support Requests` list with a resolved ticket.
2. Customer ticket detail page.
3. Status area showing `Resolved`.
4. `Latest update` card showing the resolution update.
5. Visible activity/timeline showing the resolution communication.
6. Completion evidence visible/downloadable, if present.
7. `Add information` action on a resolved ticket.
8. Example follow-up message after resolution.
9. Example where no formal Customer approval/sign-off action is shown.
10. Example of when to log a new support request for a different issue.

## Related docs

* `docs/runbooks/customer-ticket-lifecycle-v1.md`
* `docs/runbooks/pilot-outstanding-issues-timeline.md`
* `docs/user-guides/activity-process-guides.md#4-resolve-a-customer-ticket`
* `docs/user-guides/activity-process-guides.md#6-customer-adds-follow-up-information`
* `docs/user-guides/activity-process-guides.md#7-customer-views-latest-update`
* `docs/user-guides/activity-process-guides.md#8-customer-downloads-customer-visible-evidence`

# 10. Partner responds to an acceptance request

## Purpose

Use this process when Telectro has asked a Partner to confirm whether Telectro’s handling of a Partner-originated ticket is acceptable, or whether rework is required.

This process applies to the Partner acceptance train.

It is used when:

* the ticket was originally logged by a Partner;
* Telectro is responsible for fulfilment;
* Telectro has requested Partner acceptance;
* the Partner must either submit an acceptance note or request rework.

This process is not the same as submitting Partner work done.

Partner acceptance confirms whether the Partner accepts Telectro’s handling of the Partner-originated request.

Partner work done is a separate process for tickets where Telectro assigns fulfilment work to a Partner.

## Audience

Primary users:

* Partner users

Secondary users:

* Telectro Coordinator
* Telectro Ops / Supervisor
* Telectro Technician

Internal Telectro users may use this guide during training, onboarding, or when helping a Partner understand the acceptance request process.

This process is not for Customer portal users.

Customer tickets do not use the Partner acceptance/rework workflow.

## When to use this process

Use this process when:

* a Partner-originated ticket is waiting for Partner acceptance;
* the Partner sees `Submit Acceptance Note`;
* the Partner sees `Request Rework`;
* Telectro has asked the Partner to confirm acceptance;
* the Partner agrees that the issue or request has been handled sufficiently;
* the Partner believes Telectro still needs to correct, clarify, or complete something.

Typical examples:

* “Telectro has completed the request; please confirm acceptance.”
* “The ticket is waiting for Partner acceptance.”
* “The outcome is correct, and I need to accept it.”
* “The outcome is not correct, and I need to request rework.”
* “The completion is unclear, and I need Telectro to clarify.”
* “The Partner Acceptance Requested note explains what Telectro wants me to review.”

## When not to use this process

Do not use this process when:

* the ticket was not originally logged by a Partner;
* the Partner is doing work assigned by Telectro;
* the Partner needs to submit work done;
* the ticket is already `Resolved`, `Closed`, or `Archived`;
* no Partner acceptance request is pending;
* the Partner wants to create a new ticket;
* the Customer is trying to approve or reject Customer-facing work.

Use `Partner submits work done` when the Partner is completing work assigned by Telectro.

Use the Customer resolved outcome process for Customer-facing resolution review.

## Important concepts

### Partner-originated ticket

A Partner-originated ticket is a ticket logged by a Partner where the request source is `Partner`.

In this train, the Partner asks Telectro for help, and Telectro works the ticket.

### Partner acceptance request

A Partner acceptance request is Telectro’s request for the Partner to confirm whether Telectro’s handling of the Partner-originated ticket is acceptable.

The ticket’s Partner Acceptance State becomes:

```text
Pending Partner Acceptance
```

The Partner ticket page then shows Partner-side response actions.

### Submit Acceptance Note

`Submit Acceptance Note` is the Partner action used when the Partner accepts Telectro’s handling of the ticket.

The Partner must enter an acceptance note.

After submission, the Partner Acceptance State becomes:

```text
Accepted by Partner
```

The ticket then waits for Telectro review.

### Request Rework

`Request Rework` is the Partner action used when the Partner believes Telectro still needs to correct, clarify, or complete something.

The Partner must enter a reason.

After submission, the Partner Acceptance State becomes:

```text
Rework Required
```

Telectro must then review the rework reason, correct or clarify the issue, and request Partner acceptance again when ready.

### Acceptance is not completion work

Submitting an acceptance note is not the same as submitting work done.

Acceptance means:

```text
The Partner accepts Telectro’s handling of the Partner-originated request.
```

Work done means:

```text
The Partner has completed work assigned to the Partner by Telectro.
```

These are separate Partner workflow trains.

## Before you start

Before responding to a Partner acceptance request, the Partner should confirm:

* they are logged in as the correct Partner user;
* they have opened the correct Partner ticket;
* the ticket is not `Resolved`, `Closed`, or `Archived`;
* the ticket shows the correct subject and summary;
* the ticket is a Partner-originated request;
* the Partner Acceptance Requested note is visible, if one was provided;
* the visible ticket information is enough to decide whether to accept or request rework.

If the Partner cannot make a decision, they should request rework with a clear explanation or contact Telectro through the agreed support channel.

## Step-by-step process

### Step 1 — Open the Partner workspace

Log in as a Partner user.

Open the Partner workspace.

The Partner workspace is the Partner-safe starting point.

Do not use the internal Telectro workspace for this process.

### Step 2 — Open the relevant Partner ticket list

Open the Partner ticket list that contains the ticket waiting for acceptance.

This may be a current/active Partner ticket list or a Partner acceptance-related list, depending on the workspace layout.

Open the ticket from the list.

### Step 3 — Confirm this is the correct ticket

On the Partner ticket page, confirm:

* the ticket ID;
* the subject;
* the summary;
* the status;
* the request source;
* the fulfilment party;
* the Customer / Account context, where visible;
* the site, fault, or service context, where visible.

Do not submit acceptance or request rework on the wrong ticket.

### Step 4 — Read the Partner Acceptance Requested note

If a `Partner Acceptance Requested` note is visible, read it carefully.

The note may explain:

* what Telectro is asking the Partner to review;
* what was done;
* what outcome Telectro believes is ready for acceptance;
* whether any context, evidence, or limitation should be considered.

If the note is unclear, use `Request Rework` and explain what needs clarification.

### Step 5 — Review the ticket information

Review the visible Partner-safe ticket information.

This may include:

* status;
* priority;
* request type;
* due date;
* ticket type;
* request source;
* fulfilment party;
* Customer / Account;
* campus or location;
* fault category;
* fault asset;
* fault point;
* service area;
* severity;
* subject;
* summary;
* attachments;
* Partner notes;
* Telectro review or rework notes.

Only use information visible in the Partner-safe ticket view.

### Step 6 — Decide whether to accept or request rework

Choose `Submit Acceptance Note` when:

* the request has been handled sufficiently;
* the visible outcome matches what the Partner expected;
* no further correction is needed from Telectro;
* the Partner can clearly state acceptance.

Choose `Request Rework` when:

* the outcome is incomplete;
* the issue is not fixed;
* the work does not match the request;
* the result is unclear;
* important information is missing;
* the Partner needs Telectro to correct or clarify something before acceptance.

### Step 7A — Submit an acceptance note

Select `Submit Acceptance Note`.

The dialog asks for:

* `Accepted On`;
* `Acceptance Note`.

Enter a clear acceptance note.

Good examples:

```text
Accepted. Telectro has confirmed the routing change and the Partner request can be closed from our side.
```

```text
Accepted. The requested account update is reflected correctly and no further action is required.
```

```text
Accepted. The fault has been resolved and the site contact confirmed service is restored.
```

Then submit the dialog.

After submission, the ticket moves to:

```text
Accepted by Partner
```

Telectro must then review the Partner acceptance.

### Step 7B — Request rework

Select `Request Rework`.

The dialog asks for a reason.

Enter a clear rework reason.

Good examples:

```text
The issue is not resolved. The link is still unstable and dropped twice after Telectro’s update.
```

```text
The requested change was made on the wrong extension. Please update extension 214, not 241.
```

```text
The completion note does not explain what was changed. Please clarify before acceptance.
```

```text
The attached document is missing the final signed page. Please upload the complete version.
```

Then submit the dialog.

After submission, the ticket moves to:

```text
Rework Required
```

Telectro must then review the reason, perform the required follow-up, and request Partner acceptance again when ready.

### Step 8 — Verify the result

After submitting either action, reload or review the Partner ticket page.

Confirm that:

* the action no longer appears when it is no longer valid;
* the Partner Acceptance Note or Rework Required note is visible where expected;
* the Partner Acceptance State changed as expected;
* the ticket remains in the correct Partner or Telectro review queue.

If the page did not update, refresh the page and check again.

### Step 9 — Wait for Telectro review or follow-up

After the Partner submits an acceptance note, Telectro reviews the acceptance.

Telectro may:

* review only;
* resolve the ticket;
* close the ticket.

After the Partner requests rework, Telectro reviews the reason.

Telectro may:

* perform more work;
* clarify the outcome;
* update the ticket;
* request Partner acceptance again.

The Partner should not try to resolve or close the ticket directly.

## Verification checklist

The process is complete when:

* The Partner opened the correct Partner ticket.
* The Partner confirmed the ticket context before acting.
* The Partner read the Partner Acceptance Requested note, if present.
* The Partner selected the correct action:

  * `Submit Acceptance Note`; or
  * `Request Rework`.
* The Partner entered a clear note or reason.
* The Partner submitted the action.
* The Partner Acceptance State changed as expected.
* The Partner note or rework reason is visible on the ticket.
* Telectro has a clear next action.

## Common mistakes

### Mistake: Treating Partner acceptance as Partner work completion

Problem:

* The Partner may use acceptance when they should submit work done.

Correct approach:

* Use Partner acceptance for Partner-originated tickets where Telectro handled the request.
* Use `Submit Work Done` for Telectro-assigned Partner fulfilment work.

### Mistake: Submitting a vague acceptance note

Problem:

* Telectro cannot tell what was accepted or why the Partner is satisfied.

Poor example:

```text
Done.
```

Better example:

```text
Accepted. The requested routing change has been checked and is working as expected.
```

### Mistake: Requesting rework without a clear reason

Problem:

* Telectro cannot know what needs to be corrected.

Poor example:

```text
Still wrong.
```

Better example:

```text
The routing still sends after-hours calls to the old number. Please update it to the new duty number and confirm.
```

### Mistake: Acting on the wrong Partner ticket

Problem:

* Telectro may review the wrong acceptance or rework request.

Correct approach:

* Always confirm the ticket ID, subject, location, and summary before submitting.

### Mistake: Expecting to resolve or close the ticket as Partner

Problem:

* Partner acceptance is not Partner closure authority.

Correct approach:

* Submit acceptance or request rework.
* Telectro reviews and finalises the ticket.

### Mistake: Using Partner acceptance for Customer sign-off

Problem:

* Customer tickets do not use the Partner acceptance/rework train.

Correct approach:

* Keep Partner acceptance separate from Customer resolved outcome review.

## Do

* Use the Partner workspace.
* Open the correct Partner ticket.
* Read the Partner Acceptance Requested note.
* Review the visible ticket context.
* Use `Submit Acceptance Note` only when the outcome is acceptable.
* Use `Request Rework` when Telectro must correct or clarify something.
* Write clear notes.
* Check that the Partner Acceptance State changed after submission.
* Wait for Telectro review or follow-up.

## Do not

* Do not use Partner acceptance for Customer sign-off.
* Do not use Partner acceptance for Telectro-assigned Partner work completion.
* Do not submit vague notes.
* Do not request rework without explaining what must change.
* Do not act on the wrong ticket.
* Do not expect Partner users to resolve or close the ticket directly.
* Do not assume acceptance is complete until Telectro has reviewed it.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Partner workspace.
2. Partner ticket list showing a ticket awaiting acceptance.
3. Partner ticket detail page.
4. `Partner Acceptance Requested` note.
5. `Submit Acceptance Note` button.
6. `Submit Acceptance Note` dialog.
7. Completed acceptance note visible on the Partner ticket.
8. Partner Acceptance State showing `Accepted by Partner`.
9. `Request Rework` button.
10. `Request Rework` dialog.
11. Rework reason visible on the Partner ticket.
12. Partner Acceptance State showing `Rework Required`.
13. Telectro-side `Review Partner Acceptance` action.
14. Telectro-side `Request Partner Acceptance Again` action after rework.

## Related docs

* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/notification-v1-operating-model.md`
* `docs/runbooks/service-coverage-model.md`
* `docs/runbooks/customer-ticket-lifecycle-v1.md`
* `docs/user-guides/activity-process-guides.md#9-customer-checks-resolved-ticket-outcome`

# 11. Partner submits work done

## Purpose

Use this process when Telectro has assigned fulfilment work to a Partner and the Partner has completed the work.

This process records that Partner-side work is complete and ready for Telectro review.

It is used when:

* the ticket is assigned to Partner fulfilment;
* the Partner has completed the assigned work;
* the Partner needs to submit a work-done note;
* Telectro must review the Partner’s completed work.

This process is not the same as Partner acceptance.

Partner work done means:

```text
The Partner has completed work assigned to the Partner by Telectro.
```

Partner acceptance means:

```text
The Partner accepts Telectro’s handling of a Partner-originated request.
```

These are separate Partner workflow trains.

## Audience

Primary users:

* Partner users

Secondary users:

* Telectro Coordinator
* Telectro Ops / Supervisor
* Telectro Technician

Internal Telectro users may use this guide during training, onboarding, or when helping a Partner understand the work-done submission process.

This process is not for Customer portal users.

Customer tickets do not use the Partner work-done workflow directly.

## When to use this process

Use this process when:

* Telectro has assigned work to a Partner;
* the ticket’s fulfilment party is `Partner`;
* the Partner sees `Submit Work Done`;
* the Partner has completed the assigned work;
* the Partner has uploaded any required evidence;
* the Partner is ready for Telectro to review the work.

Typical examples:

* “The Partner completed the site work.”
* “The Partner replaced the hardware.”
* “The Partner completed the installation.”
* “The Partner uploaded the completion photo and needs to submit work done.”
* “Telectro requested rework and the Partner has completed the rework.”
* “The Partner needs to send the work-done note for Telectro review.”

## When not to use this process

Do not use this process when:

* the ticket was originally logged by a Partner and is waiting for Partner acceptance;
* the Partner only needs to accept Telectro’s handling of a Partner-originated request;
* no Partner work has actually been completed;
* the Partner still needs to upload required evidence;
* the ticket is already `Resolved`, `Closed`, or `Archived`;
* the Partner wants to resolve or close the ticket directly;
* the Customer is trying to confirm a Customer-facing resolution.

Use `Partner responds to an acceptance request` when the Partner is accepting or requesting rework on a Partner-originated ticket.

Use the Customer resolved outcome process for Customer-facing resolution review.

## Important concepts

### Telectro-assigned Partner work

Telectro-assigned Partner work is a ticket where Telectro has asked the Partner to perform fulfilment work.

In this train:

```text
Request Source is not Partner
Fulfilment Party is Partner
```

The Partner completes the work and then submits a work-done note.

### Partner Work State

The Partner Work State shows where the Partner work train currently is.

Common states include:

```text
Assigned to Partner
Work Completed by Partner
Rework Required
Reviewed by Telectro
```

### Submit Work Done

`Submit Work Done` is the Partner action used when the Partner has completed the assigned work.

The Partner must enter a work-done note.

The Partner may also select the completed date.

After submission, the Partner Work State becomes:

```text
Work Completed by Partner
```

The ticket then waits for Telectro work review.

### Work Done Note

The Work Done Note should explain what the Partner did.

A good Work Done Note should be specific enough for Telectro to review the work without guessing.

It may include:

* what was completed;
* what was replaced or repaired;
* what was tested;
* what evidence was uploaded;
* what remains outstanding, if anything;
* any access, site, or safety notes Telectro should know.

### Partner evidence

Partner users can upload supporting evidence on the Partner ticket page.

Evidence may include:

* photos;
* quotes;
* signed documents;
* proof-of-work files;
* worksheets;
* site notes;
* screenshots.

Evidence upload is separate from `Submit Work Done`.

If evidence is required, upload the evidence before submitting the work-done note.

### Telectro review

After the Partner submits work done, Telectro reviews the completed work.

Telectro may:

* review only;
* accept the work;
* request rework;
* resolve the ticket;
* close the ticket.

The Partner does not resolve or close the ticket directly.

## Before you start

Before submitting work done, the Partner should confirm:

* they are logged in as the correct Partner user;
* they have opened the correct Partner ticket;
* the ticket is assigned to Partner fulfilment;
* the ticket is not `Resolved`, `Closed`, or `Archived`;
* the work has actually been completed;
* any required evidence has been uploaded;
* the work-done note is ready;
* the completed date is known.

If the Partner is unsure whether the work is complete, they should not submit work done yet.

## Step-by-step process

### Step 1 — Open the Partner workspace

Log in as a Partner user.

Open the Partner workspace.

The Partner workspace is the Partner-safe starting point.

Do not use the internal Telectro workspace for this process.

### Step 2 — Open assigned Partner work

Open the Partner ticket list that contains work assigned to the Partner.

This may be shown as:

* current Partner work;
* tickets assigned to Partner;
* Partner active tickets;
* work assigned to Partner.

Open the relevant ticket.

### Step 3 — Confirm this is the correct ticket

On the Partner ticket page, confirm:

* the ticket ID;
* the subject;
* the summary;
* the status;
* the request source;
* the fulfilment party;
* the Customer / Account context, where visible;
* the site, fault, or service context, where visible;
* the Partner Work State.

Do not submit work done on the wrong ticket.

### Step 4 — Review the assigned work

Review the Partner-safe ticket information.

This may include:

* status;
* priority;
* request type;
* due date;
* ticket type;
* request source;
* fulfilment party;
* Customer / Account;
* campus or location;
* fault category;
* fault asset;
* fault point;
* service area;
* severity;
* subject;
* summary;
* attachments;
* prior Partner work notes;
* Telectro rework notes.

Make sure the Partner understands what Telectro assigned.

### Step 5 — Complete the work outside the system

Complete the assigned operational work.

Examples:

* repair the fault;
* install or replace equipment;
* complete the site visit;
* perform the configuration;
* gather the requested information;
* prepare the quote or document;
* complete the Partner-side task.

Do not submit work done before the work is actually complete.

### Step 6 — Upload supporting evidence, if required

If evidence is needed, use the Partner ticket page to upload it before submitting work done.

Use the `Upload Attachment` action.

Evidence should be relevant and readable.

Good evidence examples:

* completion photo;
* before/after photo;
* signed job card;
* installation document;
* test result;
* device screenshot;
* quote or worksheet;
* site note.

Do not upload unrelated or duplicate files.

### Step 7 — Select Submit Work Done

When the work is complete, select `Submit Work Done`.

The dialog asks for:

* `Completed On`;
* `Work Done Note`.

The completed date should reflect when the Partner completed the work.

### Step 8 — Write the Work Done Note

Write a clear Work Done Note.

Good examples:

```text
Completed. Replaced the faulty PoE injector at the cellar switch cabinet and confirmed the camera came back online. Completion photo uploaded.
```

```text
Completed. Installed the replacement router, restored internet connectivity, and confirmed browsing from the reception desk.
```

```text
Completed. Site survey done for the requested extension. Photos and measurements uploaded.
```

```text
Completed rework. The missing signed page has been uploaded and the full worksheet is now attached.
```

```text
Completed. SIM was tested in the backup router and confirmed online. Screenshot uploaded.
```

A good Work Done Note should avoid vague wording such as:

```text
Done.
```

or:

```text
Fixed.
```

### Step 9 — Submit the dialog

Submit the `Submit Work Done` dialog.

After submission, the ticket moves to:

```text
Work Completed by Partner
```

The work-done note is recorded on the ticket.

The completed date is recorded if supplied.

### Step 10 — Verify the result

After submitting, reload or review the Partner ticket page.

Confirm:

* the Partner Work State changed to `Work Completed by Partner`;
* the Partner Work Completed date is correct, if shown;
* the Partner Work Done Note is visible;
* uploaded evidence is still visible/downloadable;
* `Submit Work Done` no longer appears while the work is awaiting Telectro review.

If the page did not update, refresh the page and check again.

### Step 11 — Wait for Telectro review

After work done is submitted, Telectro reviews the work.

Telectro may:

* accept the work;
* request rework;
* resolve the ticket;
* close the ticket;
* leave a review note.

If Telectro requests rework, the Partner should complete the rework and submit work done again when ready.

## Verification checklist

The process is complete when:

* The Partner opened the correct assigned Partner ticket.
* The Partner confirmed the ticket context before acting.
* The Partner completed the assigned work.
* Required evidence was uploaded before submission.
* The Partner selected `Submit Work Done`.
* The Partner entered a clear Work Done Note.
* The Partner submitted the action.
* The Partner Work State changed to `Work Completed by Partner`.
* The Work Done Note is visible on the ticket.
* Telectro has a clear review action.

## Common mistakes

### Mistake: Using Submit Work Done for Partner acceptance

Problem:

* The Partner may submit work done when they should respond to an acceptance request.

Correct approach:

* Use `Submit Work Done` only for Telectro-assigned Partner fulfilment work.
* Use `Submit Acceptance Note` or `Request Rework` for Partner-originated acceptance requests.

### Mistake: Submitting work done before the work is complete

Problem:

* Telectro may review incomplete work and request rework.

Correct approach:

* Complete the operational work first.
* Upload evidence if required.
* Submit work done only when the work is ready for Telectro review.

### Mistake: Forgetting to upload evidence

Problem:

* Telectro may not have enough proof to review the work.

Correct approach:

* Upload relevant evidence before submitting work done.
* Mention the evidence in the Work Done Note.

### Mistake: Writing a vague Work Done Note

Problem:

* Telectro cannot tell what was completed.

Poor example:

```text
Done.
```

Better example:

```text
Completed. Replaced the faulty injector, confirmed the device powered up, and uploaded the completion photo.
```

### Mistake: Acting on the wrong Partner ticket

Problem:

* Telectro may review the wrong work or location.

Correct approach:

* Confirm the ticket ID, subject, location, and summary before submitting.

### Mistake: Expecting Partner users to resolve or close the ticket

Problem:

* Partner work done is not Partner closure authority.

Correct approach:

* Submit work done.
* Wait for Telectro review.
* Telectro resolves or closes the ticket where appropriate.

### Mistake: Ignoring a Telectro rework request

Problem:

* The ticket may remain waiting on the Partner.

Correct approach:

* Read the rework note.
* Complete the rework.
* Submit work done again when ready.

## Do

* Use the Partner workspace.
* Open the correct assigned Partner ticket.
* Review the work request before acting.
* Complete the work before submitting.
* Upload relevant evidence where required.
* Write a clear Work Done Note.
* Mention uploaded evidence in the Work Done Note.
* Confirm the Partner Work State changed to `Work Completed by Partner`.
* Wait for Telectro review.

## Do not

* Do not use `Submit Work Done` for Partner acceptance requests.
* Do not submit work done before work is complete.
* Do not skip required evidence.
* Do not write vague notes such as “Done” or “Fixed”.
* Do not submit work done on the wrong ticket.
* Do not expect Partner users to resolve or close the ticket directly.
* Do not ignore rework requested by Telectro.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Partner workspace.
2. Partner current work / assigned tickets list.
3. Partner ticket detail page.
4. Ticket showing Partner Work State `Assigned to Partner`.
5. `Upload Attachment` action.
6. Upload Attachment dialog.
7. Evidence list showing uploaded file.
8. `Submit Work Done` button.
9. `Submit Work Done` dialog.
10. Completed Work Done Note example.
11. Ticket showing Partner Work State `Work Completed by Partner`.
12. Ticket showing Partner Work Completed date.
13. Partner Work Done Note visible on the ticket.
14. Telectro-side `Review Partner Work` action.
15. Rework case showing Partner Work State `Rework Required`.

## Related docs

* `docs/user-guides/pilot-welcome-guides.md`
* `docs/user-guides/activity-process-guides.md#10-partner-responds-to-an-acceptance-request`
* `docs/runbooks/notification-v1-operating-model.md`
* `docs/runbooks/service-coverage-model.md`

# 12. Review Partner acceptance

## Purpose

Use this process when a Partner has submitted an acceptance note for a Partner-originated ticket and Telectro must review that acceptance.

This process is the Telectro-side follow-up to `Partner responds to an acceptance request`.

It is used when:

* the ticket was originally logged by a Partner;
* Telectro was responsible for fulfilment;
* Telectro requested Partner acceptance;
* the Partner submitted an acceptance note;
* the Partner Acceptance State is `Accepted by Partner`;
* Telectro must review the Partner acceptance and decide what happens next.

This process is not for Partner work completion.

Partner acceptance review confirms what Telectro does after the Partner accepts Telectro’s handling of a Partner-originated request.

Partner work review is a separate process for tickets where Telectro assigned fulfilment work to a Partner.

## Audience

Primary users:

* Telectro Coordinator
* Telectro Ops / Supervisor

Secondary users:

* Telectro Technician

Partner users do not perform this process.

Customer portal users do not perform this process.

## When to use this process

Use this process when:

* a Partner-originated ticket appears in the `Partner Acceptance Review Queue`;
* `My Current Work` shows a bucket such as `Partner acceptance review needed`;
* the Partner Acceptance State is `Accepted by Partner`;
* the Partner acceptance note must be reviewed;
* Telectro must decide whether to review only, resolve, or close the ticket.

Typical examples:

* “The Partner accepted Telectro’s handling of the request.”
* “The Partner acceptance note says the issue is accepted.”
* “The Partner Acceptance Review Queue has a ticket waiting.”
* “Telectro needs to finalise the Partner-originated ticket.”
* “The Partner accepted the result, but Telectro wants to add a review note first.”
* “The Partner accepted the result, and the ticket can now be resolved or closed.”

## When not to use this process

Do not use this process when:

* the Partner Acceptance State is not `Accepted by Partner`;
* the Partner has requested rework instead of acceptance;
* the ticket is waiting for Partner acceptance;
* the ticket is Telectro-assigned Partner fulfilment work;
* the Partner submitted work done rather than an acceptance note;
* the ticket is already `Resolved`, `Closed`, or `Archived`;
* the Customer is trying to approve or reject Customer-facing work.

Use `Partner responds to an acceptance request` when the Partner needs to submit acceptance or request rework.

Use `Partner submits work done` when a Partner has completed Telectro-assigned Partner work.

Use the later Partner work review process for `Work Completed by Partner`.

## Important concepts

### Partner acceptance review

Partner acceptance review is Telectro’s review of a Partner’s acceptance note.

It is only valid when the Partner Acceptance State is:

```text
Accepted by Partner
```

### Review Partner Acceptance

`Review Partner Acceptance` is the Telectro-side action used to review Partner acceptance.

The action appears only when the ticket is in the correct state and the current user has the correct internal review role.

The dialog provides three outcomes:

```text
Review only
Resolve ticket
Close ticket
```

The dialog also allows an optional internal review note.

### Review only

`Review only` records a Partner acceptance review comment.

It does not resolve or close the ticket.

In the current implementation, `Review only` does not change the Partner Acceptance State to `Reviewed by Telectro`.

Use `Review only` when Telectro needs to record a review note but is not ready to finalise the ticket.

Because this does not finalise the ticket, the ticket may still need a later resolve or close action.

### Resolve ticket

`Resolve ticket` records the Partner acceptance review and marks the ticket as `Resolved`.

It also sets the Partner Acceptance State to:

```text
Reviewed by Telectro
```

Use this when the Partner accepted the outcome and Telectro wants the ticket to move to a resolved state.

### Close ticket

`Close ticket` records the Partner acceptance review and marks the ticket as `Closed`.

It also sets the Partner Acceptance State to:

```text
Reviewed by Telectro
```

Use this when the Partner accepted the outcome and Telectro wants the ticket to be closed immediately.

### Accepted by Partner

`Accepted by Partner` means the Partner has submitted an acceptance note.

It does not mean Telectro has completed its internal review.

Telectro must still review the acceptance and decide whether to review only, resolve, or close.

### Reviewed by Telectro

`Reviewed by Telectro` means Telectro has finalised the Partner acceptance review through a terminal review outcome such as resolving or closing the ticket.

## Before you start

Before reviewing Partner acceptance, confirm:

* you are logged in as a Telectro Coordinator, Ops / Supervisor, or other authorised internal reviewer;
* the ticket was originally logged by a Partner;
* the ticket is not Partner fulfilment work;
* the ticket is not `Resolved`, `Closed`, or `Archived`;
* the Partner Acceptance State is `Accepted by Partner`;
* the Partner acceptance note is visible;
* the Partner’s acceptance note is clear enough to review;
* you understand whether the ticket should be reviewed only, resolved, or closed.

If the Partner acceptance note is unclear, do not guess.

Use the ticket history and normal Telectro process to clarify before finalising.

## Step-by-step process

### Step 1 — Open the Partner acceptance review queue

Open the relevant Telectro workspace.

Open the `Partner Acceptance Review Queue`, or open `My Current Work` and find the `Partner acceptance review needed` bucket.

The review queue should show Partner-originated tickets where the Partner Acceptance State is `Accepted by Partner`.

### Step 2 — Open the ticket

Open the ticket from the queue or report.

Confirm that you are on the correct HD Ticket.

### Step 3 — Confirm the ticket context

Before reviewing, confirm:

* ticket ID;
* subject;
* status;
* Account / Customer context;
* campus or site context, where relevant;
* request type;
* request source;
* fulfilment party;
* Partner Acceptance State;
* Partner Accepted On date, if shown.

The ticket should be a Partner-originated ticket.

The fulfilment party should not be Partner fulfilment work.

### Step 4 — Read the Partner acceptance note

Read the Partner acceptance note.

A useful Partner acceptance note should explain what the Partner accepted.

Look for:

* whether the Partner clearly accepted the outcome;
* whether the Partner mentions any remaining concern;
* whether the Partner references a site contact, test, document, or confirmation;
* whether the acceptance seems to match the ticket history.

If the note is unclear, Telectro should clarify before using a terminal outcome.

### Step 5 — Review the ticket history

Check the visible ticket history and relevant notes.

Look for:

* the original Partner request;
* Telectro work or response;
* any Partner acceptance request note;
* the Partner acceptance note;
* any attachments or evidence;
* prior rework notes, if this was a repeated acceptance cycle.

Do not rely only on the queue row if the ticket needs more context.

### Step 6 — Select Review Partner Acceptance

On the HD Ticket, select `Review Partner Acceptance`.

If the action is not visible, check:

* the ticket is not new;
* the ticket is an HD Ticket;
* the request source is `Partner`;
* the fulfilment party is not `Partner`;
* the Partner Acceptance State is `Accepted by Partner`;
* the status is not `Resolved`, `Closed`, or `Archived`;
* your user has an internal review role.

### Step 7 — Choose the review outcome

Choose one of the available outcomes.

#### Option A — Review only

Choose `Review only` when:

* Telectro wants to record that the Partner acceptance was reviewed;
* more internal action may still be needed;
* the ticket should not yet be resolved or closed;
* the reviewer wants to leave a note without finalising the ticket.

Use a note that explains why this is review-only.

Good examples:

```text
Reviewed Partner acceptance. Holding open until the coordinator confirms whether billing follow-up is required.
```

```text
Reviewed. Partner accepted the technical outcome, but Telectro still needs to update the internal handover note before final closure.
```

Important: `Review only` does not finalise the Partner acceptance state in the current implementation.

#### Option B — Resolve ticket

Choose `Resolve ticket` when:

* the Partner has accepted the outcome;
* Telectro considers the work complete;
* the ticket should move to `Resolved`;
* no immediate close is required.

Good examples:

```text
Partner acceptance reviewed. Partner confirmed the issue is resolved. Resolving ticket.
```

```text
Partner accepted Telectro’s completion note. No further action required before resolution.
```

#### Option C — Close ticket

Choose `Close ticket` when:

* the Partner has accepted the outcome;
* Telectro considers the ticket complete;
* no further review, waiting period, or resolution stage is required;
* the ticket should be closed immediately.

Good examples:

```text
Partner acceptance reviewed and accepted. Closing ticket because no further Telectro action is required.
```

```text
Partner accepted the final outcome and confirmed the request can be closed.
```

### Step 8 — Add a review note

The note is optional in the system, but it is useful in practice.

Use a short, clear note that explains the decision.

A good review note should include:

* what was reviewed;
* whether the Partner acceptance was clear;
* why the selected outcome was chosen;
* any remaining follow-up, if using `Review only`.

Avoid vague notes such as:

```text
OK.
```

or:

```text
Checked.
```

### Step 9 — Apply the review

Select `Apply`.

The system records a Partner acceptance review comment.

Depending on the selected outcome:

* `Review only` records the review note and leaves the ticket active;
* `Resolve ticket` sets the ticket to `Resolved` and marks Partner Acceptance State as `Reviewed by Telectro`;
* `Close ticket` sets the ticket to `Closed` and marks Partner Acceptance State as `Reviewed by Telectro`.

For `Resolve ticket` and `Close ticket`, open assignment/ToDo work is cleared as part of finalisation.

### Step 10 — Verify the result

After applying the review, reload or review the ticket.

Confirm:

* the Partner acceptance review comment is visible;
* the ticket status matches the selected outcome;
* the Partner Acceptance State matches the selected outcome;
* the ticket no longer appears in the review queue if it was resolved or closed;
* assignment state is appropriate for the outcome.

If `Review only` was selected, confirm that the ticket still has a clear next action.

## Verification checklist

The process is complete when:

* The reviewer opened the correct Partner-originated ticket.
* The Partner Acceptance State was `Accepted by Partner`.
* The Partner acceptance note was reviewed.
* The ticket history was checked where needed.
* `Review Partner Acceptance` was used.
* The correct outcome was selected:

  * `Review only`;
  * `Resolve ticket`; or
  * `Close ticket`.
* A useful review note was added where appropriate.
* The review was applied successfully.
* The resulting status and Partner Acceptance State were verified.
* The ticket has a clear next action or has been finalised.

## Common mistakes

### Mistake: Reviewing the wrong Partner workflow

Problem:

* The reviewer may use Partner acceptance review for Partner work completion.

Correct approach:

* Use `Review Partner Acceptance` only for Partner-originated tickets with Partner Acceptance State `Accepted by Partner`.
* Use `Review Partner Work` for Telectro-assigned Partner fulfilment work.

### Mistake: Assuming Accepted by Partner means Telectro is finished

Problem:

* `Accepted by Partner` means the Partner submitted acceptance, not that Telectro has completed the review.

Correct approach:

* Telectro must still review the acceptance and choose the correct outcome.

### Mistake: Using Review only when the ticket should be finalised

Problem:

* `Review only` records a comment but does not resolve or close the ticket.

Correct approach:

* Use `Resolve ticket` or `Close ticket` when the Partner acceptance should finalise the ticket.

### Mistake: Closing when the ticket should only be resolved

Problem:

* Closing too early may remove the ticket from active resolution tracking before Telectro intended.

Correct approach:

* Use `Resolve ticket` when the ticket should remain in a resolved state before final closure.
* Use `Close ticket` only when immediate closure is appropriate.

### Mistake: Resolving or closing without reading the acceptance note

Problem:

* The Partner may have accepted with a condition, concern, or limitation.

Correct approach:

* Read the Partner acceptance note before applying a terminal outcome.

### Mistake: Ignoring unclear acceptance

Problem:

* Telectro may finalise a ticket even though the Partner note is ambiguous.

Correct approach:

* Clarify ambiguous acceptance before resolving or closing.

### Mistake: Treating Partner acceptance as Customer sign-off

Problem:

* Customer-facing tickets do not use the Partner acceptance train.

Correct approach:

* Keep Partner acceptance review separate from Customer resolved outcome review.

## Do

* Open the Partner Acceptance Review Queue or relevant My Current Work bucket.
* Confirm the ticket is Partner-originated.
* Confirm Partner Acceptance State is `Accepted by Partner`.
* Read the Partner acceptance note.
* Review ticket history where needed.
* Use `Review Partner Acceptance`.
* Choose the outcome deliberately.
* Add a clear review note where useful.
* Verify the resulting status and Partner Acceptance State.
* Keep Partner acceptance separate from Partner work review and Customer workflows.

## Do not

* Do not use this process for Partner work completion.
* Do not use this process for Customer sign-off.
* Do not resolve or close without reading the Partner acceptance note.
* Do not use `Review only` when the ticket should be finalised.
* Do not close the ticket unless closure is intended.
* Do not ignore unclear or conditional Partner acceptance.
* Do not expect Partner users to perform this Telectro review step.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Telectro workspace showing Partner review access.
2. `Partner Acceptance Review Queue`.
3. Queue row showing Partner Acceptance State `Accepted by Partner`.
4. Queue row showing Partner Acceptance Note preview.
5. Full Partner Acceptance Note popup or expanded view.
6. HD Ticket showing Partner Acceptance State `Accepted by Partner`.
7. `Review Partner Acceptance` button.
8. `Review Partner Acceptance` dialog.
9. Outcome dropdown showing `Review only`, `Resolve ticket`, and `Close ticket`.
10. Example review note.
11. Ticket after `Review only`.
12. Ticket after `Resolve ticket`, showing status `Resolved`.
13. Ticket after `Close ticket`, showing status `Closed`.
14. Partner Acceptance State showing `Reviewed by Telectro` after terminal review.
15. Review comment in ticket activity/history.

## Related docs

* `docs/user-guides/activity-process-guides.md#10-partner-responds-to-an-acceptance-request`
* `docs/user-guides/activity-process-guides.md#11-partner-submits-work-done`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/notification-v1-operating-model.md`
* `docs/runbooks/service-coverage-model.md`

# 13. Review Partner completed work

## Purpose

Use this process when a Partner has submitted work done for Telectro-assigned Partner fulfilment work and Telectro must review the completed work.

This process is the Telectro-side follow-up to `Partner submits work done`.

It is used when:

* Telectro assigned fulfilment work to a Partner;
* the Partner completed the work;
* the Partner submitted a Work Done Note;
* the Partner Work State is `Work Completed by Partner`;
* Telectro must review the Partner’s completed work and decide what happens next.

This process is not for Partner acceptance.

Partner work review confirms what Telectro does after a Partner completes work assigned by Telectro.

Partner acceptance review is a separate process for Partner-originated tickets where the Partner accepts Telectro’s handling of the request.

## Audience

Primary users:

* Telectro Coordinator
* Telectro Ops / Supervisor

Secondary users:

* Telectro Technician

Partner users do not perform this process.

Customer portal users do not perform this process.

## When to use this process

Use this process when:

* a ticket is assigned to Partner fulfilment;
* the Partner Work State is `Work Completed by Partner`;
* `My Current Work` shows a bucket such as `Partner work review needed`;
* the Partner Work Done Note must be reviewed;
* uploaded Partner evidence must be checked;
* Telectro must accept the work, request rework, resolve the ticket, or close the ticket.

Typical examples:

* “The Partner submitted work done.”
* “The Partner uploaded completion evidence.”
* “The Partner says the site work is complete.”
* “The Partner Work State is Work Completed by Partner.”
* “Telectro must decide whether to accept the Partner work.”
* “The Partner completed rework and submitted work done again.”
* “The Partner work can now be resolved or closed.”

## When not to use this process

Do not use this process when:

* the Partner Work State is not `Work Completed by Partner` or `Reviewed by Telectro`;
* the work is still assigned to the Partner;
* the Partner has not submitted a Work Done Note;
* the ticket was originally logged by a Partner and is waiting for Partner acceptance review;
* the Partner submitted an acceptance note rather than work done;
* the ticket is already `Resolved`, `Closed`, or `Archived`;
* the Customer is trying to confirm a Customer-facing resolution.

Use `Partner submits work done` when the Partner still needs to submit completed work.

Use `Review Partner acceptance` when Telectro is reviewing Partner acceptance on a Partner-originated ticket.

Use the Customer resolved outcome process for Customer-facing resolution review.

## Important concepts

### Telectro-assigned Partner work

Telectro-assigned Partner work is a ticket where Telectro has asked a Partner to perform fulfilment work.

In this train:

```text
Request Source is not Partner
Fulfilment Party is Partner
```

The Partner completes the work, uploads evidence where required, and submits a Work Done Note.

Telectro then reviews the completed work.

### Partner Work State

The Partner Work State shows where the Partner fulfilment train currently is.

Common states include:

```text
Assigned to Partner
Work Completed by Partner
Rework Required
Reviewed by Telectro
```

### Work Completed by Partner

`Work Completed by Partner` means the Partner has submitted a Work Done Note.

It does not mean Telectro has accepted the work yet.

Telectro must still review the note, evidence, and ticket context.

### Review Partner Work

`Review Partner Work` is the Telectro-side action used to review completed Partner work.

When the Partner Work State is `Work Completed by Partner`, the action provides these outcomes:

```text
Review only
Accept work
Request Rework
Resolve ticket
Close ticket
```

When the Partner Work State is already `Reviewed by Telectro`, the action provides only:

```text
Resolve ticket
Close ticket
```

### Review only

`Review only` records a Partner work review comment.

It does not accept, rework, resolve, or close the ticket.

In the current implementation, `Review only` does not change the Partner Work State.

Use `Review only` when Telectro wants to record a review note but is not ready to accept, request rework, resolve, or close.

### Accept work

`Accept work` records that Telectro has accepted the Partner’s completed work.

It sets the Partner Work State to:

```text
Reviewed by Telectro
```

It also removes the ticket from the active Partner work queue by clearing open assignment/ToDo work.

Use this when the Partner’s work is acceptable, but Telectro does not yet want to resolve or close the ticket.

### Request Rework

`Request Rework` sends the work back to the Partner for correction or completion.

A rework reason is required.

It sets the Partner Work State to:

```text
Rework Required
```

It also clears the Partner Work Completed date.

Use this when the Partner’s submitted work is incomplete, unclear, incorrect, or missing required evidence.

### Resolve ticket

`Resolve ticket` accepts the Partner work, sets the Partner Work State to `Reviewed by Telectro`, and changes the ticket status to:

```text
Resolved
```

Use this when the Partner work is acceptable and the ticket should move to resolved.

### Close ticket

`Close ticket` accepts the Partner work, sets the Partner Work State to `Reviewed by Telectro`, and changes the ticket status to:

```text
Closed
```

Use this when the Partner work is acceptable and the ticket should be closed immediately.

## Before you start

Before reviewing Partner completed work, confirm:

* you are logged in as a Telectro Coordinator, Ops / Supervisor, or other authorised internal reviewer;
* the ticket is Telectro-assigned Partner fulfilment work;
* the fulfilment party is `Partner`;
* the request source is not `Partner`;
* the ticket is not `Resolved`, `Closed`, or `Archived`;
* the Partner Work State is `Work Completed by Partner`;
* the Partner Work Done Note is visible;
* any required Partner evidence is visible and readable;
* you understand whether the work should be accepted, sent back for rework, resolved, or closed.

If the Partner Work Done Note or evidence is unclear, do not guess.

Use `Request Rework` when the Partner must correct, clarify, or complete something.

## Step-by-step process

### Step 1 — Open the Partner work review queue

Open the relevant Telectro workspace.

Open `My Current Work` and find the `Partner work review needed` bucket, or open the relevant Partner workflow oversight report.

The review list should show Telectro-assigned Partner fulfilment tickets where the Partner Work State is `Work Completed by Partner`.

### Step 2 — Open the ticket

Open the HD Ticket from the queue or report.

Confirm that you are on the correct ticket.

### Step 3 — Confirm the ticket context

Before reviewing, confirm:

* ticket ID;
* subject;
* status;
* Account / Customer context;
* campus or site context, where relevant;
* request type;
* request source;
* fulfilment party;
* Partner Work State;
* Partner Work Completed date, if shown.

The ticket should be Telectro-assigned Partner fulfilment work.

It should not be a Partner-originated acceptance ticket.

### Step 4 — Read the Partner Work Done Note

Read the Partner Work Done Note.

A useful Work Done Note should explain what the Partner completed.

Look for:

* what was done;
* what was repaired, replaced, installed, tested, or checked;
* whether the Partner mentions evidence;
* whether the Partner mentions anything still outstanding;
* whether the note matches the assigned work.

If the note is vague, missing, or inconsistent, request rework.

### Step 5 — Review Partner evidence

Review any uploaded Partner evidence.

Evidence may include:

* photos;
* job cards;
* signed documents;
* installation notes;
* screenshots;
* test results;
* quotes;
* worksheets;
* site notes.

Confirm that evidence is relevant, readable, and attached to the correct ticket.

Do not accept work if required evidence is missing or obviously unrelated.

### Step 6 — Review the ticket history

Check the visible ticket history and relevant notes.

Look for:

* original request;
* Telectro assignment or handoff context;
* Partner Work Done Note;
* uploaded evidence;
* prior Partner rework notes, if any;
* previous Partner work review notes, if any.

Do not rely only on the report row if the ticket needs more context.

### Step 7 — Select Review Partner Work

On the HD Ticket, select `Review Partner Work`.

If the action is not visible, check:

* the ticket is not new;
* the ticket is an HD Ticket;
* the fulfilment party is `Partner`;
* the request source is not `Partner`;
* the Partner Work State is `Work Completed by Partner` or `Reviewed by Telectro`;
* the status is not `Resolved`, `Closed`, or `Archived`;
* your user has an internal review role.

### Step 8 — Choose the review outcome

Choose one of the available outcomes.

#### Option A — Review only

Choose `Review only` when:

* Telectro wants to record that the Partner work was reviewed;
* more internal action may still be needed;
* the ticket should not yet be accepted, reworked, resolved, or closed;
* the reviewer wants to leave a note without changing the Partner Work State.

Good examples:

```text
Reviewed Partner work. Holding open until the coordinator confirms whether a follow-up customer update is required.
```

```text
Reviewed. Evidence is present, but Telectro still needs to confirm whether billing follow-up is needed before accepting work.
```

Important: `Review only` does not finalise Partner Work State in the current implementation.

#### Option B — Accept work

Choose `Accept work` when:

* the Partner’s work is complete;
* the Work Done Note is clear;
* required evidence is present;
* no rework is needed;
* Telectro does not yet want to resolve or close the ticket.

Good examples:

```text
Partner work reviewed and accepted. Completion photo and work note are sufficient.
```

```text
Accepted. Partner replaced the faulty device and uploaded the required evidence.
```

After this outcome, the Partner Work State becomes:

```text
Reviewed by Telectro
```

#### Option C — Request Rework

Choose `Request Rework` when:

* the work is incomplete;
* the wrong work was done;
* the evidence is missing;
* the evidence is unreadable;
* the note is unclear;
* the work does not match the ticket request;
* Telectro needs the Partner to correct or clarify something.

A rework reason is required.

Good examples:

```text
Please upload a clear completion photo showing the installed replacement device and label.
```

```text
The submitted note does not confirm whether connectivity was tested. Please test from site and resubmit the work done note.
```

```text
The work appears to have been completed at the wrong fault point. Please verify the location and correct if needed.
```

```text
The signed job card is missing. Please upload the signed job card before resubmitting work done.
```

After this outcome, the Partner Work State becomes:

```text
Rework Required
```

The Partner must complete the rework and submit work done again.

#### Option D — Resolve ticket

Choose `Resolve ticket` when:

* the Partner work is acceptable;
* the ticket should move to `Resolved`;
* no immediate closure is required;
* Telectro wants to preserve a resolved state before final closure.

Good examples:

```text
Partner work reviewed and accepted. Evidence confirms completion. Resolving ticket.
```

```text
Partner completed the assigned work and uploaded sufficient proof. Resolving for final outcome tracking.
```

After this outcome:

```text
Partner Work State = Reviewed by Telectro
Ticket Status = Resolved
```

#### Option E — Close ticket

Choose `Close ticket` when:

* the Partner work is acceptable;
* no further review, waiting period, or resolution stage is required;
* Telectro wants to close the ticket immediately.

Good examples:

```text
Partner work reviewed and accepted. No further Telectro action required. Closing ticket.
```

```text
Completion note and evidence are sufficient, and the issue is finalised. Closing ticket.
```

After this outcome:

```text
Partner Work State = Reviewed by Telectro
Ticket Status = Closed
```

### Step 9 — Add a review note

The note is optional for most outcomes, but it is strongly useful in practice.

The note is required when requesting rework.

A good review note should explain:

* what was reviewed;
* whether the Work Done Note was clear;
* whether evidence was checked;
* why the selected outcome was chosen;
* what the Partner must correct, if requesting rework.

Avoid vague notes such as:

```text
OK.
```

or:

```text
Checked.
```

### Step 10 — Apply the review

Select `Apply`.

The system records a Partner work review or rework comment.

Depending on the selected outcome:

* `Review only` records the review note and leaves the Partner Work State unchanged;
* `Accept work` sets Partner Work State to `Reviewed by Telectro`;
* `Request Rework` sets Partner Work State to `Rework Required` and clears the completed date;
* `Resolve ticket` sets Partner Work State to `Reviewed by Telectro` and ticket status to `Resolved`;
* `Close ticket` sets Partner Work State to `Reviewed by Telectro` and ticket status to `Closed`.

For `Accept work`, `Resolve ticket`, and `Close ticket`, open assignment/ToDo work is cleared as part of finalisation.

For `Request Rework`, the Partner is notified and must submit work done again after completing the rework.

### Step 11 — Verify the result

After applying the review, reload or review the ticket.

Confirm:

* the Partner work review or rework comment is visible;
* the ticket status matches the selected outcome;
* the Partner Work State matches the selected outcome;
* the Partner Work Completed date is cleared if rework was requested;
* the ticket no longer appears in Partner work review needed if the work was accepted, resolved, or closed;
* assignment state is appropriate for the outcome.

If `Review only` was selected, confirm that the ticket still has a clear next action.

If `Request Rework` was selected, confirm that the ticket is now waiting on the Partner.

## Verification checklist

The process is complete when:

* The reviewer opened the correct Telectro-assigned Partner fulfilment ticket.
* The Partner Work State was `Work Completed by Partner`.
* The Partner Work Done Note was reviewed.
* Required evidence was checked.
* Ticket history was checked where needed.
* `Review Partner Work` was used.
* The correct outcome was selected:

  * `Review only`;
  * `Accept work`;
  * `Request Rework`;
  * `Resolve ticket`; or
  * `Close ticket`.
* A useful review note was added.
* Rework reason was provided if rework was requested.
* The review was applied successfully.
* The resulting status and Partner Work State were verified.
* The ticket has a clear next action or has been finalised.

## Common mistakes

### Mistake: Reviewing the wrong Partner workflow

Problem:

* The reviewer may use Partner work review for Partner acceptance.

Correct approach:

* Use `Review Partner Work` only for Telectro-assigned Partner fulfilment work.
* Use `Review Partner Acceptance` for Partner-originated tickets with Partner Acceptance State `Accepted by Partner`.

### Mistake: Assuming Work Completed by Partner means Telectro is finished

Problem:

* `Work Completed by Partner` means the Partner submitted work done, not that Telectro has accepted the work.

Correct approach:

* Telectro must still review the Work Done Note, evidence, and ticket context.

### Mistake: Accepting work without reviewing evidence

Problem:

* Telectro may accept incomplete or unproven work.

Correct approach:

* Check uploaded evidence where evidence is expected.
* Request rework if evidence is missing or unclear.

### Mistake: Using Review only when the work should be accepted or sent back

Problem:

* `Review only` records a comment but does not change the Partner Work State.

Correct approach:

* Use `Accept work` when the work is acceptable.
* Use `Request Rework` when the Partner must correct or complete something.

### Mistake: Requesting rework without a clear reason

Problem:

* The Partner may not know what to correct.

Poor example:

```text
Not good enough.
```

Better example:

```text
Please upload a clear photo of the installed replacement device and confirm that connectivity was tested from site.
```

### Mistake: Resolving or closing too early

Problem:

* The ticket may be finalised before Telectro has completed internal follow-up.

Correct approach:

* Use `Accept work` when Partner work is accepted but the ticket should remain active.
* Use `Resolve ticket` or `Close ticket` only when the ticket is ready for that status.

### Mistake: Treating Partner work review as Customer sign-off

Problem:

* Customer-facing tickets do not use Partner work review as Customer approval.

Correct approach:

* Keep Partner work review separate from Customer resolved outcome review.

## Do

* Open the relevant Partner work review queue or `My Current Work` bucket.
* Confirm the ticket is Telectro-assigned Partner fulfilment work.
* Confirm Partner Work State is `Work Completed by Partner`.
* Read the Partner Work Done Note.
* Review uploaded evidence.
* Review ticket history where needed.
* Use `Review Partner Work`.
* Choose the outcome deliberately.
* Add a clear review note.
* Provide a clear reason when requesting rework.
* Verify the resulting status and Partner Work State.

## Do not

* Do not use this process for Partner acceptance review.
* Do not accept Partner work without checking the note and evidence.
* Do not use `Review only` when the work should be accepted or sent back.
* Do not request rework without a clear reason.
* Do not resolve or close unless that outcome is intended.
* Do not treat Partner work review as Customer sign-off.
* Do not expect Partner users to perform this Telectro review step.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Telectro workspace showing Partner work review access.
2. `My Current Work` bucket showing `Partner work review needed`.
3. Partner workflow oversight report showing completed Partner work.
4. HD Ticket showing Partner Work State `Work Completed by Partner`.
5. Partner Work Done Note visible on the ticket.
6. Uploaded Partner evidence visible on the ticket.
7. `Review Partner Work` button.
8. `Review Partner Work` dialog.
9. Outcome dropdown showing `Review only`, `Accept work`, `Request Rework`, `Resolve ticket`, and `Close ticket`.
10. Example `Accept work` review note.
11. Example `Request Rework` reason.
12. Ticket after `Accept work`, showing Partner Work State `Reviewed by Telectro`.
13. Ticket after `Request Rework`, showing Partner Work State `Rework Required`.
14. Ticket after `Resolve ticket`, showing status `Resolved`.
15. Ticket after `Close ticket`, showing status `Closed`.
16. Review or rework comment in ticket activity/history.

## Related docs

* `docs/user-guides/activity-process-guides.md#11-partner-submits-work-done`
* `docs/user-guides/activity-process-guides.md#12-review-partner-acceptance`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/notification-v1-operating-model.md`
* `docs/runbooks/service-coverage-model.md`

# 14. Review current work

## Purpose

Use this process to review your current internal Telectro work and decide what needs action next.

`My Current Work` is the main internal work review report for Telectro users. It brings together tickets that are assigned to you, shared with you, or waiting for Telectro review in Partner-related workflows.

This guide explains how to use the report as a daily working list, not as a full supervisor dashboard.

## Audience

Primary users:

* Telectro Technician
* Telectro Coordinator
* Telectro Ops / Supervisor

Partner users do not use this internal report.

Customer portal users do not use this internal report.

## When to use this process

Use this process when:

* starting the day;
* returning from a break or site visit;
* checking what is currently assigned to you;
* checking tickets shared with you;
* checking Partner work or Partner acceptance review items;
* deciding which ticket needs the next action;
* verifying that your work queue is not drifting.

Typical examples:

* “What must I work on now?”
* “Which tickets are assigned to me?”
* “Which tickets are shared with me?”
* “Is there Partner work waiting for Telectro review?”
* “Is any Partner work currently with the Partner?”
* “Which current work item needs the next update?”

## When not to use this process

Do not use this process when:

* you need the full unclaimed queue;
* you need aging and SLA oversight across the whole team;
* you need first-response risk across Customer tickets;
* you need a full supervisor governance view;
* you are a Partner user checking Partner portal work;
* you are a Customer checking Customer portal tickets.

Use the relevant queue or oversight report for those workflows.

## Important concepts

### My Current Work

`My Current Work` is an internal Telectro report.

It helps internal users see active work that is relevant to them.

The report excludes terminal tickets:

```text
Resolved
Closed
Archived
```

### Assigned to me

`Assigned to me` means the ticket is assigned to your user.

This is accountable work.

You are expected to open the ticket, understand the next action, and move it forward.

### Shared with me

`Shared with me` means the ticket has been shared with you for visibility.

This is not automatically the same as accountable ownership.

Use shared visibility to review, assist, advise, or prepare context.

Do not assume you own a shared ticket unless the ticket is also assigned to you or has been deliberately handed off to you.

### Partner acceptance review needed

`Partner acceptance review needed` means a Partner-originated ticket has been accepted by the Partner and Telectro must review the acceptance.

Use the `Review Partner acceptance` process for these tickets.

### Partner acceptance rework follow-up

`Partner acceptance rework follow-up` means the Partner requested rework on a Partner-originated ticket.

Telectro must complete the required correction or clarification, then request Partner acceptance again when ready.

### Partner work review needed

`Partner work review needed` means a Partner has submitted work done for Telectro-assigned Partner fulfilment work.

Use the `Review Partner completed work` process for these tickets.

### Partner work currently with Partner

`Partner work currently with Partner` means work is currently assigned to the Partner or has been sent back to the Partner for rework.

These tickets are usually monitored rather than worked directly by Telectro unless follow-up or intervention is required.

## Before you start

Before reviewing current work, confirm:

* you are logged in as the correct internal Telectro user;
* you are using the internal Telectro workspace or report area;
* you understand whether you are acting as Technician, Coordinator, or Supervisor/Ops;
* you know whether you are checking your own work or reviewing broader team/Partner work;
* you will open tickets before acting on them rather than relying only on report rows.

## Step-by-step process

### Step 1 — Open My Current Work

From the Telectro workspace, open `My Current Work`.

Depending on the workspace, it may appear as a shortcut such as:

```text
My Current Work
```

or:

```text
My Current Work - Outstanding Things
```

### Step 2 — Scan the bucket column

Start with the `Bucket` column.

The bucket tells you why the ticket appears in the report.

Typical buckets include:

```text
Assigned to me
Shared with me
Partner acceptance review needed
Partner acceptance rework follow-up
Partner work review needed
Partner work currently with Partner
```

Do not treat all buckets the same.

The bucket tells you what kind of action is expected.

### Step 3 — Read the next action

Check the `Next Action` column.

The next action gives the intended action for that bucket.

Examples include:

```text
Work assigned ticket
Review shared ticket
Review Partner acceptance and resolve, close, or review only
Complete Telectro rework, then request Partner acceptance again
Review Partner work and accept, request rework, resolve, or close
Monitor Partner progress or follow up where needed
```

Use this as the starting instruction, then open the ticket for full context.

### Step 4 — Review ticket priority and severity

Check:

* Priority;
* Severity;
* Status;
* Modified date.

Higher severity and recently changed tickets may need earlier attention.

Do not rely only on modified date.

A high-severity ticket with an older update may still need urgent attention.

### Step 5 — Check Account, Campus, and Service Area

Use the context columns to confirm what area the ticket belongs to.

Useful columns include:

* Account;
* Campus;
* Service Area;
* Request Source;
* Fulfilment Party.

This helps confirm whether the ticket belongs to your role, team, or review responsibility.

### Step 6 — Open the ticket

Open the HD Ticket from the report row.

Do not act from the report row alone.

Review the ticket detail before making changes.

### Step 7 — Confirm ownership or visibility

Inside the ticket, confirm whether you are:

* the assigned accountable owner;
* a shared observer/helper;
* a coordinator/supervisor reviewer;
* reviewing Partner acceptance;
* reviewing Partner completed work;
* monitoring Partner work still with the Partner.

If the ticket is only shared with you, do not take ownership informally.

Use the correct claim, release, handoff, or review process.

### Step 8 — Decide the next action

Choose the next action based on the bucket and ticket context.

#### Assigned to me

Open the ticket and continue the work.

Typical actions:

* add an internal note;
* send a Customer-visible update;
* attach or review evidence;
* resolve the Customer ticket if the outcome is confirmed;
* release the ticket if it is not yours to work;
* ask for controlled handoff if accountability must move to another named user.

#### Shared with me

Open the ticket and review the context.

Typical actions:

* read the ticket;
* add useful context if appropriate;
* assist the accountable owner;
* prepare for a possible handoff;
* avoid changing ownership unless instructed.

#### Partner acceptance review needed

Open the ticket and use the `Review Partner acceptance` process.

Typical outcomes:

* review only;
* resolve ticket;
* close ticket.

#### Partner acceptance rework follow-up

Open the ticket and review what the Partner requested.

Typical actions:

* complete Telectro correction or clarification;
* add internal notes where needed;
* request Partner acceptance again when the work is ready.

#### Partner work review needed

Open the ticket and use the `Review Partner completed work` process.

Typical outcomes:

* review only;
* accept work;
* request rework;
* resolve ticket;
* close ticket.

#### Partner work currently with Partner

Open the ticket only if follow-up or monitoring is needed.

Typical actions:

* check whether the Partner is still expected to act;
* follow up if the work is stale or blocked;
* avoid taking over Partner work unless Telectro has deliberately changed fulfilment.

### Step 9 — Record useful context

If you act on a ticket, leave useful context.

Use:

* internal notes for Telectro-only information;
* Customer-visible updates for Customer-facing progress;
* Partner review notes for Partner workflow outcomes;
* evidence attachment or review processes where needed.

Do not leave work in a state where the next person has to rediscover what happened.

### Step 10 — Refresh and verify

After acting on tickets, refresh `My Current Work`.

Confirm:

* completed or terminal tickets no longer appear;
* accepted/resolved/closed Partner review items moved out of review buckets;
* rework items moved to the correct waiting state;
* assigned tickets still needing work remain visible;
* shared tickets remain visible only when still relevant.

## Verification checklist

The review is complete when:

* `My Current Work` was opened.
* Buckets were reviewed.
* Next action labels were checked.
* High-priority or high-severity tickets were identified.
* Assigned tickets were opened and reviewed.
* Shared tickets were not mistaken for accountable ownership.
* Partner acceptance review items were routed to the correct review process.
* Partner work review items were routed to the correct review process.
* Partner work currently with Partner was monitored or followed up where needed.
* Any action taken was recorded clearly.
* The report was refreshed or rechecked after material updates.

## Common mistakes

### Mistake: Treating Shared with me as Assigned to me

Problem:

* The user may start acting as if they own the ticket.

Correct approach:

* Confirm assignment before taking ownership.
* Use controlled handoff when ownership must move deliberately.

### Mistake: Working from the report row only

Problem:

* The report row does not show the full ticket history or latest context.

Correct approach:

* Open the HD Ticket before acting.

### Mistake: Ignoring the Next Action column

Problem:

* Users may miss whether the ticket needs normal work, Partner acceptance review, Partner work review, or monitoring.

Correct approach:

* Read both `Bucket` and `Next Action`.

### Mistake: Confusing Partner acceptance with Partner work review

Problem:

* The wrong Partner review action may be used.

Correct approach:

* Use `Review Partner acceptance` for Partner-originated acceptance review.
* Use `Review Partner completed work` for Telectro-assigned Partner fulfilment work.

### Mistake: Leaving rework without clear context

Problem:

* The Partner or Telectro reviewer may not know what needs to happen next.

Correct approach:

* Use clear internal notes, review notes, or rework reasons.

### Mistake: Assuming missing tickets are lost

Problem:

* Terminal tickets do not appear in `My Current Work`.

Correct approach:

* Check the relevant history, resolved, closed, archived, or supervisor reports when looking for completed work.

## Do

* Open `My Current Work` at the start of the day.
* Review the bucket and next action columns.
* Open tickets before acting.
* Treat assigned work as accountable work.
* Treat shared work as visibility unless ownership is explicit.
* Use the correct Partner review process.
* Refresh the report after major actions.
* Escalate or hand off unclear ownership through the correct process.

## Do not

* Do not use `My Current Work` as the only supervisor dashboard.
* Do not treat shared tickets as automatically assigned to you.
* Do not act on Partner review items using the wrong process.
* Do not assume terminal tickets should appear in this report.
* Do not leave tickets with unclear next action.
* Do not use informal comments as a substitute for claim, release, handoff, or review actions.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Telectro workspace showing `My Current Work`.
2. `My Current Work` report open.
3. Bucket column showing `Assigned to me`.
4. Bucket column showing `Shared with me`.
5. Bucket column showing Partner acceptance review item, if available.
6. Bucket column showing Partner work review item, if available.
7. Next Action column.
8. Ticket opened from `My Current Work`.
9. Example assigned ticket.
10. Example shared ticket.
11. Example Partner review ticket.
12. Refreshed report after an item is resolved, closed, accepted, or moved to rework.

## Related docs

* `docs/user-guides/activity-process-guides.md#2-claim-release-and-handoff-ticket-ownership`
* `docs/user-guides/activity-process-guides.md#3-internal-notes-and-customer-visible-updates`
* `docs/user-guides/activity-process-guides.md#10-partner-responds-to-an-acceptance-request`
* `docs/user-guides/activity-process-guides.md#12-review-partner-acceptance`
* `docs/user-guides/activity-process-guides.md#13-review-partner-completed-work`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/service-coverage-model.md`

# 15. Check unclaimed tickets

## Purpose

Use this process to check tickets that are in the true pool or otherwise unclaimed, and decide what should happen next.

Unclaimed work is operational risk.

A ticket with no accountable owner can be missed, delayed, or left without a clear next action. The purpose of this process is to make unclaimed work visible and move it into the correct ownership path.

This guide does not replace the `Claim`, `Release`, or `Controlled Handoff` process.

It explains when and how to review unclaimed work, and which ownership action to use after review.

## Audience

Primary users:

* Telectro Coordinator
* Telectro Ops / Supervisor

Secondary users:

* Telectro Technician

Technicians may use the unclaimed view to find work they can claim.

Coordinators and supervisors use it to monitor the pool, protect service flow, and intervene when tickets should not remain unclaimed.

Partner users do not use this internal process.

Customer portal users do not use this internal process.

## When to use this process

Use this process when:

* starting the day;
* checking the Coordinator or Ops workspace;
* monitoring queue health;
* checking whether tickets are sitting without an accountable owner;
* reviewing the unclaimed pool after tickets were released;
* checking for stale unclaimed work;
* deciding whether a ticket should be claimed, handed off, escalated, or left in the pool;
* preparing for a supervisor/coordinator daily review.

Typical examples:

* “Are there any tickets nobody owns?”
* “Which tickets are still in the pool?”
* “Has anything been unclaimed for too long?”
* “Did a released ticket get picked up?”
* “Should this be claimed by a technician or handed off to a named owner?”
* “Is the unclaimed queue hiding urgent work?”

## When not to use this process

Do not use this process when:

* you are reviewing your own assigned work;
* you are reviewing tickets shared with you;
* you are reviewing Partner acceptance;
* you are reviewing Partner completed work;
* you need SLA-first-response oversight;
* you need full aging and at-risk governance across all owned tickets.

Use `Review current work` for your own assigned/shared/review buckets.

Use `Review Partner acceptance` for Partner acceptance review.

Use `Review Partner completed work` for Partner work completion review.

Use aging, SLA, or supervisor reports for broader governance.

## Important concepts

### True pool / unclaimed ticket

A true pool ticket has no accountable individual owner.

In the pilot assignment model, true pool means:

```text
HD Ticket._assign = []
No open assignment ToDo
```

Some reports and quick lists may also treat blank `_assign` as unclaimed.

### Unclaimed is not the same as shared

An unclaimed ticket has no accountable owner.

A shared ticket may be visible to someone, but still has a different accountability model.

Do not confuse visibility with ownership.

### Unclaimed is not the same as low priority

Unclaimed does not mean unimportant.

An unclaimed ticket can be urgent, stale, or Customer-impacting.

### Claim

`Claim` is used when a user takes ownership of a true pool ticket.

Use Claim when the person claiming can actually take the next meaningful action.

### Release

`Release` returns a ticket from its current owner to the true pool with a reason.

A released ticket should be checked later to make sure it is not abandoned.

### Controlled Handoff

`Controlled Handoff` is the coordinator/supervisor action used when the next accountable owner is known.

Use Controlled Handoff instead of leaving the ticket in the pool when a specific person should own it.

## Before you start

Before checking unclaimed tickets, confirm:

* you are logged in as a Telectro internal user;
* you are using the correct workspace or report;
* you understand whether you are acting as Technician, Coordinator, or Supervisor/Ops;
* you know whether your goal is to claim work, monitor work, or intervene;
* you will open tickets before deciding ownership.

## Step-by-step process

### Step 1 — Open the unclaimed view

Open the relevant Telectro workspace.

Depending on your role, unclaimed work may appear through:

```text
Unclaimed Active Tickets
Unclaimed more than 1 Day
Unclaimed Over 1 Day
Unclaimed (War Room)
TELECTRO Unclaimed War Room
```

Coordinator and Ops workspaces may show unclaimed work through quick lists, number cards, or top-4 stale/unclaimed widgets.

Technician workspaces may include an `Unclaimed (War Room)` shortcut.

### Step 2 — Check the unclaimed count or list

Review the unclaimed count, quick list, or report.

Look for:

* how many tickets are currently unclaimed;
* whether any unclaimed tickets are older than expected;
* whether any high-priority or high-severity tickets are unclaimed;
* whether the same tickets remain unclaimed across checks.

A non-zero unclaimed count is not automatically wrong, but it needs attention.

### Step 3 — Open each important ticket

Open the ticket before deciding what to do.

Do not decide only from the list row.

Check:

* subject;
* status;
* priority;
* severity;
* Account / Customer context;
* campus or site context;
* service area;
* request source;
* fulfilment party;
* latest activity;
* why the ticket appears unclaimed.

### Step 4 — Confirm it is active work

Confirm the ticket is not terminal.

Unclaimed monitoring is for active tickets, not completed history.

Terminal statuses include:

```text
Resolved
Closed
Archived
```

If the ticket is terminal, it should not normally need unclaimed ownership intervention.

### Step 5 — Decide why it is unclaimed

Decide which case applies.

#### Case A — Normal pool work waiting to be claimed

The ticket is genuinely available for the correct technician or team member to claim.

This may be acceptable for a short period.

Next action:

* leave it visible in the pool if it is fresh and safe to wait;
* ask the correct team to claim it if needed;
* claim it yourself only if you can own the next action.

#### Case B — Ticket needs a known owner

The correct next owner is already clear.

Next action:

* use `Controlled Handoff` if you are Coordinator/Ops/Supervisor;
* include a clear reason;
* verify the ticket moves to the named owner.

Do not leave the ticket in the pool if the next accountable owner is already known.

#### Case C — Ticket needs routing or triage

The ticket is unclaimed because the service area, fault type, location, or next action is unclear.

Next action:

* add an internal note with the uncertainty;
* correct obvious missing routing/context if your role allows it;
* hand off to a coordinator/supervisor if a named owner is needed;
* keep it visible until the routing decision is made.

#### Case D — Ticket was released back to the pool

The ticket was previously owned and then released.

Next action:

* read the release reason;
* check whether the reason is clear;
* decide whether it should remain in the pool, be claimed, or be handed off;
* intervene if the reason is vague or the ticket is urgent.

#### Case E — Ticket is stale or risky

The ticket has been unclaimed too long, or urgency makes waiting unsafe.

Next action:

* open the ticket;
* add internal context if needed;
* use Controlled Handoff to assign a known accountable owner; or
* escalate through the coordinator/supervisor process.

Do not leave stale urgent work in the pool without action.

### Step 6 — Choose the correct ownership action

After reviewing the ticket, choose the correct path.

#### Option A — Leave in pool

Leave the ticket in the pool only when:

* it is genuinely pool work;
* it is fresh enough to wait;
* no specific next owner is known;
* it is visible in the correct unclaimed queue;
* there is no urgent risk.

#### Option B — Claim

Use `Claim` when:

* you are the correct person to own the ticket;
* you can take the next meaningful action;
* the ticket is actually in the true pool.

After claiming, verify it appears in your current/assigned work.

#### Option C — Controlled Handoff

Use `Controlled Handoff` when:

* a specific next owner is known;
* coordinator/supervisor intervention is required;
* the ticket should not remain in the pool;
* a stale or risky ticket needs accountable ownership.

Add a clear handoff reason.

#### Option D — Add internal context first

Add an internal note before claim or handoff when the next owner needs context.

Examples:

```text
Unclaimed after release. Appears to be Internet Connection, not PABX. Coordinator to confirm service area before handoff.
```

```text
Unclaimed > 1 day. Customer location is unclear. Please confirm fault point before dispatch.
```

```text
Released back to pool because Alfa is unavailable for site visit. Needs coordinator reassignment.
```

### Step 7 — Verify the result

After taking action, refresh the unclaimed view.

Confirm:

* the ticket no longer appears as unclaimed if it was claimed or handed off;
* the ticket appears in the new owner’s current work if assigned;
* the ticket remains visible in the pool only if that was deliberate;
* any internal note or handoff reason is visible;
* no duplicate or informal multi-owner state was created.

## Verification checklist

The unclaimed check is complete when:

* The relevant unclaimed view was opened.
* Unclaimed count/list was checked.
* Important unclaimed tickets were opened.
* Ticket priority, severity, status, account, site, service area, and latest activity were reviewed where relevant.
* Stale or risky unclaimed tickets were identified.
* Each reviewed ticket has a clear next action:

  * remain in pool;
  * claim;
  * controlled handoff;
  * internal note / triage;
  * escalation.
* Claimed or handed-off tickets no longer appear as unclaimed.
* Handoff or internal context was recorded where needed.
* No unclaimed urgent ticket was left without a deliberate decision.

## Common mistakes

### Mistake: Treating unclaimed as harmless

Problem:

* Tickets can sit without an accountable owner.

Correct approach:

* Review unclaimed work regularly and treat stale unclaimed items as operational risk.

### Mistake: Claiming work you cannot action

Problem:

* The ticket leaves the pool but still does not move forward.

Correct approach:

* Claim only when you can take the next meaningful action.
* Use Controlled Handoff or coordinator review when the correct owner is someone else.

### Mistake: Leaving a known-owner ticket in the pool

Problem:

* The ticket waits unnecessarily even though the correct owner is clear.

Correct approach:

* Use Controlled Handoff when the next accountable owner is known.

### Mistake: Ignoring release reasons

Problem:

* Released tickets may contain important routing or blocker information.

Correct approach:

* Read the release reason before deciding what to do next.

### Mistake: Acting from the quick list only

Problem:

* The list row may not show enough context to make a safe decision.

Correct approach:

* Open the ticket before claiming, handing off, or escalating.

### Mistake: Confusing unclaimed with shared

Problem:

* Shared visibility may be mistaken for pool work.

Correct approach:

* Check actual assignment/ownership before deciding.

### Mistake: Using generic Assign/Unassign

Problem:

* Generic assignment can create states that do not match the pilot ownership model.

Correct approach:

* Use Claim, Release, and Controlled Handoff as the normal pilot ownership actions.

## Do

* Check unclaimed work regularly.
* Open important unclaimed tickets before acting.
* Treat stale unclaimed tickets as risk.
* Read release reasons.
* Claim only work you can own.
* Use Controlled Handoff when the next owner is known.
* Add internal context when routing or blockers are unclear.
* Refresh the unclaimed view after acting.
* Verify that ownership changed as expected.

## Do not

* Do not ignore the unclaimed pool.
* Do not claim work only to remove it from the list.
* Do not leave urgent known-owner work in the pool.
* Do not skip release reasons.
* Do not confuse shared visibility with unclaimed work.
* Do not use generic Assign/Unassign as the normal pilot path.
* Do not leave stale unclaimed work without a deliberate decision.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Coordinator or Ops workspace showing unclaimed count / quick list.
2. `Unclaimed Active Tickets` quick list.
3. `Unclaimed more than 1 Day` widget or card.
4. `Unclaimed Over 1 Day` report.
5. Tech workspace `Unclaimed (War Room)` shortcut.
6. `TELECTRO Unclaimed War Room` report.
7. Example unclaimed ticket before review.
8. Claim action on an unclaimed ticket.
9. Controlled Handoff action for a known-owner unclaimed ticket.
10. Internal note explaining routing uncertainty.
11. Ticket after Claim showing assigned owner.
12. Ticket after Controlled Handoff showing named accountable owner.
13. Refreshed unclaimed view showing ticket removed from the pool.

## Related docs

* `docs/user-guides/activity-process-guides.md#2-claim-release-and-handoff-ticket-ownership`
* `docs/user-guides/activity-process-guides.md#14-review-current-work`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/ticket-assignment-contract.md`
* `docs/runbooks/supervisor-operating-model.md`

# 16. Check aging and at-risk tickets

## Purpose

Use this process to review active owned tickets that may be aging, stale, or at risk of drifting without visible progress.

`Aging and At-Risk Tickets` is a supervisor/coordinator attention list. It helps Telectro identify assigned tickets that may need intervention, follow-up, coaching, handoff, or a clearer next action.

This guide focuses on aging and stale owned work.

It does not replace:

* `Review current work`;
* `Check unclaimed tickets`;
* `Check first-response risk`;
* Customer SLA breach oversight;
* normal ticket execution by technicians.

## Audience

Primary users:

* Telectro Coordinator
* Telectro Ops / Supervisor

Secondary users:

* Telectro Technician, when asked to review their own aging work

Partner users do not use this internal report.

Customer portal users do not use this internal report.

## When to use this process

Use this process when:

* starting a supervisor/coordinator review;
* checking whether active owned tickets are drifting;
* checking whether assigned work has not been updated recently;
* reviewing tickets that may need intervention;
* checking workload health after busy periods;
* preparing for a team follow-up;
* checking whether a ticket needs a Customer-visible progress update;
* deciding whether ownership should stay as-is or move through Controlled Handoff.

Typical examples:

* “Which assigned tickets have not moved recently?”
* “Which tickets are at risk because nothing visible has happened?”
* “Which technician has aging work that needs a check-in?”
* “Which ticket needs a clearer next action?”
* “Should this ticket stay with the current owner?”
* “Do we need to update the Customer before this becomes a service issue?”

## When not to use this process

Do not use this process when:

* you are checking tickets that have no accountable owner;
* you are checking your own normal daily working list;
* you are checking Customer first-response risk;
* you are checking formal Customer SLA breach reports;
* you are reviewing Partner acceptance;
* you are reviewing Partner completed work.

Use:

* `Check unclaimed tickets` for true pool / unclaimed work;
* `Review current work` for personal assigned/shared/review work;
* `Check first-response risk` for Customer first-response risk;
* `Review Partner acceptance` for Partner acceptance review;
* `Review Partner completed work` for Partner work completion review.

## Important concepts

### Aging ticket

An aging ticket is an active ticket that has not been modified recently.

In the current pilot report, aging is based on the ticket `modified` timestamp.

This means the report is asking:

```text
How long has it been since this ticket last changed?
```

It is not a full SLA calculation.

### Owned work

The aging report focuses on owned work.

A ticket appears because it has an open assignment `ToDo` linked to a technician or owner.

This is different from unclaimed work.

Unclaimed tickets should be reviewed through the unclaimed process.

### Stale hours

`Stale Hours` shows how many hours have passed since the ticket was last modified.

Higher stale hours mean the ticket may need earlier supervisor attention.

### Attention band

`Attention Band` gives a practical intervention signal.

Current pilot bands include:

```text
At Risk  = 24 hours or more since last modification
Critical = 72 hours or more since last modification
```

The report is currently filtered to show tickets at 24 hours or more, so it is mainly an `At Risk` and `Critical` attention list.

### At risk is not the same as SLA breach

`At Risk` means the ticket may need attention because it has not moved recently.

It does not automatically mean the Customer SLA has breached.

Use Customer SLA / first-response reports for formal first-response or SLA timing checks.

### Supervisor intervention

Supervisor intervention does not always mean taking the ticket away.

Intervention may mean:

* asking the owner for an update;
* asking for an internal note;
* asking for a Customer-visible progress update;
* confirming the ticket is waiting on something legitimate;
* using Controlled Handoff if ownership is wrong or the owner is unavailable;
* escalating a blocker.

## Before you start

Before checking aging and at-risk tickets, confirm:

* you are logged in as the correct Telectro internal user;
* you are using the Coordinator or Ops/Supervisor workspace;
* you understand that this is an attention list, not a performance scoreboard;
* you will open tickets before deciding what action to take;
* you will not bypass controlled ownership flows.

## Step-by-step process

### Step 1 — Open the aging report

Open the relevant Coordinator or Ops/Supervisor workspace.

Open:

```text
Aging and At-Risk Tickets
```

The workspace shortcut may appear as:

```text
Aging / At-Risk Tickets
```

### Step 2 — Review the oldest or most stale tickets first

Start at the top of the report.

The report is intended to show the stalest items first.

Review:

* Ticket;
* Subject;
* Technician;
* Status;
* Stale Hours;
* Attention Band;
* Modified.

### Step 3 — Separate Critical from At Risk

Use the `Attention Band` column.

#### Critical

`Critical` means the ticket has not been modified for 72 hours or more.

These tickets should normally be opened and reviewed first.

#### At Risk

`At Risk` means the ticket has not been modified for 24 hours or more.

These tickets should be reviewed to confirm that they have a valid next action.

### Step 4 — Open the ticket

Open the HD Ticket before deciding what to do.

Do not act from the report row alone.

Check:

* latest activity;
* current owner;
* current status;
* Customer-visible updates;
* internal notes;
* assignment history if relevant;
* whether the work is waiting on a Customer, Partner, supplier, site visit, equipment, or internal decision;
* whether the next action is clear.

### Step 5 — Decide why the ticket is aging

Decide which case applies.

#### Case A — Legitimately waiting

The ticket is waiting for something real and documented.

Examples:

* waiting for Customer confirmation;
* waiting for site access;
* waiting for parts or supplier input;
* waiting for Partner action;
* waiting for a scheduled visit.

Next action:

* confirm the waiting reason is clearly documented;
* add an internal note if it is not clear;
* send a Customer-visible update if the Customer needs progress visibility;
* leave ownership unchanged if the current owner remains correct.

#### Case B — Work is active but not documented

The owner may be working on the issue, but the ticket does not show enough recent context.

Next action:

* ask the owner to add an internal note or Customer-visible update;
* check whether the Customer needs an update;
* avoid changing ownership unless the owner cannot continue.

#### Case C — Owner is wrong or unavailable

The current owner is not the right person to continue, or is unavailable.

Next action:

* use Controlled Handoff if a specific new owner is known;
* include a clear handoff reason;
* confirm the ticket moves to the new accountable owner.

Do not use generic Assign/Unassign.

#### Case D — Ticket is blocked

The ticket is stuck because of missing information, unclear decision, missing evidence, site access, Partner delay, supplier delay, or internal dependency.

Next action:

* add an internal note describing the blocker;
* escalate to the coordinator/supervisor if needed;
* hand off only if the accountable owner should change;
* send Customer-visible progress where appropriate.

#### Case E — Ticket should be resolved or closed

The ticket appears to be complete, but still remains active.

Next action:

* confirm the work outcome;
* check whether Customer-visible resolution wording is ready;
* attach or select completion evidence if required;
* use the normal resolution/closure process.

### Step 6 — Decide the intervention action

Choose the lightest effective intervention.

#### Option A — No ownership change

Use this when:

* the current owner is still correct;
* the next action is clear;
* the ticket is waiting for a valid reason;
* the ticket has adequate internal or Customer-visible context.

Add a note if the context is not clear enough.

#### Option B — Ask for update

Use this when:

* the owner is still correct;
* work may be happening;
* the ticket has not been updated recently;
* the Customer or supervisor needs clearer visibility.

Ask for either:

* an internal note; or
* a Customer-visible update, where appropriate.

#### Option C — Controlled Handoff

Use this when:

* the current owner is wrong;
* the current owner is unavailable;
* a specific new accountable owner is known;
* the ticket should not remain with the current owner.

Record a clear reason.

#### Option D — Escalate blocker

Use this when:

* the blocker cannot be resolved by the owner alone;
* the Customer or service outcome is at risk;
* a supervisor/coordinator decision is required;
* the ticket is critical and still not moving.

#### Option E — Resolve through the normal resolution process

Use this when:

* the work appears complete;
* the Customer-facing outcome is known;
* the ticket has enough evidence/context to resolve safely.

Do not leave completed work aging in active status.

### Step 7 — Add context where needed

If you review or intervene, leave a clear trace.

Use internal notes for Telectro-only context.

Examples:

```text
Supervisor review: ticket is at risk because no update has been recorded in 28 hours. Alfa still owns the next action and will update after site visit.
```

```text
Coordinator review: owner unavailable. Controlled Handoff to Bravo for site follow-up.
```

```text
Supervisor note: ticket is waiting on Customer access confirmation. Customer-visible update sent.
```

```text
Coordinator review: issue appears complete. Owner to prepare Customer-visible resolution update and evidence.
```

### Step 8 — Refresh the report

After acting, refresh `Aging and At-Risk Tickets`.

Confirm:

* the ticket still appears only if it remains stale and active;
* the owner changed if Controlled Handoff was used;
* the ticket no longer appears if it was resolved or archived;
* the latest activity now explains the next action;
* critical tickets have a clear intervention path.

## Verification checklist

The aging and at-risk check is complete when:

* `Aging and At-Risk Tickets` was opened.
* Critical tickets were reviewed first.
* At Risk tickets were reviewed for clear next action.
* Each important ticket was opened before deciding action.
* Current owner and latest activity were checked.
* Waiting reasons were confirmed or documented.
* Tickets needing updates were identified.
* Tickets needing Customer-visible progress were identified.
* Wrong-owner or unavailable-owner tickets were handled through Controlled Handoff.
* Blocked tickets were escalated or documented.
* Completed tickets were routed toward resolution/closure.
* The report was refreshed after material actions.

## Common mistakes

### Mistake: Treating the report as a performance scoreboard

Problem:

* The report can be misused to blame technicians instead of identifying operational risk.

Correct approach:

* Use it as an attention and intervention tool.

### Mistake: Assuming At Risk means SLA breach

Problem:

* At Risk is based on stale activity, not automatically a formal SLA breach.

Correct approach:

* Use SLA and Customer first-response reports for SLA timing checks.

### Mistake: Changing ownership without context

Problem:

* The next owner may not understand why the ticket was moved.

Correct approach:

* Use Controlled Handoff with a clear reason.

### Mistake: Ignoring a legitimate waiting reason

Problem:

* A ticket may be aging because it is waiting on Customer, Partner, supplier, or site access.

Correct approach:

* Confirm the waiting reason is documented and visible to the right audience.

### Mistake: Leaving completed work active

Problem:

* Completed tickets continue to age and clutter active risk views.

Correct approach:

* Use the normal resolution/closure process when the outcome is confirmed.

### Mistake: Keeping the Customer in the dark

Problem:

* A ticket may be internally understood but Customer-facing progress is unclear.

Correct approach:

* Send a Customer-visible update when the Customer needs progress visibility.

## Do

* Review Critical items first.
* Open tickets before acting.
* Treat aging as an intervention signal.
* Check whether the current owner is still correct.
* Look for clear next action.
* Add internal notes when context is missing.
* Send Customer-visible progress when appropriate.
* Use Controlled Handoff when ownership must change.
* Resolve completed work through the normal resolution process.
* Refresh the report after interventions.

## Do not

* Do not treat aging as automatic technician fault.
* Do not assume At Risk means SLA breach.
* Do not bypass Controlled Handoff.
* Do not leave stale tickets without a documented next action.
* Do not confuse aging review with first-response risk review.
* Do not leave completed tickets active just because nobody closed them.
* Do not expose internal SLA/governance detail in Customer-visible updates.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Coordinator or Ops workspace showing `Aging / At-Risk Tickets`.
2. `Aging and At-Risk Tickets` report open.
3. Ticket row showing `Stale Hours`.
4. Ticket row showing `Attention Band`.
5. Example `At Risk` ticket.
6. Example `Critical` ticket, if available.
7. Ticket opened from the aging report.
8. Latest activity/internal notes showing missing or present next action.
9. Controlled Handoff action where ownership must change.
10. Internal note recording supervisor/coordinator review.
11. Customer-visible update where progress visibility is needed.
12. Ticket resolved or updated after review.
13. Refreshed aging report after intervention.

## Related docs

* `docs/user-guides/activity-process-guides.md#2-claim-release-and-handoff-ticket-ownership`
* `docs/user-guides/activity-process-guides.md#3-internal-notes-and-customer-visible-updates`
* `docs/user-guides/activity-process-guides.md#4-resolve-a-customer-ticket`
* `docs/user-guides/activity-process-guides.md#14-review-current-work`
* `docs/user-guides/activity-process-guides.md#15-check-unclaimed-tickets`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/supervisor-operating-model.md`
* `docs/runbooks/sla-and-supervisor-risk-signals.md`

# 17. Check first-response risk

## Purpose

Use this process to identify Customer-originated tickets that still need a first Customer-visible response, and act before the first-response target is missed.

First-response risk is Customer-facing risk.

A ticket may be assigned, routed, or internally understood, but the Customer still needs a visible acknowledgement or progress response. This process helps Telectro protect that first visible response.

This guide focuses on first-response prevention.

It does not replace:

* `Review current work`;
* `Check unclaimed tickets`;
* `Check aging and at-risk tickets`;
* `Internal notes and Customer-visible updates`;
* formal Customer SLA breach review;
* normal ticket execution by technicians.

## Audience

Primary users:

* Telectro Coordinator
* Telectro Ops / Supervisor

Secondary users:

* Telectro Technician, when asked to respond on a Customer ticket

Partner users do not use this internal report.

Customer portal users do not use this internal report.

## When to use this process

Use this process when:

* starting a Coordinator or Supervisor check;
* checking Customer tickets that still need first response;
* checking first-response risk before a target is missed;
* deciding whether a Customer-visible update must be sent;
* reviewing tickets due within the next hour;
* reviewing tickets due today;
* checking whether already-missed first responses need recovery communication;
* protecting Customer confidence during intake and triage.

Typical examples:

* “Which Customer tickets still need first response?”
* “Which ticket is due in the next 15 minutes?”
* “Which tickets need a Customer-visible acknowledgement today?”
* “Has this Customer ticket received a first visible response yet?”
* “Which first-response target has already been missed?”
* “Do we need a Customer-visible update before more internal work happens?”

## When not to use this process

Do not use this process when:

* the ticket is not Customer-originated;
* the ticket already has a first response;
* you are reviewing general aging or stale work;
* you are reviewing unclaimed pool work;
* you are reviewing Partner acceptance or Partner work;
* you are checking resolution SLA rather than first response;
* you are writing an internal note only.

Use:

* `Check aging and at-risk tickets` for stale owned work;
* `Check unclaimed tickets` for pool work;
* `Review current work` for personal assigned/shared/review work;
* `Internal notes and Customer-visible updates` to decide whether a note is internal or Customer-visible;
* `Customer SLA Breach Oversight` for broader first-response and resolution breach follow-up.

## Important concepts

### First response

A first response is the first meaningful Customer-visible response after the Customer has logged or raised the ticket.

It is not the same as internal triage.

It is not satisfied by a Telectro-only internal note.

### Customer-visible response

A Customer-visible response should be written so the Customer can understand what Telectro has received, what is happening next, or what information is needed.

It should avoid internal assignment, routing, SLA, governance, or debugging detail.

### `response_by`

`response_by` is the system-derived first-response target datetime on the HD Ticket.

The first-response risk reports use this field to decide whether the first response is still saveable or already missed.

### `first_responded_on`

`first_responded_on` indicates whether the ticket has already received a first response according to the Helpdesk/SLA lifecycle.

The prevention report focuses on tickets where `first_responded_on` is still empty.

### Prevention vs recovery

There are two different states:

```text
Prevention = response_by is still in the future and first response can still be saved.
Recovery   = response_by is already in the past and first response has been missed.
```

Use `Customer Ticket Oversight` for prevention.

Use `First Response Missed` or `Customer SLA Breach Oversight` for already-missed first responses.

### First-response risk bands

The current Customer first-response prevention view uses practical risk bands such as:

```text
Due < 15m
Due < 1h
Due today
OK
```

The most urgent saveable tickets should be reviewed first.

## Before you start

Before checking first-response risk, confirm:

* you are logged in as a Telectro internal user with Coordinator/Ops/Supervisor oversight access;
* you understand this is a Customer-facing response process;
* you will send or prompt a Customer-visible response when needed;
* you will not treat an internal note as Customer first response;
* you will not expose internal SLA/governance detail to the Customer.

## Step-by-step process

### Step 1 — Open Customer Ticket Oversight

Open the Coordinator or Ops/Supervisor workspace.

Open:

```text
Customer Ticket Oversight
```

This is the primary prevention report for Customer first-response risk.

It is intended to show Customer-originated tickets where:

* the ticket is active;
* the first response has not yet been recorded;
* the first-response target exists;
* the first-response target is still in the future.

### Step 2 — Review the First Response Risk column

Start with the `First Response Risk` column.

Review the most urgent rows first.

Typical values include:

```text
Due < 15m
Due < 1h
Due today
OK
```

Prioritise:

1. `Due < 15m`
2. `Due < 1h`
3. `Due today`
4. `OK`

### Step 3 — Check Time Left and First Response By

Review:

* `Time Left`;
* `First Response By`;
* Ticket;
* Subject;
* Status;
* Account;
* Campus;
* Service Area;
* Agent Group;
* Assigned To;
* Age;
* Modified.

This tells you how urgent the Customer-visible response is and who may already own the ticket.

### Step 4 — Open the ticket

Open the HD Ticket before acting.

Do not rely only on the report row.

Check:

* Customer request;
* latest activity;
* whether a Customer-visible response already exists;
* whether only internal notes exist;
* who currently owns the ticket;
* whether the issue is triaged enough for a meaningful Customer response;
* whether more information is needed from the Customer.

### Step 5 — Decide what the Customer needs now

Choose the Customer-facing response type.

#### Case A — Simple acknowledgement needed

The ticket has been received, but no Customer-visible acknowledgement has been sent.

Next action:

* send a short Customer-visible update acknowledging receipt;
* state that Telectro is reviewing or routing the request;
* avoid internal details.

Example:

```text
We have received your support request and are reviewing it. We will update you once the next action is confirmed.
```

#### Case B — Triage is already clear

The ticket has enough information to tell the Customer what is happening next.

Next action:

* send a Customer-visible update with the next step;
* keep wording plain and Customer-safe.

Example:

```text
We have reviewed the request and are assigning it for follow-up. The team will check the affected service area and update you with the next outcome.
```

#### Case C — Customer information is missing

The ticket cannot move safely without more Customer information.

Next action:

* send a Customer-visible request for the missing information;
* ask a specific question;
* avoid vague wording.

Example:

```text
We have received the request. Please confirm which fault point or area is affected so that we can route this correctly.
```

#### Case D — Technician owns the ticket but no response is visible

The ticket may be assigned, but the Customer still has no first visible response.

Next action:

* ask the owner to send a Customer-visible update immediately; or
* send the Customer-visible update yourself if your role and process allow it;
* add internal context only if needed.

Do not assume assignment alone satisfies first response.

#### Case E — The target is almost missed

The ticket is `Due < 15m` or `Due < 1h`.

Next action:

* open immediately;
* send or prompt a Customer-visible response;
* keep the response safe and short if full triage is not complete;
* record internal context after the Customer-visible response if needed.

### Step 6 — Send the Customer-visible response

Use the Customer-visible update process.

A good first response should:

* acknowledge the request;
* be understandable to the Customer;
* give a next step where possible;
* ask for missing information if needed;
* avoid internal assignment/routing/SLA language.

Do not use an internal note as the first Customer response.

### Step 7 — Verify the ticket dropped from prevention risk

After sending or confirming the response, refresh `Customer Ticket Oversight`.

Confirm:

* the ticket no longer appears in the first-response prevention list; or
* the ticket now shows that first response has been recorded; or
* if it still appears, investigate whether the response was truly Customer-visible.

If the ticket remains listed after a Customer-visible response, check the ticket timeline and Helpdesk response fields before assuming the process succeeded.

### Step 8 — Check already-missed first responses

After prevention work, review already-missed first responses if needed.

Open:

```text
First Response Missed
```

or:

```text
Customer SLA Breach Oversight
```

Use these reports for tickets where the first-response target has already passed.

For already-missed first responses:

* open the ticket;
* confirm whether a Customer-visible response is still missing;
* send a recovery Customer-visible update if needed;
* add an internal note acknowledging the missed target and next action;
* escalate if the miss indicates a process or queue problem.

Do not treat missed first response as “no action needed” just because prevention failed.

## Verification checklist

The first-response risk check is complete when:

* `Customer Ticket Oversight` was opened.
* `Due < 15m` items were reviewed first.
* `Due < 1h` items were reviewed next.
* `Due today` items were reviewed.
* Each important ticket was opened before action.
* The latest Customer-visible activity was checked.
* Internal-only notes were not mistaken for Customer response.
* Tickets needing immediate Customer-visible acknowledgement were identified.
* Tickets needing missing Customer information were identified.
* Customer-visible updates were sent or prompted where needed.
* The report was refreshed after responses.
* Remaining rows have a clear reason and next action.
* Already-missed first responses were checked through the missed/breach view where needed.

## Common mistakes

### Mistake: Treating assignment as first response

Problem:

* The ticket may be assigned internally, but the Customer still has no visible acknowledgement.

Correct approach:

* Send a Customer-visible response.

### Mistake: Using an internal note as Customer response

Problem:

* Internal notes are not visible to the Customer.

Correct approach:

* Use a Customer-visible update for first response.

### Mistake: Waiting for perfect triage

Problem:

* The first-response target can be missed while the team waits for full technical clarity.

Correct approach:

* Send a safe acknowledgement or request for missing information.

### Mistake: Exposing internal SLA or routing detail

Problem:

* The Customer sees internal process language that may confuse or undermine confidence.

Correct approach:

* Keep Customer-visible wording focused on receipt, next step, and needed information.

### Mistake: Ignoring already-missed first responses

Problem:

* Once prevention fails, the Customer may still need a response.

Correct approach:

* Use `First Response Missed` or `Customer SLA Breach Oversight` for recovery follow-up.

### Mistake: Assuming the report updated without checking

Problem:

* The report may still show the ticket if the response was not recorded as Customer-visible first response.

Correct approach:

* Refresh the report and verify the ticket/timeline.

## Do

* Check Customer first-response risk regularly.
* Prioritise `Due < 15m`.
* Open tickets before acting.
* Send Customer-visible acknowledgements where needed.
* Ask clear Customer questions when information is missing.
* Keep first responses short, clear, and Customer-safe.
* Use internal notes only for Telectro-only context.
* Refresh the report after action.
* Review already-missed first responses separately.

## Do not

* Do not wait for full technical diagnosis before acknowledging receipt.
* Do not treat internal notes as Customer first response.
* Do not expose internal SLA, routing, assignment, or governance detail.
* Do not ignore `Due < 15m` rows.
* Do not assume assigned tickets have been responded to.
* Do not treat already-missed first responses as irrelevant.
* Do not confuse first-response risk with general aging or resolution risk.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Ops or Coordinator workspace showing Customer SLA / oversight area.
2. `Customer Ticket Oversight` report open.
3. `First Response Risk` column.
4. `Due < 15m` row, if available.
5. `Due < 1h` row, if available.
6. `First Response By` and `Time Left` columns.
7. Ticket opened from Customer Ticket Oversight.
8. Ticket activity showing no Customer-visible response yet.
9. Customer-visible update dialog.
10. Example safe first-response wording.
11. Refreshed Customer Ticket Oversight after response.
12. `First Response Missed` report.
13. `Customer SLA Breach Oversight` row showing first-response breach, if available.

## Related docs

* `docs/user-guides/activity-process-guides.md#3-internal-notes-and-customer-visible-updates`
* `docs/user-guides/activity-process-guides.md#14-review-current-work`
* `docs/user-guides/activity-process-guides.md#15-check-unclaimed-tickets`
* `docs/user-guides/activity-process-guides.md#16-check-aging-and-at-risk-tickets`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/sla-and-supervisor-risk-signals.md`
* `docs/runbooks/supervisor-operating-model.md`

# 18. Intervene on a stale or blocked ticket

## Purpose

Use this process when a ticket has been identified as stale, blocked, risky, or unclear, and Telectro needs to decide what intervention is required.

This guide starts after a ticket has already been found through one of the normal monitoring paths, such as:

* `Review current work`;
* `Check unclaimed tickets`;
* `Check aging and at-risk tickets`;
* `Check first-response risk`;
* Supervisor / Coordinator reports;
* direct escalation from a technician;
* Customer follow-up;
* Partner follow-up.

The purpose is to turn “this ticket looks stuck” into a clear next action.

This guide does not replace:

* normal technician ownership;
* Claim, Release, and Controlled Handoff;
* internal note and Customer-visible update guidance;
* Partner acceptance or Partner work review;
* Customer resolution;
* SLA breach reporting.

## Audience

Primary users:

* Telectro Coordinator
* Telectro Ops / Supervisor

Secondary users:

* Telectro Technician, when escalating or explaining a blocker

Partner users do not use this internal intervention process.

Customer portal users do not use this internal intervention process.

## When to use this process

Use this process when:

* a ticket is aging without visible progress;
* a ticket is blocked by missing information, site access, equipment, supplier input, Partner action, or internal decision;
* the current owner is unclear, unavailable, or no longer the right owner;
* a Customer has followed up and the ticket still lacks a clear next action;
* an at-risk ticket needs a supervisor/coordinator decision;
* a first-response or Customer-visible update risk has been identified;
* a Partner-related ticket is waiting on Telectro review or rework;
* a ticket appears complete but is still active;
* someone says “this ticket is stuck” but the ticket does not clearly explain why.

Typical examples:

* “This ticket has not moved in two days.”
* “The Customer is asking for an update.”
* “The technician is waiting on site access but it is not documented.”
* “The owner is on leave.”
* “This should probably go to another technician.”
* “The Partner has completed work but Telectro has not reviewed it.”
* “The work looks done but the ticket is still open.”
* “The ticket is unclaimed and looks urgent.”
* “The ticket is assigned, but there is no visible next action.”

## When not to use this process

Do not use this process when:

* the ticket has a clear owner, clear next action, and recent progress;
* you only need to work your own assigned ticket normally;
* you only need to add a routine Customer-visible progress update;
* you only need to resolve a completed Customer ticket;
* you only need to review Partner acceptance;
* you only need to review Partner completed work;
* the issue is already handled by a more specific guide.

Use the more specific guide when the action is already obvious.

Examples:

* Use `Claim, release, and handoff ticket ownership` when the only decision is ownership movement.
* Use `Internal notes and Customer-visible updates` when the only decision is message audience.
* Use `Resolve a Customer ticket` when the work is complete and ready for Customer-facing resolution.
* Use `Review Partner acceptance` when Partner acceptance is waiting for Telectro review.
* Use `Review Partner completed work` when Partner work has been submitted for review.

## Important concepts

### Intervention

Intervention means Telectro deliberately decides what must happen next to restore service flow.

It does not always mean changing the owner.

Intervention may be as light as asking for a note, or as strong as Controlled Handoff or escalation.

### Stale ticket

A stale ticket has not changed recently or does not show visible progress.

A stale ticket is not automatically a bad ticket.

It may be legitimately waiting, but the reason must be clear.

### Blocked ticket

A blocked ticket cannot progress until something else happens.

Common blockers include:

* missing Customer information;
* no site access;
* equipment or stock dependency;
* supplier dependency;
* Partner dependency;
* unclear internal decision;
* wrong service area;
* wrong owner;
* missing evidence;
* unclear Customer-facing outcome.

### Clear next action

A clear next action tells the next person what should happen next, who is responsible, and what is being waited on.

A ticket should not remain stale or blocked without a clear next action.

### Customer-visible vs internal information

Some intervention information is internal only.

Some information must be communicated to the Customer.

Use internal notes for Telectro-only coordination.

Use Customer-visible updates when the Customer needs to know progress, next step, missing information, or outcome.

### Ownership intervention

Ownership intervention must follow the pilot ownership controls.

Use:

* Claim, when work is unclaimed and you are taking it yourself;
* Release, when you own the ticket and it should return to the pool;
* Controlled Handoff, when a Coordinator/Supervisor must transfer accountability to a specific new owner.

Do not use generic Assign/Unassign to bypass the pilot ownership model.

## Before you start

Before intervening, confirm:

* the ticket is not already terminal;
* the latest ticket activity has been read;
* the current owner or pool state is understood;
* the Customer-visible history has been checked where relevant;
* internal notes have been checked;
* Partner state has been checked if Partner involvement exists;
* you know whether this is an ownership issue, information issue, communication issue, blocker, or completion issue.

## Step-by-step process

### Step 1 — Open the ticket

Open the HD Ticket from the report, workspace, queue, or link that identified it.

Do not intervene based only on a report row.

### Step 2 — Read the current context

Review:

* subject;
* status;
* Customer request;
* latest activity;
* latest internal notes;
* latest Customer-visible updates;
* current owner / assignment state;
* service area / team;
* fault location or asset details;
* Partner fields, if Partner is involved;
* SLA / response / resolution indicators if relevant;
* attachments or evidence if relevant.

### Step 3 — Identify the main problem

Choose the main reason the ticket needs intervention.

#### Case A — No accountable owner

The ticket is unclaimed or in the true pool.

Next action:

* use `Claim` if you are taking the ticket yourself;
* use `Controlled Handoff` if a Coordinator/Supervisor knows the correct named owner;
* add an internal note first if the next owner needs context;
* do not leave urgent or stale work in the pool without a decision.

#### Case B — Current owner is still correct, but context is missing

The owner is still the right person, but the ticket does not explain what is happening.

Next action:

* ask the owner to add an internal note;
* ask the owner to send a Customer-visible update if the Customer needs progress visibility;
* add supervisor/coordinator context if you performed the review;
* leave ownership unchanged.

#### Case C — Current owner is wrong or unavailable

The current owner cannot or should not continue.

Next action:

* use Controlled Handoff to move accountability to a specific new owner;
* include a clear handoff reason;
* add an internal note before handoff if the new owner needs context;
* confirm the new owner appears as the accountable owner after handoff.

Do not use informal assignment changes.

#### Case D — Waiting on Customer

The ticket cannot progress until the Customer provides information, confirmation, access, or availability.

Next action:

* send a Customer-visible update asking clearly for what is needed;
* add an internal note if Telectro needs additional internal context;
* keep the current owner if they remain accountable for follow-up;
* escalate only if Customer delay creates operational risk.

#### Case E — Waiting on Partner

The ticket is waiting on Partner action, Partner acceptance, Partner work done, or Partner rework.

Next action:

* check the Partner state;
* use the Partner acceptance or Partner completed work review process where applicable;
* add internal context if the Partner dependency is unclear;
* do not use Controlled Handoff as a substitute for Partner review/rework workflow.

#### Case F — Waiting on supplier or external dependency

The ticket is waiting on a supplier, stock, third-party input, or external availability.

Next action:

* add an internal note explaining the dependency;
* send a Customer-visible update if the Customer needs progress visibility;
* set or confirm the owner who will follow up;
* escalate if the dependency threatens service outcome.

#### Case G — Technical blocker

The owner cannot continue because of an unresolved technical decision, missing information, access issue, or unclear route.

Next action:

* add an internal note describing the blocker;
* ask for Coordinator/Supervisor help if needed;
* use Controlled Handoff only if the accountable owner must change;
* send Customer-visible progress if the Customer needs to know the delay or next step.

#### Case H — Customer needs an update

The internal situation may be understood, but the Customer has not been kept informed.

Next action:

* send a Customer-visible update;
* keep it clear, calm, and Customer-safe;
* avoid internal routing, blame, SLA, governance, or debugging detail.

#### Case I — Work appears complete

The work appears done, but the ticket remains active.

Next action:

* confirm the outcome;
* check whether completion evidence is required;
* send the correct Customer-visible resolution update if this is a Customer ticket;
* resolve or close through the correct process;
* do not leave completed work aging in active queues.

### Step 4 — Choose the lightest effective intervention

Pick the smallest action that restores clear flow.

Possible actions:

* add an internal note;
* ask the owner for an update;
* send a Customer-visible update;
* claim the ticket;
* release the ticket to pool;
* use Controlled Handoff;
* request Customer information;
* follow up Partner work/rework;
* escalate a blocker;
* resolve or close the ticket.

Do not change ownership when a note or update is enough.

Do not leave ownership unchanged when the owner is clearly wrong or unavailable.

### Step 5 — Record internal context

If the intervention is not obvious from the ticket history, add an internal note.

A good internal note should explain:

* what was reviewed;
* why the ticket is stale or blocked;
* what is being waited on;
* who owns the next action;
* whether a Customer-visible update was sent or is still needed;
* whether ownership changed.

Examples:

```text
Coordinator review: ticket is stale because no site access date is confirmed. Alfa remains owner and will request Customer access confirmation today.
```

```text
Supervisor review: current owner unavailable. Controlled Handoff to Bravo for follow-up on Internet Connection fault.
```

```text
Internal note: waiting on supplier quote before Customer resolution can be prepared. Owner to follow up tomorrow morning.
```

```text
Coordinator review: Partner work is marked completed. Telectro review required before resolution.
```

```text
Internal note: Customer has asked for an update. Customer-visible progress update sent.
```

### Step 6 — Communicate to the Customer where needed

Send a Customer-visible update when the Customer needs progress, clarification, next step, or recovery communication.

Good Customer-visible examples:

```text
We are still working on this request and are waiting for site access confirmation before the next step can be completed.
```

```text
We have reviewed the request and need one detail before we can proceed. Please confirm which area or fault point is affected.
```

```text
The work is still in progress. We are following up on the required part and will update you once the next step is confirmed.
```

Avoid:

```text
Ticket was stale in supervisor report.
```

```text
SLA breach risk because technician did not update.
```

```text
Internal routing was wrong and handoff was required.
```

Put internal detail in an internal note instead.

### Step 7 — Move ownership only when needed

If ownership must change, use the approved ownership action.

#### Claim

Use `Claim` when:

* the ticket is unclaimed;
* you are taking accountability yourself;
* you can continue the work.

#### Release

Use `Release` when:

* you own the ticket;
* you cannot continue;
* the correct next owner is not known;
* the ticket should return to the pool with a clear reason.

#### Controlled Handoff

Use `Controlled Handoff` when:

* Coordinator/Supervisor intervention is needed;
* the next accountable owner is known;
* the current owner is wrong or unavailable;
* the ticket is stale or blocked and needs a named owner.

Good handoff reasons:

```text
Supervisor intervention: current owner unavailable; Bravo to continue site follow-up.
```

```text
Coordinator intervention: wrong service area ownership; handoff to Alfa for Internet Connection follow-up.
```

```text
Supervisor intervention: stale ticket requires dedicated owner and Customer progress update.
```

Poor handoff reasons:

```text
Please handle.
```

```text
Moved.
```

```text
Stale.
```

### Step 8 — Escalate when the blocker cannot be solved locally

Escalate when:

* the owner cannot resolve the blocker;
* Customer impact is high;
* the ticket is repeatedly stale;
* the same dependency keeps blocking progress;
* Partner/supplier delay needs management attention;
* the Customer has escalated;
* a decision is needed from Supervisor/Ops.

Escalation should still leave a clear ticket trace.

### Step 9 — Verify the intervention worked

After intervention, confirm:

* the ticket has a clear accountable owner or is deliberately in the pool;
* the latest internal note explains the intervention if needed;
* any Customer-visible update was sent safely;
* handoff/release/claim result is visible where expected;
* Partner state was updated through the correct Partner workflow if applicable;
* the next action is clear;
* the ticket no longer appears stuck for the same reason.

## Verification checklist

The stale or blocked ticket intervention is complete when:

* The ticket was opened and reviewed.
* Latest activity was checked.
* Internal notes were checked.
* Customer-visible activity was checked where relevant.
* Current owner or pool state was confirmed.
* Partner state was checked where relevant.
* The blocker or stale reason was identified.
* The correct intervention action was selected.
* Internal context was added where needed.
* Customer-visible update was sent where needed.
* Controlled Handoff was used if accountability had to move to a known owner.
* Release was used only by the current owner when returning work to the pool.
* Claim was used only when taking unclaimed work yourself.
* Partner workflows were used for Partner acceptance/work review cases.
* The final ticket state has a clear next action.
* Reports or queues were refreshed where appropriate.

## Common mistakes

### Mistake: Treating every stale ticket as an ownership problem

Problem:

* The owner may be correct, but the ticket lacks visible context.

Correct approach:

* Add or request an internal note or Customer-visible update before changing ownership.

### Mistake: Leaving a blocked ticket without a next action

Problem:

* The ticket remains stuck and the next person still does not know what to do.

Correct approach:

* Record the blocker and the next action.

### Mistake: Using Customer-visible updates for internal problems

Problem:

* The Customer sees internal routing, assignment, SLA, or governance detail.

Correct approach:

* Keep internal details in internal notes.

### Mistake: Using internal notes when the Customer needs progress

Problem:

* Telectro has documented the issue internally, but the Customer remains uninformed.

Correct approach:

* Send a Customer-visible update when the Customer needs to know progress or next steps.

### Mistake: Bypassing Controlled Handoff

Problem:

* Ownership becomes unclear or duplicate assignments appear.

Correct approach:

* Use Controlled Handoff when a Coordinator/Supervisor transfers accountability to a known owner.

### Mistake: Using handoff when Partner review is required

Problem:

* Partner work states are bypassed or confused.

Correct approach:

* Use Partner acceptance/work review processes for Partner workflow cases.

### Mistake: Closing or resolving without checking Customer-facing outcome

Problem:

* The ticket disappears from active work, but the Customer may not understand the outcome.

Correct approach:

* Use the Customer resolution process where Customer-facing resolution is required.

## Do

* Open the ticket before intervening.
* Identify the actual blocker or stale reason.
* Preserve current ownership when it is still correct.
* Use internal notes for Telectro-only context.
* Use Customer-visible updates when the Customer needs progress.
* Use Controlled Handoff for known-owner accountability transfer.
* Use Partner review/rework workflows for Partner cases.
* Escalate blockers that cannot be solved locally.
* Leave a clear next action.
* Refresh reports or queues after material intervention.

## Do not

* Do not intervene from the report row alone.
* Do not treat stale work as automatic technician fault.
* Do not use generic Assign/Unassign to bypass the pilot ownership model.
* Do not move ownership when a note or update would solve the issue.
* Do not leave a stale ticket without a documented next action.
* Do not expose internal blocker, SLA, routing, assignment, or governance detail to the Customer.
* Do not use Customer-visible updates as internal coordination.
* Do not ignore Partner workflow state.
* Do not leave completed work active.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Ticket identified from `Aging and At-Risk Tickets`.
2. Ticket identified from `My Current Work`.
3. Ticket identified from `Customer Ticket Oversight`.
4. Ticket opened from report or workspace.
5. Ticket activity showing stale or missing next action.
6. Internal notes area before intervention.
7. Internal note recording blocker or supervisor review.
8. Customer-visible update dialog for progress communication.
9. Controlled Handoff action.
10. Controlled Handoff reason field.
11. Ticket after Controlled Handoff showing new accountable owner.
12. Partner state area where Partner review/rework is relevant.
13. Ticket after intervention showing clear next action.
14. Refreshed report or queue after intervention.

## Related docs

* `docs/user-guides/activity-process-guides.md#2-claim-release-and-handoff-ticket-ownership`
* `docs/user-guides/activity-process-guides.md#3-internal-notes-and-customer-visible-updates`
* `docs/user-guides/activity-process-guides.md#4-resolve-a-customer-ticket`
* `docs/user-guides/activity-process-guides.md#12-review-partner-acceptance`
* `docs/user-guides/activity-process-guides.md#13-review-partner-completed-work`
* `docs/user-guides/activity-process-guides.md#14-review-current-work`
* `docs/user-guides/activity-process-guides.md#15-check-unclaimed-tickets`
* `docs/user-guides/activity-process-guides.md#16-check-aging-and-at-risk-tickets`
* `docs/user-guides/activity-process-guides.md#17-check-first-response-risk`
* `docs/runbooks/supervisor-operating-model.md`
* `docs/runbooks/ticket-assignment-contract.md`
* `docs/runbooks/sla-and-supervisor-risk-signals.md`

# 19. Review Partner acceptance queue

## Purpose

Use this process to review the queue of Partner-originated tickets where the Partner has accepted the request and Telectro must decide what happens next.

This is a queue-level process.

It explains how Coordinator/Ops/Supervisor users find and triage Partner acceptance items before opening each ticket and using the detailed `Review Partner acceptance` action.

The detailed ticket action is covered in:

* `# 12. Review Partner acceptance`

This guide focuses on:

* finding tickets waiting for Telectro acceptance review;
* reading the queue safely;
* prioritising the review list;
* opening each ticket;
* deciding whether the ticket needs review only, resolution, or closure.

## Audience

Primary users:

* Telectro Coordinator
* Telectro Ops / Supervisor

Secondary users:

* Telectro Technician, when asked to help review or provide context

Partner users do not use this internal queue.

Customer portal users do not use this internal queue.

## When to use this process

Use this process when:

* a Partner-originated ticket has been accepted by the Partner;
* the `Partner Acceptance Review Queue` has rows;
* `My Current Work` shows `Partner acceptance review needed`;
* Telectro needs to review Partner acceptance before resolving or closing the ticket;
* a Supervisor/Coordinator is checking Partner workflow health;
* Partner-originated tickets appear stuck after Partner acceptance;
* Telectro needs to confirm whether the Partner acceptance note is sufficient.

Typical examples:

* “The Partner Acceptance Review Queue has a ticket waiting.”
* “The Partner has accepted this Partner-originated request.”
* “Telectro must decide whether this Partner-originated ticket is ready to resolve.”
* “This Partner acceptance needs review before closure.”
* “The Partner acceptance note needs to be checked.”
* “My Current Work shows Partner acceptance review needed.”

## When not to use this process

Do not use this process when:

* the ticket was not Partner-originated;
* the Partner Acceptance State is not `Accepted by Partner`;
* the ticket is already `Resolved`, `Closed`, or `Archived`;
* Partner work completion is waiting for review;
* Partner acceptance still needs to be requested;
* Partner acceptance rework is required;
* the ticket is a Telectro-to-Partner work fulfilment ticket rather than a Partner-originated acceptance review case.

Use:

* `Review Partner acceptance` for the detailed ticket action;
* `Review Partner completed work` for Telectro-to-Partner work completion review;
* `Intervene on a stale or blocked ticket` when the issue is a general blocker rather than Partner acceptance review;
* Partner rework/follow-up process when the Partner acceptance was rejected or needs correction.

## Important concepts

### Partner-originated ticket

A Partner-originated ticket is a ticket created or submitted by a Partner, where Telectro must review the Partner’s acceptance before the ticket is finalised.

This is different from a Telectro ticket assigned to a Partner for work fulfilment.

### Partner Acceptance State

The key state for this queue is:

```text
Accepted by Partner
```

This means the Partner has submitted an acceptance note.

It does not mean Telectro has completed its review.

### Partner Acceptance Review Queue

`Partner Acceptance Review Queue` is the report used to find Partner-originated tickets that are waiting for Telectro review.

The queue should show tickets where:

* Request Source is `Partner`;
* Partner Acceptance State is `Accepted by Partner`;
* ticket status is not terminal.

Terminal statuses are:

```text
Resolved
Closed
Archived
```

### Partner Acceptance Note

The Partner Acceptance Note is the Partner’s submitted note explaining or confirming acceptance.

The queue may show a shortened preview.

Use `View full` where available to read the full note.

### Review Partner Acceptance action

`Review Partner Acceptance` is the ticket-level action used after you open the ticket.

Current outcomes are:

```text
Review only
Resolve ticket
Close ticket
```

In the current implementation, `Review only` records review context but does not finalise the acceptance state as `Reviewed by Telectro`.

`Resolve ticket` and `Close ticket` finalise the Partner acceptance review and mark the Partner Acceptance State as `Reviewed by Telectro`.

## Before you start

Before reviewing the queue, confirm:

* you are logged in as a Telectro internal user with Coordinator/Ops/Supervisor access;
* you are using the Partner acceptance review queue, not the Partner work completion queue;
* you understand that `Accepted by Partner` still needs Telectro review;
* you will open the HD Ticket before applying the review action;
* you will not resolve or close without checking the Partner note and ticket context.

## Step-by-step process

### Step 1 — Open the Partner Acceptance Review Queue

Open the relevant Coordinator or Ops/Supervisor workspace.

Open:

```text
Partner Acceptance Review Queue
```

You may also find the same work through:

```text
My Current Work
```

Look for a bucket such as:

```text
Partner acceptance review needed
```

### Step 2 — Review the queue rows

Review the queue columns.

Typical useful columns include:

* ID;
* Subject;
* Status;
* Account;
* Campus;
* Request Type;
* Partner Acceptance State;
* Partner Accepted On;
* Partner Acceptance Note;
* Modified.

The queue is intended to help Telectro identify which Partner-originated tickets are waiting for acceptance review.

### Step 3 — Confirm the acceptance state

Confirm the row shows:

```text
Partner Acceptance State = Accepted by Partner
```

Do not use this queue process for rows where the state is:

```text
Pending Partner Acceptance
Rework Required
Reviewed by Telectro
```

Those states belong to other Partner workflow steps.

### Step 4 — Read the Partner Acceptance Note preview

Read the Partner Acceptance Note preview in the queue.

If the preview is shortened, use `View full` where available.

Look for:

* whether the Partner clearly accepted;
* what the Partner says was accepted;
* whether the note is vague or incomplete;
* whether the note suggests rework or missing information;
* whether the note supports resolving or closing the ticket.

Do not decide only from the preview if the note may be truncated.

### Step 5 — Prioritise the queue

Review the most important Partner acceptance items first.

Prioritise:

* older accepted items;
* high-impact Customer or Account issues;
* tickets with unclear acceptance notes;
* tickets with recent Customer or Telectro follow-up;
* tickets that appear ready to resolve or close;
* tickets blocking downstream work.

The queue is not just a list to clear mechanically.

Each row needs enough review to decide the correct outcome.

### Step 6 — Open the HD Ticket

Open the ticket from the queue.

Do not perform final review from the report row alone.

Check:

* original Partner request;
* Partner Acceptance State;
* Partner Accepted On;
* Partner Acceptance Note;
* latest activity;
* internal notes;
* Customer / Account context where relevant;
* status;
* any linked location or fault information;
* whether any Telectro action is still outstanding.

### Step 7 — Decide the review outcome

Choose the appropriate ticket-level outcome.

#### Option A — Review only

Use `Review only` when:

* Telectro has looked at the acceptance;
* more information or action is still needed;
* the ticket should remain active;
* the acceptance review should be noted but not finalised.

Examples:

* the Partner accepted, but Telectro still needs to confirm details;
* the note is acceptable but the ticket cannot yet be resolved;
* another Telectro action is required before terminal status.

Remember: in the current implementation, `Review only` does not change the Partner Acceptance State to `Reviewed by Telectro`.

#### Option B — Resolve ticket

Use `Resolve ticket` when:

* the Partner acceptance is sufficient;
* the ticket outcome is complete;
* the ticket should move to `Resolved`;
* there is no further active work required.

This outcome marks Partner Acceptance State as `Reviewed by Telectro`.

#### Option C — Close ticket

Use `Close ticket` when:

* Telectro has completed review;
* the ticket should be closed rather than resolved;
* the Partner acceptance is accepted as complete;
* no further active work is required.

This outcome marks Partner Acceptance State as `Reviewed by Telectro`.

### Step 8 — Use Review Partner Acceptance

On the HD Ticket, use:

```text
Review Partner Acceptance
```

Select the correct outcome:

```text
Review only
Resolve ticket
Close ticket
```

Add a note when useful.

Good review notes:

```text
Telectro reviewed the Partner acceptance note. Acceptance is clear, but ticket remains active pending final Account confirmation.
```

```text
Partner acceptance reviewed and accepted. Ticket ready to resolve.
```

```text
Partner acceptance reviewed. Closing because no further Telectro action is required.
```

Poor review notes:

```text
Done.
```

```text
OK.
```

```text
Reviewed.
```

### Step 9 — Confirm the result

After submitting the review action, confirm:

* the ticket saved successfully;
* the review note appears in activity where expected;
* if `Resolve ticket` was selected, status is `Resolved`;
* if `Close ticket` was selected, status is `Closed`;
* if a terminal outcome was selected, Partner Acceptance State is `Reviewed by Telectro`;
* if `Review only` was selected, the ticket still has a clear next action;
* the ticket no longer appears in the queue once terminal review is complete.

### Step 10 — Refresh the queue

Return to `Partner Acceptance Review Queue`.

Refresh the report.

Confirm:

* terminally reviewed tickets are no longer listed;
* remaining tickets still require Telectro review;
* any `Review only` item still has a clear next action;
* no old accepted Partner-originated ticket is sitting without attention.

## Verification checklist

The Partner acceptance queue review is complete when:

* `Partner Acceptance Review Queue` was opened.
* Queue rows were reviewed.
* Partner Acceptance State was confirmed as `Accepted by Partner`.
* Partner Acceptance Note preview was read.
* Full Partner Acceptance Note was opened where needed.
* Each important ticket was opened before action.
* The ticket was confirmed as Partner-originated.
* The correct review outcome was chosen.
* `Review Partner Acceptance` was used on the HD Ticket.
* Review note was added where useful.
* Terminal outcomes moved the ticket to `Resolved` or `Closed`.
* Terminal outcomes marked Partner Acceptance State as `Reviewed by Telectro`.
* `Review only` items still had a clear next action.
* The queue was refreshed after review.

## Common mistakes

### Mistake: Treating the queue as the review action

Problem:

* The queue only identifies tickets waiting for review.

Correct approach:

* Open the HD Ticket and use `Review Partner Acceptance`.

### Mistake: Assuming Accepted by Partner means Telectro is finished

Problem:

* `Accepted by Partner` means the Partner submitted acceptance, not that Telectro completed review.

Correct approach:

* Telectro must still review the ticket.

### Mistake: Reviewing from the preview only

Problem:

* The Partner Acceptance Note may be shortened in the queue.

Correct approach:

* Use `View full` or open the ticket before deciding.

### Mistake: Using Partner acceptance review for Partner work completion

Problem:

* Partner acceptance and Partner completed work are different workflows.

Correct approach:

* Use `Review Partner completed work` for Partner work completion cases.

### Mistake: Choosing Review only and assuming the ticket is finalised

Problem:

* In the current implementation, `Review only` does not mark Partner Acceptance State as `Reviewed by Telectro`.

Correct approach:

* Use `Resolve ticket` or `Close ticket` when the ticket is truly finalised.

### Mistake: Closing without checking the ticket context

Problem:

* The Partner note may be acceptable, but the ticket may still need Telectro action.

Correct approach:

* Read the ticket activity and confirm no active next action remains.

## Do

* Review the Partner Acceptance Review Queue regularly.
* Confirm the state is `Accepted by Partner`.
* Read the Partner Acceptance Note.
* Open the HD Ticket before taking action.
* Use `Review Partner Acceptance` for the actual review.
* Choose `Review only` when further work remains.
* Choose `Resolve ticket` or `Close ticket` only when the ticket is ready.
* Add a useful review note.
* Refresh the queue after review.

## Do not

* Do not treat the queue itself as completion.
* Do not assume `Accepted by Partner` means Telectro has reviewed it.
* Do not resolve or close from the note preview alone.
* Do not use this process for Partner work completion review.
* Do not use `Review only` when the ticket should actually be finalised.
* Do not leave old accepted Partner-originated tickets sitting in the queue without a next action.
* Do not bypass the ticket-level `Review Partner Acceptance` action.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Coordinator/Ops workspace showing `Partner Acceptance Review Queue`.
2. `Partner Acceptance Review Queue` report open.
3. Queue row showing Partner Acceptance State `Accepted by Partner`.
4. Queue row showing Partner Accepted On.
5. Partner Acceptance Note preview.
6. `View full` Partner Acceptance Note, if available.
7. HD Ticket opened from the queue.
8. HD Ticket showing Partner Acceptance State `Accepted by Partner`.
9. `Review Partner Acceptance` button.
10. `Review Partner Acceptance` dialog.
11. Outcome options: `Review only`, `Resolve ticket`, `Close ticket`.
12. Review note field.
13. Ticket after `Review only`, showing clear next action.
14. Ticket after `Resolve ticket` or `Close ticket`.
15. Partner Acceptance State showing `Reviewed by Telectro` after terminal review.
16. Refreshed queue after completed review.

## Related docs

* `docs/user-guides/activity-process-guides.md#10-partner-responds-to-an-acceptance-request`
* `docs/user-guides/activity-process-guides.md#12-review-partner-acceptance`
* `docs/user-guides/activity-process-guides.md#13-review-partner-completed-work`
* `docs/user-guides/activity-process-guides.md#14-review-current-work`
* `docs/user-guides/activity-process-guides.md#18-intervene-on-a-stale-or-blocked-ticket`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/partner-workflow-v1.md`

# 20. Review Partner work completion queue

## Purpose

Use this process to review Telectro-assigned Partner fulfilment work where the Partner has submitted work done and Telectro must decide what happens next.

This guide covers the **Telectro → Partner** train:

```text
Telectro asks Partner to do work
→ Partner submits Work Done
→ Partner Work State = Work Completed by Partner
→ Telectro reviews through Review Partner Work
→ Telectro chooses Review only / Accept work / Request Rework / Resolve / Close
→ Request Rework sends it back to Partner
→ Accept / Resolve / Close marks Partner Work State = Reviewed by Telectro
```

This is a queue-level process.

It explains how Coordinator/Ops/Supervisor users find and triage Partner work completion items before opening each ticket and using the detailed `Review Partner completed work` action.

The detailed ticket action is covered in:

* `# 13. Review Partner completed work`

This guide focuses on:

* finding Partner work waiting for Telectro review;
* reading the review list safely;
* prioritising completed Partner work;
* opening each ticket;
* deciding whether to review only, accept work, request rework, resolve, or close.

## Audience

Primary users:

* Telectro Coordinator
* Telectro Ops / Supervisor

Secondary users:

* Telectro Technician, when asked to help confirm the work outcome or provide context

Partner users do not use this internal queue.

Customer portal users do not use this internal queue.

## When to use this process

Use this process when:

* Telectro assigned work to a Partner;
* a Partner has submitted work done;
* the Partner Work State is `Work Completed by Partner`;
* `Work Completion Review Queue` has work waiting;
* `My Current Work` shows `Partner work review needed`;
* `Partner Current Work` shows `Waiting for Telectro work review`;
* `Partner Workflow War Room` shows `Partner Work Completed / Telectro Review Needed`;
* Telectro needs to review Partner fulfilment work before accepting, reworking, resolving, or closing;
* Customer-visible resolution may depend on Partner work review.

Typical examples:

* “The Partner has submitted work done.”
* “The Work Completion Review Queue has an item waiting.”
* “My Current Work shows Partner work review needed.”
* “The Partner Work State is Work Completed by Partner.”
* “Telectro must decide whether to accept or request rework.”
* “The Partner work looks complete, but Telectro has not reviewed it.”
* “This Customer ticket cannot be resolved until Partner work is reviewed.”

## When not to use this process

Do not use this process when:

* the Partner has not submitted work done yet;
* the Partner Work State is not `Work Completed by Partner`;
* the ticket is Partner-originated and waiting for Partner acceptance review;
* the ticket is waiting for Partner acceptance rather than Partner work completion;
* Partner rework is already required and the Partner has not resubmitted work;
* the issue is a general stale/blocker intervention rather than Partner work review.

Use:

* `Review Partner completed work` for the detailed ticket action;
* `Review Partner acceptance queue` for Partner-originated acceptance review;
* `Intervene on a stale or blocked ticket` when the issue is a general blocker;
* Customer resolution process when Partner work has already been accepted and the Customer-facing outcome is ready.

## Important concepts

### Telectro-assigned Partner fulfilment work

This is work where Telectro has assigned fulfilment to a Partner.

It is different from a Partner-originated ticket where the Partner submitted the original request and Telectro must review Partner acceptance.

### Partner Work State

The key state for this queue is:

```text
Work Completed by Partner
```

This means the Partner has submitted a Work Done Note.

It does not mean Telectro has accepted the work.

### Work Completion Review Queue

`Work Completion Review Queue` is the Partner Work Area shortcut for Telectro-side review of Partner work submitted back to Telectro.

The shortcut links to:

```text
Partner Work Completion Review Queue
```

The same review need may also appear in:

* `My Current Work` as `Partner work review needed`;
* `Partner Current Work` as `Waiting for Telectro work review`;
* `Partner Workflow War Room` as `Partner Work Completed / Telectro Review Needed`.

These views all point to the same business condition: Partner Work State is `Work Completed by Partner`, and Telectro must open the HD Ticket and use `Review Partner Work`.

### Review Partner Work action

`Review Partner Work` is the ticket-level action used after you open the ticket.

When Partner Work State is `Work Completed by Partner`, the action provides these outcomes:

```text
Review only
Accept work
Request Rework
Resolve ticket
Close ticket
```

### Reviewed by Telectro

`Reviewed by Telectro` means Telectro has accepted the Partner work or finalised the ticket through a terminal review outcome.

The following outcomes mark Partner Work State as `Reviewed by Telectro`:

```text
Accept work
Resolve ticket
Close ticket
```

### Rework Required

`Rework Required` means Telectro reviewed the Partner work and decided that the Partner must correct, complete, or clarify the work.

`Request Rework` should include a useful reason.

## Before you start

Before reviewing the queue, confirm:

* you are logged in as a Telectro internal user with Coordinator/Ops/Supervisor access;
* you are reviewing Partner work completion, not Partner acceptance;
* the Partner Work State is `Work Completed by Partner`;
* you will open the HD Ticket before applying the review action;
* you will not accept, resolve, or close without checking the Partner’s Work Done Note and ticket context;
* you will request rework when the Partner submission is incomplete or unclear.

## Step-by-step process

### Step 1 — Open the Partner work review queue

Open the Partner Work Area in the Coordinator/Ops/Supervisor workspace.

Use the shortcut:

```text
Work Completion Review Queue
```

This opens the Partner work completion review entry point for work submitted back to Telectro.

You may also find the same work through:

```text
My Current Work
```

Look for:

```text
Partner work review needed
```

Partner workflow oversight reports may also show the same work as:

```text
Waiting for Telectro work review
Partner Work Completed / Telectro Review Needed
```

All of these indicate that Partner work has been submitted and Telectro must open the HD Ticket and use `Review Partner Work`.

### Step 2 — Review the queue or bucket rows

Review the available row information.

Useful fields normally include:

* ticket ID;
* subject;
* status;
* Account;
* Campus;
* request or fault type;
* Partner Work State;
* latest Partner work note or work done context;
* modified date;
* owner or bucket.

The review list is intended to help Telectro identify Partner fulfilment work that has been submitted and needs Telectro decision.

### Step 3 — Confirm the work state

Confirm the ticket shows:

```text
Partner Work State = Work Completed by Partner
```

Do not use this queue process for rows where the work state is:

```text
Assigned to Partner
Rework Required
Reviewed by Telectro
```

Those states belong to other Partner workflow steps.

### Step 4 — Open the HD Ticket

Open the ticket from the queue, bucket, or oversight list.

Do not perform final review from a report row alone.

Check:

* original Customer or Telectro request;
* current status;
* Partner Work State;
* Partner Work Done Note;
* latest activity;
* internal notes;
* Customer-visible updates where relevant;
* fault location or asset details;
* evidence or attachments;
* whether the Partner work appears complete;
* whether any Telectro action is still outstanding;
* whether Customer-visible resolution is ready.

### Step 5 — Read the Partner Work Done Note

Read the Partner’s submitted work note carefully.

Look for:

* what work was completed;
* when the work was completed;
* whether the note matches the original request;
* whether any evidence is mentioned;
* whether the Partner reports an unresolved issue;
* whether the note is too vague;
* whether the work can be accepted;
* whether rework is needed;
* whether the ticket can be resolved or closed.

If the note is unclear, do not accept the work mechanically.

### Step 6 — Decide the review outcome

Choose the appropriate ticket-level outcome.

#### Option A — Review only

Use `Review only` when:

* Telectro has looked at the Partner work;
* more information or action is still needed;
* the ticket should remain active;
* the work should not yet be accepted, reworked, resolved, or closed.

Examples:

* the Partner work note has been reviewed, but Telectro still needs Customer confirmation;
* the Partner work appears complete, but evidence must still be checked;
* internal confirmation is required before final acceptance.

#### Option B — Accept work

Use `Accept work` when:

* the Partner work is acceptable;
* Telectro accepts the submitted work;
* the ticket should remain active for final internal or Customer-facing steps;
* the ticket should no longer sit in Partner work review needed.

This outcome marks Partner Work State as `Reviewed by Telectro`.

#### Option C — Request Rework

Use `Request Rework` when:

* the work is incomplete;
* the work note is unclear;
* evidence is missing;
* the wrong issue was addressed;
* the Partner needs to correct or complete something.

A rework reason is required.

Good rework reasons are specific and actionable.

#### Option D — Resolve ticket

Use `Resolve ticket` when:

* the Partner work is accepted;
* the ticket outcome is complete;
* the ticket should move to `Resolved`;
* no further active work is required.

This outcome marks Partner Work State as `Reviewed by Telectro`.

#### Option E — Close ticket

Use `Close ticket` when:

* Telectro has completed review;
* the ticket should be closed rather than resolved;
* the Partner work is accepted as complete;
* no further active work is required.

This outcome marks Partner Work State as `Reviewed by Telectro`.

### Step 7 — Use Review Partner Work

On the HD Ticket, use:

```text
Review Partner Work
```

Select the correct outcome:

```text
Review only
Accept work
Request Rework
Resolve ticket
Close ticket
```

Add a note when useful.

A note is especially important when:

* choosing `Review only`;
* choosing `Request Rework`;
* accepting work but leaving the ticket active;
* resolving or closing with important context.

Good review notes:

```text
Partner work reviewed. Work appears complete, but Telectro still needs to confirm Customer access outcome before resolution.
```

```text
Partner work accepted. Ticket remains active for Customer-visible resolution update and completion evidence.
```

```text
Rework required: Partner note does not confirm whether the affected fault point was tested after repair.
```

```text
Partner work reviewed and accepted. Ticket ready to resolve.
```

Poor review notes:

```text
Done.
```

```text
OK.
```

```text
Check again.
```

### Step 8 — Confirm the result

After submitting the review action, confirm:

* the ticket saved successfully;
* the review note appears in activity where expected;
* if `Accept work` was selected, Partner Work State is `Reviewed by Telectro`;
* if `Request Rework` was selected, Partner Work State is `Rework Required`;
* if `Resolve ticket` was selected, status is `Resolved`;
* if `Close ticket` was selected, status is `Closed`;
* if a terminal outcome was selected, Partner Work State is `Reviewed by Telectro`;
* if `Review only` was selected, the ticket still has a clear next action;
* the ticket no longer appears in Partner work review needed after accept, resolve, or close.

### Step 9 — Check Customer-facing follow-up

If the work affects a Customer ticket, check whether the Customer needs a visible update or resolution.

Use a Customer-visible update when the Customer needs progress visibility.

Use the Customer resolution process when the ticket is complete and ready for Customer-facing resolution.

Do not expose internal Partner review detail unnecessarily.

### Step 10 — Refresh the queue

Return to the Partner work review list.

Refresh the report, bucket, or oversight view.

Confirm:

* accepted work no longer appears as needing Partner work review;
* resolved or closed tickets no longer appear as active review work;
* rework items now show the correct rework state;
* `Review only` items still have a clear next action;
* no old Partner work completion item is sitting without attention.

## Verification checklist

The Partner work completion queue review is complete when:

* The Partner work review queue was opened.
* `Partner work review needed` items were reviewed where applicable.
* Partner Work State was confirmed as `Work Completed by Partner`.
* Each important ticket was opened before action.
* The Partner Work Done Note was read.
* Ticket context and latest activity were checked.
* The correct review outcome was chosen.
* `Review Partner Work` was used on the HD Ticket.
* Review note was added where useful.
* Rework reasons were specific when rework was requested.
* Accepted work marked Partner Work State as `Reviewed by Telectro`.
* Rework marked Partner Work State as `Rework Required`.
* Resolved/closed outcomes changed the ticket status correctly.
* Customer-visible follow-up was considered where relevant.
* The review list was refreshed after review.

## Common mistakes

### Mistake: Treating Work Completed by Partner as final

Problem:

* `Work Completed by Partner` means the Partner submitted work done, not that Telectro has accepted the work.

Correct approach:

* Telectro must review the work.

### Mistake: Reviewing from the queue row only

Problem:

* The queue or bucket row does not provide enough context for final review.

Correct approach:

* Open the HD Ticket and use `Review Partner Work`.

### Mistake: Confusing Partner acceptance with Partner work completion

Problem:

* Partner acceptance and Partner completed work are different workflows.

Correct approach:

* Use `Review Partner acceptance queue` for Partner-originated acceptance review.
* Use this process for Telectro-assigned Partner fulfilment work.

### Mistake: Accepting vague work notes

Problem:

* The Partner note does not prove what was done or whether the issue was addressed.

Correct approach:

* Request rework or clarification with a specific reason.

### Mistake: Requesting rework with a vague reason

Problem:

* The Partner does not know what to correct.

Correct approach:

* Write a clear, actionable rework reason.

### Mistake: Accepting work but forgetting Customer follow-up

Problem:

* Telectro accepts the Partner work internally, but the Customer is not updated.

Correct approach:

* Send a Customer-visible update or resolution where appropriate.

### Mistake: Leaving Review only items without a next action

Problem:

* The ticket remains active but nobody knows what must happen next.

Correct approach:

* Add a note explaining the next action and owner.

## Do

* Review Partner work completion items regularly.
* Confirm Partner Work State is `Work Completed by Partner`.
* Open the HD Ticket before taking action.
* Read the Partner Work Done Note.
* Use `Review Partner Work` for the actual review.
* Choose `Accept work` only when the work is acceptable.
* Choose `Request Rework` when correction or clarification is required.
* Use specific rework reasons.
* Consider Customer-visible follow-up after accepting work.
* Refresh the queue or bucket after review.

## Do not

* Do not treat the queue itself as completion.
* Do not assume `Work Completed by Partner` means Telectro has accepted the work.
* Do not accept vague or incomplete Partner notes.
* Do not use this process for Partner-originated acceptance review.
* Do not request rework with a vague reason.
* Do not resolve or close without checking ticket context.
* Do not expose internal Partner review detail unnecessarily to the Customer.
* Do not leave old Partner work completion items sitting without a next action.

## Screenshot checklist

Recommended screenshots for the Obsidian/training version:

1. Partner Work Area showing `Work Completion Review Queue`.
2. `Work Completion Review Queue` opened.
3. `My Current Work` bucket showing `Partner work review needed`.
4. `Partner Current Work` showing `Waiting for Telectro work review`.
5. `Partner Workflow War Room` showing `Partner Work Completed / Telectro Review Needed`.
6. Queue/bucket row showing Partner Work State `Work Completed by Partner`.
7. HD Ticket opened from the queue or bucket.
8. HD Ticket showing Partner Work State `Work Completed by Partner`.
9. Partner Work Done Note.
10. `Review Partner Work` button.
11. `Review Partner Work` dialog.
12. Outcome options: `Review only`, `Accept work`, `Request Rework`, `Resolve ticket`, `Close ticket`.
13. Review note / rework reason field.
14. Ticket after `Accept work`, showing Partner Work State `Reviewed by Telectro`.
15. Ticket after `Request Rework`, showing Partner Work State `Rework Required`.
16. Ticket after `Resolve ticket` or `Close ticket`.
17. Customer-visible update or resolution action, where appropriate.
18. Refreshed queue/bucket after completed review.

## Related docs

* `docs/user-guides/activity-process-guides.md#11-partner-submits-work-done`
* `docs/user-guides/activity-process-guides.md#13-review-partner-completed-work`
* `docs/user-guides/activity-process-guides.md#14-review-current-work`
* `docs/user-guides/activity-process-guides.md#18-intervene-on-a-stale-or-blocked-ticket`
* `docs/user-guides/activity-process-guides.md#19-review-partner-acceptance-queue`
* `docs/user-guides/pilot-welcome-guides.md`
* `docs/runbooks/partner-workflow-v1.md`

# 21. Activity Process Guide backlog

The following follow-up items remain for this document as the pilot training pack matures.

## Internal Telectro ticket execution

Follow-up items:

- Extend internal note / Customer-visible update guide after production screenshots are captured
- Extend Customer-visible evidence update guide after production screenshots are captured

## Partner collaboration

Terminal status note:

Partner-side archive/history visibility is not currently a separate Activity Process Guide.

In V1, Partner-related tickets that are `Resolved`, `Closed`, or `Archived` are treated as terminal/history items for reporting and Partner History visibility. The pilot does not yet define a separate operational difference between `Resolved`, `Closed`, and `Archived` for Partner-side work beyond their terminal/reporting behaviour.

Closing a Partner-related ticket after review remains a Telectro staff decision and is covered by `Review Partner completed work`.

Any stricter distinction between `Resolved`, `Closed`, and `Archived` should be defined after the pilot if Telectro identifies a real operational or reporting need.

---

# 22. Maintenance rule

Keep Activity Process Guides practical.

When updating this document:

- describe what the user does;
- include what the user must verify;
- link back to canonical runbooks for implementation detail;
- avoid duplicating technical contracts from runbooks;
- avoid turning Welcome Guides into long process manuals;
- keep screenshots in Obsidian unless they are deliberately added to the repo.
