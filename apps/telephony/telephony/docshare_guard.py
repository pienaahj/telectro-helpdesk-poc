import frappe

POOL_USER = "helpdesk@local.test"

def _delete_pool_docshare(doctype, name):
    frappe.db.delete(
        "DocShare",
        {
            "share_doctype": doctype,
            "share_name": name,
            "user": POOL_USER,
        },
    )

def hd_ticket_after_insert(doc, method=None):
    # If ticket was inserted and pool docshare got created, remove it.
    _delete_pool_docshare(doc.doctype, doc.name)

def hd_ticket_on_update(doc, method=None):
    # If someone assigns back to pool and that triggers a share, remove it.
    _delete_pool_docshare(doc.doctype, doc.name)