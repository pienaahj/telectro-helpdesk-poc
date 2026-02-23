from datetime import timedelta
import frappe

def _dt_hours_ago(hours: int):
    return frappe.utils.now_datetime() - timedelta(hours=hours)

def _is_bounce_row(sender: str, subject: str) -> bool:
    s = (sender or "").strip().lower()
    subj = (subject or "").strip().lower()
    if s.startswith("mailer-daemon@") or s.startswith("postmaster@"):
        return True
    if "undelivered mail returned to sender" in subj:
        return True
    return False

def run(limit: int = 10, per_inbox: int = 5):
    print("Stage G Status")
    print("=" * 80)
    
    print("\n--- Bounce volume (from Received Communications) ---")

    since_24h = _dt_hours_ago(24)
    since_1h = _dt_hours_ago(1)

    def count_bounces(since_dt):
        rows = frappe.get_all(
            "Communication",
            filters={
                "sent_or_received": "Received",
                "reference_doctype": "HD Ticket",
                "creation": [">=", since_dt],
            },
            fields=["sender", "subject"],
            limit_page_length=2000,
            ignore_permissions=True,
        )
        return sum(1 for r in rows if _is_bounce_row(r.get("sender"), r.get("subject")))

    b24 = count_bounces(since_24h)
    b1 = count_bounces(since_1h)
    print("bounces_last_24h:", b24)
    print("bounces_last_1h :", b1)
    
    print("\n--- Open non-bounce tickets per inbox ---")

    tickets = frappe.get_all(
        "HD Ticket",
        fields=["email_account", "status", "subject"],
        filters={"status": ["!=", "Closed"]},
        limit_page_length=2000,
        ignore_permissions=True,
    )

    counts = {}
    for t in tickets:
        subj = (t.get("subject") or "")
        if "Undelivered Mail Returned to Sender" in subj:
            continue
        inbox = (t.get("email_account") or "UNKNOWN").strip() or "UNKNOWN"
        counts[inbox] = counts.get(inbox, 0) + 1

    for inbox in sorted(counts.keys()):
        print(f"{inbox}: {counts[inbox]}")

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
    stage_c(limit=limit, per_inbox=per_inbox, hide_bounces=1, hide_closed_bounces=0)