import frappe
from frappe.utils import cint, pretty_date


@frappe.whitelist()
def unclaimed_over_1_day_card(limit=4):
    limit = cint(limit or 4)

    from telephony.ftelephony.report.unclaimed_over_1_day.unclaimed_over_1_day import execute

    columns, data, *_ = execute()

    rows = []
    for row in data[:limit]:
        rows.append(
            {
                "name": row["name"],
                "subject": row.get("subject") or row["name"],
                "status": row.get("status") or "",
                "modified": row.get("modified"),
                "modified_pretty": pretty_date(row.get("modified")) if row.get("modified") else "",
                "idle_hours": row.get("idle_hours") or 0,
                "route": f"/app/hd-ticket/{row['name']}",
            }
        )

    return {
        "title": "Unclaimed > 1 Day",
        "count": len(data),
        "rows": rows,
        "report_route": "/app/query-report/Unclaimed%20Over%201%20Day",
    }