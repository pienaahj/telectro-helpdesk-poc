import json
import frappe


PULL_BASE = "telephony:pull_pilot_inboxes"


def _hook_list(hooks, doctype: str, event: str) -> list[str]:
    dt = (hooks or {}).get(doctype) or {}
    cur = dt.get(event)
    if not cur:
        return []
    if isinstance(cur, list):
        return [str(x) for x in cur]
    return [str(cur)]


def _cache(key: str):
    return frappe.cache().get_value(f"{PULL_BASE}:{key}")


def _pretty(val):
    if val is None:
        return None

    if isinstance(val, bytes):
        try:
            val = val.decode("utf-8")
        except Exception:
            return val

    if isinstance(val, str):
        s = val.strip()
        if not s:
            return s
        try:
            return json.loads(s)
        except Exception:
            return val

    return val


def run(limit: int = 8):
    hooks = frappe.get_hooks("doc_events") or {}

    hd_before_insert = _hook_list(hooks, "HD Ticket", "before_insert")
    hd_validate = _hook_list(hooks, "HD Ticket", "validate")
    hd_after_insert = _hook_list(hooks, "HD Ticket", "after_insert")
    hd_on_update = _hook_list(hooks, "HD Ticket", "on_update")

    print("\nRuntime")
    print("site                    :", frappe.local.site)
    print("user                    :", frappe.session.user)

    print("\nHD Ticket hooks")
    print("before_insert           :", hd_before_insert)
    print("validate                :", hd_validate)
    print("after_insert            :", hd_after_insert)
    print("on_update               :", hd_on_update)

    print("\nHook presence checks")
    print(
        "has_seed_ticket_routing :",
        "telephony.telectro_ticket_routing.seed_ticket_routing" in hd_validate,
    )
    print(
        "has_populate_from_email :",
        "telephony.telectro_intake.populate_from_email" in hd_before_insert,
    )
    print(
        "has_assign_after_insert :",
        "telephony.telectro_round_robin.assign_after_insert" in hd_after_insert,
    )
    print(
        "has_assign_sync         :",
        "telephony.telectro_assign_sync.sync_ticket_assignments" in hd_on_update,
    )

    print("\nPoller breadcrumb snapshot")
    print("fingerprint             :", _cache("fingerprint"))
    print("stage                   :", _cache("stage"))
    print("last_run                :", _cache("last_run"))
    print("last_ok                 :", _cache("last_ok"))
    print("last_err                :", _cache("last_err"))
    print("last_nonfatal_err       :", _cache("last_nonfatal_err"))
    print("per_account             :", _pretty(_cache("per_account")))

    print("\nLatest HD Tickets (routing sanity)")
    rows = frappe.get_all(
        "HD Ticket",
        fields=[
            "name",
            "creation",
            "email_account",
            "custom_service_area",
            "agent_group",
            "_assign",
            "subject",
        ],
        order_by="creation desc",
        limit_page_length=int(limit or 8),
        ignore_permissions=True,
    )
    for r in rows:
        print(r)

    print("")