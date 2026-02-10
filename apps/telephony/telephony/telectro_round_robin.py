import frappe
import json

# Per-group round-robin pools
POOLS = {
    "Routing": ["tech.alfa@local.test", "tech.bravo@local.test"],
    "PABX": ["tech.charlie@local.test"],
    "SIM": ["tech.bravo@local.test"],
}

def _is_assigned(assign_val) -> bool:
    return bool(assign_val) and assign_val not in ("", "[]", [], None)

def _get_group(doc) -> str:
    return (doc.get("agent_group") or doc.get("email_account") or "").strip()

def _parse_assign_users(assign_val) -> list[str]:
    """HD Ticket._assign is usually a JSON string like '["user@x"]'. Return list of users."""
    if not assign_val:
        return []
    if isinstance(assign_val, list):
        return [str(x).strip() for x in assign_val if str(x).strip()]
    if not isinstance(assign_val, str):
        return []
    s = assign_val.strip()
    if not s:
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return []


def _open_todos_for_ticket(ticket: str):
    return frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "status": "Open",
        },
        fields=["name", "allocated_to", "creation"],
        order_by="creation desc",  # newest first
        ignore_permissions=True,
        limit_page_length=200,
    )



def _rr_key(group: str) -> str:
    # Stored in tabSingles under doctype "TELECTRO_RR" (arbitrary keyspace)
    return f"rr_idx__{group}"

def _get_idx(group: str) -> int:
    key = _rr_key(group)
    rows = frappe.db.sql(
        """
        SELECT value
        FROM tabSingles
        WHERE doctype = %s AND field = %s
        """,
        ("TELECTRO_RR", key),
        as_dict=True,
    )
    if not rows:
        return 0
    try:
        return int(rows[0].get("value") or 0)
    except Exception:
        return 0

def _set_idx(group: str, idx: int) -> None:
    key = _rr_key(group)
    # Upsert into tabSingles
    frappe.db.sql(
        """
        INSERT INTO tabSingles (doctype, field, value)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE value = VALUES(value)
        """,
        ("TELECTRO_RR", key, str(int(idx))),
    )

def _next_assignee(group: str) -> str | None:
    pool = POOLS.get(group) or []
    if not pool:
        return None

    idx = _get_idx(group)
    assignee = pool[idx % len(pool)]
    _set_idx(group, idx + 1)
    return assignee

def _ensure_open_todo(ticket_name: str, assignee: str, desc: str = "") -> None:
    ticket_name = (ticket_name or "").strip()
    assignee = (assignee or "").strip()
    if not ticket_name or not assignee:
        return

    exists = frappe.db.exists(
        "ToDo",
        {
            "reference_type": "HD Ticket",
            "reference_name": ticket_name,
            "allocated_to": assignee,
            "status": "Open",
        },
    )
    if exists:
        return

    frappe.get_doc(
        {
            "doctype": "ToDo",
            "allocated_to": assignee,
            "reference_type": "HD Ticket",
            "reference_name": ticket_name,
            "status": "Open",
            "description": (desc or "")[:140],
        }
    ).insert(ignore_permissions=True)


def assign_after_insert(doc, method=None):
    # doc_event hook
    ticket = str(doc.name).strip()
    if not ticket:
        return

    # --- Gate on canonical truth (ToDo), not on cache (_assign) ---

    open_todos = _open_todos_for_ticket(ticket)
    if open_todos:
        # If multiple Open ToDos exist, keep newest and close the rest (or keep first)
        keep = None
        for td in open_todos:
            u = (td.get("allocated_to") or "").strip()
            if u:
                keep = u
                break

        if keep:
            kept = False
            for td in open_todos:
                u = (td.get("allocated_to") or "").strip()
                if (not kept) and u == keep:
                    kept = True
                    continue
                frappe.db.set_value("ToDo", td["name"], "status", "Closed", update_modified=False)

        _mirror_assign_from_todo(doc)
        return

    assign_users = _parse_assign_users(doc.get("_assign"))
    if assign_users:
        # Drift repair: _assign exists but no Open ToDo → recreate ToDo then mirror
        assignee = assign_users[0]
        _ensure_open_todo(
            ticket,
            assignee,
            desc=(doc.get("subject") or "Repair: recreate missing ToDo"),
        )
        _mirror_assign_from_todo(doc)
        return

    # --- Normal RR path (unassigned + no ToDo) ---

    group = _get_group(doc)
    assignee = _next_assignee(group)
    if not assignee:
        return

    assignee = str(assignee).strip()
    if not assignee:
        return

    # 1) Canonical: enforce exactly ONE Open ToDo for this ticket (owned by assignee)
    open_todos = _open_todos_for_ticket(ticket)

    kept = False
    for td in open_todos or []:
        allocated = (td.get("allocated_to") or "").strip()

        if (not kept) and allocated == assignee:
            kept = True
            continue

        frappe.db.set_value("ToDo", td["name"], "status", "Closed", update_modified=False)

    if not kept:
        frappe.get_doc(
            {
                "doctype": "ToDo",
                "allocated_to": assignee,
                "reference_type": "HD Ticket",
                "reference_name": ticket,
                "status": "Open",
                "description": (doc.get("subject") or "Auto-assigned (round-robin)")[:140],
            }
        ).insert(ignore_permissions=True)

    # 2) Mirror cache for list views / filters (ToDo is truth)
    _mirror_assign_from_todo(doc)

    # IMPORTANT: no frappe.db.commit() here

def _todo_assignees(ticket_name: str) -> list[str]:
    rows = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket_name,
            "status": "Open",
        },
        pluck="allocated_to",
        ignore_permissions=True,
    )
    out = []
    seen = set()
    for u in rows or []:
        u = (u or "").strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    out.sort()
    return out

def _mirror_assign_from_todo(doc) -> None:
    users = _todo_assignees(doc.name)
    doc.db_set("_assign", json.dumps(users), update_modified=False)
