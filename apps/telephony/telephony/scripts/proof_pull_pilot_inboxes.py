import json
import frappe

STAGE_A_BASE = "telephony:stage_a"
PULL_BASE = "telephony:pull_pilot_inboxes"


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


def _print_section(title, base, keys):
    print(f"\n{title}")
    for key in keys:
        full = f"{base}:{key}"
        val = frappe.cache().get_value(full)
        print(f"{key:24}: {_pretty(val)}")


def run(limit=10):
    _print_section(
        "Stage A / intake breadcrumbs",
        STAGE_A_BASE,
        [
            "last_ok",
            "last_ticket",
            "last_updates",
            "last_sender",
            "last_custom_customer",
            "last_customer_map_reason",
            "last_ticket_link",
            "last_customer_confirm_link",
            "last_sender_non_bounce",
            "last_sender_non_bounce_ticket",
            "last_sender_non_bounce_subject",
            "last_sender_non_bounce_at",
            "last_bounce_guard_hit",
            "last_bounce_guard_seen_at",
            "last_bounce_guard_key",
            "last_bounce_guard_window_seconds",
            "last_bounce_ticket",
            "last_bounce_reason",
            "last_bounce_subject",
            "last_bounce_sender",
            "last_bounce_at",
            "last_autoreply_verdict",
            "last_autoreply_sent_ok",
            "last_autoreply_sent_at",
            "last_autoreply_sent_to",
            "last_autoreply_error",
        ],
    )

    _print_section(
        "Pull Pilot Inboxes job breadcrumbs",
        PULL_BASE,
        [
            "fingerprint",
            "stage",
            "lock_acquired",
            "last_run",
            "last_start",
            "last_skip",
            "last_ok",
            "last_err",
            "last_nonfatal_err",
            "processed_total",
            "processed_last_run",
            "last_comm",
            "last_ticket",
            "last_mail_meta",
            "last_skip_meta",
            "per_account",
            "last_per_account_nonzero",
        ],
    )

    print("\nLatest HD Tickets (sanity)")
    rows = frappe.get_all(
        "HD Ticket",
        fields=[
            "name",
            "creation",
            "custom_customer",
            "customer",
            "raised_by",
            "custom_site_group",
            "agent_group",
            "subject",
        ],
        order_by="creation desc",
        limit=limit,
        ignore_permissions=True,
    )

    for r in rows:
        print(r)

    print("")
    print("\nQuick verdict")
    print("poller_last_ok        :", frappe.cache().get_value(f"{PULL_BASE}:last_ok"))
    print("poller_last_err       :", frappe.cache().get_value(f"{PULL_BASE}:last_err"))
    print("poller_last_nonfatal  :", frappe.cache().get_value(f"{PULL_BASE}:last_nonfatal_err"))
    print("last_skip_meta        :", _pretty(frappe.cache().get_value(f"{PULL_BASE}:last_skip_meta")))
    print("last_nonzero_snapshot :", _pretty(frappe.cache().get_value(f"{PULL_BASE}:last_per_account_nonzero")))