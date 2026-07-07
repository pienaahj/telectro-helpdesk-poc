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

# 7. Activity Process Guide backlog

The following process guides are candidates for this document as the pilot training pack matures.

## Internal Telectro ticket execution

Planned guides:

- Claim a ticket
- Release a ticket
- Handoff / share ticket context
- Extend internal note / Customer-visible update guide after production screenshots are captured
- Extend Customer-visible evidence update guide after production screenshots are captured
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

- Customer views latest update
- Customer downloads Customer-visible evidence
- Customer checks resolved ticket outcome

---

# 8. Maintenance rule

Keep Activity Process Guides practical.

When updating this document:

- describe what the user does;
- include what the user must verify;
- link back to canonical runbooks for implementation detail;
- avoid duplicating technical contracts from runbooks;
- avoid turning Welcome Guides into long process manuals;
- keep screenshots in Obsidian unless they are deliberately added to the repo.
