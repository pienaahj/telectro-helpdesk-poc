import frappe


TERMINAL_STATUSES = ("Resolved", "Closed", "Archived")

INTERNAL_REVIEW_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
}

INTERNAL_WORK_ROLES = INTERNAL_REVIEW_ROLES | {
    "TELECTRO-POC Role - Tech",
    "Agent",
    "Support Team",
}


def execute(filters=None):
    return get_columns(), get_data(filters or {})


def get_columns():
    return [
        {"label": "Bucket", "fieldname": "bucket", "fieldtype": "Data", "width": 220},
        {"label": "Next Action", "fieldname": "next_action", "fieldtype": "Data", "width": 260},
        {"label": "Ticket", "fieldname": "name", "fieldtype": "Link", "options": "HD Ticket", "width": 110},
        {"label": "Subject", "fieldname": "subject", "fieldtype": "Data", "width": 280},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Priority", "fieldname": "priority", "fieldtype": "Data", "width": 90},
        {"label": "Customer", "fieldname": "custom_customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Campus", "fieldname": "custom_site_group", "fieldtype": "Link", "options": "Location", "width": 150},
        {"label": "Service Area", "fieldname": "custom_service_area", "fieldtype": "Data", "width": 130},
        {"label": "Request Source", "fieldname": "custom_request_source", "fieldtype": "Data", "width": 130},
        {"label": "Fulfilment Party", "fieldname": "custom_fulfilment_party", "fieldtype": "Data", "width": 130},
        {"label": "Partner Acceptance", "fieldname": "custom_partner_acceptance_state", "fieldtype": "Data", "width": 170},
        {"label": "Partner Work", "fieldname": "custom_partner_work_state", "fieldtype": "Data", "width": 170},
        {"label": "Modified", "fieldname": "modified", "fieldtype": "Datetime", "width": 160},
    ]


def get_data(filters):
    user = frappe.session.user

    if not _is_internal_user(user):
        return []

    broad_partner_visibility = _can_see_broad_partner_work(user)

    rows = []
    seen = set()

    # Priority order matters. A ticket needing review/rework should appear in that bucket
    # before generic "Assigned to me".
    sources = [
        _get_partner_acceptance_review_needed(user, broad_partner_visibility),
        _get_partner_acceptance_rework_follow_up(user, broad_partner_visibility),
        _get_partner_work_review_needed(user, broad_partner_visibility),
        _get_partner_work_currently_with_partner(user, broad_partner_visibility),
        _get_assigned_to_me(user),
        _get_shared_with_me(user),
    ]

    for source_rows in sources:
        for row in source_rows:
            name = str(row.get("name"))
            if name in seen:
                continue

            rows.append(row)
            seen.add(name)

    return rows


def _is_internal_user(user: str) -> bool:
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user))
    return bool(roles & INTERNAL_WORK_ROLES)


def _can_see_broad_partner_work(user: str) -> bool:
    roles = set(frappe.get_roles(user))
    return bool(roles & INTERNAL_REVIEW_ROLES)


def _base_select():
    return """
        select
            t.name,
            t.subject,
            t.status,
            t.priority,
            t.custom_customer,
            t.custom_site_group,
            t.custom_service_area,
            t.custom_request_source,
            t.custom_fulfilment_party,
            t.custom_partner_acceptance_state,
            t.custom_partner_work_state,
            t.modified
        from `tabHD Ticket` t
    """


def _scope_condition(broad_partner_visibility: bool):
    if broad_partner_visibility:
        return ""

    return """
        and (
            ifnull(t._assign, '') like %(assign_like)s
            or exists (
                select 1
                from `tabDocShare` ds
                where
                    ds.share_doctype = 'HD Ticket'
                    and ds.share_name = t.name
                    and ds.user = %(user)s
                    and ifnull(ds.read, 0) = 1
            )
        )
    """


def _params(user: str):
    return {
        "terminal_statuses": TERMINAL_STATUSES,
        "user": user,
        "assign_like": f'%"{user}"%',
    }


def _apply_bucket(rows, bucket: str, next_action: str):
    for row in rows:
        row["bucket"] = bucket
        row["next_action"] = next_action
    return rows


def _get_partner_acceptance_review_needed(user: str, broad_partner_visibility: bool):
    rows = frappe.db.sql(
        _base_select()
        + """
        where
            t.status not in %(terminal_statuses)s
            and ifnull(t.custom_request_source, '') = 'Partner'
            and ifnull(t.custom_fulfilment_party, '') != 'Partner'
            and ifnull(t.custom_partner_acceptance_state, '') = 'Accepted by Partner'
        """
        + _scope_condition(broad_partner_visibility)
        + """
        order by t.modified desc
        """,
        _params(user),
        as_dict=True,
    )

    return _apply_bucket(
        rows,
        "Partner acceptance review needed",
        "Review Partner acceptance and resolve, close, or review only",
    )


def _get_partner_acceptance_rework_follow_up(user: str, broad_partner_visibility: bool):
    rows = frappe.db.sql(
        _base_select()
        + """
        where
            t.status not in %(terminal_statuses)s
            and ifnull(t.custom_request_source, '') = 'Partner'
            and ifnull(t.custom_fulfilment_party, '') != 'Partner'
            and ifnull(t.custom_partner_acceptance_state, '') = 'Rework Required'
        """
        + _scope_condition(broad_partner_visibility)
        + """
        order by t.modified desc
        """,
        _params(user),
        as_dict=True,
    )

    return _apply_bucket(
        rows,
        "Partner acceptance rework follow-up",
        "Complete Telectro rework, then request Partner acceptance again",
    )


def _get_partner_work_review_needed(user: str, broad_partner_visibility: bool):
    rows = frappe.db.sql(
        _base_select()
        + """
        where
            t.status not in %(terminal_statuses)s
            and ifnull(t.custom_request_source, '') != 'Partner'
            and ifnull(t.custom_fulfilment_party, '') = 'Partner'
            and ifnull(t.custom_partner_work_state, '') = 'Work Completed by Partner'
        """
        + _scope_condition(broad_partner_visibility)
        + """
        order by t.modified desc
        """,
        _params(user),
        as_dict=True,
    )

    return _apply_bucket(
        rows,
        "Partner work review needed",
        "Review Partner work and accept, request rework, resolve, or close",
    )


def _get_partner_work_currently_with_partner(user: str, broad_partner_visibility: bool):
    rows = frappe.db.sql(
        _base_select()
        + """
        where
            t.status not in %(terminal_statuses)s
            and ifnull(t.custom_request_source, '') != 'Partner'
            and ifnull(t.custom_fulfilment_party, '') = 'Partner'
            and ifnull(t.custom_partner_work_state, '') in ('Assigned to Partner', 'Rework Required')
        """
        + _scope_condition(broad_partner_visibility)
        + """
        order by t.modified desc
        """,
        _params(user),
        as_dict=True,
    )

    return _apply_bucket(
        rows,
        "Partner work currently with Partner",
        "Monitor Partner progress or follow up where needed",
    )


def _get_assigned_to_me(user: str):
    rows = frappe.db.sql(
        _base_select()
        + """
        where
            t.status not in %(terminal_statuses)s
            and ifnull(t._assign, '') like %(assign_like)s
        order by t.modified desc
        """,
        _params(user),
        as_dict=True,
    )

    return _apply_bucket(
        rows,
        "Assigned to me",
        "Work assigned ticket",
    )


def _get_shared_with_me(user: str):
    rows = frappe.db.sql(
        _base_select()
        + """
        where
            t.status not in %(terminal_statuses)s
            and exists (
                select 1
                from `tabDocShare` ds
                where
                    ds.share_doctype = 'HD Ticket'
                    and ds.share_name = t.name
                    and ds.user = %(user)s
                    and ifnull(ds.read, 0) = 1
            )
        order by t.modified desc
        """,
        _params(user),
        as_dict=True,
    )

    return _apply_bucket(
        rows,
        "Shared with me",
        "Review shared ticket",
    )