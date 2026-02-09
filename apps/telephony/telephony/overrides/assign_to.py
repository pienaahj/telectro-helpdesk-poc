import json
import frappe
from frappe import _

# Delegate to core implementation for everyone except pilot-tech restrictions.
from frappe.desk.form import assign_to as core_assign_to


def _as_dict_from_first(arg0):
    """Accept dict, JSON string, or None and return dict."""
    if arg0 is None:
        return {}
    if isinstance(arg0, dict):
        return dict(arg0)
    if isinstance(arg0, str):
        try:
            d = json.loads(arg0)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}
    return {}

def _names_json(d):
    """
    Core Frappe remove_multiple expects `names` as a JSON string.
    Incoming can be:
      - JSON string '["414","413"]'  (most common from UI)
      - list ["414","413"]           (rare)
      - plain string "414"           (rare)
    """
    names = d.get("names")

    if isinstance(names, str):
        s = names.strip()
        # If it's already JSON array string, keep it
        if s.startswith("[") and s.endswith("]"):
            return s
        # Otherwise treat as single docname
        return json.dumps([s]) if s else "[]"

    if isinstance(names, list):
        return json.dumps(names)

    if names is None:
        return "[]"

    # Fallback: stringify
    return json.dumps([str(names)])



def _merge_args_kwargs(*args, **kwargs):
    """
    Frappe calls whitelisted methods in a few shapes:
      - add(args={...})
      - add(args='{"doctype":...}')
      - remove(doctype='HD Ticket', name='...')
      - etc

    We normalize into ONE dict for easier checks.
    """
    d = {}
    if args:
        # If first positional is dict/json-string, merge it.
        d.update(_as_dict_from_first(args[0]))

    if kwargs:
        # Some calls wrap everything in 'args'
        if 'args' in kwargs and isinstance(kwargs['args'], (dict, str)):
            d.update(_as_dict_from_first(kwargs.get('args')))
            # keep other kwargs too (kwargs wins)
            rest = dict(kwargs)
            rest.pop('args', None)
            d.update(rest)
        else:
            d.update(kwargs)

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
    # Bulk endpoints often send names as JSON string '["414"]'
    names = d.get("names")
    if isinstance(names, list):
        return names
    if isinstance(names, str):
        try:
            parsed = json.loads(names)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        # fall back: treat as a single name
        s = names.strip()
        return [s] if s else []
    return []



@frappe.whitelist()
def add(*args, **kwargs):
    d = _merge_args_kwargs(*args, **kwargs)
    _block_if_needed(d, 'assignment')
    # Core expects a dict (not JSON string)
    return core_assign_to.add(d)


@frappe.whitelist()
def remove(*args, **kwargs):
    d = _merge_args_kwargs(*args, **kwargs)
    _block_if_needed(d, 'unassign')

    # Frappe RPC calls this with kwargs: doctype, name, assign_to
    doctype = d.get("doctype")
    name = d.get("name")
    assign_to = d.get("assign_to")

    # If something weird comes in, fail with a useful message (instead of TypeError)
    if not doctype or not name or not assign_to:
        frappe.throw(
            f"assign_to.remove missing args: doctype={doctype}, name={name}, assign_to={assign_to}"
        )

    return core_assign_to.remove(doctype, name, assign_to)



@frappe.whitelist()
def remove_multiple(doctype=None, names=None, ignore_permissions=None, *args, **kwargs):
    """
    Accept all common call shapes:
      - remove_multiple("HD Ticket", '["A","B"]', 0)
      - remove_multiple(doctype="HD Ticket", names='["A","B"]')
      - remove_multiple({"doctype":"HD Ticket","names":'["A","B"]'})
      - remove_multiple(args={"doctype":"HD Ticket","names":'["A","B"]'})

    Normalize into dict `d`, enforce pilot block, then call core.
    """

    # If first param is actually a payload dict/json, treat it like the old *args shape.
    if isinstance(doctype, (dict, str)) and not names and not ignore_permissions:
        # dict OR JSON string: merge as payload
        payload = _as_dict_from_first(doctype)
        d = _merge_args_kwargs(payload, **kwargs)
    else:
        d = _merge_args_kwargs(*args, **kwargs)

        # Overlay explicit params (positional/keyword)
        if doctype is not None:
            d["doctype"] = doctype
        if names is not None:
            d["names"] = names
        if ignore_permissions is not None:
            d["ignore_permissions"] = ignore_permissions

    _block_if_needed(d, "bulk unassign")

    doctype_val = d.get("doctype") or ""
    doctype_str = doctype_val.strip() if isinstance(doctype_val, str) else str(doctype_val).strip()

    names_json = _names_json(d)

    ip = d.get("ignore_permissions")
    if isinstance(ip, str) and ip.strip().isdigit():
        ignore_permissions_bool = bool(int(ip.strip()))
    elif isinstance(ip, int):
        ignore_permissions_bool = bool(ip)
    else:
        ignore_permissions_bool = bool(ip)

    return core_assign_to.remove_multiple(
        doctype=doctype_str,
        names=names_json,
        ignore_permissions=ignore_permissions_bool,
    )


@frappe.whitelist()
def close_all_assignments(*args, **kwargs):
    d = _merge_args_kwargs(*args, **kwargs)
    _block_if_needed(d, 'close assignments')
    return core_assign_to.close_all_assignments(d)
