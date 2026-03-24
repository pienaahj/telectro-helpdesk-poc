def execute(filters=None):
    filters = filters or {}

    # default to logged-in user when UI opens report with {}
    user = filters.get("assigned_user") or frappe.session.user
    pattern = '%"' + user + '"%'

    team = filters.get("team")  # optional

    columns = [
        {"label": "Ticket",  "fieldname": "name",       "fieldtype": "Link", "options": "HD Ticket", "width": 120},
        {"label": "Subject", "fieldname": "subject",    "fieldtype": "Data", "width": 360},
        {"label": "Status",  "fieldname": "status",     "fieldtype": "Data", "width": 100},
        {"label": "Priority","fieldname": "priority",   "fieldtype": "Data", "width": 100},
        {"label": "Team",    "fieldname": "agent_group","fieldtype": "Data", "width": 120},
        {"label": "Modified","fieldname": "modified",   "fieldtype": "Datetime", "width": 160},
    ]

    flt = [
        ["HD Ticket", "_assign", "like", pattern],
    ]
    if team:
        flt.append(["HD Ticket", "agent_group", "=", team])

    rows = frappe.get_all(
        "HD Ticket",
        fields=["name", "subject", "status", "priority", "agent_group", "modified"],
        filters=flt,
        order_by="modified desc",
        limit_page_length=50,
    )

    return columns, rows

data = execute(filters)