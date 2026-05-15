import frappe

app_name = "telephony"
app_title = "Telephony"
app_publisher = "Frappe Technologies Pvt. Ltd."
app_description = "Telephony for Frappe apps"
app_email = "pratik@frappe.io"
app_license = "agpl-3.0"


fixtures = [
    {"dt": "Role", "filters": [["role_name", "like", "TP%"]]},

    {
        "dt": "Workspace",
        "filters": [
            ["name", "in", ["TELECTRO-POC Tech", "TELECTRO-POC Ops", "TELECTRO-POC Coordinator", "TELECTRO-POC Partner"]],
        ],
    },

    {
        "dt": "Custom HTML Block",
        "filters": [
            ["name", "in", [
                "Unclaimed Over1 Day Card",
            ]],
        ],
    },

    {
        "dt": "HD Ticket Type",
        "filters": [
            ["name", "in", ["Faults", "Service Request", "Assistance"]]
        ],
    },

    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "=", "HD Ticket"],
            ["fieldname", "in", [
                "custom_customer",
                "custom_site_group",
                "custom_fault_category",
                "custom_site",
                "custom_fault_asset",
                "custom_ownership_model",
                "custom_severity",
                "custom_equipment_ref",
                "custom_service_area",
                "custom_fulfilment_party",
                "custom_request_type",
                "custom_due_date",
                "custom_request_source",
                "custom_partner_acceptance_state",
                "custom_partner_accepted_on",
                "custom_partner_work_state",
                "custom_partner_work_completed",
            ]],
        ],
    },

    {
        "dt": "Number Card",
        "filters": [
            ["name", "in", [
                "TELECTRO Ops — Unassigned",
                "TELECTRO Ops — Unassigned above 60m",
                "TELECTRO Ops — Unclaimed above 4 hours",
                "TELECTRO Ops — Total Active",
                "TELECTRO Ops — Partner Queue",
                "Submitted by Partner",
                "Assigned to Partner",
            ]],
        ],
    },

    {
        "dt": "Dashboard Chart",
        "filters": [
            ["name", "in", [
                "Supervisor Active Work by Bucket",
            ]],
        ],
    },

    {
        "dt": "Client Script",
        "filters": [
            ["dt", "=", "HD Ticket"],
            ["enabled", "=", 1],
        ],
    },

    {
        "dt": "Property Setter",
        "filters": [
            ["doc_type", "=", "HD Ticket"],
            ["field_name", "=", "ticket_type"],
            ["property", "=", "default"],
        ],
    },

    {
        "dt": "Report",
        "filters": [
            ["name", "in", [
                "Active Tickets by Technician",
                "Aging and At-Risk Tickets",
                "Coordinator Uplift History",
                "First Response Missed",
                "My HD Tickets",
                "Tickets Assigned to Partner",
                "Partner Archived Tickets",
                "Tickets Submitted by Partner",
                "Supervisor Active Work by Bucket",
                "Supervisor Active Work by Owner Bucket",
                "Supervisor Team Load Snapshot",
                "Supervisor Team Snapshot",
                "Unclaimed Over 1 Day",
                "TELECTRO Assignment Handoff Audit",
                "TELECTRO Repeat Faults by Location",
                "Partner Acceptance Review",
                "Partner Acceptance Review Queue",
                "Partner Acceptance Rework Queue",
                "Partner Workflow War Room",
                "My Current Work",
                "Partner Current Work",
            ]],
        ],
    },

    {
        "dt": "Scheduled Job Type",
        "filters": [
            ["method", "=", "telephony.jobs.pull_pilot_inboxes.run"],
        ],
    },

    {
        "dt": "HD Team",
        "filters": [
            ["name", "in", ["PABX", "Routing", "Helpdesk Team"]],
        ],
    },
]

# ------------------
# Crons
# ------------------

scheduler_events = dict(globals().get("scheduler_events") or {})

cron_events = dict(scheduler_events.get("cron") or {})
minute_expr = "*/1 * * * *"
minute_jobs = list(cron_events.get(minute_expr) or [])

job_path = "telephony.jobs.pull_pilot_inboxes.run"
if job_path not in minute_jobs:
    minute_jobs.append(job_path)

cron_events[minute_expr] = minute_jobs
scheduler_events["cron"] = cron_events

# ------------------
# TELECTRO Pilot hooks
# ------------------
import os

doc_events = dict(globals().get("doc_events") or {})
doc_events.setdefault("HD Ticket", {})
doc_events.setdefault("DocShare", {})

def _append_hook(target, event, handler):
    cur = target.get(event)
    if not cur:
        target[event] = handler
        return
    if isinstance(cur, list):
        if handler not in cur:
            cur.append(handler)
        return
    if cur == handler:
        return
    target[event] = [cur, handler]

# Gate debug-only instrumentation (default OFF)
TELECTRO_DEBUG = os.getenv("TELECTRO_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")

# --- Partner Permissions ---
permission_query_conditions = {
    "HD Ticket": "telephony.permissions.hd_ticket_query_conditions",
}

# --- HD Ticket hooks ---
_append_hook(doc_events["HD Ticket"], "before_insert", "telephony.telectro_intake.populate_from_email")

_append_hook(doc_events["HD Ticket"], "after_insert", "telephony.telectro_round_robin.assign_after_insert")
_append_hook(doc_events["HD Ticket"], "after_insert", "telephony.docshare_guard.hd_ticket_after_insert")

# validate: keep deterministic order (routing seed first, then site guard, then assign/_assign hygiene)
doc_events["HD Ticket"]["validate"] = [
    "telephony.telectro_ticket_routing.seed_ticket_routing",
    "telephony.telectro_site_guard.validate_site_fields",
    "telephony.telectro_ticket_edit_guard.validate_ticket_edit_rights",
    "telephony.telectro_assign_sync.dedupe_assign_field",
    "telephony.partner_create.enforce_partner_create_v1",
    "telephony.partner_create.apply_partner_work_state",
    "telephony.partner_create.normalize_partner_train_fields",
]

_append_hook(doc_events["HD Ticket"], "on_update", "telephony.telectro_reassign_on_update.reassign_if_routing_changed")
_append_hook(doc_events["HD Ticket"], "on_update", "telephony.telectro_assign_sync.sync_ticket_assignments")
_append_hook(doc_events["HD Ticket"], "on_update", "telephony.docshare_guard.hd_ticket_on_update")

# --- DocShare debug hook (OFF by default) ---
if TELECTRO_DEBUG:
    _append_hook(doc_events["DocShare"], "before_insert", "telephony.debug_docshare.log_pool_hd_ticket_docshare")

# Redirect TELECTRO-POC Tech users off Helpdesk landing to War Room
app_include_js = list(globals().get("app_include_js") or [])
for p in [
    "/assets/telephony/js/telectro_home_redirect.js?v=2026-04-13-2",
    "/assets/telephony/js/telectro_datetime_guard.js?v=2026-02-25-1",
    "/assets/telephony/js/telectro_ops_workspace.js?v=2026-04-14-1",
    "/assets/telephony/js/partner_acceptance_review.js?v=2026-05-13-3",
    "/assets/telephony/js/partner_route_guard.js?v=2026-05-15-1",
    "/assets/telephony/js/telectro_handoff_action.js?v=2026-05-06-1",
]:
    if p not in app_include_js:
        app_include_js.append(p)

# monkey patches to guard against notification floods and assignment rule loops (pilot)
before_request = list(globals().get("before_request") or [])
for fn in [
    "telephony.monkey_patches.notification_log_guard.apply",
]:
    if fn not in before_request:
        before_request.append(fn)

before_job = list(globals().get("before_job") or [])
for fn in [
    "telephony.monkey_patches.notification_log_guard.apply",
]:
    if fn not in before_job:
        before_job.append(fn)

# Assignment-rule timeline debug is OFF by default.
# This is intentionally separate from TELECTRO_DEBUG because it writes visible HD Ticket comments.
TELECTRO_RULE_DEBUG_COMMENTS = bool(
    frappe.conf.get("telectro_rule_debug_comments")
)

if TELECTRO_RULE_DEBUG_COMMENTS:
    for fn in ["telephony.monkey_patches.assignment_rule_debug.apply"]:
        if fn not in before_request:
            before_request.append(fn)
        if fn not in before_job:
            before_job.append(fn)

# ✅ Whitelisted method overrides (must exist at module level)
override_whitelisted_methods = dict(globals().get("override_whitelisted_methods") or {})
override_whitelisted_methods.update({
    "frappe.desk.form.assign_to.add": "telephony.overrides.assign_to.add",
    "frappe.desk.form.assign_to.remove": "telephony.overrides.assign_to.remove",
    "frappe.desk.form.assign_to.remove_multiple": "telephony.overrides.assign_to.remove_multiple",
    "frappe.desk.form.assign_to.close_all_assignments": "telephony.overrides.assign_to.close_all_assignments",

    # ✅ Report alias (stops disabled-report login loops)
    "frappe.desk.query_report.get_script": "telephony.overrides.query_report.get_script",
    "frappe.desk.query_report.run": "telephony.overrides.query_report.run",
})