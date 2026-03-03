import frappe
import json

# Per-group round-robin pools
POOLS = {
    "Routing": ["tech.alfa@local.test", "tech.bravo@local.test"],
    "PABX": ["tech.charlie@local.test"],
    "SIM": ["tech.bravo@local.test"],
}

POOL_USER = "helpdesk@local.test"

def _seed_pool_if_unassigned(ticket: str, subject: str = "") -> None:
    # If already has an Open ToDo, don't interfere
    open_todos = _open_todos_for_ticket(ticket)
    if open_todos:
        return

    # If _assign already set, don't interfere
    assign_users = _parse_assign_users(frappe.db.get_value("HD Ticket", ticket, "_assign") or "")
    if assign_users:
        return

    # Create exactly one Open ToDo for pool user
    _ensure_open_todo(
        ticket,
        POOL_USER,
        desc=(subject or "Pool")[:140],
    )

    # Mirror _assign from ToDo (canonical truth)
    users = _todo_assignees(ticket)
    frappe.db.set_value("HD Ticket", ticket, "_assign", json.dumps(users), update_modified=False)

def _get_group(doc) -> str:
    return (doc.get("agent_group") or "").strip()

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



def _rr_group(group: str) -> str:
    return (group or "").strip()

def _rr_cursor_key(group: str) -> str:
    g = _rr_group(group)
    return f"telectro:rr:v1:idx:{g}"

def _rr_lock_key(group: str) -> str:
    g = _rr_group(group)
    return f"telectro:rr:v1:lock:{g}"

def _get_idx(group: str) -> int:
    try:
        v = frappe.cache().get_value(_rr_cursor_key(group))
        return int(v) if v is not None else 0
    except Exception:
        return 0

def _set_idx(group: str, idx: int) -> None:
    try:
        # If your cache supports expires_in_sec, you can add it; otherwise omit.
        frappe.cache().set_value(_rr_cursor_key(group), int(idx))
    except Exception:
        pass

def _next_assignee(group: str) -> str | None:
    pool = POOLS.get(_rr_group(group)) or []
    if not pool:
        return None

    with frappe.cache().lock(_rr_lock_key(group), timeout=10, wait=2):
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
    ticket = str(getattr(doc, "name", "") or "").strip()
    if not ticket:
        return

    group = _get_group(doc)

    # --- Seed pool for non-RR groups (e.g. Helpdesk Team) ---
    if group not in POOLS:
        _seed_pool_if_unassigned(ticket, subject=(doc.get("subject") or ""))
        return

    # --- Gate on canonical truth (ToDo), not on cache (_assign) ---
    open_todos = _open_todos_for_ticket(ticket)
    if open_todos:
        # keep newest allocated_to (first non-empty), close rest
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
    assignee = _next_assignee(group)
    if not assignee:
        return

    assignee = str(assignee).strip()
    if not assignee:
        return

    # Enforce exactly ONE Open ToDo for this ticket (owned by assignee)
    open_todos = _open_todos_for_ticket(ticket)

    kept = False
    for td in open_todos or []:
        allocated = (td.get("allocated_to") or "").strip()
        if (not kept) and allocated == assignee:
            kept = True
            continue
        frappe.db.set_value("ToDo", td["name"], "status", "Closed", update_modified=False)

    if not kept:
        _ensure_open_todo(ticket, assignee, desc=(doc.get("subject") or "Auto-assigned (round-robin)")[:140])

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
    return out

def _mirror_assign_from_todo(doc) -> None:
    users = _todo_assignees(doc.name)
    doc.db_set("_assign", json.dumps(users), update_modified=False)

def rr_reset(group: str) -> None:
    """Reset RR cursor for a given group (testing)."""
    frappe.cache().delete_value(_rr_cursor_key(group))