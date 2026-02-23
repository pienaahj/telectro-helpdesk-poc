import frappe

def _is_bounce_sender(sender: str) -> bool:
    s = (sender or "").strip().lower()
    return s.startswith("mailer-daemon@") or s.startswith("postmaster@")

def _is_bounce_subject(subject: str) -> bool:
    subj = (subject or "").strip().lower()
    return "undelivered mail returned to sender" in subj

def _is_bounce(comm: dict | None) -> bool:
    if not comm:
        return False
    return _is_bounce_sender(comm.get("sender")) or _is_bounce_subject(comm.get("subject"))

def _comm_body(comm_row: dict) -> str:
    return (comm_row.get("text_content") or comm_row.get("content") or "") or ""

def _has_tokens(body: str) -> tuple[bool, bool]:
    body = body or ""
    return ("SITE:" in body), ("ASSET:" in body)

def _latest_received_comm(ticket_id: str) -> dict | None:
    rows = frappe.get_all(
        "Communication",
        filters={
            "reference_doctype": "HD Ticket",
            "reference_name": ticket_id,
            "sent_or_received": "Received",
        },
        fields=["name", "creation", "sender", "subject", "content", "text_content"],
        order_by="creation desc",
        limit_page_length=1,
        ignore_permissions=True,
    )
    return rows[0] if rows else None

def run(limit: int = 30, per_inbox: int = 10, hide_bounces: int = 1, hide_closed_bounces: int = 1):
    """
    Stage C verification matrix.
    Prints latest tickets grouped by inbox and whether comm contains SITE/ASSET tokens.

    Args:
      limit: how many most recent tickets to scan
      per_inbox: how many rows to print per inbox group (0 = no cap)
    """
    
    hide_bounces = int(hide_bounces) if hide_bounces is not None else 1
    hide_closed_bounces = int(hide_closed_bounces) if hide_closed_bounces is not None else 1
    
    limit = int(limit) if limit is not None else 30
    per_inbox = int(per_inbox) if per_inbox is not None else 10

    c = frappe.cache()

    print("Stage C Verification Matrix")
    print("=" * 80)

    # 1) Cache breadcrumbs (what happened last)
    print("\n--- Stage A cache breadcrumbs ---")
    for k in [
        "telephony:stage_a:last_autoreply_to",
        "telephony:stage_a:last_autoreply_subject",
        "telephony:stage_a:last_autoreply_body",

        "telephony:stage_a:last_autoreply_verdict",
        "telephony:stage_a:last_autoreply_sent_ok",
        "telephony:stage_a:last_autoreply_sent_at",
        "telephony:stage_a:last_autoreply_sent_to",
        "telephony:stage_a:last_autoreply_error",

        "telephony:stage_a:last_ticket",
        "telephony:stage_a:last_updates",
        "telephony:stage_a:last_ok",
        "telephony:stage_a:last_sender",
        "telephony:stage_a:last_custom_customer",
        "telephony:stage_a:last_customer_map_reason",
        "telephony:stage_a:last_ticket_link",
        "telephony:stage_a:last_customer_confirm_link",
    ]:
        val = c.get_value(k)
        if k in ("telephony:stage_a:last_autoreply_body", "telephony:stage_a:last_autoreply_error") and val:
            val = val.replace("\n", "\\n")
            val = (val[:220] + "…") if len(val) > 220 else val
        print(k, "=>", val)

    # 2) Load last N tickets
    tickets = frappe.get_all(
        "HD Ticket",
        fields=[
            "name",
            "creation",
            "email_account",
            "subject",
            "custom_site",
            "custom_equipment_ref",
            "custom_customer",
            "status",
        ],
        order_by="creation desc",
        limit_page_length=limit,
        ignore_permissions=True,
    )

    # Group by inbox
    groups: dict[str, list[dict]] = {}
    for t in tickets:
        inbox = (t.get("email_account") or "UNKNOWN").strip() or "UNKNOWN"
        groups.setdefault(inbox, []).append(t)

    # 3) Print groups
    print("\n--- Tickets grouped by inbox ---")
    for inbox in sorted(groups.keys()):
        rows = groups[inbox]
        print(f"\n## Inbox: {inbox} (showing {min(len(rows), per_inbox) if per_inbox else len(rows)} / {len(rows)})")
        shown = 0

        for t in rows:
            if per_inbox and shown >= per_inbox:
                break

            tid = t["name"]
            comm = _latest_received_comm(tid)
            is_bounce = _is_bounce(comm)
            is_closed = ((t.get("status") or "").strip().lower() == "closed")

            if hide_bounces and is_bounce:
                # if hide_closed_bounces=1, only hide when actually closed; otherwise hide all bounces
                if (not hide_closed_bounces) or is_closed:
                    continue

            if comm:
                body = _comm_body(comm)
                has_site, has_asset = _has_tokens(body)
                token_str = ("SITE" if has_site else "-") + " " + ("ASSET" if has_asset else "-")
                sender = (comm.get("sender") or "")
                comm_id = comm.get("name")
                    
            else:
                token_str = "NO_COMM"
                sender = ""
                comm_id = None

            print(
                f"- {tid} | {t.get('creation')} | tokens: {token_str}"
                f" | cust={t.get('custom_customer') or ''}"
                f" | site={t.get('custom_site') or ''}"
                f" | eq={t.get('custom_equipment_ref') or ''}"
                f" | sender={sender}"
                f" | comm={comm_id or ''}"
                f" | subj={(t.get('subject') or '')[:70]}"
            )
            shown += 1

    # 4) Summary counts
    print("\n--- Summary ---")
    total = len(tickets)
    with_site = sum(1 for t in tickets if (t.get("custom_site") or "").strip())
    with_eq = sum(1 for t in tickets if (t.get("custom_equipment_ref") or "").strip())
    with_cust = sum(1 for t in tickets if (t.get("custom_customer") or "").strip())
    print("tickets_scanned:", total)
    print("tickets_with_custom_site:", with_site)
    print("tickets_with_custom_equipment_ref:", with_eq)
    print("tickets_with_custom_customer:", with_cust)