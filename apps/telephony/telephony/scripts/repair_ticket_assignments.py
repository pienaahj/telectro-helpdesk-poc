import json
import frappe


def _parse_assign(assign_val) -> list[str]:
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


def _user_exists(user: str) -> bool:
    user = (user or "").strip()
    if not user:
        return False
    return bool(frappe.db.exists("User", user))


def _open_todos(ticket: str) -> list[dict]:
    # newest first so "keep first" is deterministic
    return frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "status": "Open",
        },
        fields=["name", "allocated_to", "creation", "description"],
        order_by="creation desc",
        ignore_permissions=True,
        limit_page_length=200,
    )


def _close_todo(name: str, dry_run: int):
    if dry_run:
        return
    frappe.db.set_value("ToDo", name, "status", "Closed", update_modified=False)


def _ensure_open_todo(ticket: str, user: str, desc: str, dry_run: int):
    ticket = (ticket or "").strip()
    user = (user or "").strip()
    if not ticket or not user:
        return
    if not _user_exists(user):
        return

    exists = frappe.db.exists(
        "ToDo",
        {
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "allocated_to": user,
            "status": "Open",
        },
    )
    if exists:
        return

    if dry_run:
        return

    frappe.get_doc(
        {
            "doctype": "ToDo",
            "allocated_to": user,
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "status": "Open",
            "description": (desc or "")[:140],
        }
    ).insert(ignore_permissions=True)


def _mirror_assign_from_open_todos(ticket: str, dry_run: int):
    todos = _open_todos(ticket)  # newest first
    users = []
    seen = set()

    # preserve canonical ordering (newest first)
    for td in todos:
        u = (td.get("allocated_to") or "").strip()
        if u and u not in seen:
            seen.add(u)
            users.append(u)

    if dry_run:
        return users

    frappe.db.set_value("HD Ticket", ticket, "_assign", json.dumps(users), update_modified=False)
    return users


def _repair_one(ticket: str, prefer_assign: int, dry_run: int) -> dict:
    """
    prefer_assign:
      0 = prefer Open ToDo (canonical)
      1 = if no Open ToDo, recreate from _assign[0]
    """
    t = frappe.db.get_value(
        "HD Ticket",
        ticket,
        ["name", "subject", "status", "_assign"],
        as_dict=True,
    )
    if not t:
        return {"ticket": ticket, "ok": 0, "reason": "missing_ticket"}

    subj = (t.get("subject") or "").strip()
    assign_users = _parse_assign(t.get("_assign"))
    todos = _open_todos(ticket)

    changed = 0
    actions = []

    # Case A: multiple Open ToDos -> keep newest (first with allocated_to), close others
    if len(todos) > 1:
        keep_todo = None
        for td in todos:
            u = (td.get("allocated_to") or "").strip()
            if u:
                keep_todo = td["name"]
                break

        if keep_todo:
            for td in todos:
                if td["name"] == keep_todo:
                    continue
                _close_todo(td["name"], dry_run)
                changed = 1
                actions.append(f"close_todo:{td['name']}")

            actions.append(f"kept_todo:{keep_todo}")
            todos = _open_todos(ticket)

    # Case B: no Open ToDo, but _assign exists -> recreate ToDo (repair drift)
    if (not todos) and assign_users and prefer_assign:
        owner = assign_users[0]
        if _user_exists(owner):
            _ensure_open_todo(
                ticket,
                owner,
                desc=(subj or "Repair: recreate missing ToDo"),
                dry_run=dry_run,
            )
            actions.append(f"create_todo:{owner}")
            changed = 1
            todos = _open_todos(ticket)
        else:
            actions.append(f"skip_create_todo_invalid_user:{owner}")

    # Case C: Open ToDo exists -> mirror _assign from ToDo (canonical)
    if todos:
        before = assign_users
        after = _mirror_assign_from_open_todos(ticket, dry_run=dry_run)
        if before != after:
            changed = 1
            actions.append(f"mirror_assign:{before}->{after}")

    return {
        "ticket": ticket,
        "status": t.get("status"),
        "assign": t.get("_assign"),
        "todos_open": len(todos),
        "todo_users": [(td.get("allocated_to") or "").strip() for td in (todos or [])],
        "changed": changed,
        "actions": actions,
        "dry_run": int(bool(dry_run)),
    }


@frappe.whitelist()
def run(limit: int = 50, dry_run: int = 1, prefer_assign: int = 1, only_open: int = 1):
    """
    Repair assignment drift for recent tickets.

    Args:
      limit: how many newest HD Tickets to scan
      dry_run: 1=report only, 0=apply changes
      prefer_assign: if no Open ToDo but _assign exists, recreate ToDo from _assign[0]
      only_open: 1=only status='Open', 0=all statuses
    """
    limit = int(limit or 50)
    dry_run = 1 if int(dry_run or 0) else 0
    prefer_assign = 1 if int(prefer_assign or 0) else 0
    only_open = 1 if int(only_open or 0) else 0

    print("=== Repair Ticket Assignments ===")
    print("limit        :", limit)
    print("dry_run      :", dry_run)
    print("prefer_assign:", prefer_assign)
    print("only_open    :", only_open)

    filters = {}
    if only_open:
        filters["status"] = "Open"

    rows = frappe.get_all(
        "HD Ticket",
        filters=filters,
        fields=["name", "creation"],
        order_by="creation desc",
        limit_page_length=limit,
        ignore_permissions=True,
    )

    print("\nTickets scanned:", len(rows))

    changed = 0
    for r in rows:
        tid = str(r.get("name") or "").strip()
        res = _repair_one(tid, prefer_assign=prefer_assign, dry_run=dry_run)
        if res.get("changed"):
            changed += 1
            print(
                "-",
                res["ticket"],
                "| todos_open=",
                res["todos_open"],
                "| todo_users=",
                json.dumps(res["todo_users"]),
                "| actions=",
                json.dumps(res["actions"]),
            )

    print("\nSummary: scanned=", len(rows), "| changed=", changed, "| dry_run=", dry_run)
