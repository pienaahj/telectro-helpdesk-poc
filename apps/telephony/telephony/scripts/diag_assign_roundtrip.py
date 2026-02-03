import frappe
from frappe.desk.form import assign_to as core
from telephony.overrides import assign_to as ov

def _todos(doctype, name):
    # ToDo stores assignments (reference_type/reference_name)
    return frappe.get_all(
        "ToDo",
        filters={"reference_type": doctype, "reference_name": name, "status": ("!=", "Cancelled")},
        fields=["name", "owner", "allocated_to", "status", "description"],
        limit_page_length=50,
    )

def run(ticket=None):
    doctype = "HD Ticket"
    if not ticket:
        ticket = frappe.get_all(doctype, pluck="name", limit=1)[0]

    print("ticket:", ticket)

    # Clean slate: remove ToDos for this ticket and clear _assign
    for t in _todos(doctype, ticket):
        frappe.delete_doc("ToDo", t["name"], force=1)
    frappe.db.set_value(doctype, ticket, "_assign", "", update_modified=False)
    frappe.db.commit()

    print("before _assign:", frappe.db.get_value(doctype, ticket, "_assign"))
    print("before todos:", _todos(doctype, ticket))

    # Create a REAL assignment via core API (creates ToDo + updates _assign)
    core.add({
        "doctype": doctype,
        "name": ticket,
        "assign_to": ["Administrator"],
        "description": "diag assign roundtrip",
        "notify": 0,
    })
    frappe.db.commit()

    print("after add _assign:", frappe.db.get_value(doctype, ticket, "_assign"))
    print("after add todos:", _todos(doctype, ticket))

    # Now bulk-remove via your override (should delete ToDo + clear _assign)
    ov.remove_multiple(doctype, f'["{ticket}"]', 0)
    frappe.db.commit()

    print("after remove_multiple _assign:", frappe.db.get_value(doctype, ticket, "_assign"))
    print("after remove_multiple todos:", _todos(doctype, ticket))

    print("done")