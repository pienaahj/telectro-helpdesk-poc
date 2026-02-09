import frappe

def run(limit=20):
    rows = frappe.get_all(
        "HD Ticket",
        fields=["name", "creation", "subject", "email_account", "custom_service_area", "agent_group", "_assign", "status"],
        order_by="creation desc",
        limit_page_length=int(limit),
        ignore_permissions=True,
    )

    print("Recent HD Tickets:", len(rows))
    for r in rows:
        print(
            r.get("name"),
            "|",
            r.get("creation"),
            "| acct=", r.get("email_account"),
            "| area=", r.get("custom_service_area"),
            "| group=", r.get("agent_group"),
            "| status=", r.get("status"),
            "| _assign=", r.get("_assign"),
            "| subject=", (r.get("subject") or "")[:80],
        )
