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

# 4. Activity Process Guide backlog

The following process guides are candidates for this document as the pilot training pack matures.

## Internal Telectro ticket execution

Planned guides:

- Claim a ticket
- Release a ticket
- Handoff / share ticket context
- Extend internal note / Customer-visible update guide after production screenshots are captured
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

# 5. Maintenance rule

Keep Activity Process Guides practical.

When updating this document:

- describe what the user does;
- include what the user must verify;
- link back to canonical runbooks for implementation detail;
- avoid duplicating technical contracts from runbooks;
- avoid turning Welcome Guides into long process manuals;
- keep screenshots in Obsidian unless they are deliberately added to the repo.
