import json
import frappe
from frappe import _

# Delegate to core implementation for everyone except pilot-tech restrictions.
from frappe.desk.form import assign_to as core_assign_to

import traceback
import time

def _parse_assign_to_users(assign_to):
    """Accept list, single user, or JSON list string like '["user@x"]'."""
    def clean(seq):
        out = []
        for u in (seq or []):
            s = (str(u) if u is not None else "").strip()
            if s:
                out.append(s)
        return out

    if not assign_to:
        return []

    if isinstance(assign_to, list):
        return clean(assign_to)

    if isinstance(assign_to, str):
        s = assign_to.strip()
        if not s:
            return []
        # UI often sends JSON list as a string
        if s.startswith("["):
            try:
                parsed = frappe.parse_json(s)
                if isinstance(parsed, list):
                    return clean(parsed)
            except Exception:
                pass
        return [s]

    # fallback: single value
    return [str(assign_to).strip()]

def _as_assign_list(x):
    """Coerce responses into the list shape expected by assign_to.js (so it can .map)."""
    if x is None:
        return []

    if isinstance(x, list):
        return x

    if isinstance(x, tuple):
        return list(x)

    if isinstance(x, dict):
        # your current broken shape: {"results":[...]}
        if isinstance(x.get("results"), list):
            return x.get("results") or []

        # occasionally seen: {"message":[...]}
        if isinstance(x.get("message"), list):
            return x.get("message") or []

        # your exact observed shape: {"message":{"results":[...]}}
        msg = x.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("results"), list):
            return msg.get("results") or []

    # last resort: don't crash UI
    return []

def _cancel_closed_todos_for_ticket(ticket: str) -> int:
    ticket = (ticket or "").strip()
    if not ticket:
        return 0

    closed = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket,
            "status": "Closed",
        },
        pluck="name",
        ignore_permissions=True,
        limit_page_length=200,
    )

    for n in closed or []:
        frappe.db.set_value("ToDo", n, "status", "Cancelled", update_modified=False)

    return len(closed or [])

def _cancel_closed_todos_for_tickets(tickets: list[str]) -> int:
    changed = 0
    for t in tickets or []:
        changed += _cancel_closed_todos_for_ticket(t)
    return changed


def _dbg(label: str, d=None, *, args=None, kwargs=None):
    """
    Debug logger for assignment overrides.
    Controlled by site_config.json:
      - telephony_assign_debug: true/false
      - telephony_assign_debug_stack: true/false
    """
    try:
        if not frappe.conf.get("telephony_assign_debug"):
            return

        user = getattr(getattr(frappe, "session", None), "user", None)
        ts = time.strftime("%H:%M:%S")
        print(f"\n[assign_override] {ts} {label} user={user!r}")

        if d is not None and isinstance(d, dict):
            keys = [
                "doctype", "name", "docname", "reference_type", "reference_name",
                "assign_to", "assign_to_user", "allocated_to", "names", "ignore_permissions"
            ]
            slim = {k: d.get(k) for k in keys if k in d}
            print("[assign_override] payload:", slim)

        if args is not None or kwargs is not None:
            print("[assign_override] raw_args:", args)
            print("[assign_override] raw_kwargs:", kwargs)

        # OPTIONAL: only if you truly need it
        try:
            cid = frappe.db.sql("SELECT CONNECTION_ID()", pluck=True)[0]
        except Exception:
            cid = None
        print(f"[assign_override] db_conn_id={cid}")

        if frappe.conf.get("telephony_assign_debug_stack"):
            print("[assign_override] stack:")
            print("".join(traceback.format_stack(limit=8)))

    except Exception:
        pass




def _as_dict_from_first(arg0):
    """Accept dict, JSON string, or None and return dict."""
    if arg0 is None:
        return {}

    if isinstance(arg0, dict):
        return dict(arg0)

    if isinstance(arg0, str):
        try:
            v = json.loads(arg0)
            if isinstance(v, dict):
                return v
            if isinstance(v, list):
                # treat JSON list as names payload
                return {"names": v}
            return {}
        except Exception:
            return {}

    return {}


def _names_json(d):
    """
    Always return JSON array string for core remove_multiple (json.loads(names)).
    Supports:
      - '["414","413"]'
      - ["414","413"]
      - "414"
      - "414,413"
      - ("414","413"), {"414","413"}
    """
    names = d.get("names")

    # list/tuple/set -> JSON list
    if isinstance(names, (list, tuple, set)):
        out = [str(x).strip() for x in names if str(x).strip()]
        return json.dumps(out)

    # string -> maybe JSON list, maybe single, maybe comma-list
    if isinstance(names, str):
        s = names.strip()
        if not s:
            return "[]"

        # If it *looks* like a JSON array, keep it (do not validate to avoid breaking callers)
        if s.startswith("[") and s.endswith("]"):
            return s

        # Comma-separated?
        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
            return json.dumps(parts)

        # Single docname
        return json.dumps([s])

    if names is None:
        return "[]"

    # fallback single
    s = str(names).strip()
    return json.dumps([s]) if s else "[]"



def _merge_args_kwargs(*args, **kwargs):
    """
    Normalize common Frappe whitelisted call shapes into a single payload dict.

    Handles:
    - fn(args={...}) / fn(args='{"..."}')  (wrapped payload)
    - fn({...}) / fn('{"..."}')           (positional payload)
    - fn(doctype=..., name=..., ...)      (plain kwargs)

    Precedence: explicit kwargs override payload values.
    """

    d = {}
    # 1) positional payload
    if args:
        d.update(_as_dict_from_first(args[0]))

    # 2) kwargs payload container `args=...` (Frappe pattern)
    if "args" in kwargs and isinstance(kwargs["args"], (dict, str)):
        d.update(_as_dict_from_first(kwargs["args"]))

    # 3) everything else (explicit kwargs always win)
    rest = dict(kwargs)
    rest.pop("args", None)
    d.update(rest)

    return d


def _target_is_hd_ticket(d):
    # Cover common key shapes across assign_to methods.
    doctype = (d.get("doctype") or d.get("reference_type") or "").strip()

    # Single-doc actions
    name = (d.get("name") or d.get("docname") or d.get("reference_name") or "").strip()

    # Bulk actions
    names = d.get("names")

    has_bulk = False
    if isinstance(names, list):
        has_bulk = len(names) > 0
    elif isinstance(names, str):
        has_bulk = names.strip() not in ("", "[]")

    # For bulk, the presence of names is enough
    return doctype == "HD Ticket" and (bool(name) or has_bulk)



def _is_telectro_tech():
    # Frappe v15: use get_roles(user)
    user = getattr(frappe, "session", None) and getattr(frappe.session, "user", None)
    if not user:
        return False

    # Never block admin / system managers (prevents lockouts during pilot)
    if user == "Administrator":
        return False

    try:
        roles = frappe.get_roles(user) or []
        if "System Manager" in roles:
            return False
        return "TELECTRO-POC Tech" in roles
    except Exception:
        return False




def _block_if_needed(d, action_word):
    if _is_telectro_tech() and _target_is_hd_ticket(d):
        frappe.throw(
            _('Pilot workflow: use Claim / Handoff. Direct {0} is blocked for Techs.').format(action_word),
            frappe.PermissionError,
        )
        
def _names_arg(d):
    """
    Return python list of docnames.
    Accepts:
      - list
      - JSON array string
      - "423"
      - "423,424"
    """
    names = d.get("names")

    if isinstance(names, (list, tuple, set)):
        return [str(x).strip() for x in names if str(x).strip()]

    if isinstance(names, str):
        s = names.strip()
        if not s:
            return []

        # JSON list?
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass

        # comma list?
        if "," in s:
            return [p.strip() for p in s.split(",") if p.strip()]

        # single
        return [s]

    return []

def _ensure_core_assign_to_shape(d: dict) -> dict:
    """
    Core assign_to.add expects args["assign_to"] to be either:
      - a JSON array string, e.g. '["a@x","b@x"]'
      - OR a python list, e.g. ["a@x","b@x"]

    This helper makes sure we never pass a raw "a@x" string into core.
    """
    out = dict(d)

    # Prefer assign_to, but support common alternates
    v = out.get("assign_to")
    if v is None:
        v = out.get("assign_to_user")
    if v is None:
        v = out.get("allocated_to")

    # If caller used an alternate key, normalize into assign_to
    if v is not None and "assign_to" not in out:
        out["assign_to"] = v

    v = out.get("assign_to")

    # list/tuple/set -> keep as list of strings
    if isinstance(v, (list, tuple, set)):
        users = [str(x).strip() for x in v if str(x).strip()]
        out["assign_to"] = users
        return out

    # string -> ensure JSON array string
    if isinstance(v, str):
        s = v.strip()

        # empty -> leave as-is (core will error, but that's correct)
        if not s:
            out["assign_to"] = "[]"
            return out

        # already JSON list string -> keep
        if s.startswith("[") and s.endswith("]"):
            out["assign_to"] = s
            return out

        # comma list -> json list
        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
            out["assign_to"] = json.dumps(parts)
            return out

        # single user -> json list
        out["assign_to"] = json.dumps([s])
        return out

    # anything else: leave untouched
    return out

@frappe.whitelist()
def add(*args, **kwargs):
    d = _merge_args_kwargs(*args, **kwargs)
    _dbg("add:enter", d, args=args, kwargs=kwargs)
    _block_if_needed(d, "assignment")

    # Only harden idempotency for HD Ticket (pilot scope)
    doctype = (d.get("doctype") or d.get("reference_type") or "").strip()
    name = (d.get("name") or d.get("docname") or d.get("reference_name") or "").strip()

    assign_to = d.get("assign_to") or d.get("assign_to_user") or d.get("allocated_to")
    users = _parse_assign_to_users(assign_to)
    
    _dbg("add:parsed_users", {"assign_to_raw": assign_to, "users": users})


    def _clean_users(seq):
        out = []
        for u in (seq or []):
            s = (str(u) if u is not None else "").strip()
            if s:
                out.append(s)
        return out

    if isinstance(assign_to, list):
        users = _clean_users(assign_to)

    elif isinstance(assign_to, str):
        s = assign_to.strip()
        if s:
            # UI often sends JSON string list like '["user@example.com"]'
            parsed = None
            if s[:1] == "[":
                try:
                    parsed = frappe.parse_json(s)  # handles JSON list strings
                except Exception:
                    parsed = None

            if isinstance(parsed, list):
                users = _clean_users(parsed)
            else:
                users = [s]

    # If we can't positively identify the target, fall back to core.
    # IMPORTANT: return core's response shape (UI expects an array-ish "message")
    if doctype != "HD Ticket" or not name or not users:
        core_assign_to.add(_ensure_core_assign_to_shape(d))
        return _as_assign_list(core_assign_to.get({"doctype": doctype, "name": name}))


    # De-dupe incoming list
    seen = set()
    uniq_users = []
    for u in users:
        if u not in seen:
            seen.add(u)
            uniq_users.append(u)

    # For each user, ensure exactly one Open ToDo exists (newest), and all older are Cancelled
    for u in uniq_users:
        todos = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": "HD Ticket",
                "reference_name": name,
                "allocated_to": u,
            },
            fields=["name", "status", "creation"],
            order_by="creation desc",
            ignore_permissions=True,
            limit_page_length=50,
        )

        if todos:
            newest = todos[0]["name"]

            # Ensure newest is Open
            if (todos[0].get("status") or "") != "Open":
                frappe.db.set_value("ToDo", newest, "status", "Open", update_modified=False)

            # Cancel older ones (Closed can resurrect in your stack)
            for td in todos[1:]:
                if (td.get("status") or "") != "Cancelled":
                    frappe.db.set_value("ToDo", td["name"], "status", "Cancelled", update_modified=False)

            continue

        # No ToDo exists at all -> create via core (keeps core side effects)
        payload = dict(d)
        payload["doctype"] = "HD Ticket"
        payload["name"] = name
        payload["assign_to"] = [u]  # core expects list or JSON-list-string
        core_assign_to.add(payload)

    # Extra hardening: Closed -> Cancelled (prevents reopen-on-save weirdness)
    try:
        _cancel_closed_todos_for_ticket(name)
    except Exception:
        pass

    # Normalize _assign from OPEN ToDos (canonical)
    try:
        open_users = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": "HD Ticket",
                "reference_name": name,
                "status": "Open",
            },
            pluck="allocated_to",
            ignore_permissions=True,
            limit_page_length=200,
        )
        final_users = sorted({(u or "").strip() for u in (open_users or []) if (u or "").strip()})
        frappe.db.set_value("HD Ticket", name, "_assign", json.dumps(final_users), update_modified=False)
    except Exception:
        pass

    _dbg("add:exit", {"doctype": doctype, "name": name})

    # CRITICAL: return the same shape the UI expects (a list)
    # This is what removes the `e.map is not a function` + hanging modal.
    return _as_assign_list(core_assign_to.get({"doctype": "HD Ticket", "name": name}))

@frappe.whitelist()
def remove(*args, **kwargs):
    d = _merge_args_kwargs(*args, **kwargs)
    _dbg("remove:enter", d, args=args, kwargs=kwargs)
    _block_if_needed(d, "unassign")

    # Frappe RPC calls this with kwargs: doctype, name, assign_to
    doctype = d.get("doctype")
    name = d.get("name")
    assign_to = d.get("assign_to")

    # If something weird comes in, fail with a useful message (instead of TypeError)
    if not doctype or not name or not assign_to:
        frappe.throw(
            f"assign_to.remove missing args: doctype={doctype}, name={name}, assign_to={assign_to}"
        )

    res = core_assign_to.remove(doctype, name, assign_to)

    # IMPORTANT: In this stack Closed ToDos can resurrect to Open later.
    # Cancelled behaves final and prevents old duplicates from being reopened on save().
    if (doctype or "").strip() == "HD Ticket":
        try:
            _cancel_closed_todos_for_ticket(name)
        except Exception:
            # Never break core remove
            pass

    return res


@frappe.whitelist()
def remove_multiple(doctype=None, names=None, ignore_permissions=None, *args, **kwargs):
    # 1) build payload dict
    if isinstance(doctype, (dict, str)) and names is None and ignore_permissions is None and not args and not kwargs:
        payload = _as_dict_from_first(doctype)
        d = _merge_args_kwargs(payload, **kwargs)
    else:
        d = _merge_args_kwargs(*args, **kwargs)
        if doctype is not None:
            d["doctype"] = doctype
        if names is not None:
            d["names"] = names
        if ignore_permissions is not None:
            d["ignore_permissions"] = ignore_permissions

    # 2) block
    _block_if_needed(d, "bulk unassign")

    # 3) normalize doctype
    doctype_val = d.get("doctype") or ""
    doctype_str = doctype_val.strip() if isinstance(doctype_val, str) else str(doctype_val).strip()

    # 4) normalize names to JSON string (core expects JSON string)
    names_json = _names_json(d)
    if names_json == "[]":
        frappe.throw("remove_multiple requires names")

    # 5) normalize ignore_permissions
    ip = d.get("ignore_permissions")
    if isinstance(ip, str) and ip.strip().isdigit():
        ignore_permissions_bool = bool(int(ip.strip()))
    elif isinstance(ip, int):
        ignore_permissions_bool = bool(ip)
    else:
        ignore_permissions_bool = bool(ip)

    _dbg("remove_multiple:call_core", {
        "doctype": doctype_str,
        "names_json": names_json,
        "ignore_permissions": ignore_permissions_bool,
    })

    # 6) hardened HD Ticket path
    if doctype_str == "HD Ticket":
        tickets = _names_arg({"names": names_json})

        # optional: make lock waits fail fast (avoid wedging the system)
        # keep it best-effort: older MariaDB may not like this var name in some configs
        try:
            frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 5")
        except Exception:
            pass

        changed_todos = 0
        changed_assign = 0
        failed = 0

        # deterministic order reduces deadlock likelihood
        for t in sorted([x for x in tickets if (x or "").strip()]):
            t = t.strip()
            try:
                # 1) Cancel all non-cancelled ToDos for this ticket (deterministic by ToDo.name)
                todos = frappe.get_all(
                    "ToDo",
                    filters={
                        "reference_type": "HD Ticket",
                        "reference_name": t,
                        "status": ("!=", "Cancelled"),
                    },
                    pluck="name",
                    ignore_permissions=True,
                    limit_page_length=200,
                )

                for todo_name in todos or []:
                    try:
                        frappe.db.set_value("ToDo", todo_name, "status", "Cancelled", update_modified=False)
                        changed_todos += 1
                    except Exception:
                        # keep going; we don't want one bad row to wedge bulk
                        pass

                # 2) Extra hardening: Closed -> Cancelled (covers reopen-on-save behavior)
                try:
                    changed_todos += _cancel_closed_todos_for_ticket(t)
                except Exception:
                    pass

                # 3) Normalize _assign from remaining OPEN ToDos (canonical)
                try:
                    open_users = frappe.get_all(
                        "ToDo",
                        filters={
                            "reference_type": "HD Ticket",
                            "reference_name": t,
                            "status": "Open",
                        },
                        pluck="allocated_to",
                        ignore_permissions=True,
                        limit_page_length=200,
                    )
                    final_users = sorted({(u or "").strip() for u in (open_users or []) if (u or "").strip()})
                    frappe.db.set_value("HD Ticket", t, "_assign", json.dumps(final_users), update_modified=False)
                    changed_assign += 1
                except Exception:
                    pass

                # ✅ critical: don’t leave an open transaction holding locks
                try:
                    frappe.db.commit()
                except Exception:
                    pass

            except Exception:
                failed += 1
                try:
                    frappe.db.rollback()
                except Exception:
                    pass

        return {
            "ok": 1,
            "doctype": doctype_str,
            "tickets": tickets,
            "changed_todos": changed_todos,
            "changed_assign": changed_assign,
            "failed": failed,
        }

    # 7) non-HD Ticket: delegate to core
    return core_assign_to.remove_multiple(
        doctype=doctype_str,
        names=names_json,
        ignore_permissions=ignore_permissions_bool,
    )



