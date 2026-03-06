# apps/telephony/telephony/scripts/proof_report_my_hd_tickets.py

import frappe
import frappe.desk.query_report as qr

REPORT = "My HD Tickets"


def run_case(filters):
    res = qr.run(REPORT, filters=filters or {})
    cols = res.get("columns") or []
    rows = res.get("result") or []

    print("\n---", REPORT, "filters=", filters, "---")
    print("columns:", len(cols))
    print("rows:", len(rows))

    if cols:
        print("colnames:", [c.get("label") or c.get("fieldname") for c in cols])

    if rows:
        print("sample rows:", rows[:2])


def run(user="tech.alfa@local.test"):
    # Basic environment proof
    print("site:", frappe.local.site)
    print("user:", frappe.session.user)

    # Report doc sanity
    rep = frappe.get_doc("Report", REPORT)
    print("report:", rep.name, "| type:", rep.report_type, "| ref_doctype:", rep.ref_doctype)

    # Quick script prefix (helps confirm correct version deployed)
    script = rep.get("report_script") or ""
    print("script_prefix:\n", script[:400])

    # The 3 cases
    run_case({})
    run_case({"user": user})
    run_case({"assigned_user": user})