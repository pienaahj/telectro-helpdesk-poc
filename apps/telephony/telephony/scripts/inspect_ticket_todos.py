import frappe

def run(ticket):
    rows = frappe.get_all(
        "ToDo",
        filters={"reference_type": "HD Ticket", "reference_name": str(ticket)},
        fields=["name", "allocated_to", "status", "owner", "assigned_by", "creation", "modified", "description"],
        order_by="creation asc",
        ignore_permissions=True,
        limit_page_length=50,
    )
    print("Ticket:", ticket, "ToDos:", len(rows))
    for r in rows:
        print(r)
