"""Additional Telectro Communication read restrictions.

Deny unauthorised access to Communications linked to HD Tickets.

Returning None defers to native Frappe permissions.
This module never grants permission.
"""

import frappe

from helpdesk.utils import get_customer

from telephony.customer_communication_privacy import (
    classify_actor_roles,
)


def _get_ticket_hd_customer(ticket_name):
    """Read the saved Helpdesk Customer identity."""

    return frappe.db.get_value(
        "HD Ticket",
        ticket_name,
        "customer",
    )


def communication_has_permission(
    doc,
    ptype,
    user=None,
    debug=False,
):
    """Apply Communication audience restrictions.

    Frappe's native Communication permission handler remains
    responsible for checking permission on the referenced document.
    """

    if ptype not in {"read", "write", "delete"}:
        return None

    if doc.get("reference_doctype") != "HD Ticket":
        return None

    user = str(
        user or frappe.session.user or ""
    ).strip()

    if user == "Administrator":
        return None

    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user))

    linked_customers = []

    if "Customer" in roles:
        linked_customers = list(get_customer(user))

    actor_kind = classify_actor_roles(
        roles,
        linked_hd_customers=linked_customers,
    )

    # Ticket-linked Communications are mutable only through
    # native permissions for explicitly recognised internal staff.
    # Customer, Partner and unknown actors cannot write or delete,
    # even when native DocPerm grants owner-based deletion.
    if ptype in {"write", "delete"}:
        return None if actor_kind == "internal" else False

    if actor_kind == "internal":
        # Internal staff still require native ticket permission.
        return None

    if actor_kind != "customer":
        # Partner, ambiguous and unknown identities.
        return False

    if doc.get("custom_telectro_audience") != "Customer":
        return False

    ticket_name = str(
        doc.get("reference_name") or ""
    ).strip()

    if not ticket_name:
        return False

    ticket_customer = _get_ticket_hd_customer(
        ticket_name
    )

    if (
        not ticket_customer
        or len(linked_customers) != 1
        or linked_customers[0] != ticket_customer
    ):
        return False

    # The audience check passed.
    # Native Frappe must still authorise ticket access.
    return None

def communication_query_conditions(user=None):
    """Restrict generic listing of HD Ticket Communications.

    External actors must use authorised Helpdesk conversation
    endpoints rather than generic Communication list queries.

    Returning None leaves native Frappe conditions unchanged.
    """

    user = str(
        user or frappe.session.user or ""
    ).strip()

    if user == "Administrator":
        return None

    outside_ticket = (
        "COALESCE(`tabCommunication`.`reference_doctype`, '') "
        "!= 'HD Ticket'"
    )

    if not user or user == "Guest":
        return outside_ticket

    roles = set(frappe.get_roles(user))

    actor_kind = classify_actor_roles(
        roles,
        linked_hd_customers=(),
    )

    if actor_kind == "internal":
        return None

    return outside_ticket
