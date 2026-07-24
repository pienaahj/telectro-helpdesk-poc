import frappe
from frappe import _


SUPERVISOR_ROLE = "TELECTRO-POC Role - Supervisor Governance"


def _require_access():
    user = frappe.session.user

    if user == "Administrator":
        return

    roles = set(frappe.get_roles(user) or [])

    if SUPERVISOR_ROLE not in roles:
        frappe.throw(
            _("You are not allowed to view coordinator uplift history."),
            frappe.PermissionError,
        )


def execute(filters=None):
    _require_access()

    columns = [
        {
            "label": "Time",
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 180,
        },
        {
            "label": "Target User",
            "fieldname": "reference_name",
            "fieldtype": "Link",
            "options": "User",
            "width": 220,
        },
        {
            "label": "Actor",
            "fieldname": "owner",
            "fieldtype": "Link",
            "options": "User",
            "width": 220,
        },
        {
            "label": "Details",
            "fieldname": "content",
            "fieldtype": "Data",
            "width": 1200,
        },
    ]

    data = frappe.get_all(
        "Comment",
        filters={
            "reference_doctype": "User",
            "comment_type": "Info",
        },
        or_filters=[
            [
                "Comment",
                "content",
                "like",
                "Coordinator uplift granted%",
            ],
            [
                "Comment",
                "content",
                "like",
                "Coordinator uplift revoked%",
            ],
        ],
        fields=[
            "creation",
            "owner",
            "reference_name",
            "content",
        ],
        order_by="creation desc",
    )

    return columns, data
