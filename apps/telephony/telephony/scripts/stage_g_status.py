import frappe

def run(limit: int = 10, per_inbox: int = 5):
    print("Stage G Status")
    print("=" * 80)

    # 1) Config snapshot
    print("\n--- Autoreply config ---")
    keys = [
        "telephony_autoreply_enabled",
        "telephony_autoreply_inboxes",
        "telephony_autoreply_require_customer",
        "telephony_autoreply_sender_block_prefixes",
        "telephony_autoreply_subject_block_contains",
    ]
    for k in keys:
        print(k, "=>", frappe.conf.get(k))

    # 2) Last send breadcrumbs
    c = frappe.cache()
    print("\n--- Last autoreply send breadcrumbs ---")
    bkeys = [
        "telephony:stage_a:last_autoreply_verdict",
        "telephony:stage_a:last_autoreply_sent_ok",
        "telephony:stage_a:last_autoreply_sent_at",
        "telephony:stage_a:last_autoreply_sent_to",
        "telephony:stage_a:last_autoreply_error",
    ]
    for k in bkeys:
        v = c.get_value(k)
        if k == "telephony:stage_a:last_autoreply_error" and v:
            v = v.replace("\n", "\\n")
            v = (v[:220] + "…") if len(v) > 220 else v
        print(k, "=>", v)

    # 3) Stage C matrix (reuse existing)
    print("\n--- Stage C matrix ---")
    from telephony.scripts.verify_stage_c_matrix import run as stage_c
    stage_c(limit=limit, per_inbox=per_inbox)