import frappe
import json
from telephony.telectro_round_robin import PARTNER_USER

DOCT = "HD Ticket"

LINKS_AREAS_CATS = {"links", "areas"}

# Ticket Types considered "fault-like" (strict validation)
FAULT_TICKET_TYPES = {"Faults", "Incident"}

def _ticket_type(doc) -> str:
    # fieldname is typically "ticket_type" (Link to HD Ticket Type)
    return (doc.get("ticket_type") or "").strip()

def _is_fault_ticket(doc) -> bool:
    t = _ticket_type(doc)
    # Back-compat: if blank, treat as Fault-like so old tickets remain strict
    return (not t) or (t in FAULT_TICKET_TYPES)

def _cat_norm(doc) -> str:
    return (doc.get("custom_fault_category") or "").strip().lower()

def _has_fault_asset(doc) -> bool:
    return bool((doc.get("custom_fault_asset") or "").strip())

def _validate_site_group_and_leaf(doc) -> None:
    # Optional debug (pilot): keep or remove
    frappe.logger("telectro").info(
        "validate_site_group_and_leaf: cat=%r asset=%r site=%r group=%r docname=%r",
        doc.get("custom_fault_category"),
        doc.get("custom_fault_asset"),
        doc.get("custom_site"),
        doc.get("custom_site_group"),
        doc.name,
    )

    # ✅ NEW: Only enforce fault-site rules for Fault-like ticket types
    if not _is_fault_ticket(doc):
        return
    
    cat = _cat_norm(doc)

    # Links/Areas are asset-driven
    if cat in LINKS_AREAS_CATS:
        if _has_fault_asset(doc):
            return
        frappe.throw("Please select a Fault Asset for Links/Areas tickets.")

    site_group = (doc.get("custom_site_group") or "").strip()
    site_leaf = (doc.get("custom_site") or "").strip()

    # If neither is set, don't block (pilot-friendly). Tighten later if needed.
    if not site_group and not site_leaf:
        return

    # ✅ Email intake is triage-first: allow campus-only (site leaf can be filled later)
    src = (doc.get("custom_request_source") or "").strip().lower()
    raised_by = (doc.get("raised_by") or "").strip().lower()

    def _looks_like_email(s: str) -> bool:
        return ("@" in s) and (" " not in s) and (len(s) >= 5)

    is_email_intake = (src in ("email", "mail", "inbound email")) or _looks_like_email(raised_by)

    if is_email_intake:
        if site_leaf and not site_group:
            frappe.throw("Please select a Site Group first, then a Site Location.")
        return

    # If one is set, require the other (prevents half-filled location)
    if site_group and not site_leaf:
        frappe.throw("Please select a Site Location under the chosen Site Group.")
    if site_leaf and not site_group:
        frappe.throw("Please select a Site Group first, then a Site Location.")

    # Validate group is a group
    group_is_group = frappe.db.get_value("Location", site_group, "is_group")
    if group_is_group is None:
        frappe.throw(f"Site Group '{site_group}' does not exist. Please re-select.")
    if not group_is_group:
        frappe.throw(f"Site Group '{site_group}' must be a group Location.")

    # Validate leaf is a leaf and belongs to group (nested set: descendant check)
    leaf = frappe.db.get_value("Location", site_leaf, ["is_group", "lft", "rgt"], as_dict=True)
    if not leaf:
        frappe.throw(f"Site Location '{site_leaf}' does not exist. Please re-select.")
    if leaf.get("is_group"):
        frappe.throw(f"Site Location '{site_leaf}' is a group node. Please select a leaf Location.")

    group_lr = frappe.db.get_value("Location", site_group, ["lft", "rgt"], as_dict=True)
    if not group_lr:
        frappe.throw(f"Site Group '{site_group}' does not exist. Please re-select.")

    if not (leaf.lft >= group_lr.lft and leaf.rgt <= group_lr.rgt):
        frappe.throw(
            f"Site Location '{site_leaf}' is not under Site Group '{site_group}'. Please select a valid leaf."
        )

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


def _open_todos(ticket: str) -> list[dict]:
    # newest first so keep-first is deterministic
    return frappe.get_all(
        "ToDo",
        filters={"reference_type": DOCT, "reference_name": ticket, "status": "Open"},
        fields=["name", "allocated_to", "creation"],
        order_by="creation desc",
        ignore_permissions=True,
        limit_page_length=200,
    )


def _ensure_open_todo(ticket: str, user: str, desc: str = "") -> None:
    ticket = (ticket or "").strip()
    user = (user or "").strip()
    if not ticket or not user:
        return

    exists = frappe.db.exists(
        "ToDo",
        {
            "reference_type": DOCT,
            "reference_name": ticket,
            "allocated_to": user,
            "status": "Open",
        },
    )
    if exists:
        return

    frappe.get_doc(
        {
            "doctype": "ToDo",
            "allocated_to": user,
            "reference_type": DOCT,
            "reference_name": ticket,
            "status": "Open",
            "description": (desc or "")[:140],
        }
    ).insert(ignore_permissions=True)


def _close_todo(todo_name: str) -> None:
    # IMPORTANT:
    # In this stack, Closed ToDos for HD Ticket can be resurrected to Open by assignment logic.
    # Cancelled behaves "final" and prevents old duplicates from being reopened on save().
    frappe.db.set_value("ToDo", todo_name, "status", "Cancelled", update_modified=False)



def _set_assign(ticket: str, users: list[str]) -> None:
    # stable + deduped
    uniq = sorted({(u or "").strip() for u in (users or []) if (u or "").strip()})
    frappe.db.set_value(DOCT, ticket, "_assign", json.dumps(uniq), update_modified=False)
    
def _mirror_assign(ticket: str, users: list[str]) -> None:
    # Mirror/normalize _assign in DB (compat alias used by sync_ticket_assignments)
    _set_assign(ticket, users)

def _is_partner_fulfilment(doc) -> bool:
    return (doc.get("custom_fulfilment_party") or "").strip() == "Partner"


def _enforce_partner_assignment(ticket: str, doc=None) -> None:
    """
    Partner fulfilment invariant.

    Partner fulfilment must replace accountable ownership, not append to it:
      - exactly one Open ToDo for PARTNER_USER
      - no other Open ToDos
      - _assign = [PARTNER_USER]
    """
    ticket = (ticket or "").strip()
    if not ticket:
        return

    todos = _open_todos(ticket)

    keep_partner_todo = None

    for td in todos:
        user = (td.get("allocated_to") or "").strip()

        if user == PARTNER_USER and keep_partner_todo is None:
            keep_partner_todo = td["name"]
            continue

        _close_todo(td["name"])

    if keep_partner_todo is None:
        _ensure_open_todo(
            ticket,
            PARTNER_USER,
            desc="Assigned via TELECTRO pilot action",
        )

    assign_json = json.dumps([PARTNER_USER])

    if doc is not None:
        doc._assign = assign_json

    frappe.db.set_value(
        DOCT,
        ticket,
        "_assign",
        assign_json,
        update_modified=False,
    )  
  
def dedupe_assign_field(doc, method=None) -> None:
    """
    Runs at validate time.

    Pilot rule:
    - _assign is a mirror/cache, not canonical truth.
    - Open ToDo is canonical.
    - If Open ToDo exists, keep only the newest accountable owner.
    - If no Open ToDo exists, collapse _assign to at most one user.

    Partner fulfilment exception:
    - Partner fulfilment always normalizes ownership to PARTNER_USER.
    - This prevents generic Fulfilment Party edits from appending Partner while
      leaving the previous owner active.
    """
    _validate_site_group_and_leaf(doc)

    ticket = str(getattr(doc, "name", "") or "").strip()

    if ticket and _is_partner_fulfilment(doc):
        _enforce_partner_assignment(ticket, doc=doc)
        return

    if ticket:
        todos = _open_todos(ticket)
        if todos:
            owner = (todos[0].get("allocated_to") or "").strip()
            doc._assign = json.dumps([owner] if owner else [])
            return

    users = _parse_assign_users(doc.get("_assign"))
    owner = users[0] if users else ""
    doc._assign = json.dumps([owner] if owner else [])



def sync_ticket_assignments(doc, method=None, prefer_assign: int = 1) -> None:
    """
    Canonicalize pilot assignment state after HD Ticket update.

    Pilot invariant:
    - Owned ticket:
        exactly one Open ToDo
        _assign = ["owner"]
    - True pool:
        no Open ToDos
        _assign = []

    Open ToDo is canonical. _assign is only used as a repair hint when there
    are no Open ToDos.
    """
    ticket = str(getattr(doc, "name", "") or "").strip()
    if not ticket:
        return

    if _is_partner_fulfilment(doc):
        _enforce_partner_assignment(ticket, doc=doc)
        return
    
    todos = _open_todos(ticket)

    # A) If multiple Open ToDos exist, keep newest only.
    owner = ""
    keep_todo = None

    for td in todos:
        user = (td.get("allocated_to") or "").strip()
        if not user:
            _close_todo(td["name"])
            continue

        if not owner:
            owner = user
            keep_todo = td["name"]
            continue

        _close_todo(td["name"])

    # B) If no Open ToDo exists, optionally repair from first _assign user.
    if not owner and prefer_assign:
        assigned = _parse_assign_users(doc.get("_assign"))
        owner = assigned[0] if assigned else ""

        if owner:
            _ensure_open_todo(
                ticket,
                owner,
                desc=(doc.get("subject") or "Repair: recreate missing ToDo"),
            )

            todos = _open_todos(ticket)
            keep_todo = None

            # Re-read and still enforce exactly one, in case a helper recreated
            # against dirty historical state.
            for td in todos:
                user = (td.get("allocated_to") or "").strip()

                if user == owner and not keep_todo:
                    keep_todo = td["name"]
                    continue

                _close_todo(td["name"])

    # C) Mirror final canonical owner into _assign.
    _mirror_assign(ticket, [owner] if owner else [])




