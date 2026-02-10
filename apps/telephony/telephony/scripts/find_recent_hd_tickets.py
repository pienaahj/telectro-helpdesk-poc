import json
import frappe


def _parse_assign(assign_val) -> list[str]:
    """Return list of users from HD Ticket._assign JSON string."""
    if not assign_val:
        return []
    try:
        parsed = json.loads(assign_val) if isinstance(assign_val, str) else assign_val
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return []


def _todo_summary_for_tickets(ticket_names: list[str]) -> dict[str, dict]:
    """
    Return per-ticket summary of OPEN ToDos:
      { "<ticket>": { "open_count": int, "assignees": [..] } }
    Uses frappe.get_all for correctness across DB quirks.
    """
    ticket_names = [str(x).strip() for x in (ticket_names or []) if str(x).strip()]
    if not ticket_names:
        return {}

    rows = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ("in", ticket_names),
            "status": "Open",
        },
        fields=["reference_name", "allocated_to"],
        ignore_permissions=True,
        limit_page_length=1000,
    )

    out: dict[str, dict] = {}
    for name in ticket_names:
        out[name] = {"open_count": 0, "assignees": []}

    for r in rows or []:
        ticket = str(r.get("reference_name") or "").strip()
        u = str(r.get("allocated_to") or "").strip()
        if not ticket:
            continue

        if ticket not in out:
            out[ticket] = {"open_count": 0, "assignees": []}

        out[ticket]["open_count"] += 1
        if u and u not in out[ticket]["assignees"]:
            out[ticket]["assignees"].append(u)

    # stable output
    for v in out.values():
        v["assignees"].sort()

    return out



@frappe.whitelist()
def run(limit: int = 5):
    limit = int(limit or 5)

    rows = frappe.get_all(
        "HD Ticket",
        fields=[
            "name",
            "creation",
            "subject",
            "email_account",
            "custom_service_area",
            "agent_group",
            "_assign",
            "status",
        ],
        order_by="creation desc",
        limit_page_length=limit,
        ignore_permissions=True,
    )

    print("Recent HD Tickets:", len(rows))

    names = [str(r.get("name") or "").strip() for r in rows if r.get("name")]
    todo_map = _todo_summary_for_tickets(names)

    drift_count = 0
    drift_by_type = {"_assign_no_todo": 0, "todo_without_assign": 0}

    for r in rows:
        tid = str(r.get("name") or "").strip()
        assign_users = _parse_assign(r.get("_assign"))

        ts = todo_map.get(tid) or {"open_count": 0, "assignees": []}
        todos_open = int(ts.get("open_count") or 0)
        todo_users = ts.get("assignees") or []

        drift = ""
        if assign_users and todos_open == 0:
            drift = " | DRIFT:_assign_no_todo"
            drift_count += 1
            drift_by_type["_assign_no_todo"] += 1
        elif (not assign_users) and todos_open > 0:
            drift = " | DRIFT:todo_without_assign"
            drift_count += 1
            drift_by_type["todo_without_assign"] += 1

        print(
            tid,
            "|",
            r.get("creation"),
            "| acct=",
            r.get("email_account"),
            "| area=",
            r.get("custom_service_area"),
            "| group=",
            r.get("agent_group"),
            "| status=",
            r.get("status"),
            "| _assign=",
            r.get("_assign"),
            "| todos_open=",
            todos_open,
            "| todo_users=",
            json.dumps(todo_users),
            "| subject=",
            (r.get("subject") or "")[:80],
            drift,
        )

    # footer summary (CI-ish)
    print(
        "\nSummary:",
        "total=" + str(len(rows)),
        "| drift=" + str(drift_count),
        "| _assign_no_todo=" + str(drift_by_type["_assign_no_todo"]),
        "| todo_without_assign=" + str(drift_by_type["todo_without_assign"]),
    )

