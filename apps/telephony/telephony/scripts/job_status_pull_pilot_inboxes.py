import frappe

BASE = "telephony:pull_pilot_inboxes"

KEYS = [
    "fingerprint",
    "stage",
    "lock_acquired",
    "last_run",
    "last_skip",
    "last_ok",
    "last_err",
    "processed_total",
    "last_comm",
    "last_ticket",
    "per_account",
]

def run():
    cache = frappe.cache()

    out = {}
    for k in KEYS:
        try:
            out[k] = cache.get_value(f"{BASE}:{k}")
        except Exception as e:
            out[k] = f"<err: {repr(e)[:120]}>"

    print(f"\nJob status keyspace: {BASE}:*\n")
    for k in KEYS:
        v = out.get(k)
        # Pretty-print dict-ish payloads (per_account) without importing json
        if isinstance(v, (dict, list)):
            print(f"{k}: {v}")
        else:
            print(f"{k}: {v}")

    print("\nDone.\n")
