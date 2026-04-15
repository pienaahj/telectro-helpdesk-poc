import frappe
from frappe import _
from frappe.utils import cint, pretty_date


TECHNICIAN_PROFILE = "TELECTRO-POC Profile - Technician"
COORDINATOR_TECHNICIAN_PROFILE = "TELECTRO-POC Profile - Coordinator-Technician"

ALLOWED_GOVERNANCE_ROLES = {
    "System Manager",
    "TELECTRO-POC Role - Supervisor Governance",
}

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
    return _serialize_governance_state(doc, _("Coordinator uplift granted."))


@frappe.whitelist()
def revoke_coordinator_uplift(user_email):
    _require_coordinator_governance_access()

    doc = _get_user_doc_for_governance(user_email)

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
    
    