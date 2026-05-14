import json
import frappe
from frappe.utils import now_datetime

def _notify_controlled_handoff_receiver(ticket: str, to_user: str, from_user: str | None, reason: str, changed_by: str):
    ...

def _notify_controlled_handoff_receiver(
    ticket: str,
    to_user: str,
    from_user: str | None,
    reason: str,
    changed_by: str,
):
    """
    Notify the receiving user after a Controlled Handoff.

    This is intentionally scoped to the receiver only.

    Native assignment notifications are not produced by the TELECTRO
    controlled handoff path because assignment is normalised directly.
    This helper creates one explicit action-required Notification Log.
    """
    ticket = (ticket or "").strip()
    to_user = (to_user or "").strip()
    from_user = (from_user or "").strip()
    reason = (reason or "").strip()
    changed_by = (changed_by or "").strip() or frappe.session.user

    if not ticket or not to_user:
        return None

    doc = frappe.get_doc("HD Ticket", ticket)

    subject = frappe.utils.escape_html(doc.get("subject") or ticket)
    from_label = frappe.utils.escape_html(from_user or "Pool")
    to_label = frappe.utils.escape_html(to_user)
    changed_by_label = frappe.utils.escape_html(
        frappe.db.get_value("User", changed_by, "full_name") or changed_by
    )
    reason_label = frappe.utils.escape_html(reason)

    notification_subject = (
        f"<strong>{changed_by_label}</strong> handed off "
        f"<strong>HD Ticket</strong> "
        f'<b class="subject-title">{subject}</b> to you'
    )

    email_content = (
        f"<p>You have received a controlled handoff for "
        f"<strong>HD Ticket {frappe.utils.escape_html(ticket)}</strong>.</p>"
        f"<p><strong>From:</strong> {from_label}<br>"
        f"<strong>To:</strong> {to_label}<br>"
        f"<strong>Reason:</strong> {reason_label}</p>"
    )

    notification = frappe.get_doc({
        "doctype": "Notification Log",
        "subject": notification_subject,
        "for_user": to_user,
        "type": "Alert",
        "document_type": "HD Ticket",
        "document_name": ticket,
        "email_content": email_content,
    })
    notification.insert(ignore_permissions=True)

    return notification.name
    
def _insert_handoff_audit_log(
    *,
    ticket: str,
    ticket_subject: str | None,
    changed_by: str,
    from_user: str | None,
    to_user: str,
    reason: str,
    source: str = "Controlled Handoff",
) -> None:
    """
    Durable audit log for accountable-owner transfer.

    This is intentionally separate from timeline comments:
    - comments are useful for humans on the ticket
    - this DocType is useful for reports, governance, and demo proof
    """
    ticket = (ticket or "").strip()
    changed_by = (changed_by or "").strip()
    from_user = (from_user or "").strip()
    to_user = (to_user or "").strip()
    reason = (reason or "").strip()
    source = (source or "").strip() or "Controlled Handoff"

    if not ticket or not changed_by or not to_user or not reason:
        return

    frappe.get_doc(
        {
            "doctype": "TELECTRO Assignment Handoff Log",
            "ticket": ticket,
            "ticket_subject": ticket_subject or "",
            "changed_on": now_datetime(),
            "changed_by": changed_by,
            "from_user": from_user or None,
            "to_user": to_user,
            "reason": reason,
            "source": source,
        }
    ).insert(ignore_permissions=True)
    
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
        ignore_permissions=True,
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
        ignore_permissions=True,
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


def _roles_for(user: str) -> set[str]:
    try:
        return set(frappe.get_roles(user))
    except Exception:
        return set()


def _is_operational_intervention_user(user: str) -> bool:
    if not user or user == "Administrator":
        return True

    roles = _roles_for(user)

    allowed = {
        "System Manager",
        "Pilot Admin",
        "TELECTRO-POC Role - Supervisor Governance",
        "TELECTRO-POC Role - Coordinator Ops",
    }
    return bool(roles & allowed)


@frappe.whitelist(methods=["POST"])
def telectro_handoff_ticket(ticket: str, to_user: str, reason: str = ""):
    """
    Controlled pilot reassignment / handoff.

    Pilot rule:
      - HD Ticket assignment represents the accountable owner.
      - Handoff transfers accountability.
      - It does not add a second assignee.
    """
    ticket = (ticket or "").strip()
    to_user = (to_user or "").strip()
    reason = (reason or "").strip()

    if not ticket:
        return {"ok": 0, "reason": "missing_ticket"}

    if not to_user:
        return {"ok": 0, "reason": "missing_to_user"}

    if not reason:
        return {"ok": 0, "reason": "missing_handoff_reason"}

    user = frappe.session.user

    if not _is_operational_intervention_user(user):
        return {"ok": 0, "reason": "not_permitted"}

    if not frappe.db.exists("HD Ticket", ticket):
        return {"ok": 0, "reason": "invalid_ticket", "ticket": ticket}

    target = frappe.db.get_value(
        "User",
        to_user,
        ["name", "enabled", "user_type"],
        as_dict=True,
    )

    if not target:
        return {"ok": 0, "reason": "invalid_user", "to_user": to_user}

    if not int(target.enabled or 0):
        return {"ok": 0, "reason": "disabled_user", "to_user": to_user}

    doc = frappe.get_doc("HD Ticket", ticket)

    if doc.status in ("Resolved", "Closed", "Archived"):
        return {
            "ok": 0,
            "reason": "terminal_ticket",
            "ticket": ticket,
            "status": doc.status,
        }

    fulfilment_party = (doc.get("custom_fulfilment_party") or "").strip()
    if fulfilment_party == "Partner":
        return {
            "ok": 0,
            "reason": "partner_fulfilment_ticket",
            "ticket": ticket,
        }

    current = frappe.db.get_value("HD Ticket", ticket, "_assign") or ""
    from_user = _first_assignee(current)

    if from_user == to_user:
        return {
            "ok": 0,
            "reason": "already_assigned_to_user",
            "ticket": ticket,
            "to_user": to_user,
        }

    msg = "Controlled handoff: {0} -> {1} | Reason: {2} | By: {3}".format(
        from_user or "Pool",
        to_user,
        reason,
        user,
    )

    _normalize_assignment(ticket, to_user, note=msg)

    _insert_handoff_audit_log(
        ticket=ticket,
        ticket_subject=doc.get("subject"),
        changed_by=user,
        from_user=from_user,
        to_user=to_user,
        reason=reason,
        source="Controlled Handoff",
    )

    _notify_controlled_handoff_receiver(
        ticket=ticket,
        to_user=to_user,
        from_user=from_user,
        reason=reason,
        changed_by=user,
    )

    frappe.db.commit()

    return {
        "ok": 1,
        "ticket": ticket,
        "from": from_user,
        "to": to_user,
        "by": user,
    }
    
@frappe.whitelist()
def telectro_ticket_assignment_state(ticket: str):
    """
    Return current pilot assignment state for an HD Ticket.

    Canonical source:
      - Open ToDo rows

    Mirror/cache:
      - HD Ticket._assign

    Used by the Controlled Handoff dialog so the UI does not rely on stale
    or missing frm.doc._assign data.
    """
    ticket = (ticket or "").strip()
    if not ticket:
        return {"ok": 0, "reason": "missing_ticket"}

    if not frappe.db.exists("HD Ticket", ticket):
        return {"ok": 0, "reason": "invalid_ticket", "ticket": ticket}

    doc = frappe.get_doc("HD Ticket", ticket)

    open_todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "status": "Open",
        },
        fields=["name", "allocated_to", "creation"],
        order_by="creation asc",
        ignore_permissions=True,
        limit_page_length=20,
    )

    todo_users = []
    seen = set()

    for td in open_todos:
        user = (td.get("allocated_to") or "").strip()
        if not user or user in seen:
            continue
        seen.add(user)
        todo_users.append(user)

    assign_users = []
    raw_assign = doc.get("_assign")

    if raw_assign:
        try:
            parsed = json.loads(raw_assign) if isinstance(raw_assign, str) else raw_assign
            if isinstance(parsed, list):
                assign_users = [
                    str(x).strip()
                    for x in parsed
                    if str(x).strip()
                ]
        except Exception:
            assign_users = []

    effective_users = todo_users or assign_users

    return {
        "ok": 1,
        "ticket": ticket,
        "todo_users": todo_users,
        "assign_users": assign_users,
        "effective_users": effective_users,
        "current_owner": effective_users[0] if effective_users else "",
        "is_pool": not effective_users,
        "has_assignment_drift": todo_users != assign_users,
        "open_todo_count": len(open_todos),
        "status": doc.status,
        "fulfilment_party": doc.get("custom_fulfilment_party"),
    }