# Phase 2 time booking DEV acceptance

On 20 November 2026, the `frontend` site in local DEV backend `bf79674a643d` passed the native submitted Timesheet replacement and rollback checks. The proof used the site's enabled Phase 2 runtime and an existing eligible technician with read permission for the selected Activity Type. It used Customer Support with an unlisted customer and Snapfix metadata, so the setup required no test ticket, Project, or Task.

## Native replacement and rollback

The proof ran native Frappe document operations and MariaDB writes under a single uncommitted transaction per case. The fixture used the normal booking operation for Draft creation and scoped document permission elevation for fixture submission. Replacement then used the existing technician endpoint and its native permission scopes. The run used the Frappe JSON parser and RPC dispatcher in process, without the HTTP success commit.

Preflight verified the active Timesheet hooks, the absence of enabled Timesheet and audit automation covered by the review, the transactional table engines, and the absence of database triggers. The proof disabled global search only in its Python process because Timesheet indexing can write to Redis outside the database transaction. Frappe's standard realtime callbacks remained deferred until commit. The SQL fence rejected commits, implicit transaction restarts, and writes to any unreviewed table. Observed writes touched only `tabTimesheet`, `tabTimesheet Detail`, `tabSeries`, and `tabTELECTRO Booking Correction Audit`, all InnoDB.

| Marker | Observed result |
| --- | --- |
| `B3_87M_112_NATIVE_ACCEPTANCE_TEST_DESIGN=PASS` | Transaction and side-effect guards were in place before fixture creation. |
| `B3_87M_113_NATIVE_SUBMITTED_REPLACEMENT=PASS` | The original became Cancelled. The same time slot was saved as a separate Draft under the technician's identity with the mandatory booking metadata. The linked audit retained the submitted snapshot and all 17 request fields. An identical retry returned the same audit and replacement, and a native attempt to edit the audit was rejected. |
| `B3_87M_114_INDEPENDENT_SUCCESS_ROLLBACK_VERIFICATION=PASS` | A fresh connection found none of the two Timesheets, two details, or one audit after the explicit rollback. |
| `B3_87M_115_ENDPOINT_FAILURE_ROLLBACK=PASS` | A failure thrown after native audit insertion caused the endpoint to roll back the original, replacement, details, and audit before the test harness performed cleanup. |
| `B3_87M_116_INDEPENDENT_FAILURE_ROLLBACK_VERIFICATION=PASS` | A fresh connection independently confirmed that all five records from the failure case were absent. |

The run identifier was `phase2-native-7634b8ecf10f4066bf158232fb241709`.

## Booking form verification

The Desk entry point uses the existing technician identity gate. It provides own-booking history and uses the audited Draft correction, Draft withdrawal, submitted replacement, and submitted cancellation endpoints. The form carries no historical-work attestation action or Coordinator privilege.

| Marker | Observed result |
| --- | --- |
| `B3_87M_117_BOOKING_FORM_JSON_RPC_AND_OWN_HISTORY=PASS` | Frappe parsed the numeric Emergency and duration values from JSON, executed the native replacement, and returned the Cancelled original and replacement Draft in own-booking history with the current revision. |
| `B3_87M_118_BOOKING_READ_IDENTITY_GATE=PASS` | Guest and Administrator did not receive form options, history, or ticket Service Area through the booking API. Local nginx returned HTTP 403 for unauthenticated requests to each new route. |
| `B3_87M_119_HELPDESK_SERVICE_AREA_LOOKUP=PASS` | The booking workflow returned the configured Service Area from an existing ticket readable by the eligible DEV technician. |
| `B3_87M_120_BOOKING_FORM_CONDITIONAL_FIELDS_AND_REQUESTS=PASS` | The JavaScript harness covered conditional fields and payloads in all four work contexts, the Travel exception, both conditional origin fields, explicit Emergency values, canonical numeric ticket IDs, and correction request routing. |

The focused suite passed 118 tests. JavaScript syntax checks, DEV asset delivery, the DEV dependency audit, and Git whitespace validation passed. Interactive acceptance in an authenticated Desk browser remains open.
