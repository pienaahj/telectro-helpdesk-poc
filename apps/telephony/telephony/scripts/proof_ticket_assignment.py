import frappe

def run(ticket=None):
    # pick latest ticket if none provided
    if not ticket:
        ticket = frappe.get_all(
            "HD Ticket",
            order_by="creation desc",
            pluck="name",
            limit_page_length=1,
            ignore_permissions=True,
        )
        ticket = ticket[0] if ticket else None

    if not ticket:
        print("No HD Ticket found.")
        return

    t = frappe.db.get_value(
        "HD Ticket",
        ticket,
        ["name", "agent_group", "email_account", "custom_service_area", "status", "_assign", "creation", "modified"],
        as_dict=True,
    )

    print("Ticket:", t.get("name"))
    for k in ["creation", "modified", "email_account", "custom_service_area", "agent_group", "status", "_assign"]:
        print(k.ljust(18), ":", t.get(k))

    todos = frappe.get_all(
        "ToDo",
        filters={"reference_type": "HD Ticket", "reference_name": ticket},
        fields=["allocated_to", "status", "modified", "owner", "name"],
        order_by="modified asc",
        ignore_permissions=True,
        limit_page_length=50,
    )

    print("ToDos:", len(todos))
    for r in todos:
        print("-", r["allocated_to"], "|", r["status"], "|", r["modified"], "| owner:", r["owner"])
