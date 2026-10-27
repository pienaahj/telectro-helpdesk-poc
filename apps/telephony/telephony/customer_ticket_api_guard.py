"""
Telectro Helpdesk ticket API read-containment guards.

Protect ticket-related Helpdesk endpoints that do not enforce
ticket-level read permissions before returning information.

Preserve upstream response formats for authorised users.
"""

import frappe
from frappe import _

from helpdesk.helpdesk.doctype.hd_ticket import api as helpdesk_api


def _require_ticket_read(ticket):
    """Reject access unless the current user can read the ticket."""

    if not ticket or not frappe.has_permission(
        "HD Ticket",
        "read",
        doc=str(ticket),
    ):
        frappe.throw(
            _("Insufficient permission to read this ticket"),
            frappe.PermissionError,
        )


def _filter_readable_tickets(rows):
    """Retain only related tickets readable by the current user."""

    return [
        row
        for row in (rows or [])
        if row.get("name")
        and frappe.has_permission(
            "HD Ticket",
            "read",
            doc=str(row["name"]),
        )
    ]


@frappe.whitelist()
def get_ticket_activities(ticket: str):
    from telephony.customer_communication_privacy import (
        get_current_actor_access,
    )
    from telephony.customer_communication_projection import (
        project_customer_activities,
    )

    _require_ticket_read(ticket)

    access = get_current_actor_access(ticket)

    if (
        access["actor_kind"] == "internal"
        and access["ticket_read_allowed"]
    ):
        return helpdesk_api.get_ticket_activities(ticket)

    if not (
        access["actor_kind"] == "customer"
        and access["ticket_read_allowed"]
        and access["is_ticket_customer"]
    ):
        frappe.throw(
            "Not permitted to view ticket activities.",
            frappe.PermissionError,
        )

    candidates = frappe.get_all(
        "Communication",
        filters={
            "reference_doctype": "HD Ticket",
            "reference_name": str(ticket),
            "custom_telectro_audience": "Customer",
        },
        pluck="name",
        limit_page_length=0,
    )

    visible_names = []

    for name in candidates:
        if frappe.has_permission(
            "Communication",
            "read",
            doc=name,
        ):
            visible_names.append(name)

    activities = helpdesk_api.get_ticket_activities(ticket)

    return project_customer_activities(
        activities,
        visible_names,
    )


@frappe.whitelist()
def get_one(name: str, is_customer_portal=False):
    """Return ticket details according to the authenticated actor.

    The client-supplied is_customer_portal value is never used
    to determine access or response visibility.
    """
    from telephony.customer_communication_privacy import (
        get_current_actor_access,
    )
    from telephony.customer_communication_projection import (
        project_customer_ticket_detail,
    )

    _require_ticket_read(name)

    access = get_current_actor_access(name)

    if (
        access["actor_kind"] == "internal"
        and access["ticket_read_allowed"]
    ):
        return helpdesk_api.get_one(
            name,
            is_customer_portal=False,
        )

    if not (
        access["actor_kind"] == "customer"
        and access["ticket_read_allowed"]
        and access["is_ticket_customer"]
    ):
        frappe.throw(
            "Not permitted to view ticket details.",
            frappe.PermissionError,
        )

    detail = helpdesk_api.get_one(
        name,
        is_customer_portal=True,
    )

    result = project_customer_ticket_detail(
        detail,
        visible_communication_names=(),
        viewer_email=frappe.session.user,
    )

    result.update(get_ticket_activities(name))

    return result


@frappe.whitelist()
def get_ticket_assignees(ticket: str):
    from telephony.customer_communication_privacy import (
        get_current_actor_access,
    )

    _require_ticket_read(ticket)

    access = get_current_actor_access(ticket)

    if (
        access["actor_kind"] == "internal"
        and access["ticket_read_allowed"]
    ):
        return helpdesk_api.get_ticket_assignees(ticket)

    if (
        access["actor_kind"] == "customer"
        and access["ticket_read_allowed"]
        and access["is_ticket_customer"]
    ):
        return "[]"

    frappe.throw(
        "Not permitted to view ticket assignees.",
        frappe.PermissionError,
    )


@frappe.whitelist()
def get_ticket_contact(ticket: str):
    from telephony.customer_communication_privacy import (
        get_current_actor_access,
    )

    _require_ticket_read(ticket)

    access = get_current_actor_access(ticket)

    if (
        access["actor_kind"] == "internal"
        and access["ticket_read_allowed"]
    ):
        return helpdesk_api.get_ticket_contact(ticket)

    if (
        access["actor_kind"] == "customer"
        and access["ticket_read_allowed"]
        and access["is_ticket_customer"]
    ):
        viewer = frappe.session.user

        return {
            "name": viewer,
            "email_id": viewer,
            "image": None,
        }

    frappe.throw(
        "Not permitted to view ticket contact.",
        frappe.PermissionError,
    )


@frappe.whitelist()
def get_recent_similar_tickets(ticket: str):
    _require_ticket_read(ticket)

    result = helpdesk_api.get_recent_similar_tickets(ticket)

    return {
        **result,
        "recent_tickets": _filter_readable_tickets(
            result.get("recent_tickets")
        ),
        "similar_tickets": _filter_readable_tickets(
            result.get("similar_tickets")
        ),
    }
