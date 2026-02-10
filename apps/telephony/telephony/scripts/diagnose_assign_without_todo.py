import frappe

SUSPICIOUS_NEEDLES = [
    "_assign",
    "assign_to",
    "ToDo",
    "tabToDo",
    "frappe.desk.form.assign_to",
    "add_assign",
    "remove_assign",
    "allocated_to",
]

TARGET_SCRIPT_NAMES = [
    "TELECTRO Task Routing + Assign - before",
    "TELECTRO Task Routing + Assign - after",
    "Pull pilot inboxes",
    "Pull faults",
]


def _print_kv(label, val):
    print(f"{label:<20}: {val}")


def _safe_get_server_script(name: str):
    if not frappe.db.exists("Server Script", name):
        return None
    try:
        return frappe.get_doc("Server Script", name)
    except Exception as e:
        print(f"!! Failed to load Server Script '{name}': {e}")
        return None


def _todos_for_ticket(ticket: str):
    rows = frappe.get_all(
        "ToDo",
        filters={"reference_type": "HD Ticket", "reference_name": ticket},
        fields=["name", "status", "allocated_to", "owner", "creation", "description"],
        order_by="creation desc",
        ignore_permissions=True,
        limit_page_length=50,
    )
    return rows


def _todos_any_reference_type(ticket: str):
    return frappe.db.sql(
        """
        SELECT name, reference_type, reference_name, status, allocated_to, owner, creation, description
        FROM tabToDo
        WHERE reference_name=%s
        ORDER BY creation DESC
        LIMIT 50
        """,
        (ticket,),
        as_dict=True,
    )

def _print_script_head(doc, max_lines: int = 60):
    code = (doc.script or "").strip()
    if not code:
        print("  (no script body)")
        return

    lines = code.splitlines()
    print("\n".join(lines[:max_lines]))
    if len(lines) > max_lines:
        print("  ... (truncated)")

def _find_suspicious_server_scripts(limit: int = 200):
    like_clauses = " OR ".join(["script LIKE %s" for _ in SUSPICIOUS_NEEDLES])
    params = [f"%{n}%" for n in SUSPICIOUS_NEEDLES]

    rows = frappe.db.sql(
        f"""
        SELECT name, script_type, disabled
        FROM `tabServer Script`
        WHERE IFNULL(script,'') != ''
          AND ({like_clauses})
        ORDER BY modified DESC
        LIMIT {int(limit)}
        """,
        params,
        as_dict=True,
    )
    return rows


@frappe.whitelist()
def run(ticket: str, limit: int = 200):
    ticket = str(ticket).strip()
    print("=== Diagnose: _assign set but ToDo missing ===")
    _print_kv("ticket", ticket)

    if not frappe.db.exists("HD Ticket", ticket):
        print("!! Ticket not found")
        return

    t = frappe.get_doc("HD Ticket", ticket)

    print("\n--- Ticket fields ---")
    _print_kv("creation", t.get("creation"))
    _print_kv("modified", t.get("modified"))
    _print_kv("status", t.get("status"))
    _print_kv("subject", t.get("subject"))
    _print_kv("email_account", t.get("email_account"))
    _print_kv("custom_service_area", t.get("custom_service_area"))
    _print_kv("agent_group", t.get("agent_group"))
    _print_kv("_assign", t.get("_assign"))

    print("\n--- ToDos (reference_type='HD Ticket') ---")
    rows = _todos_for_ticket(ticket)
    print("count:", len(rows))
    for r in rows:
        print(" ", r["name"], "|", r["status"], "|", r.get("allocated_to"), "|", r.get("creation"))

    print("\n--- ToDos (any reference_type, by reference_name) ---")
    rows2 = _todos_any_reference_type(ticket)
    print("count:", len(rows2))
    for r in rows2:
        print(" ", r["name"], "|", r["reference_type"], "|", r["status"], "|", r.get("allocated_to"), "|", r.get("creation"))

    print("\n--- Target Server Scripts (by name) ---")
    for name in TARGET_SCRIPT_NAMES:
        doc = _safe_get_server_script(name)
        if not doc:
            print(f"\n- {name}: NOT FOUND")
            continue
        print(f"\n- {name}")
        _print_kv("script_type", doc.script_type)
        _print_kv("disabled", doc.disabled)
        _print_kv("ref_doctype", getattr(doc, "reference_doctype", None))
        print("  head:")
        _print_script_head(doc)

    print("\n--- Suspicious Server Scripts (keyword scan) ---")
    hits = _find_suspicious_server_scripts(limit=limit)
    print("hits:", len(hits))
    for h in hits[:50]:
        print(f" - {h['name']} | type={h['script_type']} | disabled={h['disabled']}")