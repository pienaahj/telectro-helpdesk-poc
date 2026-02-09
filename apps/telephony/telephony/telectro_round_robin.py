import frappe

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

def assign_after_insert(doc, method=None):
    # doc_event hook

    # If mirror is already set OR there is already canonical assignment, do nothing.
    if _is_assigned(doc.get("_assign")):
        return

    existing = _todo_assignees(doc.name)
    if existing:
        _mirror_assign_from_todo(doc)
        return

    group = _get_group(doc)
    assignee = _next_assignee(group)
    if not assignee:
        return

    # Create canonical assignment (ToDo) via core implementation.
    # Call core directly to avoid any pilot-tech restriction edge cases.
    from frappe.desk.form import assign_to as core_assign_to

    core_assign_to.add(
        {
            "doctype": "HD Ticket",
            "name": doc.name,
            "assign_to": [assignee],
            "description": "Auto-assigned (round-robin)",
        }
    )

    # Mirror compat field from canonical ToDo state
    _mirror_assign_from_todo(doc)

    # No manual commit — let the request/job transaction handle it.


import json

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
