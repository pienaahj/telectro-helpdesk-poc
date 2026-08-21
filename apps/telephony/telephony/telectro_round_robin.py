import frappe
import json

from telephony.partner_identity import resolve_partner_dispatch_user
from telephony.telectro_routing_policy import resolve_ticket_routing_policy

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

def assign_after_insert(doc, method=None):
    # doc_event hook
    ticket = str(getattr(doc, "name", "") or "").strip()
    if not ticket:
        return
    
    # Partner fulfilment overrides normal native team assignment.
    party = (doc.get("custom_fulfilment_party") or "").strip()

    if party == "Partner":
        partner_name = (
            doc.get("custom_fulfilment_partner") or ""
        ).strip()

        partner_user = resolve_partner_dispatch_user(
            partner_name
        )

        # If already has an Open ToDo, don't interfere.
        open_todos = _open_todos_for_ticket(ticket)

        if not open_todos:
            # If _assign is already populated, don't interfere.
            assign_users = _parse_assign_users(
                frappe.db.get_value(
                    "HD Ticket",
                    ticket,
                    "_assign",
                )
                or ""
            )

            if not assign_users:
                _ensure_open_todo(
                    ticket,
                    partner_user,
                    desc=(
                        doc.get("subject")
                        or "Partner"
                    )[:140],
                )
                _mirror_assign_from_todo(doc)

        return
     # 2) Pilot Campus/Site routing policy
    policy = resolve_ticket_routing_policy(doc)
    if policy and policy.get("target_user"):
        target_user = str(policy.get("target_user") or "").strip()

        open_todos = _open_todos_for_ticket(ticket)
        if not open_todos:
            assign_users = _parse_assign_users(
                frappe.db.get_value("HD Ticket", ticket, "_assign") or ""
            )

            if not assign_users:
                _ensure_open_todo(
                    ticket,
                    target_user,
                    desc=(
                        policy.get("reason")
                        or doc.get("subject")
                        or "Campus routing policy"
                    )[:140],
                )
                _mirror_assign_from_todo(doc)

        return
    # 3) Normal internal team routing is handled by the native
    # HD Team Assignment Rule.
    #
    # seed_ticket_routing() has already selected agent_group.
    # Do not create a ToDo here. Frappe's normal on_update
    # Assignment Rule processing will choose a member of that team.
    return

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
