import json
import frappe

POOL = "helpdesk@local.test"
POOL_USER = "helpdesk@local.test"

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

    # 1) force single-owner assignment
    assign_json = json.dumps([owner_email])
    frappe.db.sql(
        """
        UPDATE `tabHD Ticket`
           SET `_assign` = %s
         WHERE `name` = %s
        """,
        (assign_json, ticket),
    )

    # 2) normalize ToDos
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
    closed = 0

    for t in todos:
        allocated = (t.get("allocated_to") or "").strip()
        if allocated == owner_email and kept_open == 0:
            kept_open = 1
            continue

        frappe.db.set_value("ToDo", t["name"], "status", "Closed", update_modified=False)
        closed += 1

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
        kept_open = 1

    # 3) optional audit note
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


@frappe.whitelist(methods=["POST"])
def telectro_claim_ticket(ticket: str):
    ticket = (ticket or "").strip()
    if not ticket:
        return {"ok": 0, "reason": "missing_ticket"}

    user = frappe.session.user
    assign_json = json.dumps([user])

    pool_json = json.dumps([POOL_USER])

    # Atomic first-claim-wins:
    # allow claim if ticket is unassigned OR currently owned by POOL_USER
    frappe.db.sql(
        """
        UPDATE `tabHD Ticket`
           SET `_assign` = %s
         WHERE `name` = %s
           AND (
             IFNULL(`_assign`, '') = '' OR `_assign` = '[]'
             OR `_assign` = %s
           )
        """,
        (assign_json, ticket, pool_json),
    )


    current = frappe.db.get_value("HD Ticket", ticket, "_assign") or ""
    if current == assign_json:
        _normalize_assignment(ticket, user, note="Claim")
        frappe.db.commit()
        return {"ok": 1, "ticket": ticket, "assigned_to": user}

    return {"ok": 0, "ticket": ticket, "assigned_to": current, "reason": "already_claimed"}


@frappe.whitelist(methods=["POST"])
def telectro_handoff_ticket(ticket: str, to_user: str, reason: str = ""):
    """
    Pilot: tech-to-tech handoff (reassign) with timeline audit.
    - Sets HD Ticket._assign to [to_user]
    - Normalizes ToDo (single Open for to_user; closes others)
    - Writes a Comment row so it shows in the timeline
    """
    ticket = (ticket or "").strip()
    to_user = (to_user or "").strip()
    reason = (reason or "").strip()

    if not ticket or not to_user:
        return {"ok": 0, "reason": "missing_args"}

    if not frappe.db.exists("User", to_user):
        return {"ok": 0, "reason": "invalid_user", "to_user": to_user}

    current = frappe.db.get_value("HD Ticket", ticket, "_assign") or ""
    from_user = _first_assignee(current)
    
    # Pilot guardrail:
    # - Only the current assignee can handoff
    # - Ops/Admin (System Manager) can handoff anything (they already have normal assign/unassign too)
    user = frappe.session.user
    roles = frappe.get_roles(user) or []

    is_adminish = (user == "Administrator") or ("System Manager" in roles)

    if not is_adminish:
        if not from_user:
            return {"ok": 0, "reason": "not_assigned"}
        if from_user != user:
            return {"ok": 0, "reason": "not_owner", "from": from_user, "user": user}


    if from_user == to_user:
        # If drift exists (multi-assign), normalize anyway instead of short-circuiting.
        cur = (current or "").strip()
        drift = (cur.startswith("[") and cur.endswith("]") and "," in cur)

        if drift:
            msg = "Normalize: keep {0} as owner".format(to_user)
            if reason:
                msg += " | Reason: {0}".format(reason)
            _normalize_assignment(ticket, to_user, note=msg)
            frappe.db.commit()
            return {"ok": 1, "ticket": ticket, "from": from_user, "to": to_user, "normalized": 1}

        return {"ok": 0, "reason": "already_assigned", "ticket": ticket, "assigned_to": to_user}


    msg = "Handoff: {0} -> {1}".format(from_user or "Unassigned", to_user)
    if reason:
        msg += " | Reason: {0}".format(reason)

    _normalize_assignment(ticket, to_user, note=msg)
    frappe.db.commit()

    return {"ok": 1, "ticket": ticket, "from": from_user, "to": to_user}
