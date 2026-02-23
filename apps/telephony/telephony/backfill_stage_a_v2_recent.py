import frappe

def _is_missing(v) -> bool:
    return not (v or "").strip()

def _has_tokens(body: str) -> tuple[bool, bool]:
    body = body or ""
    return ("SITE:" in body), ("ASSET:" in body)
    
def _to_int(v, default: int) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default


def run(limit: int = 30, dry_run: int = 1, require_tokens: int = 1):
    """
    Backfill Stage A v2 by replaying populate_ticket_from_communication() for recent tickets
    missing custom_site/custom_equipment_ref.

    Args:
      limit: last N tickets to consider
      dry_run: 1 = only report, 0 = apply backfill
      require_tokens: 1 = only backfill when SITE:/ASSET: tokens are present in Received comm body
    """
    from telephony.telectro_intake import populate_ticket_from_communication

    limit = _to_int(limit, 30)
    dry_run = _to_int(dry_run, 1)
    require_tokens = _to_int(require_tokens, 1)

    tickets = frappe.get_all(
        "HD Ticket",
        fields=[
            "name", "creation", "subject",
            "custom_site", "custom_equipment_ref",
            "customer", "email_account",
        ],
        order_by="creation desc",
        limit_page_length=limit,
        ignore_permissions=True,
    )

    cands = []
    for t in tickets:
        if _is_missing(t.get("custom_site")) or _is_missing(t.get("custom_equipment_ref")):
            cands.append(t)

    print(f"Last {limit} tickets: {len(tickets)}")
    print(f"Candidates missing site/equipment: {len(cands)}")
    print("---")

    stats = {
        "no_comm": 0,
        "with_tokens": 0,
        "no_tokens": 0,
        "attempted": 0,
        "updated": 0,
        "errors": 0,
    }

    for t in cands:
        tid = t["name"]

        comms = frappe.get_all(
            "Communication",
            filters={
                "reference_doctype": "HD Ticket",
                "reference_name": tid,
                "sent_or_received": "Received",
            },
            fields=["name", "creation", "subject", "sender", "content", "text_content"],
            order_by="creation desc",
            limit_page_length=1,
            ignore_permissions=True,
        )

        if not comms:
            stats["no_comm"] += 1
            print(
                tid, "-> NO Received Communication found",
                "| inbox=", (t.get("email_account") or ""),
                "| subj=", (t.get("subject") or "")[:60],
            )
            continue

        c = comms[0]
        body = (c.get("text_content") or c.get("content") or "") or ""
        has_site, has_asset = _has_tokens(body)

        if has_site or has_asset:
            stats["with_tokens"] += 1
        else:
            stats["no_tokens"] += 1

        before_site = (t.get("custom_site") or "")
        before_eq = (t.get("custom_equipment_ref") or "")

        print(
            tid,
            "-> COMM", c["name"],
            "| tokens:", ("SITE" if has_site else "-"), ("ASSET" if has_asset else "-"),
            "| before:", f"site='{before_site}'", f"eq='{before_eq}'",
            "| sender=", (c.get("sender") or "")[:40],
            "| subj=", (c.get("subject") or "")[:50],
        )

        if dry_run:
            continue

        if require_tokens and not (has_site or has_asset):
            continue

        try:
            stats["attempted"] += 1
            comm_doc = frappe.get_doc("Communication", c["name"])
            populate_ticket_from_communication(comm_doc)

            # re-read ticket after populate
            after = frappe.get_value(
                "HD Ticket",
                tid,
                ["custom_site", "custom_equipment_ref"],
                as_dict=True,
            ) or {}

            after_site = (after.get("custom_site") or "")
            after_eq = (after.get("custom_equipment_ref") or "")

            changed = (after_site != before_site) or (after_eq != before_eq)
            if changed:
                stats["updated"] += 1
                print("   ✅ updated ->", f"site='{after_site}'", f"eq='{after_eq}'")
            else:
                print("   ↪️  no change")

        except Exception as e:
            stats["errors"] += 1
            print("   ❌ error:", repr(e))

    print("---")
    print("Summary:")
    for k in ["with_tokens", "no_tokens", "no_comm", "attempted", "updated", "errors"]:
        print(f"  {k}: {stats[k]}")