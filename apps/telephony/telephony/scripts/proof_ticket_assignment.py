import frappe

def run(ticket=None):
    ticket = (str(ticket or "").strip())

    if not ticket or ticket in ("<ID>", "{ID}", "ID"):
        print("ERROR: missing/placeholder ticket id. Example:")
        print('  bench --site frontend execute telephony.scripts.proof_ticket_assignment.run --kwargs \'{"ticket":"420"}\'')
        return

    t = frappe.db.get_value(
        "HD Ticket",
        ticket,
        ["name", "creation", "modified", "email_account", "custom_service_area", "agent_group", "status", "_assign"],
        as_dict=True,
    )

    if not t:
        print(f"ERROR: HD Ticket not found: {ticket}")
        return

    print("Ticket:", t.get("name"))
    print("creation           :", t.get("creation"))
    print("modified           :", t.get("modified"))
    print("email_account      :", t.get("email_account"))
    print("custom_service_area :", t.get("custom_service_area"))
    print("agent_group        :", t.get("agent_group"))
    print("status             :", t.get("status"))
    print("_assign            :", t.get("_assign"))

    todos = frappe.get_all(
        "ToDo",
        filters={"reference_type": "HD Ticket", "reference_name": ticket},
        fields=["allocated_to", "status", "modified", "owner", "description"],
        order_by="modified asc",
        ignore_permissions=True,
        limit_page_length=50,
    )

    print("ToDos:", len(todos))
    for r in todos:
        print(
            "-",
            r.get("allocated_to"),
            "|",
            r.get("status"),
            "|",
            r.get("modified"),
            "| owner:",
            r.get("owner"),
            "|",
            (r.get("description") or ""),
        )
