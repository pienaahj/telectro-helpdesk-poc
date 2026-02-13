#!/usr/bin/env bash
set -euo pipefail

SITE="${PILOT_SITE:-frontend}"
TICKET="${PILOT_TICKET:-423}"

docker compose exec -T \
  -e PILOT_SITE="$SITE" \
  -e PILOT_TICKET="$TICKET" \
  backend bash -s <<'BASH'
set -euo pipefail

BENCH=/home/frappe/frappe-bench
SITE="${PILOT_SITE:-frontend}"
TICKET="${PILOT_TICKET:-423}"

cd "$BENCH"

# Ensure log dirs exist (Frappe logger can choke if missing)
mkdir -p "$BENCH/logs"
mkdir -p "$BENCH/sites/$SITE/logs"
# 🔧 compatibility: some contexts resolve site logs under BENCH/<site>/logs
mkdir -p "$BENCH/$SITE/logs"

cat > /tmp/pilot_smoke.py <<'PY'
import os
import frappe

SITE = os.environ.get("PILOT_SITE", "frontend")
TICKET = os.environ.get("PILOT_TICKET", "423")
BENCH_ROOT = os.environ.get("FRAPPE_BENCH_ROOT", "/home/frappe/frappe-bench")
SITES_PATH = os.path.join(BENCH_ROOT, "sites")

FAILS = []
WARNS = []

def hook_has_value(d, key, want):
    """frappe.get_hooks() sometimes returns list-valued entries. Normalize."""
    v = (d or {}).get(key)
    if v is None:
        return False, v
    if isinstance(v, (list, tuple, set)):
        return want in v, v
    return v == want, v

def fail(msg):
    FAILS.append(msg)
    print("❌", msg)

def warn(msg):
    WARNS.append(msg)
    print("⚠️ ", msg)

def ok(msg):
    print("✅", msg)

def exists_dt(doctype, name):
    try:
        return bool(frappe.db.exists(doctype, name))
    except Exception:
        return False

def print_kv(k, v):
    print(f"  - {k}: {v}")

def main():
    os.chdir(BENCH_ROOT)

    print("\n=== ERPNext Pilot Smoke ===")
    print_kv("site", SITE)
    print_kv("bench_root", BENCH_ROOT)
    print_kv("sites_path", SITES_PATH)
    print_kv("ticket", TICKET)

    frappe.init(site=SITE, sites_path=SITES_PATH)
    frappe.connect()

    # Optional: show what file we imported for telephony.hooks (helps diagnose drift)
    try:
        import telephony.hooks as th
        ok(f"telephony.hooks imported from: {getattr(th, '__file__', None)}")
    except Exception as e:
        warn(f"telephony.hooks import failed: {e}")

    # --- Apps installed ---
    apps = frappe.get_installed_apps() or []
    if "telephony" not in apps:
        fail("telephony app is NOT installed on this site")
    else:
        ok("telephony installed")

    # --- Hooks sanity (single source of truth: frappe.get_hooks) ---
    print("\n[hooks]")

    hooks_ov = frappe.get_hooks("override_whitelisted_methods") or {}
    ok1, got_ov = hook_has_value(
        hooks_ov,
        "frappe.desk.form.assign_to.add",
        "telephony.overrides.assign_to.add",
    )
    if not ok1:
        fail(f"override_whitelisted_methods missing/incorrect for assign_to.add (got {got_ov})")
    else:
        ok("override assign_to.add ok")

    hooks_de = frappe.get_hooks("doc_events") or {}
    hd = hooks_de.get("HD Ticket") or {}

    if not isinstance(hd, dict) or not hd:
        fail(f"doc_events for HD Ticket missing/empty (got type={type(hd).__name__})")
    else:
        want = {
            "after_insert": "telephony.telectro_round_robin.assign_after_insert",
            "validate": "telephony.telectro_assign_sync.dedupe_assign_field",
            "on_update": "telephony.telectro_assign_sync.sync_ticket_assignments",
        }

        bad = []
        for k, expected in want.items():
            okk, got = hook_has_value(hd, k, expected)
            if not okk:
                bad.append((k, got))

        if bad:
            fail(f"HD Ticket doc_events wrong targets: {bad}")
        else:
            ok("HD Ticket doc_events targets ok")

    # Helpful debug (kept here, without re-checking twice)
    print_kv("override_whitelisted_methods type", type(hooks_ov).__name__)
    print_kv("override_whitelisted_methods keys sample", sorted(list(hooks_ov.keys()))[:12])

    print_kv("doc_events type", type(hooks_de).__name__)
    print_kv("doc_events has HD Ticket", "HD Ticket" in hooks_de)
    if "HD Ticket" in hooks_de:
        hd2 = hooks_de.get("HD Ticket") or {}
        print_kv("HD Ticket doc_events type", type(hd2).__name__)
        print_kv("HD Ticket doc_events keys", sorted(list(hd2.keys())))
        for k in sorted(list(hd2.keys())):
            print_kv(f"HD Ticket.{k}", hd2.get(k))

    # --- Custom Fields ---
    print("\n[custom fields]")
    cf_names = [
        "HD Ticket-custom_customer",
        "HD Ticket-custom_site",
        "HD Ticket-custom_equipment_ref",
    ]
    missing = [n for n in cf_names if not exists_dt("Custom Field", n)]
    if missing:
        fail(f"Missing Custom Field(s): {missing}")
    else:
        ok("Custom Fields present")

    for name in cf_names:
        if not exists_dt("Custom Field", name):
            continue
        doc = frappe.get_doc("Custom Field", name)
        print(f"- {name}")
        print_kv("dt", doc.dt)
        print_kv("fieldname", doc.fieldname)
        print_kv("fieldtype", doc.fieldtype)
        print_kv("label", doc.label)
        print_kv("insert_after", getattr(doc, "insert_after", None))
        print_kv("options", doc.get("options"))

    # --- Client Scripts ---
    print("\n[client scripts]")
    script_names = [
        "Clear Customer and filter List",
        "Claim HD Ticket",
        "Pull Faults",
    ]
    missing = [n for n in script_names if not exists_dt("Client Script", n)]
    if missing:
        fail(f"Missing Client Script(s): {missing}")
    else:
        ok("Client Scripts present")

    markers = {
        "Clear Customer and filter List": ["parent_location", "Pilot Sites", "custom_site", "custom_customer"],
        "Claim HD Ticket": ["POOL_USER", "telephony.telectro_claim", "Claim", "Handoff"],
        "Pull Faults": ["frappe.listview_settings", "list_update", "custom_service_area", "faults"],
    }

    for n in script_names:
        if not exists_dt("Client Script", n):
            continue
        doc = frappe.get_doc("Client Script", n)
        s = (doc.get("script") or "")
        print(f"- {n}")
        print_kv("dt", doc.dt)
        print_kv("view", getattr(doc, "view", None))
        print_kv("enabled", doc.enabled)

        want = markers.get(n) or []
        missing_m = [m for m in want if m not in s]
        if missing_m:
            warn(f"{n}: missing markers {missing_m}")
        else:
            ok(f"{n}: marker check ok")

    # --- Pilot Sites existence ---
    print("\n[sites model]")
    if exists_dt("Location", "Pilot Sites"):
        ok('Location "Pilot Sites" exists')
    else:
        warn('Location "Pilot Sites" NOT FOUND (site filtering may not work)')

    # --- Ticket read check ---
    print("\n[ticket read]")
    if exists_dt("HD Ticket", TICKET):
        t = frappe.get_doc("HD Ticket", TICKET)
        ok(f"Ticket {TICKET} exists")
        print_kv("subject", getattr(t, "subject", None))
        print_kv("custom_customer", t.get("custom_customer"))
        print_kv("custom_site", t.get("custom_site"))
        print_kv("custom_equipment_ref", t.get("custom_equipment_ref"))
    else:
        warn(f"Ticket {TICKET} not found (OK)")

    print("\n=== summary ===")
    print_kv("fails", len(FAILS))
    print_kv("warns", len(WARNS))

    if FAILS:
        raise SystemExit(1)

    print("\n✅ SMOKE PASS\n")

if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            frappe.destroy()
        except Exception:
            pass
PY

FRAPPE_BENCH_ROOT="$BENCH" \
  "$BENCH/env/bin/python" /tmp/pilot_smoke.py
BASH
