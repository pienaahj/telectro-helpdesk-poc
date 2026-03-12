import json

import frappe

from telephony.telectro_claim import _normalize_assignment, _normalize_to_pool
from telephony.telectro_round_robin import POOLS, PARTNER_USER, _next_assignee
from telephony.telectro_ticket_routing import seed_ticket_routing


ROUTING_FIELDS = {
    "ticket_type",
    "custom_request_type",
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
    - Non-RR groups fall to true pool
    - RR groups keep current assignee if still valid in that pool
    - Otherwise choose a new RR assignee
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
        if current_assignee != PARTNER_USER:
            _normalize_assignment(
                ticket,
                PARTNER_USER,
                note=f"Routing change: reassigned to Partner queue | {subject}",
            )
        return

    # 2) Non-RR groups -> true pool
    if group not in POOLS:
        _normalize_to_pool(
            ticket,
            note=f"Routing change: released to pool (group={group or 'blank'}) | {subject}",
        )
        return

    # 3) RR groups: keep current assignee if still valid in that pool
    pool = [u.strip() for u in (POOLS.get(group) or []) if u and str(u).strip()]
    if current_assignee and current_assignee in pool:
        return

    # 4) Need a new deterministic assignee
    next_user = _clean(_next_assignee(group))
    if next_user:
        _normalize_assignment(
            ticket,
            next_user,
            note=f"Routing change: reassigned via RR for group {group} | {subject}",
        )
        return

    # 5) Safety fallback
    _normalize_to_pool(
        ticket,
        note=f"Routing change: released to pool (no valid RR assignee for group {group}) | {subject}",
    )