# ERPNext Pilot — Data Request / Data Provisioning Production Migration Playbook

**Status:** DRAFT — production execution not approved.
**Prepared:** 2026-11-04 (Africa/Johannesburg).
**Repository:** `pienaahj/telectro-helpdesk-poc`
**Intended repository path:** `docs/runbooks/data-provisioning-production-migration.md`
**Parent procedure:** `docs/runbooks/production-runtime-release.md` (authoritative; this playbook does not override its phase order or approvals).
**Source snapshot reviewed:** `main` at `c1e217e7309510ffd4055e88473865739aa3eab0` (merged PRs #411 and #412).
**Intended release ID at time of drafting:** `20261104-c1e217e` — **must be recalculated** if any additional commit, including this guide, is merged before build.
**Last recorded deployed runtime:** `prod-20261103-75b8e70`, commit `75b8e70df2989334cdfa9937fd4073570852ba0e`; independently reconfirm the live production identity before touching production.

> **Stop / approval boundary:** This document records the DEV-proven sequence, production differences, checks and stop conditions. It is not permission to migrate, to change production membership, or to activate a runtime. All such operations remain behind the authoritative release runbook's explicit Phase 2 human review and subsequent gates.

## 1. Purpose and scope

Promote the **Data Request** Service Area and its **Data Provisioning** HD Team into production while preserving all existing customer and operational data, contextual assignment policy, manual Claim authorization, and the **disabled** Data Provisioning Support Rotation. Also install the new Data Request Notification Intent schema and preserve the customer attachment browser correction from PR #411 in the same release candidate.

Do not broaden this release to the 10-minute Coordinator escalation. Test it separately; if a correction is needed, make a separate PR. Do not claim notification delivery passed merely because an Intent was captured.

## 2. Proven DEV recipe (do not redo in production)

The following is **historical acceptance evidence**, not a requirement to generate new test data:

| Sequence | Verified DEV result | Evidence reference |
| --- | --- | --- |
| Service Area | `HD Ticket-custom_service_area` includes `Data Request` | `173CI.111CE–CF` |
| Routing | `Data Request` routes to `Data Provisioning` | `173CI.111CE–CF` |
| Durability | `Data Provisioning` is in required HD Team list; `after_migrate` hook registered | `173CI.111CE–CF` |
| Team / Rule | `Data Provisioning` and `Data Provisioning - Support Rotation` exist; linked rule deliberately disabled | `173CI.111CE–CF` |
| Membership | DEV synthetic Technician `tech.bravo@local.test` added through native Frappe lifecycle; persisted in fresh session | `173CI.111CH-R8`, `173CI.111CI` |
| Native behavior | Adding/saving a team Technician **can enable the linked Assignment Rule**; DEV explicitly restored `disabled=1` and verified persistence | `173CI.111CH–CI` |
| Ticket lifecycle | Synthetic DEV ticket #956 created through native lifecycle with Data Request, Service Request, correct Team / Customer / Campus; no auto ownership or customer email | `173CI.111CJ-R4`, `173CI.111CK` |
| Browser Claim | Ticket #956 appeared in Unclaimed War Room; Technician claimed successfully | `173CI.111CL–CN` |
| Persisted ownership | Ticket #956 remains Open with one owner `tech.bravo@local.test` and exactly one open ToDo | `173CI.111CO` |
| Audit & outbox | Claim audit `mcausp6gtk`; ToDo `mcarn9a1lv`; pending Task Notification Intent `145a3228a37404ca81923c997fcfcf8776bc340948ad414536beffbf906cd699` | `173CI.111CO` |

DEV ticket **#956 stays Open and assigned**. Do not recreate it, copy it, or copy the DEV synthetic Customer, Campus or Technician into production. The historical DEV membership increased a rule-member count from 49 to 50 without deleting the existing memberships; those are **DEV observations, not production count expectations**.

## 3. Reviewed candidate implementation

| Artifact | Intended contract |
| --- | --- |
| `apps/telephony/telephony/fixtures/custom_field.json` | Adds exactly one `Data Request` service option; adds hidden, read-only Datetime field `custom_data_request_first_completed_on` |
| `apps/telephony/telephony/telectro_ticket_routing.py` | `AREA_TO_TEAM["Data Request"] == "Data Provisioning"` |
| `apps/telephony/telephony/setup/hd_team_durability.py` | Seven required teams; preserves existing users, linked rules and operational state; creates missing teams via native `HD Team.insert()`; reports unexpected/conflicting state rather than silently rewriting it |
| `apps/telephony/telephony/hooks.py` | Registers `telephony.setup.hd_team_durability.after_migrate` once; ticket arrival and first-completion handlers present |
| `apps/telephony/telephony/ftelephony/doctype/telectro_data_request_notification_intent/*` | New `TELECTRO Data Request Notification Intent` DocType; 13 fields; module `FTelephony`; separate from the existing Task Notification Intent schema |
| `bin/release-validators/validate-hd-team-durability.sh` | Expects seven required teams |
| PR #411 Helpdesk frontend fix | Propagates ticket context into customer attachment download links; requires browser acceptance on ticket #54 |

**Source-completeness recovery — DEV/Mac identity verified; PR and candidate validation pending:**

The two Python modules referenced by the recovered HD Ticket hooks were confirmed missing from committed Git source but present in the canonical DEV container.

Both were subsequently recovered using `bin/pull-telephony-changes.sh --include-new`, with exactly two new source files and no modifications to existing tracked source or fixtures.

- `data_request_arrival_outbox.py`: handler `capture_arrival_intents`; DEV/Mac SHA-256 `09f21ae1ef3d0d465cf756ca7f8be5fb8299268e6b5a29e9ddd9712b82e82160`.
- `data_request_completion.py`: handler `capture_first_completion`; DEV/Mac SHA-256 `9beaa090dea89bd502b5cc2c02956b974db6ccab83778291df70320652f23f45`.

Both handlers passed Python AST syntax and function-presence checks. The source synchronization dependency audit reported zero missing runtime dependencies, zero custom untracked dependencies and zero syntax errors.

**Remaining release gates:** Commit and merge both modules through a focused PR; establish a new exact release identity; verify both hook imports in the immutable candidate image. DEV source identity alone is not candidate runtime proof.

## 4. Production state: establish fresh baseline (read-only)

Before release activation, independently capture the **current** production runtime, commit, site state, actual Service Area options, Teams, linked Assignment Rules, and Technician memberships. The 2026-11-03 baseline was: 37 tickets (33 Resolved, 4 Closed, 0 Open), no Data Request option, no Data Provisioning Team, no associated rule or member. **Do not treat those counts as current without a fresh read.**

Use the repository-controlled production wrappers and evidence locations specified by the parent runbook. For Frappe-aware checks, enter the *production* Bench console through `./bin/prod-console.sh` only in the supported production execution context. The following are **read-only Bench-console snippets**; run separately and inspect each output before proceeding:

```python
import frappe
print("SITE=", frappe.local.site)
print("DATA_REQUEST_OPTION_PRESENT=", "Data Request" in (frappe.db.get_value("Custom Field", "HD Ticket-custom_service_area", "options") or "").splitlines())
print("DATA_PROVISIONING_TEAM_EXISTS=", bool(frappe.db.exists("HD Team", "Data Provisioning")))
print("DATA_REQUEST_INTENT_TABLE_EXISTS=", bool(frappe.db.table_exists("TELECTRO Data Request Notification Intent", cached=False)))
```

For an existing Team, inspect the **linked** rule rather than inferring a rule from its display name:

```python
team = frappe.db.get_value("HD Team", "Data Provisioning", ["name", "team_name", "assignment_rule"], as_dict=True)
print("DATA_PROVISIONING_TEAM=", dict(team) if team else None)
if team and team.assignment_rule:
    rule = frappe.db.get_value("Assignment Rule", team.assignment_rule, ["name", "document_type", "assign_condition", "disabled"], as_dict=True)
    print("DATA_PROVISIONING_LINKED_RULE=", dict(rule) if rule else None)
```

**STOP** if production differs materially from the expected baseline, or if any existing Team/Rule has unexpected links, enabled rotation, or unknown assigned users. A baseline read does not authorize repair.

## 5. Phase 2 approval / migration impact assessment

Record explicit operator approval in the **parent runbook Phase 2** after reviewing the exact previous-production-commit to candidate diff and resolving the source-completeness hold. Required classifications: Helpdesk frontend/assets; Ticket hook and routing source; Custom Field fixture; new DocType/table and permissions; HD Team after-migrate behavior; tests and validator scripts.

**Migration required: YES (proposed, subject to human approval).** The Custom Field and DocType changes require the normal site migration. Required parent runbook markers include `RELEASE_CHANGE_REVIEW_OK`, `RELEASE_MIGRATION_DECISION_RECORDED`, and `LOCAL_FIXTURE_VALIDATION_OK` (fixture changed). Neither this guide nor DEV success substitutes for Phase 2 human approval.

Before authorizing the runtime-to-migration interval, explicitly review whether any non-Claim assignment or handoff writes could run against missing new schema. The Task Notification Claim guard does **not** cover all assignment paths. Establish the operational restriction required by the parent runbook before the runtime switch if risk cannot be excluded.

## 6. Release execution — parent runbook only

Follow the **exact order** and wrappers in `docs/runbooks/production-runtime-release.md`: identity/source preflight → Phase 2 change review and human approval → source artifact → immutable AMD64 runtime build → candidate-specific semantic validators and host prerequisites → archive/checksums → production transfer/load → fresh verified four-part backup → controlled image/environment change → five runtime services only → nginx reload/direct+routed health → single replay-protected migration → cache/database validation → customer browser acceptance → final evidence and closure.

Do **not** execute `bench migrate` ad hoc or rerun it automatically if its started record exists. The protected production wrapper is `bin/prod-migrate.sh`; it creates migration started/completed/failed/review-required evidence under:

`/opt/telectro/erpnext/deploy-evidence/releases/<release-id>/production-migration/`

A migration failure or ambiguous evidence state is **STOP / operator review**. A previous runtime image may be incompatible with already-migrated database schema; rollback is not simply retagging the image.

The three validators already run in DEV were: HD Team durability **PASS** (15-test contract inventory), contextual routing **PASS** (57-test contract inventory), and Task Notification **PASS** (100 unit tests actually executed). **These are not substitutes for the required validators against the NEW immutable candidate.** Retain the parent runbook's required contextual routing, assignment-policy, customer privacy and Task Notification validator gates and all applicable host-level prerequisites.

## 7. Immediately after migration — state inspection before membership changes

Run *read-only* production Bench inspections **in a fresh console** and record evidence:

1. Verify migration wrapper's completed evidence; do not infer success solely from terminal exit.
2. Verify the `Data Request` Service Area option exists once in the persisted Custom Field.
3. Verify `custom_data_request_first_completed_on` is a hidden, read-only Datetime Custom Field.
4. Verify `Data Provisioning` Team exists, with the correct `team_name` and a linked Assignment Rule that exists as a document.
5. Verify the linked Rule uses `HD Ticket` and expected contextual-safe condition (DEV: `status == 'Open' and agent_group == 'Data Provisioning' and not custom_contextual_assignment_hold`), and is **disabled**.
6. Verify `TELECTRO Data Request Notification Intent` table exists and `intent_id` is uniquely constrained; also preserve Task Notification Intent schema, not confuse the two.
7. Confirm **existing Teams, Team users, linked rules, ticket inventory and current assignments** match the pre-release baseline, aside from explicitly reviewed expected changes.
8. Check for unexpected enabled orphan Assignment Rules; stop on unresolved conflicts.

Useful read-only checks:

```python
import frappe
f = frappe.get_doc("Custom Field", "HD Ticket-custom_data_request_first_completed_on")
print("COMPLETION_FIELD=", f.dt, f.fieldtype, f.hidden, f.read_only)
print("DATA_REQUEST_OPTION_COUNT=", (frappe.db.get_value("Custom Field", "HD Ticket-custom_service_area", "options") or "").splitlines().count("Data Request"))
print("DATA_REQUEST_INTENT_SCHEMA=", bool(frappe.db.table_exists("TELECTRO Data Request Notification Intent", cached=False)))
from telephony.setup.hd_team_durability import verify_hd_teams
check = verify_hd_teams()
print("HD_TEAM_VERIFY_OK=", check["ok"], "ISSUE_COUNT=", check["issue_count"])
print("HD_TEAM_ISSUES=", check["issues"])
```

Note: `verify_hd_teams()` checks structural Team/Rule integrity but does **not** assert that the Data Provisioning linked rule is disabled. Inspect that property **separately**. Existing Team operational state is deliberately not rewritten by `ensure_hd_teams()`, so the presence of the new Team alone does not constitute production acceptance.

**STOP** on any unexpected enabled Data Provisioning rotation. Do not allow automatic assignment while investigating. Production acceptance must explicitly prove it is disabled.

## 8. Production Technician onboarding — deliberately separate, controlled action

No real production Data Provisioning Technician account has been selected or authorized by this draft. DEV's `tech.bravo@local.test` must never be copied into production.

Before adding a real Technician, require the approved identity and confirm the account is an enabled System User with Technician role and approved Data Provisioning responsibility. Capture Team membership and linked Rule state **before** the change. Use the normal Frappe document lifecycle, not direct SQL or broad fixture import. Respect normal permissions and role governance.

**Native Helpdesk side effect observed in DEV:** When a Technician is saved to a Team, Helpdesk can automatically enable its linked Assignment Rule. Therefore, **before committing the membership transaction**, inspect the linked Rule and explicitly restore `disabled=1` through the reviewed Frappe lifecycle; verify the persisted state in an independent fresh session. If the operator cannot keep it disabled atomically/safely, stop and design a separate reviewed provisioning action instead. Do not silently change existing rule memberships or duplicate Team users.

No production membership step is authorized until its operator, account, change procedure and approval are recorded. Do not run the DEV membership code blindly against production.

## 9. Post-release focused acceptance and evidence

| Acceptance | PASS condition | Status at drafting |
| --- | --- | --- |
| Service Area | `Data Request` visible in **production Customer Portal → New Service Request** | Pending deployment |
| Team / routing | Team exists; mapping and Team links resolve correctly | Pending deployment |
| Rotation safety | Data Provisioning linked Rule disabled after migration and after any membership change | Must prove independently |
| Real Technician | Approved account has correct role, active state and native HD Team membership | Operator approval pending |
| Customer attachments | Authorized Emerald Life customer downloads Aug/Sep/Oct XLS from ticket #54; unauthorized/Guest remains denied | Backend proved; browser pending PR #411 deployment |
| Existing production tickets | Pre/post inventory and assignments preserved; no synthetic acceptance tickets | Must compare fresh inventories |
| Notification schema | Both relevant Intent schemas present and operationally readable | Must prove after migration |
| Coordinator 10-minute escalation | Controlled DEV test; fix in separate PR if needed | Explicitly OUT OF SCOPE |
| Actual notification delivery | Dispatcher/status/channel/recipient and retries | Not proved by Pending Intent alone |

Capture evidence per parent runbook under `/opt/telectro/erpnext/deploy-evidence`, including candidate SHA/image identity, migration log and sentinels, fresh production state, rule `disabled=1` before/after membership, browser results and explicit pass/fail markers. Record each unknown as **PENDING**, not PASS.

Suggested release-specific evidence markers (supplementary; not replacements for parent runbook markers):

```text
DATA_REQUEST_SERVICE_AREA_PROD=PASS
DATA_PROVISIONING_TEAM_PROD=PASS
DATA_PROVISIONING_LINKED_RULE=PASS
DATA_PROVISIONING_ROTATION_DISABLED=PASS
DATA_REQUEST_INTENT_SCHEMA_PROD=PASS
PRODUCTION_EXISTING_TICKETS_PRESERVED=PASS
CUSTOMER_ATTACHMENT_BROWSER_DOWNLOADS=PASS
```

## 10. Stop conditions and change control

- Hook source missing from committed Git/candidate or cannot import: **STOP, source-recovery PR**.
- Phase 2 not explicitly approved: **STOP**.
- Changed runtime/production baseline, unexpected Team/Rule links or enabled rotation: **STOP**.
- No proven operational restriction for unsafe runtime-to-migration write paths: **STOP**.
- Missing backup, checksum, identity, migration evidence or mandatory validator markers: **STOP**.
- Migration started sentinel already present: **DO NOT automatically rerun migration**.
- Error after migration: preserve original failure/evidence and assess database/image compatibility before any rollback.
- No real Technician approved: **leave membership provisioning pending**; do not use DEV synthetic identity.
- 10-minute escalation or delivery fails: **separate PR**, not an unreviewed change in the correction release.

## 11. Reuse and upkeep

This playbook is a release-specific supplement to the canonical production release runbook. Keep it under Git review. If documentation is added to `main` **before** building the candidate, regenerate `RELEASE_ID`, release identity, source artifact, and candidate-specific validation inputs from the new exact `main` commit. Never reuse `20261104-c1e217e` for changed image contents. Update this guide with the new commit, approved membership identity, migration evidence paths and final acceptance outcomes after the operator completes each gate.
