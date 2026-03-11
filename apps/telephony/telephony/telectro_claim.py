import json
import frappe


def _first_assignee(assign_val: str | None):
    if not assign_val:
        return None
    try:
        parsed = json.loads(assign_val) if assign_val else []
        if isinstance(parsed, list) and parsed:
            return parsed[0]
    except Exception:
        return None
    return None


def _normalize_assignment(ticket: str, owner_email: str, note: str | None = None):
    """
    Enforce pilot invariant:
      - HD Ticket._assign = JSON list with exactly one user
      - Exactly ONE Open ToDo exists for this ticket (allocated_to = owner_email)
      - Any other Open ToDos for the ticket are Closed
      - Optionally writes a timeline comment (Info)
    """
    ticket = (ticket or "").strip()
    owner_email = (owner_email or "").strip()
    if not ticket or not owner_email:
        return

    assign_json = json.dumps([owner_email])
    frappe.db.sql(
        """
        UPDATE `tabHD Ticket`
           SET `_assign` = %s
         WHERE `name` = %s
        """,
        (assign_json, ticket),
    )

    todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "status": "Open",
        },
        fields=["name", "allocated_to", "creation"],
        order_by="creation asc",
        limit_page_length=200,
    )

    kept_open = 0

    for t in todos:
        allocated = (t.get("allocated_to") or "").strip()
        if allocated == owner_email and kept_open == 0:
            kept_open = 1
            continue

        frappe.db.set_value("ToDo", t["name"], "status", "Closed", update_modified=False)

    if kept_open == 0:
        frappe.get_doc(
            {
                "doctype": "ToDo",
                "allocated_to": owner_email,
                "reference_type": "HD Ticket",
                "reference_name": ticket,
                "status": "Open",
                "description": "Assigned via TELECTRO pilot action",
            }
        ).insert(ignore_permissions=True)

    if note:
        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "HD Ticket",
                "reference_name": ticket,
                "content": f"{note} | Assigned via TELECTRO pilot action",
            }
        ).insert(ignore_permissions=True)


def _normalize_to_pool(ticket: str, note: str | None = None):
    """
    True pool invariant:
      - HD Ticket._assign = []
      - NO Open ToDo exists for this ticket
      - Optionally writes a timeline comment (Info)
    """
    ticket = (ticket or "").strip()
    if not ticket:
        return

    todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "status": "Open",
        },
        fields=["name"],
        order_by="creation asc",
        limit_page_length=200,
    )

    for t in todos:
        frappe.db.set_value("ToDo", t["name"], "status", "Closed", update_modified=False)

    frappe.db.set_value("HD Ticket", ticket, "_assign", json.dumps([]), update_modified=False)

    if note:
        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "HD Ticket",
                "reference_name": ticket,
                "content": f"{note} | Released to TELECTRO pool",
            }
        ).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def telectro_claim_ticket(ticket: str):
    ticket = (ticket or "").strip()
    if not ticket:
        return {"ok": 0, "reason": "missing_ticket"}

    user = frappe.session.user
    assign_json = json.dumps([user])

    # Atomic first-claim-wins from TRUE POOL only
    frappe.db.sql(
        """
        UPDATE `tabHD Ticket`
           SET `_assign` = %s
         WHERE `name` = %s
           AND (
             IFNULL(`_assign`, '') = '' OR `_assign` = '[]'
           )
        """,
        (assign_json, ticket),
    )

    current = frappe.db.get_value("HD Ticket", ticket, "_assign") or ""
    if current == assign_json:
        _normalize_assignment(ticket, user, note="Claim")
        frappe.db.commit()
        return {"ok": 1, "ticket": ticket, "assigned_to": user}

    return {"ok": 0, "ticket": ticket, "assigned_to": current, "reason": "already_claimed"}


@frappe.whitelist(methods=["POST"])
def telectro_release_ticket(ticket: str, reason: str = ""):
    ticket = (ticket or "").strip()
    reason = (reason or "").strip()

    if not ticket:
        return {"ok": 0, "reason": "missing_ticket"}
    if not reason:
        return {"ok": 0, "reason": "missing_release_reason"}

    current = frappe.db.get_value("HD Ticket", ticket, "_assign") or ""
    from_user = _first_assignee(current)

    user = frappe.session.user

    if not from_user:
        return {"ok": 0, "reason": "not_assigned"}
    if from_user != user:
        return {"ok": 0, "reason": "not_owner", "from": from_user, "user": user}

    msg = f"Release: {from_user} -> Pool | Reason: {reason}"
    _normalize_to_pool(ticket, note=msg)
    frappe.db.commit()

    return {"ok": 1, "ticket": ticket, "from": from_user, "to": "Pool"}


@frappe.whitelist(methods=["POST"])
def telectro_handoff_ticket(ticket: str, to_user: str, reason: str = ""):
    """
    Deprecated for normal tech flow.
    Keep temporarily only for controlled/admin use until fully removed.
    """
    ticket = (ticket or "").strip()
    to_user = (to_user or "").strip()
    reason = (reason or "").strip()

    if not ticket or not to_user:
        return {"ok": 0, "reason": "missing_args"}

    if not frappe.db.exists("User", to_user):
        return {"ok": 0, "reason": "invalid_user", "to_user": to_user}

    user = frappe.session.user
    roles = frappe.get_roles(user) or []
    is_adminish = (user == "Administrator") or ("System Manager" in roles)

    if not is_adminish:
        return {"ok": 0, "reason": "not_supervisor"}

    current = frappe.db.get_value("HD Ticket", ticket, "_assign") or ""
    from_user = _first_assignee(current)

    msg = "Supervisor assign: {0} -> {1}".format(from_user or "Pool", to_user)
    if reason:
        msg += " | Reason: {0}".format(reason)

    _normalize_assignment(ticket, to_user, note=msg)
    frappe.db.commit()

    return {"ok": 1, "ticket": ticket, "from": from_user, "to": to_user}