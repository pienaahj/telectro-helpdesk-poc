# Pilot Outstanding Issues and Timeline

## Purpose

This document tracks the remaining ERPNext Pilot issues, expected order of work, and rough timeline.

The goal is to keep pilot scope clear:

- protect demo-critical flows
- avoid mixing unrelated workflow changes
- keep technical debt visible
- separate urgent pilot issues from later polish
- preserve proven Customer / Partner containment decisions before adding new fields or workflow surfaces

---

## Current state

The pilot now has working foundations for:

- Partner-safe ticket request and ticket detail flows
- Partner acceptance and rework flow
- Partner work completion and review flow
- Partner-safe ticket evidence upload/list/download
- Internal Ticket Evidence V1 upload/list/download/camera capture
- Customer Intake V1 through the native Helpdesk customer portal
- Customer Website User containment
- Customer organisation-level ticket visibility
- Customer Service Area capture and routing
- Customer private evidence upload against HD Tickets
- Customer-visible follow-up updates through Communications
- Telectro-side `Resolve Customer Ticket` action
- Customer-visible resolution updates
- optional Customer-facing completion evidence attached to the resolution Communication
- controlled Customer completion-evidence download endpoint
- Customer portal Knowledge Base/article suggestion suppression for V1
- Customer portal Close action suppression / backend closure guard
- Notification V1 in-app alerts for selected action-required workflow states
- Partner-safe notification routing
- Explicit creator take-ownership option for internal manual tickets
- Current-work and team-load visibility through reports/workspaces

Reports and workspaces remain the primary internal operational source of truth.

Notifications are supporting nudges only.

Customer portal visibility is intentionally scoped by Customer organisation, not just by individual ticket ownership. This allows multiple named Customer Website Users from the same Customer organisation to see and update that organisation’s portal tickets while preserving per-user audit identity.

---

## Timeline view

### Immediate / demo-safe

These items should be prioritised before further broad workflow expansion.

---

### 1. Customer Location/Campus scoped-filtering discovery

Status: next priority / discovery required

Reason:

- Customer Intake V1 is now strong enough for ticket creation, evidence, updates, resolution visibility, and Customer-facing completion evidence.
- Customer organisation-level ticket visibility is proven.
- The next likely Customer-side improvement is Location/Campus capture.
- Unsafe Link-field exposure could leak other customers’ locations, campuses, or sites.

Current proof foundation:

```text
Customer Website User
→ Contact / Contact Email
→ Dynamic Link
→ HD Customer
→ HD Ticket.customer
```

Proven example:

- `test@boschendal.co.za` resolves to `HD Customer = Boschendal`.
- `customer2@boschendal.co.za` resolves to `HD Customer = Boschendal`.
- Both users can see the same Boschendal portal ticket set.
- `customer2@boschendal.co.za` sees zero non-Boschendal tickets.
- `customer2@boschendal.co.za` created ticket 809 and uploaded private evidence.
- `test@boschendal.co.za` could view ticket 809 and add a Customer update.
- Ticket 809 retained separate audit identity for each Customer user through owner/raised_by/contact and Communication sender.

Target outcome:

- Customer users can only search/select locations belonging to their linked Customer organisation.
- Boschendal Customer users can see/select only Boschendal locations.
- Boschendal Customer users cannot search/select another Customer’s locations.
- Filtering is enforced server-side, not only through browser-side filters.
- Customer-facing Location/Campus fields are exposed only after containment proof.

Suggested next slice:

1. Identify current Location/Campus/Site doctypes and fields.
2. Identify how Customer or HD Customer links to location/campus data.
3. Prove the safe server-side lookup/filter path.
4. Prove negative containment before exposing any Customer portal field.
5. Only then decide whether V1 exposes:
   - Campus only
   - Location only
   - Campus + Location
   - or keeps Location/Campus deferred

---

### 2. Production Customer onboarding model

Status: needs documentation / production setup detail

Reason:

- Production Customer users should not share login accounts.
- Multiple Customer-side staff may need to cover one another’s tickets.
- Telectro still needs per-person audit identity.

Target production model:

```text
Named Customer Website User
→ matching Contact
→ Dynamic Link to HD Customer
→ Customer portal access
```

Target outcome:

- Each Customer-side person gets a separate Website User.
- Each Customer-side person has the `Customer` role only.
- Each Customer-side person links to the correct `HD Customer`.
- Multiple users linked to the same `HD Customer` can see/update that Customer organisation’s tickets.
- Cross-customer visibility remains blocked.
- Desk/Internal roles are not granted to Customer users.

Suggested next slice:

- Update production deployment/user onboarding documentation.
- Add required Customer onboarding fields to the production setup checklist.
- Preserve the rule that Customer Website Users are organisation-contained but individually audited.

---

### 3. Stabilise workspace landing behaviour

Status: mostly stabilised / re-test after workspace or route changes

Problem:

- Internal and Partner landing behaviour can become inconsistent after route-guard or workspace changes.
- Partner route containment must remain strict.
- Internal users should land on the correct Tech / Coordinator / Ops workspace based on role.
- Stale browser routes from a previous login must not trap a different role on an inaccessible workspace.

Current outcome:

- Stale workspace route handling on login has been fixed.
- Partner users should land on `TELECTRO-POC Partner`.
- Tech users should land on `TELECTRO-POC Tech`.
- Coordinator users should land on `TELECTRO-POC Coordinator`.
- Supervisor/Ops users should land on `TELECTRO-POC Ops`.
- Internal maintenance users can still manually inspect workspaces after boot where appropriate.

Target outcome:

- No Partner user should land on raw HD Ticket list/report/workspace surfaces.
- Customer Website Users should remain contained to the customer portal and not Desk workspaces.
- Landing behaviour should be re-tested after any route guard, workspace, or login redirect change.

Suggested next slice:

- Re-test current landing behaviour by role only when route/workspace code changes.
- Capture actual route outcomes.
- Fix only proven broken redirects.

---

### 4. Continue assignment/timeline noise cleanup discovery

Status: discovery started / lower priority than Customer Location/Campus

Findings so far:

- Fresh creator take-ownership assignment is clean.
- Normal routing assignment is clean.
- Older Partner transition tickets show noisy timeline sequences when assignment changes from Telectro owner to Partner queue.
- Noise is layered:
  - native Frappe `Assigned` comments
  - native `Assignment Completed` comments
  - TELECTRO explicit `Info` comments from assignment normalisation
  - historical repair/setup actions
- `TELECTRO_RULE_DEBUG` comments should remain disabled unless explicitly needed for debugging.

Target outcome:

- Do not suppress native assignment comments globally.
- Avoid unnecessary assignment mutation when the final owner is already correct.
- For Partner fulfilment transitions, prefer one clear workflow signal where possible.
- Keep assignment state correct before optimising timeline appearance.

Suggested next slice:

- Pick one current reproducible noisy transition.
- Prove exact function/hook responsible.
- Patch only if semantics are not affected.

---

### 5. Verify My Team Load operating fit

Status: implemented / needs user-fit validation

Reason:

- A Telectro technician requested visibility of team load so technicians can help one another.
- This is a team-awareness and peer-support report, not only a supervisor governance report.

Current outcome:

- `My Team Load` report shows current active load by owner / pool.
- Uses Open ToDo as the canonical assignment source.
- Shows total open tickets, pool count, and Partner queue items.
- Anchored for internal use.

Target outcome:

- Confirm the report appears in the intended Tech / Coordinator / Ops workspaces.
- Confirm technicians understand it as a peer-support view.
- Confirm counts are useful and not misleading.

Suggested next slice:

- Validate report from Tech user.
- Validate report from Coordinator user.
- Validate report from Supervisor/Ops user.
- Consider minor label changes only if users misunderstand the purpose.

---

## Near-term pilot backlog

### 6. Customer completion evidence documentation

Status: implemented / docs should stay aligned

Reason:

- Telectro can now resolve a Customer ticket with a Customer-visible resolution update.
- Telectro can optionally attach deliberate Customer-facing completion evidence.
- This model is intentionally separate from arbitrary internal evidence exposure.

Current outcome:

- Completion evidence starts from an existing private HD Ticket File.
- Backend creates a separate private File link attached to the Customer-visible Communication.
- Customer portal download uses a controlled endpoint.
- Raw `/private/files/...` links are not exposed as the access model.

Target outcome:

- Keep docs clear that Customer-facing completion evidence is selective.
- Do not imply all ticket evidence is Customer-visible.
- Use this as the preferred V1 answer when Customers need proof of work/completion.

Suggested next slice:

- Ensure `customer-ticket-lifecycle-v1.md` and production runbook both describe:
  - internal evidence
  - Customer-uploaded evidence
  - Customer-facing completion evidence
  - controlled download expectations

---

### 7. Customer Site evidence upload model

Status: outstanding / may be superseded by Location/Campus work

Reason:

- Ticket Evidence V1 currently supports evidence against HD Tickets.
- Customer Intake V1 supports Customer evidence attached to tickets.
- The next practical model may be evidence against Customer Site / Location context where useful.

Target outcome:

- Define whether evidence belongs to:
  - HD Ticket only
  - Customer Site / Location
  - both via ticket context
- Avoid turning ticket evidence into a full document-management system.
- Avoid exposing site/location evidence before Customer Location/Campus containment is proven.

Suggested order:

1. Complete Customer Location/Campus scoped-filtering discovery.
2. Define data model.
3. Define internal upload/list/download path.
4. Define Customer/Partner-safe exposure only if needed.
5. Add audit/context comments only where useful.

---

### 8. Evidence metadata / category / context

Status: outstanding

Reason:

- Current evidence upload works, but files are mostly attached files plus comments.
- Telectro may later need better context around why a file was uploaded.

Possible fields:

- evidence category
- uploaded by actor type
- evidence note
- workflow step
- visible to Partner flag
- visible to Customer flag
- related Customer completion evidence flag
- related site/fault asset

Suggested approach:

- Keep V1 evidence simple.
- Add metadata only when a real workflow need is proven.
- Do not mix metadata expansion into Location/Campus containment work.

---

### 9. Download audit logging

Status: optional / later

Reason:

- Controlled download endpoints exist for Partner and Customer completion evidence.
- Audit logging could help prove who accessed private evidence.

Target outcome:

- Record download events only for controlled endpoints.
- Avoid noisy audit rows for every internal browser preview unless explicitly needed.

---

### 10. Optional evidence deletion/removal policy

Status: optional / later

Reason:

- Evidence deletion/removal can become governance-sensitive.
- Current priority is upload/view/download.

Target outcome:

- Define who may remove evidence.
- Preserve audit trail.
- Avoid silent deletion of pilot proof.

---

## Partner containment backlog

### 11. Partner report access tightening for multi-user Partner accounts

Status: future hardening

Reason:

- Current Partner access is owner-only for generic HD Ticket access.
- Customer organisation-level visibility has now been deliberately implemented for Customer users.
- Partner organisation-level visibility should not be assumed from the Customer model.
- If multiple Partner users/accounts are used under the same Partner organisation, visibility rules may need separate refinement.

Target outcome:

- Decide whether Partner users see:
  - only tickets they own
  - all tickets for their Partner organisation
  - only tickets assigned to their Partner queue
- Implement explicit Partner organisation model rather than relying on owner alone.

Suggested approach:

- Keep current Partner containment unchanged for now.
- Revisit only when Telectro confirms multi-user Partner organisation requirements.

---

### 12. Partner-safe history visibility

Status: optional

Reason:

- Partner ticket detail currently surfaces selected latest notes.
- Some use cases may need broader Partner-visible ticket history.

Target outcome:

- Expose useful history without leaking internal-only timeline entries.
- Keep raw HD Ticket timeline hidden from Partner users.

---

## Notification backlog

### 13. Recipient fallback rules

Status: future hardening

Current V1 is narrow and proven.

Potential future cases:

- no Telectro assignee exists
- ticket owner is not an internal user
- Partner assignee is missing
- Coordinator/Ops should receive fallback alerts
- Customer-visible resolution/update notification expectations are clarified

Suggested approach:

- Do not add broad fallback notifications until a real missed-action case is proven.
- Reports/workspaces remain the source of truth.

---

### 14. Email / mobile / browser push

Status: mostly out of scope for V1, except production incoming/outgoing email where explicitly required

Current position:

- Notification V1 is in-app `Notification Log` only.
- Email notifications are not the main action-required mechanism.
- Mobile/browser push is not promised.
- Production incoming email handling is separately in scope only where Telectro requires day-one email-to-ticket behaviour.

Suggested approach:

- Only add outbound email notifications for high-value events if Telectro explicitly needs them.
- Avoid notification noise.
- Keep incoming mailbox processing proof separate from Notification V1.

---

## Later polish / technical debt

### 15. Duplicate helper cleanup in `partner_create.py`

Status: later cleanup

Known examples:

- duplicated helper patterns
- duplicate note-key style areas
- evidence helper consolidation opportunities

Suggested approach:

- Do not refactor during active workflow changes.
- Only clean when tests/proof flows are stable.

---

### 16. Workspace fixture noise management

Status: ongoing

Reason:

- Workspace changes can export broad fixture noise.
- Route/landing behaviour can regress after workspace edits.

Suggested approach:

- Keep workspace PRs small.
- Inspect fixture diffs carefully.
- Use restore scripts where appropriate.
- Validate landing after route/workspace PRs.

---

### 17. Customer portal UX polish

Status: later polish

Known items:

- Native Customer portal follow-up/update affordance may not be obvious enough.
- Customer portal lifecycle visibility may need clearer wording for status/resolution.
- Empty or unsupported Helpdesk features should remain hidden for V1.
- Location/Campus fields should not be exposed until scoped filtering is proven.

Suggested approach:

- Keep V1 simple.
- Fix only UX issues that affect operational understanding or demo clarity.
- Avoid custom Customer portal rewrite unless the native portal becomes a blocker.

---

## Working principles

- One slice at a time.
- Verify existing code before augmenting.
- Prefer in-container edits with VSCode Dev Containers.
- Use bench console for proof.
- Use `frappe.get_list()` or browser/API behaviour for permission-aware containment proof.
- Do not use `frappe.get_all()` as containment proof because it bypasses normal list permissions.
- Pull changed files back to host before Git diff/commit.
- Avoid changing assignment semantics unless the exact before/after behaviour is proven.
- Keep Partner containment stricter than internal convenience.
- Keep Customer organisation containment explicit and server-enforced.
- Do not expose unrestricted Link fields to Customer users.
- Reports/workspaces are the internal source of truth; notifications are nudges.
- Customer portal is the Customer-facing source of truth for intake, updates, resolution visibility, and Customer-facing completion evidence.

## Production deployment planning estimate

Once all outstanding production information is available, the production server is ready, and the backup Samba mount points are provided, allow approximately **one week** for deployment, smoke testing, issue correction, and sign-off.

This is a planning estimate, not an estimate for container startup only.

The actual technical Docker deployment may take less time, but the one-week window allows for:

```text
- validating VPN/server access and Docker/runtime readiness
- confirming the production hostname, DNS, firewall, and HTTPS certificate path
- configuring production environment values and secrets
- confirming certificate files, private key handling, and renewal responsibility
- configuring SMTP/IMAP for tickets@telectro.co.za
- configuring backup storage and verifying backup output to the Samba mount
- running smoke tests for login, Customer portal, ticket creation, internal visibility,
  incoming email ticket creation, outbound email, and backup checks
- fixing small environment-specific issues discovered during deployment
- allowing Telectro and Boschendal to test, review, and sign off
```

This estimate assumes the required production information is complete and correct when the deployment window starts.

Missing or incorrect server access, certificate, DNS/firewall, email, secrets, or backup details will extend the timeline.

### Production readiness checkpoint — 2026-06-04

Current production-readiness status has improved, but the deployment remains blocked on server-side access/proof and the missing CLM client contract.

#### Received / improved

- Customer portal ticket list visibility was hardened.
  - Customer portal `/helpdesk/my-tickets` now shows Customer-safe fallback columns.
  - No broad `HD View` or `Location` permissions were granted.
- Samba share details and credentials have been received locally.
- Email-system and email-account credentials have been received locally.
- Certificate delivery architecture has been clarified at a high level.
  - Certificate issuance and renewal are handled by Telectro’s CLM server.
  - Production certificate material is expected to be pulled from the CLM server through secure API access using a certificate-set-specific API key.

#### Samba / backup details received

The following Samba backup share details were received:

```text
SMB share: \\192.168.0.30\erp
Username: erp
Password: received locally, not stored in repository
```

Production backup implementation still requires:

- production server access;
- secure placement of Samba credentials on the server;
- mount path decision;
- backup-output proof to the Samba share;
- backup monitoring expectation;
- restore-test timing;
- restore ownership during incidents.

#### Email details received

Incoming email settings received:

```text
Server: mail.telectro.co.za
Port: 993
Encryption: SSL/TLS
Username: tickets@telectro.co.za assumed, pending Telectro confirmation
Password: received locally, not stored in repository
```

Outgoing email settings received:

```text
Server: mail.telectro.co.za
Port: 587
Encryption: STARTTLS
Username: tickets@telectro.co.za assumed, pending Telectro confirmation
Password: received locally, not stored in repository
```

Important follow-up:

```text
The expected mailbox is tickets@telectro.co.za.
One supplied value appeared to contain a spelling mismatch.
A confirmation request has been sent to Telectro, with follow-up due on 2026-06-05.
Until confirmed, production configuration should treat tickets@telectro.co.za as the assumed mailbox but not final sign-off proof.
```

Production email implementation still requires:

- secure placement of email credentials on the production server;
- confirmation of exact SMTP username;
- confirmation whether incoming IMAP uses the same username;
- SMTP smoke test;
- IMAP smoke test;
- incoming email-to-ticket proof;
- outbound email proof;
- operational monitoring expectation for failed email pulls/sends.

#### Certificate / CLM status

Telectro confirmed that production certificate issuance and renewal are handled by a CLM server.

The production certificate model is now understood at architecture level:

```text
CLM server
→ handles certificate request, validation, issuance, and renewal
→ exposes current certificate material through secure API access
→ production server/client pulls certificate material with an API key
→ local deployment installs the pulled files for Traefik
```

Available certificate package formats are expected to include:

- public certificate + private key PEM;
- public certificate + private key + full chain PEM;
- public certificate + private key + full chain PFX.

Preferred deployment format for Traefik remains:

```text
fullchain PEM + private key PEM
```

The following CLM client contract details are still required before production certificate automation can be implemented safely:

- exact CLM endpoint URL;
- HTTP method;
- required headers;
- API key header/name format;
- working example `curl` command with dummy/redacted values;
- exact response format:
  - separate PEM files,
  - ZIP/tar archive,
  - JSON payload,
  - PFX,
  - or another format;
- expected output file names;
- whether the private key PEM is encrypted;
- whether PFX requires a password if PFX is used;
- whether the endpoint requires VPN access or IP allowlisting;
- whether the CLM endpoint uses public TLS or an internal/private CA;
- recommended pull frequency;
- renewal timing expectations;
- failure handling and monitoring expectations;
- ownership split between Telectro/Robbie CLM renewal and ERPNext production pull/install.

Current assumption:

```text
Telectro/Robbie owns CLM issuance and renewal.
ERPNext production deployment owns the production-side pull/install script once the CLM client contract is supplied.
```

#### Secrets handling position

Credentials received locally must not be committed to the repository or copied into normal project notes.

Once the production server is available, credentials should be placed in a root-owned secrets location on the server, for example:

```text
/root/telectro-secrets/
  production.env
  samba-backup.env
  email.env
  clm-cert-pull.env
```

Recommended permissions:

```bash
chmod 700 /root/telectro-secrets
chmod 600 /root/telectro-secrets/*.env
chown -R root:root /root/telectro-secrets
```

Production secrets expected in this area include:

- SMTP username/password or app password;
- IMAP username/password or app password;
- Samba username/password;
- CLM API key;
- database passwords;
- ERPNext admin/bootstrap secrets.

#### Still blocked before production deployment

The following remain deployment blockers:

- production server access;
- VPN/SSH proof;
- server-side secure secret placement;
- CLM endpoint/client contract;
- certificate pull implementation;
- HTTPS proof with production hostname;
- Samba mount proof;
- backup output proof;
- SMTP/IMAP smoke proof;
- incoming email ticket creation proof;
- outbound email proof;
- final Telectro/Boschendal UAT and sign-off.

#### Work that can continue while blocked

While waiting for the CLM client contract and production server access, continue with:

- Customer portal final smoke pass;
- Telectro feedback visibility checks;
- production secret placement plan;
- backup/Samba mount checklist;
- email smoke-test checklist;
- HTTPS/Traefik certificate pull script skeleton;
- deployment runbook tightening.

Updated production-readiness status:

```text
Samba credentials have been received locally.
Email credentials have been received locally, with tickets@telectro.co.za assumed pending confirmation.
Certificate transfer model is known at architecture level.
CLM client contract is still missing.
Production server-side secure secret placement remains pending until server access is available.
Deployment remains blocked on infrastructure integration proof, not current application code.
```

### Production secrets handover update — 2026-06-04

Samba share credentials and email-system/email-account credentials have been received and saved locally.

These credentials must not be committed to the repository or copied into normal project notes.

Once the production server is available, credentials should be placed in a root-owned secrets location on the server, for example:

```text
/root/telectro-secrets/
  production.env
  samba-backup.env
  email.env
  clm-cert-pull.env
```

Recommended permissions:

```bash
chmod 700 /root/telectro-secrets
chmod 600 /root/telectro-secrets/*.env
chown -R root:root /root/telectro-secrets
```

Production secrets expected in this area include:

- SMTP username/password or app password;
- IMAP username/password or app password;
- Samba username/password;
- CLM API key;
- database passwords;
- ERPNext admin/bootstrap secrets.

Updated production-readiness status:

```text
Samba and email credentials have been received locally.
Certificate transfer model is known at architecture level.
CLM client contract is still missing.
Production server-side secure secret placement remains pending until server access is available.
```

### Suggested one-week deployment shape

```text
Day 1:
  server access, Docker/runtime, production secrets, certificate, DNS/firewall,
  backup mount verification, and deployment

Day 2:
  HTTPS, app access, login, Customer portal, and internal ticket visibility smoke tests

Day 3:
  SMTP/IMAP, incoming email ticket creation, outbound email, and backup smoke tests

Day 4:
  Telectro/Boschendal UAT fixes, retesting, and operational checks

Day 5:
  sign-off, rollback/fallback confirmation, and go/no-go decision
```

The exact work may not require all five days, but one week is the safer planning estimate because it includes testing, correction, and sign-off rather than only container startup.

### Important distinction

```text
Technical deployment sign-off is not the same as operational go-live.
```

Technical deployment means the system is installed, reachable, and passes core smoke tests.

Operational go-live means Telectro has accepted the workflow, email behaviour, Customer portal behaviour, support ownership, backup/restore expectations, and fallback/rollback plan.
