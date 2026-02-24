__version__ = "2026-02-24b"
from datetime import timedelta
import frappe

def _is_test_ticket_subject(subject: str) -> bool:
    s = (subject or "").lower()
    needles = [
        "smoke:",
        "proof",
        "test ticket",
        "[bi-manual]",
        "race test",
        "testing ",
    ]
    return any(n in s for n in needles)

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

def run(
    limit: int = 10,
    per_inbox: int = 5,
    show_config: int = 0,
    show_breadcrumbs: int = 1,
    show_unknown_samples: int = 0,
    show_stage_c: int = 0,
):
    print("Stage G Status")
    print("=" * 80)

    # --- Bounce volume ---
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

    # --- Open tickets per inbox ---
    print("\n--- Open non-bounce tickets per inbox ---")
    tickets = frappe.get_all(
        "HD Ticket",
        fields=["name", "email_account", "status", "subject", "creation"],
        filters={"status": ["!=", "Closed"]},
        limit_page_length=2000,
        ignore_permissions=True,
    )

    counts = {}
    unknown = []
    test_skipped = 0
    
    for t in tickets:
        subj = (t.get("subject") or "")

        # skip bounce/system
        if "Undelivered Mail Returned to Sender" in subj:
            continue

        # skip proof/smoke/test tickets from operator stats
        if _is_test_ticket_subject(subj):
            test_skipped += 1
            continue

        inbox = (t.get("email_account") or "UNKNOWN").strip() or "UNKNOWN"
        counts[inbox] = counts.get(inbox, 0) + 1

        if inbox == "UNKNOWN":
            unknown.append(t)

    for inbox in sorted(counts.keys()):
        print(f"{inbox}: {counts[inbox]}")

    print("\nopen_non_bounce_total:", sum(counts.values()))
    print("open_non_bounce_unknown:", counts.get("UNKNOWN", 0))
    print("open_non_bounce_test_skipped:", test_skipped)

    if show_unknown_samples and unknown:
        print(f"\n--- UNKNOWN sample (top {show_unknown_samples}) ---")
        unknown_sorted = sorted(unknown, key=lambda x: x.get("creation") or "", reverse=True)
        for t in unknown_sorted[: int(show_unknown_samples)]:
            print(t["name"], "|", t.get("creation"), "|", (t.get("subject") or "")[:80])

    if show_config:
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

    if show_breadcrumbs:
        c = frappe.cache()
        print("\n--- Last autoreply send breadcrumbs ---")
        bkeys = [
            "telephony:stage_a:last_autoreply_verdict",
            "telephony:stage_a:last_autoreply_sent_ok",
            "telephony:stage_a:last_autoreply_sent_at",
            "telephony:stage_a:last_autoreply_sent_to",
            "telephony:stage_a:last_autoreply_error",
            # non-bounce sender breadcrumbs
            "telephony:stage_a:last_sender_non_bounce",
            "telephony:stage_a:last_sender_non_bounce_at",
            "telephony:stage_a:last_sender_non_bounce_to",
            "telephony:stage_a:last_sender_non_bounce_subject",
        ]
        shown = 0
        out = []

        for k in bkeys:
            v = c.get_value(k)

            if k == "telephony:stage_a:last_autoreply_error" and v:
                v = v.replace("\n", "\\n")
                v = (v[:220] + "…") if len(v) > 220 else v

            if not v:
                continue

            out.append((k, v))
            shown += 1

        if shown:
            print("\n--- Last autoreply send breadcrumbs ---")
            for k, v in out:
                print(k, "=>", v)

print("breadcrumbs_present:", shown, "/", len(bkeys))

    if show_stage_c:
        print("\n--- Stage C matrix ---")
        from telephony.scripts.verify_stage_c_matrix import run as stage_c
        stage_c(limit=limit, per_inbox=per_inbox, hide_bounces=1, hide_closed_bounces=0)