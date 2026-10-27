"""Server-side authorisation for HD Ticket realtime rooms.

Native Frappe document rooms can carry complete Communication
documents. Helpdesk ticket-viewing rooms carry ticket notifications.

These two channels therefore require different access policies.
"""

import frappe

from telephony.customer_communication_privacy import (
    get_current_actor_access,
)


NATIVE_DOCUMENT_CHANNEL = "native_doc"
HELPDESK_TICKET_CHANNEL = "helpdesk_ticket"

HELPDESK_ALLOWED_ACTORS = frozenset(
    {"internal", "customer", "partner"}
)


# A DocType-wide HD Ticket room includes tickets from every customer.
# Only explicitly designated Telectro operational personnel may use it.
INTERNAL_HD_TICKET_DOCTYPE_ROLES = frozenset({
    "TELECTRO-POC Role - Tech",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
})
PARTNER_HD_TICKET_ROLES = frozenset({
    "TELECTRO-POC Role - Partner",
    "TELECTRO-POC Role - Partner Creator",
})


@frappe.whitelist()
def require_internal_hd_ticket_doctype_realtime_access() -> bool:
    """Authorise unscoped `doctype:HD Ticket` realtime events.

    Reevaluate the authenticated principal, enabled status, current role
    membership and current DocType read permission on every request.
    Partner identity is a veto even if operational roles overlap.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        raise frappe.PermissionError("Authenticated internal access is required.")

    account = frappe.db.get_value(
        "User", user, ["enabled", "user_type"], as_dict=True
    )
    if not account or not account.enabled or account.user_type != "System User":
        raise frappe.PermissionError("Enabled internal System User required.")

    roles = set(frappe.get_roles(user) or ())
    if roles.intersection(PARTNER_HD_TICKET_ROLES):
        raise frappe.PermissionError("Partner roles cannot receive all tickets.")
    if not roles.intersection(INTERNAL_HD_TICKET_DOCTYPE_ROLES):
        raise frappe.PermissionError("Telectro operational role required.")

    if not frappe.has_permission("HD Ticket", ptype="read"):
        raise frappe.PermissionError("HD Ticket read permission required.")

    return True


@frappe.whitelist()
def require_ticket_realtime_access(
    ticket_name: str,
    channel: str,
) -> bool:
    """Authorise one HD Ticket realtime channel.

    Denials raise PermissionError so socket handlers receive
    an HTTP permission failure rather than a successful response
    containing False.

    This function does not create room memberships or modify data.
    """

    ticket_name = str(ticket_name or "").strip()
    channel = str(channel or "").strip()

    if not ticket_name:
        raise frappe.PermissionError(
            "HD Ticket identity is required."
        )

    if channel not in {
        NATIVE_DOCUMENT_CHANNEL,
        HELPDESK_TICKET_CHANNEL,
    }:
        raise frappe.PermissionError(
            "Unsupported ticket realtime channel."
        )

    if frappe.session.user in (None, "", "Guest"):
        raise frappe.PermissionError(
            "Authenticated ticket access is required."
        )

    actor = get_current_actor_access(ticket_name) or {}

    if not actor.get("ticket_read_allowed"):
        raise frappe.PermissionError(
            "Ticket read permission is required."
        )

    actor_kind = actor.get("actor_kind")

    if channel == NATIVE_DOCUMENT_CHANNEL:
        if actor_kind != "internal":
            raise frappe.PermissionError(
                "Native ticket realtime access is internal only."
            )

    elif actor_kind == "customer":
        if not actor.get("is_ticket_customer"):
            raise frappe.PermissionError(
                "Ticket Customer ownership is required."
            )

    elif actor_kind not in HELPDESK_ALLOWED_ACTORS:
        raise frappe.PermissionError(
            "Ticket realtime access is not authorised."
        )

    return True
