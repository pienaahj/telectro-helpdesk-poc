import frappe
from frappe.utils import now_datetime, time_diff_in_hours


TERMINAL_STATUSES = ("Resolved", "Closed", "Archived")
POOL_LABEL = "Unclaimed (Pool)"

INTERNAL_VIEW_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Tech",
    "Agent",
    "Support Team",
}


def execute(filters=None):
    user = frappe.session.user

    if not _can_view_report(user):
        return get_columns(), []

    rows = _get_rows()
    data = _build_summary_rows(rows)

    return get_columns(), data, None, _build_chart(data), _build_report_summary(data)


def get_columns():
    return [
        {
            "label": "Owner / Bucket",
            "fieldname": "owner_label",
            "fieldtype": "Data",
            "width": 240,
        },
        {
            "label": "Open Tickets",
            "fieldname": "open_tickets",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": "Sev1",
            "fieldname": "sev1",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": "Sev2",
            "fieldname": "sev2",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": "Sev3",
            "fieldname": "sev3",
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "label": "Partner Queue",
            "fieldname": "partner_queue",
            "fieldtype": "Int",
            "width": 130,
        },
        {
            "label": "Oldest Age Hours",
            "fieldname": "oldest_age_hours",
            "fieldtype": "Float",
            "precision": 1,
            "width": 140,
        },
        {
            "label": "Oldest Ticket",
            "fieldname": "oldest_ticket",
            "fieldtype": "Link",
            "options": "HD Ticket",
            "width": 120,
        },
        {
            "label": "Latest Activity",
            "fieldname": "latest_activity",
            "fieldtype": "Datetime",
            "width": 170,
        },
    ]


def _can_view_report(user: str) -> bool:
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user))
    return bool(roles & INTERNAL_VIEW_ROLES)


def _get_rows():
    return frappe.db.sql(
        """
        select
            t.name,
            t.subject,
            t.status,
            t.priority,
            t.custom_severity,
            t.custom_fulfilment_party,
            t.custom_partner_acceptance_state,
            t.custom_partner_work_state,
            t.creation,
            t.modified,
            t._assign,
            td.allocated_to as todo_owner
        from `tabHD Ticket` t
        left join `tabToDo` td
            on td.reference_type = 'HD Ticket'
            and td.reference_name = t.name
            and td.status = 'Open'
        where t.status not in %(terminal_statuses)s
        order by t.creation asc
        """,
        {"terminal_statuses": TERMINAL_STATUSES},
        as_dict=True,
    )


def _build_summary_rows(rows):
    buckets = {}

    for row in rows:
        owner = _owner_bucket(row)
        bucket = buckets.setdefault(
            owner,
            {
                "owner": owner,
                "owner_label": owner,
                "open_tickets": 0,
                "sev1": 0,
                "sev2": 0,
                "sev3": 0,
                "partner_queue": 0,
                "oldest_age_hours": 0,
                "oldest_ticket": "",
                "latest_activity": None,
                "_oldest_creation": None,
                "_ticket_names": set(),
            },
        )

        # A ticket can have duplicate Open ToDos in dirty historical data.
        # Count each ticket once per owner bucket.
        ticket_name = str(row.get("name") or "").strip()
        if not ticket_name or ticket_name in bucket["_ticket_names"]:
            continue

        bucket["_ticket_names"].add(ticket_name)
        bucket["open_tickets"] += 1

        severity = str(row.get("custom_severity") or row.get("priority") or "").strip()
        if severity == "Sev1":
            bucket["sev1"] += 1
        elif severity == "Sev2":
            bucket["sev2"] += 1
        elif severity == "Sev3":
            bucket["sev3"] += 1

        if _is_partner_queue_item(row):
            bucket["partner_queue"] += 1

        creation = row.get("creation")
        if creation and (not bucket["_oldest_creation"] or creation < bucket["_oldest_creation"]):
            bucket["_oldest_creation"] = creation
            bucket["oldest_ticket"] = ticket_name

        modified = row.get("modified")
        if modified and (not bucket["latest_activity"] or modified > bucket["latest_activity"]):
            bucket["latest_activity"] = modified

    now = now_datetime()

    data = []
    for bucket in buckets.values():
        oldest_creation = bucket.pop("_oldest_creation", None)
        bucket.pop("_ticket_names", None)

        if oldest_creation:
            bucket["oldest_age_hours"] = round(time_diff_in_hours(now, oldest_creation), 1)

        data.append(bucket)

    data.sort(
        key=lambda row: (
            0 if row["owner_label"] == POOL_LABEL else 1,
            -int(row.get("open_tickets") or 0),
            row["owner_label"],
        )
    )

    _apply_user_labels(data)

    return data


def _owner_bucket(row) -> str:
    todo_owner = str(row.get("todo_owner") or "").strip()
    if todo_owner:
        return todo_owner

    assign_users = _parse_assign_users(row.get("_assign"))
    if assign_users and assign_users != ["helpdesk@local.test"]:
        return assign_users[0]

    return POOL_LABEL


def _parse_assign_users(assign_val) -> list[str]:
    if not assign_val:
        return []

    if isinstance(assign_val, list):
        return [str(x).strip() for x in assign_val if str(x).strip()]

    if not isinstance(assign_val, str):
        return []

    value = assign_val.strip()
    if not value:
        return []

    try:
        parsed = frappe.parse_json(value)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        return []

    return []


def _is_partner_queue_item(row) -> bool:
    fulfilment_party = str(row.get("custom_fulfilment_party") or "").strip()
    acceptance_state = str(row.get("custom_partner_acceptance_state") or "").strip()
    work_state = str(row.get("custom_partner_work_state") or "").strip()

    return (
        fulfilment_party == "Partner"
        or acceptance_state in {"Pending Partner Acceptance", "Accepted by Partner", "Rework Required"}
        or work_state in {"Assigned to Partner", "Work Completed by Partner", "Rework Required"}
    )


def _apply_user_labels(data):
    user_ids = [
        row["owner"]
        for row in data
        if row.get("owner") and row.get("owner") != POOL_LABEL
    ]

    if not user_ids:
        return

    users = frappe.get_all(
        "User",
        filters={"name": ["in", user_ids]},
        fields=["name", "full_name"],
    )

    full_name_map = {
        user["name"]: (user.get("full_name") or user["name"])
        for user in users
    }

    for row in data:
        owner = row.get("owner")
        if owner and owner != POOL_LABEL:
            row["owner_label"] = full_name_map.get(owner, owner)


def _build_chart(data):
    return {
        "data": {
            "labels": [row["owner_label"] for row in data],
            "datasets": [
                {
                    "name": "Open Tickets",
                    "values": [row["open_tickets"] for row in data],
                }
            ],
        },
        "type": "bar",
        "height": 300,
    }


def _build_report_summary(data):
    total_open = sum(int(row.get("open_tickets") or 0) for row in data)
    pool_count = next(
        (
            int(row.get("open_tickets") or 0)
            for row in data
            if row.get("owner_label") == POOL_LABEL
        ),
        0,
    )
    partner_queue = sum(int(row.get("partner_queue") or 0) for row in data)

    return [
        {
            "label": "Total Open Tickets",
            "value": total_open,
            "indicator": "Blue",
        },
        {
            "label": "Unclaimed (Pool)",
            "value": pool_count,
            "indicator": "Orange" if pool_count else "Green",
        },
        {
            "label": "Partner Queue Items",
            "value": partner_queue,
            "indicator": "Purple" if partner_queue else "Green",
        },
    ]
