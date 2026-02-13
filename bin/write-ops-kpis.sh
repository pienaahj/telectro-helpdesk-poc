#!/usr/bin/env bash
set -euo pipefail

DEST="/home/frappe/frappe-bench/apps/telephony/telephony/ops_kpis.py"

docker compose exec -T backend bash -lc "cat > '$DEST'" <<'PY'
import frappe

# Unassigned definition:
# `_assign` is stored as a JSON list string like '["user@example.com"]'
# so we treat NULL/''/'[]' as unassigned.
_UNASSIGNED_SQL = "IFNULL(`_assign`, '') IN ('', '[]')"

def _count_unassigned(min_idle_minutes: int) -> int:
    mins = int(min_idle_minutes)

    # NOTE: using "creation age" as the idle proxy (simple + reliable).
    # If later you define idle as "since last comm / last status change",
    # this becomes the one place to update.
    row = frappe.db.sql(
        f"""
        SELECT COUNT(*) AS c
        FROM `tabHD Ticket`
        WHERE {_UNASSIGNED_SQL}
          AND TIMESTAMPDIFF(MINUTE, creation, NOW()) >= %s
        """,
        (mins,),
        as_dict=True,
    )[0]

    return int(row.get("c") or 0)

@frappe.whitelist()
def unassigned_now() -> int:
    return _count_unassigned(0)

@frappe.whitelist()
def unassigned_over_60m() -> int:
    return _count_unassigned(60)

@frappe.whitelist()
def unassigned_over_4h() -> int:
    return _count_unassigned(240)
PY

echo "✅ Wrote: $DEST"
