import json

import frappe
from frappe import _
from frappe.utils import cint, pretty_date, strip_html


TECHNICIAN_PROFILE = "TELECTRO-POC Profile - Technician"
COORDINATOR_TECHNICIAN_PROFILE = "TELECTRO-POC Profile - Coordinator-Technician"

ALLOWED_GOVERNANCE_ROLES = {
    "System Manager",
    "TELECTRO-POC Role - Supervisor Governance",
}

SHARE_CONTEXT_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
}


@frappe.whitelist()
def share_ticket_context(ticket_name, collaborator, note):
    ticket = _get_ticket_for_context_share(ticket_name)
    collaborator_doc = _get_context_share_collaborator(collaborator)
    note = (note or "").strip()

    if not note:
        frappe.throw(_("A note / reason is required."), frappe.ValidationError)

    _require_ticket_context_share_access(ticket)

    before_assign = ticket.get("_assign") or ""

    content = _build_ticket_context_share_comment(
        ticket=ticket,
        collaborator_doc=collaborator_doc,
        note=note,
    )

    frappe.get_doc(
        {
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "HD Ticket",
            "reference_name": ticket.name,
            "content": content,
        }
    ).insert(ignore_permissions=True)

    # Defensive proof: this action must never mutate assignment.
    after_assign = frappe.db.get_value("HD Ticket", ticket.name, "_assign") or ""
    if after_assign != before_assign:
        frappe.throw(
            _("Share Ticket Context attempted to change assignment. No share was applied."),
            frappe.ValidationError,
        )

    frappe.db.commit()

    return {
        "ok": True,
        "ticket": ticket.name,
        "collaborator": collaborator_doc.name,
        "collaborator_name": collaborator_doc.full_name or collaborator_doc.name,
        "message": _("Ticket context shared."),
    }

def _get_context_display_value(doctype, name, display_fields):
    name = (name or "").strip()

    if not name:
        return "-"

    if not frappe.db.exists(doctype, name):
        return name

    for fieldname in display_fields:
        value = frappe.db.get_value(doctype, name, fieldname)
        if value:
            return value

    title_field = frappe.get_meta(doctype).title_field
    if title_field:
        value = frappe.db.get_value(doctype, name, title_field)
        if value:
            return value

    return name


def _get_context_customer_name(customer):
    return _get_context_display_value("Customer", customer, ["customer_name"])


def _get_context_location_name(location):
    return _get_context_display_value("Location", location, ["location_name"])

def _get_ticket_for_context_share(ticket_name):
    if not ticket_name:
        frappe.throw(_("A ticket is required."), frappe.ValidationError)

    if not frappe.db.exists("HD Ticket", ticket_name):
        frappe.throw(_("Ticket {0} was not found.").format(ticket_name))

    return frappe.get_doc("HD Ticket", ticket_name)


def _get_context_share_collaborator(collaborator):
    if not collaborator:
        frappe.throw(_("A collaborator is required."), frappe.ValidationError)

    if not frappe.db.exists("User", collaborator):
        frappe.throw(_("User {0} was not found.").format(collaborator))

    doc = frappe.get_doc("User", collaborator)

    if cint(doc.enabled) != 1:
        frappe.throw(_("User {0} is disabled.").format(collaborator))

    if (doc.user_type or "System User") != "System User":
        frappe.throw(_("User {0} is not a System User.").format(collaborator))

    return doc


def _require_ticket_context_share_access(ticket):
    user = frappe.session.user

    if user == "Administrator":
        return

    roles = set(frappe.get_roles(user) or [])
    if roles & SHARE_CONTEXT_ROLES:
        return

    assigned_users = set(_parse_assigned_users(ticket.get("_assign")))

    if user in assigned_users:
        return

    frappe.throw(
        _("You are not allowed to share context for this ticket."),
        frappe.PermissionError,
    )


def _parse_assigned_users(raw_assign):
    if not raw_assign:
        return []

    if isinstance(raw_assign, list):
        return [user for user in raw_assign if user]

    if isinstance(raw_assign, str):
        raw_assign = raw_assign.strip()

        if not raw_assign:
            return []

        try:
            parsed = json.loads(raw_assign)
        except Exception:
            return [raw_assign]

        if isinstance(parsed, list):
            return [user for user in parsed if user]

        if parsed:
            return [str(parsed)]

    return []


def _build_ticket_context_share_comment(*, ticket, collaborator_doc, note):
    collaborator_label = collaborator_doc.full_name or collaborator_doc.name

    customer = _get_context_customer_name(ticket.get("custom_customer") or ticket.get("customer"))
    campus = _get_context_location_name(ticket.get("custom_site_group"))
    fault_point = _get_context_location_name(ticket.get("custom_site"))
    fault_asset = _get_context_location_name(ticket.get("custom_fault_asset"))

    lines = [
        f"Ticket context shared by {frappe.session.user} with {collaborator_label} ({collaborator_doc.name}).",
        "",
        "Reason / note:",
        strip_html(note),
        "",
        "Ticket context:",
        f"- Ticket: {ticket.name}",
        f"- Subject: {ticket.subject or '-'}",
        f"- Status: {ticket.status or '-'}",
        f"- Customer: {customer}",
        f"- Campus: {campus}",
        f"- Fault Point: {fault_point}",
        f"- Fault Asset: {fault_asset}",
        f"- Service Area: {ticket.get('custom_service_area') or '-'}",
        f"- Severity: {ticket.get('custom_severity') or '-'}",
        f"- Fulfilment Party: {ticket.get('custom_fulfilment_party') or '-'}",
    ]

    return "<br>".join(frappe.utils.escape_html(line) for line in lines)

@frappe.whitelist()
def coordinator_uplift_candidates():
    _require_coordinator_governance_access()

    data = frappe.db.sql(
        """
        SELECT
            u.name,
            u.full_name,
            u.enabled,
            u.email,
            u.role_profile_name,
            u.modified
        FROM `tabUser` u
        WHERE u.role_profile_name IN (
            %(technician_profile)s,
            %(coordinator_technician_profile)s
        )
          AND IFNULL(u.user_type, 'System User') = 'System User'
        ORDER BY
            CASE
                WHEN u.role_profile_name = %(coordinator_technician_profile)s THEN 0
                ELSE 1
            END,
            u.enabled DESC,
            u.full_name ASC,
            u.name ASC
        """,
        {
            "technician_profile": TECHNICIAN_PROFILE,
            "coordinator_technician_profile": COORDINATOR_TECHNICIAN_PROFILE,
        },
        as_dict=True,
    )

    rows = []
    for row in data:
        is_uplifted = (row.get("role_profile_name") or "") == COORDINATOR_TECHNICIAN_PROFILE
        rows.append(
            {
                "name": row["name"],
                "full_name": row.get("full_name") or row["name"],
                "email": row.get("email") or row["name"],
                "enabled": cint(row.get("enabled") or 0),
                "role_profile_name": row.get("role_profile_name") or "",
                "is_coordinator_uplifted": is_uplifted,
                "status_label": "Coordinator active" if is_uplifted else "Technician only",
            }
        )

    return {
        "rows": rows,
    }


def _log_coordinator_uplift_change(*, target_user, action, before_profile, after_profile):
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "User",
        "reference_name": target_user,
        "content": (
            f"Coordinator uplift {action} by {frappe.session.user}. "
            f"Profile changed from {before_profile or '-'} to {after_profile or '-'}."
        ),
    }).insert(ignore_permissions=True)
    
    
def _require_coordinator_governance_access():
    user = frappe.session.user

    if user == "Administrator":
        return

    user_roles = set(frappe.get_roles(user) or [])
    if not (user_roles & ALLOWED_GOVERNANCE_ROLES):
        frappe.throw(
            _("You are not allowed to manage coordinator uplift."),
            frappe.PermissionError,
        )


def _get_user_doc_for_governance(user_email):
    if not user_email:
        frappe.throw(_("A target user is required."))

    if not frappe.db.exists("User", user_email):
        frappe.throw(_("User {0} was not found.").format(user_email))

    doc = frappe.get_doc("User", user_email)

    if cint(doc.enabled) != 1:
        frappe.throw(_("User {0} is disabled.").format(user_email))

    if (doc.user_type or "System User") != "System User":
        frappe.throw(_("User {0} is not a System User.").format(user_email))

    return doc


def _is_technician_profile(doc):
    return (doc.role_profile_name or "") == TECHNICIAN_PROFILE


def _is_coordinator_uplifted_profile(doc):
    return (doc.role_profile_name or "") == COORDINATOR_TECHNICIAN_PROFILE


def _serialize_governance_state(doc, message):
    roles = sorted([row.role for row in doc.roles])
    return {
        "ok": True,
        "user": doc.name,
        "full_name": doc.full_name,
        "enabled": cint(doc.enabled or 0),
        "role_profile_name": doc.role_profile_name or "",
        "is_coordinator_uplifted": _is_coordinator_uplifted_profile(doc),
        "roles": roles,
        "message": message,
    }


@frappe.whitelist()
def grant_coordinator_uplift(user_email):
    _require_coordinator_governance_access()

    doc = _get_user_doc_for_governance(user_email)
    before_profile = doc.role_profile_name or ""

    if _is_coordinator_uplifted_profile(doc):
        return _serialize_governance_state(doc, _("Coordinator uplift already granted."))

    if not _is_technician_profile(doc):
        frappe.throw(
            _("Coordinator uplift can only be granted to users in the Technician profile."),
            frappe.ValidationError,
        )

    doc.role_profile_name = COORDINATOR_TECHNICIAN_PROFILE
    doc.populate_role_profile_roles()
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    doc = frappe.get_doc("User", user_email)

    _log_coordinator_uplift_change(
        target_user=user_email,
        action="granted",
        before_profile=before_profile,
        after_profile=doc.role_profile_name,
    )

    return _serialize_governance_state(doc, _("Coordinator uplift granted."))


@frappe.whitelist()
def revoke_coordinator_uplift(user_email):
    _require_coordinator_governance_access()

    doc = _get_user_doc_for_governance(user_email)
    before_profile = doc.role_profile_name or ""

    if _is_technician_profile(doc):
        return _serialize_governance_state(doc, _("Coordinator uplift already revoked."))

    if not _is_coordinator_uplifted_profile(doc):
        frappe.throw(
            _("Coordinator uplift can only be revoked from users in the Coordinator-Technician profile."),
            frappe.ValidationError,
        )

    doc.role_profile_name = TECHNICIAN_PROFILE
    doc.populate_role_profile_roles()
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    doc = frappe.get_doc("User", user_email)

    _log_coordinator_uplift_change(
        target_user=user_email,
        action="revoked",
        before_profile=before_profile,
        after_profile=doc.role_profile_name,
    )

    return _serialize_governance_state(doc, _("Coordinator uplift revoked."))

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


@frappe.whitelist()
def current_coordinator_uplift_card(limit=10):
    limit = cint(limit or 10)

    data = frappe.db.sql(
        """
        SELECT
            u.name,
            u.full_name,
            u.enabled,
            u.email,
            u.modified,
            u.role_profile_name
        FROM `tabUser` u
        WHERE u.role_profile_name = %(role_profile_name)s
          AND IFNULL(u.user_type, 'System User') = 'System User'
        ORDER BY u.enabled DESC, u.full_name ASC, u.name ASC
        LIMIT %(limit)s
        """,
        {
            "role_profile_name": COORDINATOR_TECHNICIAN_PROFILE,
            "limit": limit,
        },
        as_dict=True,
    )

    rows = []
    for row in data:
        rows.append(
            {
                "name": row["name"],
                "full_name": row.get("full_name") or row["name"],
                "email": row.get("email") or row["name"],
                "enabled": cint(row.get("enabled") or 0),
                "modified": row.get("modified"),
                "modified_pretty": pretty_date(row.get("modified")) if row.get("modified") else "",
                "role_profile_name": row.get("role_profile_name") or "",
                "route": f"/app/user/{row['name']}",
            }
        )

    return {
        "title": "Current Coordinator Uplift",
        "count": len(data),
        "rows": rows,
        "report_route": "/app/query-report/Current%20Coordinator%20Uplift",
    }
    
    