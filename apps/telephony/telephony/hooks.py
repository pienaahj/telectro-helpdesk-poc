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

# Redirect TELECTRO-POC Tech users off Helpdesk landing to War Room
app_include_js = [
    "/assets/telephony/js/telectro_home_redirect.js?v=2026-02-04-1",
]

# --- TELECTRO: Round-robin assignment for HD Ticket (pilot) ---
# Merge into existing dicts if they exist, otherwise create them.
doc_events = (globals().get("doc_events") or {})
doc_events.setdefault("HD Ticket", {})
doc_events["HD Ticket"]["after_insert"] = "telephony.telectro_round_robin.assign_after_insert"
doc_events["HD Ticket"]["validate"] = "telephony.telectro_assign_sync.dedupe_assign_field"
doc_events["HD Ticket"]["on_update"] = "telephony.telectro_assign_sync.sync_ticket_assignments"
doc_events["HD Ticket"]["before_insert"] = "telephony.telectro_intake.populate_from_email"

before_request = list(globals().get("before_request") or [])
if "telephony.monkey_patches.notification_log_guard.apply" not in before_request:
    before_request.append("telephony.monkey_patches.notification_log_guard.apply")

before_job = list(globals().get("before_job") or [])
if "telephony.monkey_patches.notification_log_guard.apply" not in before_job:
    before_job.append("telephony.monkey_patches.notification_log_guard.apply")

override_whitelisted_methods = (globals().get("override_whitelisted_methods") or {})
override_whitelisted_methods.update({
    "frappe.desk.form.assign_to.add": "telephony.overrides.assign_to.add",
    "frappe.desk.form.assign_to.remove": "telephony.overrides.assign_to.remove",
    "frappe.desk.form.assign_to.remove_multiple": "telephony.overrides.assign_to.remove_multiple",
    "frappe.desk.form.assign_to.close_all_assignments": "telephony.overrides.assign_to.close_all_assignments",

    # ✅ Report alias (stops disabled-report login loops)
    "frappe.desk.query_report.get_script": "telephony.overrides.query_report.get_script",
    "frappe.desk.query_report.run": "telephony.overrides.query_report.run",
})

override_doctype_class = (globals().get("override_doctype_class") or {})
override_doctype_class.update({
    "Email Account": "helpdesk.overrides.email_account.CustomEmailAccount",
})
