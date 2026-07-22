import json
import frappe
import traceback

POOL_USER = "helpdesk@local.test"
MARKER = "TELECTRO_DOCSHARE_HOOK_FIRED"

def log_pool_hd_ticket_docshare(doc, method=None):
    if (doc.get("share_doctype") or "") != "HD Ticket":
        return
    if (doc.get("user") or "") != POOL_USER:
        return

    stack = traceback.format_stack(limit=60)  # enough to show who called insert()

    payload = {
        "marker": MARKER,
        "share_doctype": doc.get("share_doctype"),
        "share_name": doc.get("share_name"),
        "user": doc.get("user"),
        "owner": doc.get("owner"),
        "session_user": getattr(getattr(frappe, "session", None), "user", None),
        "stack": stack,
    }

    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Comment",
        "reference_doctype": "HD Ticket",
        "reference_name": doc.get("share_name"),
        "content": json.dumps(payload, default=str)[:8000],
    }).insert(ignore_permissions=True)