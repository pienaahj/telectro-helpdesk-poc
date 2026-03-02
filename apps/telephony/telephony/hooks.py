app_name = "telephony"
app_title = "Telephony"
app_publisher = "Frappe Technologies Pvt. Ltd."
app_description = "Telephony for Frappe apps"
app_email = "pratik@frappe.io"
app_license = "agpl-3.0"


fixtures = [
    {"dt": "Role", "filters": [["role_name", "like", "TP%"]]},

    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "=", "HD Ticket"],
            ["fieldname", "in", ["custom_equipment_ref"]],
        ],
    },

    {
        "dt": "Client Script",
        "filters": [
            ["dt", "=", "HD Ticket"],
            ["name", "in", [
                "Clear Customer and filter List",
                "Claim HD Ticket",
                "Pull Faults",
            ]],
        ],
    },
]


# ------------------
# TELECTRO Pilot hooks
# ------------------

# --- TELECTRO: Round-robin assignment for HD Ticket (pilot) ---
doc_events = (globals().get("doc_events") or {})

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

doc_events.setdefault("HD Ticket", {})
doc_events.setdefault("DocShare", {})

# make it merge-safe like your other hooks
cur = doc_events["DocShare"].get("before_insert")
if not cur:
    doc_events["DocShare"]["before_insert"] = "telephony.debug_docshare.log_pool_hd_ticket_docshare"
elif isinstance(cur, list):
    if "telephony.debug_docshare.log_pool_hd_ticket_docshare" not in cur:
        cur.append("telephony.debug_docshare.log_pool_hd_ticket_docshare")
elif cur != "telephony.debug_docshare.log_pool_hd_ticket_docshare":
    doc_events["DocShare"]["before_insert"] = [cur, "telephony.debug_docshare.log_pool_hd_ticket_docshare"]

# keep existing after_insert, but add docshare guard too
_append_hook(doc_events["HD Ticket"], "after_insert", "telephony.telectro_round_robin.assign_after_insert")
_append_hook(doc_events["HD Ticket"], "after_insert", "telephony.docshare_guard.hd_ticket_after_insert")

# validate is already a list (leave as-is)
doc_events["HD Ticket"]["validate"] = [
    "telephony.telectro_assign_sync.dedupe_assign_field",
    "telephony.telectro_site_guard.validate_site_fields",
]

# keep existing on_update, add docshare guard too
_append_hook(doc_events["HD Ticket"], "on_update", "telephony.telectro_assign_sync.sync_ticket_assignments")
_append_hook(doc_events["HD Ticket"], "on_update", "telephony.docshare_guard.hd_ticket_on_update")

# before_insert remains unchanged
doc_events["HD Ticket"]["before_insert"] = "telephony.telectro_intake.populate_from_email"

# Redirect TELECTRO-POC Tech users off Helpdesk landing to War Room
app_include_js = list(globals().get("app_include_js") or [])
for p in [
    "/assets/telephony/js/telectro_home_redirect.js?v=2026-02-04-1",
    "/assets/telephony/js/telectro_datetime_guard.js?v=2026-02-25-1",
]:
    if p not in app_include_js:
        app_include_js.append(p)

# monkey pathes to guard against notification floods and assignment rule loops (pilot)
before_request = list(globals().get("before_request") or [])
for fn in [
  "telephony.monkey_patches.notification_log_guard.apply",
  "telephony.monkey_patches.assignment_rule_debug.apply",
]:
  if fn not in before_request:
    before_request.append(fn)

before_job = list(globals().get("before_job") or [])
for fn in [
  "telephony.monkey_patches.notification_log_guard.apply",
  "telephony.monkey_patches.assignment_rule_debug.apply",
]:
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