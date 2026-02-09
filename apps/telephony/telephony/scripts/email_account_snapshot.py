import frappe

def run():
    meta = frappe.get_meta("Email Account")
    cols = (meta.get_valid_columns() or [])
    # keep it focused; show a safe subset that actually helps debugging
    fields = [c for c in [
        "name",
        "enable_incoming",
        "default_incoming",
        "email_id",
        "login_id",
        "service",
        "domain",
        "use_imap",
        "use_ssl",
        "use_tls",
        "imap_server",
        "imap_port",
        "smtp_server",
        "smtp_port",
    ] if c in cols]

    rows = frappe.get_all("Email Account", fields=fields, ignore_permissions=True, limit_page_length=200)
    print("Email Accounts:", len(rows))
    for r in rows:
        print(r)
