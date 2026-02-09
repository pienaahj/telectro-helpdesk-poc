import frappe
from telephony import telectro_claim

def run(ticket, to_user="helpdesk@local.test"):
    ticket = str(ticket).strip()
    print("Ticket:", ticket)

    # 0) baseline
    t0 = frappe.db.get_value("HD Ticket", ticket, ["_assign", "agent_group", "email_account"], as_dict=True)
    print("Before _assign:", t0.get("_assign"), "| group:", t0.get("agent_group"), "| acct:", t0.get("email_account"))

    # 1) claim as Administrator (bench execute runs as Administrator effectively)
    r1 = telectro_claim.telectro_claim_ticket(ticket)
    print("Claim result:", r1)

    # 2) show after claim
    t1 = frappe.db.get_value("HD Ticket", ticket, ["_assign"], as_dict=True)
    print("After claim _assign:", t1.get("_assign"))

    todos1 = frappe.get_all(
        "ToDo",
        filters={"reference_type":"HD Ticket", "reference_name":ticket},
        fields=["allocated_to","status","description","modified"],
        order_by="modified asc",
        ignore_permissions=True,
    )
    print("ToDos after claim:", len(todos1))
    for r in todos1:
        print("-", r)

    # 3) handoff
    r2 = telectro_claim.telectro_handoff_ticket(ticket, to_user, reason="proof")
    print("Handoff result:", r2)

    # 4) show after handoff
    t2 = frappe.db.get_value("HD Ticket", ticket, ["_assign"], as_dict=True)
    print("After handoff _assign:", t2.get("_assign"))

    todos2 = frappe.get_all(
        "ToDo",
        filters={"reference_type":"HD Ticket", "reference_name":ticket},
        fields=["allocated_to","status","description","modified"],
        order_by="modified asc",
        ignore_permissions=True,
    )
    print("ToDos after handoff:", len(todos2))
    for r in todos2:
        print("-", r)
