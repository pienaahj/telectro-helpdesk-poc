import json

import frappe

from telephony.telectro_claim import _normalize_assignment, _normalize_to_pool
from telephony.telectro_round_robin import PARTNER_USER
from telephony.telectro_ticket_routing import seed_ticket_routing
from telephony.telectro_routing_policy import resolve_ticket_routing_policy

ROUTING_FIELDS = {
    "ticket_type",
    "custom_request_type",
    "customer",
    "custom_customer",
    "custom_site_group",
    "custom_site",
    "custom_fault_asset",
    "custom_service_area",
    "custom_fulfilment_party",
    "agent_group",
}


def _clean(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _parse_assign_users(assign_val) -> list[str]:
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


def _current_assignee(ticket_name: str) -> str | None:
    assign_val = frappe.db.get_value("HD Ticket", ticket_name, "_assign") or ""
    users = _parse_assign_users(assign_val)
    return users[0] if users else None

def _native_team_users(group: str) -> list[str]:
    group = _clean(group)
    if not group:
        return []

    rule = _clean(
        frappe.db.get_value(
            "HD Team",
            group,
            "assignment_rule",
        )
    )
    if not rule:
        return []

    if not frappe.db.exists("Assignment Rule", rule):
        return []

    if frappe.db.get_value("Assignment Rule", rule, "disabled"):
        return []

    users = frappe.get_all(
        "Assignment Rule User",
        filters={
            "parent": rule,
            "parenttype": "Assignment Rule",
            "parentfield": "users",
        },
        pluck="user",
        order_by="idx asc",
    )

    return [
        _clean(user)
        for user in users
        if _clean(user)
    ]

def _release_for_native_team_assignment(
    doc,
    ticket: str,
    note: str | None = None,
) -> None:
    ticket = _clean(ticket)
    if not ticket:
        return

    # Preserve the existing TELECTRO pool-release behaviour and audit comment.
    _normalize_to_pool(ticket, note=note)

    # Native Assignment Rule processing treats any non-Cancelled ToDo as an
    # existing assignment. Closed ToDos can also be reopened, so routing
    # replacement must permanently retire every previous assignment first.
    todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "status": ("!=", "Cancelled"),
        },
        pluck="name",
        ignore_permissions=True,
        limit_page_length=200,
    )

    for todo_name in todos:
        frappe.db.set_value(
            "ToDo",
            todo_name,
            "status",
            "Cancelled",
            update_modified=False,
        )

    # sync_ticket_assignments() runs immediately after this hook. Clear both
    # representations so it cannot repair ownership from stale in-memory state.
    assign_json = json.dumps([])
    doc._assign = assign_json

    frappe.db.set_value(
        "HD Ticket",
        ticket,
        "_assign",
        assign_json,
        update_modified=False,
    )

def _get_old_doc(doc):
    old_doc = None

    try:
        old_doc = doc.get_doc_before_save()
    except Exception:
        old_doc = None

    if old_doc:
        return old_doc

    if not getattr(doc, "name", None):
        return None

    try:
        return frappe.get_doc(doc.doctype, doc.name)
    except Exception:
        return None


def _routing_changed(doc, old_doc) -> bool:
    if not old_doc:
        return False

    for fieldname in ROUTING_FIELDS:
        old_val = _clean(old_doc.get(fieldname))
        new_val = _clean(doc.get(fieldname))
        if old_val != new_val:
            return True

    return False


def reassign_if_routing_changed(doc, method=None):
    """
    Re-evaluate ownership when routing-relevant fields change on an existing ticket.

    Behavior:
    - Trigger on upstream or final routing field changes
    - Re-seed final routing state first (important for service-area edits)
    - Partner overrides all and assigns to PARTNER_USER
    - Campus/Site policy may assign a specific user directly
    - Ordinary team routing uses the current HD Team Assignment Rule
    - Keep the current assignee when still valid for that team
    - Otherwise release ownership so native Assignment Rule processing can reassign
    """
    ticket = _clean(getattr(doc, "name", ""))
    if not ticket:
        return

    if doc.is_new():
        return

    old_doc = _get_old_doc(doc)
    if not _routing_changed(doc, old_doc):
        return

    # IMPORTANT:
    # Refresh final routing state from current doc values before deciding ownership.
    seed_ticket_routing(doc, method=None)

    group = _clean(doc.get("agent_group"))
    party = _clean(doc.get("custom_fulfilment_party"))
    subject = _clean(doc.get("subject")) or ticket
    current_assignee = _current_assignee(ticket)

    # 1) Partner override
    if party == "Partner":
        _normalize_assignment(
            ticket,
            PARTNER_USER,
            note=f"Routing change: reassigned to Partner fulfilment | {subject}",
        )
        return
    # 2) Pilot Campus/Site routing policy
    policy = resolve_ticket_routing_policy(doc)
    if policy and policy.get("target_user"):
        target_user = _clean(policy.get("target_user"))
        if target_user and current_assignee != target_user:
            _normalize_assignment(
                ticket,
                target_user,
                note=(
                    f"Routing change: reassigned via "
                    f"{policy.get('reason') or 'Campus routing policy'} | {subject}"
                ),
            )
        return
    # 3) Ordinary internal team routing is owned by the native
    # HD Team Assignment Rule.
    team_users = _native_team_users(group)

    # Preserve the current owner when that user remains a valid member
    # of the team selected by the current routing state.
    if current_assignee and current_assignee in team_users:
        return

    # Otherwise remove stale ownership. Frappe's later wildcard
    # Assignment Rule on_update hook will evaluate the current HD Team
    # rule and choose the appropriate team member.
    _release_for_native_team_assignment(
        doc,
        ticket,
        note=(
            f"Routing change: released for native team assignment "
            f"(group={group or 'blank'}) | {subject}"
        ),
    )
