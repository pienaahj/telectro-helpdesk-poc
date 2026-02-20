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

OK_STALE_AFTER_S = 180
ERR_STALE_AFTER_S = 600


def _to_dt(val):
    if not val:
        return None
    if hasattr(val, "strftime"):
        return val
    try:
        return frappe.utils.get_datetime(val)
    except Exception:
        return None


def _age_s(dt, now):
    if not dt:
        return None
    try:
        return int((now - dt).total_seconds())
    except Exception:
        return None


def _fmt_age(s):
    if s is None:
        return "-"
    if s < 0:
        return f"{s}s (future?)"
    if s < 60:
        return f"{s}s"
    m = s // 60
    r = s % 60
    if m < 60:
        return f"{m}m{r:02d}s"
    h = m // 60
    mm = m % 60
    return f"{h}h{mm:02d}m"


def run():
    cache = frappe.cache()

    # Avoid stale values in long-lived bench console sessions
    try:
        frappe.local.cache = {}
    except Exception:
        pass

    out = {}
    for k in KEYS:
        try:
            out[k] = cache.get_value(f"{BASE}:{k}")  # shared=False matches job writes
        except Exception as e:
            out[k] = f"<err: {repr(e)[:120]}>"

    now = frappe.utils.now_datetime()

    last_run_dt = _to_dt(out.get("last_run"))
    last_ok_dt = _to_dt(out.get("last_ok"))
    last_skip_dt = _to_dt(out.get("last_skip"))

    run_age = _age_s(last_run_dt, now)
    ok_age = _age_s(last_ok_dt, now)
    skip_age = _age_s(last_skip_dt, now)

    verdict = "WARN"
    reasons = []

    if out.get("last_err"):
        verdict = "ERR"
        reasons.append("last_err set")
    else:
        if ok_age is None:
            verdict = "WARN"
            reasons.append("last_ok missing")
        elif ok_age <= OK_STALE_AFTER_S:
            verdict = "OK"
            reasons.append(f"last_ok {_fmt_age(ok_age)} ago")
        elif ok_age <= ERR_STALE_AFTER_S:
            verdict = "WARN"
            reasons.append(f"last_ok stale ({_fmt_age(ok_age)} ago)")
        else:
            verdict = "ERR"
            reasons.append(f"last_ok too old ({_fmt_age(ok_age)} ago)")

    print(f"\nJob status keyspace: {BASE}:*\n")
    print(f"verdict: {verdict} ({', '.join(reasons)})")
    print(f"now: {now}")
    print(f"run_age: {_fmt_age(run_age)}")
    print(f"ok_age: {_fmt_age(ok_age)}")
    print(f"skip_age: {_fmt_age(skip_age)}")
    print("")

    for k in KEYS:
        print(f"{k}: {out.get(k)}")

    print("\nDone.\n")