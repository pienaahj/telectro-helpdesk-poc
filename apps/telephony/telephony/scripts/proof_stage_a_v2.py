# telephony/scripts/proof_stage_a_v2.py
import frappe

def run(limit=10):
    cache = frappe.cache()
    last_ticket = cache.get_value("telephony:stage_a:last_ticket")
    last_updates = cache.get_value("telephony:stage_a:last_updates")
    last_ok = cache.get_value("telephony:stage_a:last_ok")

    print("\nStage A v2 breadcrumbs")
    print("last_ticket :", last_ticket)
    print("last_updates:", last_updates)
    print("last_ok     :", last_ok)

    print("\nLatest HD Tickets (sanity)")
    rows = frappe.get_all(
        "HD Ticket",
        fields=["name", "creation", "custom_site", "custom_equipment_ref", "custom_customer", "subject"],
        order_by="creation desc",
        limit=limit,
        ignore_permissions=True,
    )
    for r in rows:
        print(r["creation"], "|", r["name"], "|", r.get("custom_site"), "|", r.get("custom_equipment_ref"), "|", r.get("custom_customer"), "|", r.get("subject"))
    print("")