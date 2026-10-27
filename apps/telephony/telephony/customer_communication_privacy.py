"""Telectro Communication audience policy.

This module defines visibility decisions only. It does not grant
ticket permissions, modify Communications, or publish API responses.
"""

import frappe
from helpdesk.utils import get_customer
from contextlib import contextmanager
from contextvars import ContextVar
from telephony.telectro_ticket_edit_guard import (
    validate_ticket_edit_rights,
)

INTERNAL_ROLES = frozenset({
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Tech",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
})

PARTNER_ROLES = frozenset({
    "TELECTRO-POC Role - Partner",
    "TELECTRO-POC Role - Partner Creator",
})

_customer_outbound_intent = ContextVar(
    "telectro_customer_outbound_intent",
    default=None,
)

def classify_actor_roles(roles, *, linked_hd_customers=()):
    """Classify an actor without treating System User as internal."""

    assigned = set(roles or ())

    customers = {
        str(name).strip()
        for name in (linked_hd_customers or ())
        if str(name).strip()
    }

    internal = bool(assigned & INTERNAL_ROLES)
    partner = bool(assigned & PARTNER_ROLES)
    customer_role = "Customer" in assigned

    # Mixed audience roles are security-sensitive.
    if sum((internal, partner, customer_role)) != 1:
        return "unknown"

    if internal:
        return "internal"

    if partner:
        return "partner"

    if len(customers) == 1:
        return "customer"

    return "unknown"


def can_view_communication(
    *,
    ticket_read_allowed,
    actor_kind,
    audience,
    is_ticket_customer=False,
):
    """Apply audience containment after ticket authorisation."""

    if not ticket_read_allowed:
        return False

    if actor_kind == "internal":
        return True

    if actor_kind == "customer":
        return (
            bool(is_ticket_customer)
            and audience == "Customer"
        )

    # Partner Communication access belongs to a future,
    # separately authorised Partner workflow.
    return False

def get_current_actor_access(ticket_name):
    """Resolve Communication access from the authenticated session.

    Never accept an actor identity, ticket ownership decision,
    or permission result from a client request.
    """

    ticket_name = str(ticket_name or "").strip()

    user = frappe.session.user or "Guest"
    roles = set(frappe.get_roles(user))

    linked_hd_customers = []

    if "Customer" in roles:
        linked_hd_customers = list(get_customer(user))

    actor_kind = classify_actor_roles(
        roles,
        linked_hd_customers=linked_hd_customers,
    )

    ticket_read_allowed = bool(
        ticket_name
        and frappe.has_permission(
            "HD Ticket",
            "read",
            doc=ticket_name,
        )
    )

    is_ticket_customer = False

    if ticket_read_allowed and actor_kind == "customer":
        ticket_hd_customer = frappe.db.get_value(
            "HD Ticket",
            ticket_name,
            "customer",
        )

        is_ticket_customer = bool(
            ticket_hd_customer
            and len(linked_hd_customers) == 1
            and linked_hd_customers[0] == ticket_hd_customer
        )

    return {
        "actor_kind": actor_kind,
        "ticket_read_allowed": ticket_read_allowed,
        "is_ticket_customer": is_ticket_customer,
    }

def classify_new_customer_communication(doc, method=None):
    """Classify a new, authenticated Customer-originated message.

    This function is intended for the Communication before_insert
    lifecycle hook.

    A caller cannot request an audience classification through
    a Communication field. Classification is derived exclusively
    from the authenticated session and saved ticket identity.
    """

    supplied_audience = str(
        doc.get("custom_telectro_audience") or ""
    ).strip()

    if supplied_audience:
        frappe.throw(
            "Communication audience cannot be supplied directly.",
            frappe.PermissionError,
        )

    # Explicit Customer-directed outbound operations are authorised
    # by a temporary server-side scope, never by client fields.
    outbound_intent = _customer_outbound_intent.get()

    if outbound_intent is not None:
        expected_ticket, expected_recipient, expected_actor = (
            outbound_intent
        )

        current_actor = str(
            getattr(frappe.session, "user", "") or ""
        ).strip()

        valid_outbound = all((
            doc.get("reference_doctype") == "HD Ticket",
            str(doc.get("reference_name") or "") == expected_ticket,
            doc.get("sent_or_received") == "Sent",
            doc.get("communication_type") == "Communication",
            doc.get("communication_medium") == "Email",
            str(doc.get("sender") or "").strip() == expected_actor,
            str(doc.get("recipients") or "").strip()
                == expected_recipient,
            current_actor == expected_actor,
            not doc.get("cc"),
            not doc.get("bcc"),
        ))

        if not valid_outbound:
            frappe.throw(
                "Customer-directed Communication does not match "
                "the authorised outbound operation.",
                frappe.PermissionError,
            )

        doc.custom_telectro_audience = "Customer"
        return

    if doc.get("reference_doctype") != "HD Ticket":
        return

    if doc.get("sent_or_received") != "Received":
        return

    ticket_name = str(
        doc.get("reference_name") or ""
    ).strip()

    user = str(
        getattr(frappe.session, "user", "") or ""
    ).strip()

    sender = str(
        doc.get("sender") or ""
    ).strip()

    if not ticket_name or not user or user == "Guest":
        return

    if sender != user:
        return

    context = get_current_actor_access(ticket_name)

    if (
        context["actor_kind"] == "customer"
        and context["ticket_read_allowed"]
        and context["is_ticket_customer"]
    ):
        doc.custom_telectro_audience = "Customer"

def validate_communication_audience_integrity(doc, method=None):
    """Protect the audience and provenance of saved ticket messages.

    This validation is for the normal Document save lifecycle.
    Controlled historical classification requires a separate,
    explicitly authorised workflow.
    """

    previous = doc.get_doc_before_save()

    if previous is None:
        return

    if (
        previous.get("reference_doctype") != "HD Ticket"
        and doc.get("reference_doctype") != "HD Ticket"
    ):
        return

    old_audience = previous.get("custom_telectro_audience") or ""
    new_audience = doc.get("custom_telectro_audience") or ""

    if old_audience != new_audience:
        frappe.throw(
            "Communication audience cannot be changed after creation.",
            frappe.PermissionError,
        )

    if not old_audience:
        return

    protected_fields = (
        "reference_doctype",
        "reference_name",
        "sender",
        "sent_or_received",
        "recipients",
        "cc",
        "bcc",
    )

    changed = [
        field
        for field in protected_fields
        if (previous.get(field) or "") != (doc.get(field) or "")
    ]

    if changed:
        frappe.throw(
            "Classified Communication provenance cannot be changed.",
            frappe.PermissionError,
        )

def require_customer_update_authority(ticket_name, recipient):
    """Verify an internal actor may send to this ticket's Customer.

    Both actor authority and recipient identity are resolved on
    the server. This function does not modify any document.
    """

    ticket_name = str(ticket_name or "").strip()
    recipient = str(recipient or "").strip()

    if not ticket_name or not recipient:
        raise frappe.PermissionError(
            "Customer ticket and recipient are required."
        )

    actor = get_current_actor_access(ticket_name)

    if not (
        actor["actor_kind"] == "internal"
        and actor["ticket_read_allowed"]
    ):
        raise frappe.PermissionError(
            "Internal ticket access is required."
        )

    if not frappe.has_permission(
        "HD Ticket",
        "write",
        doc=ticket_name,
    ):
        raise frappe.PermissionError(
            "Ticket write permission is required."
        )

    ticket = frappe.db.get_value(
        "HD Ticket",
        ticket_name,
        ["customer", "raised_by"],
        as_dict=True,
    )

    if not ticket or not ticket.get("customer"):
        raise frappe.PermissionError(
            "Ticket Customer identity is required."
        )

    if recipient != str(ticket.get("raised_by") or "").strip():
        raise frappe.PermissionError(
            "Recipient must match the ticket raiser."
        )

    if not frappe.db.get_value("User", recipient, "enabled"):
        raise frappe.PermissionError(
            "Customer recipient account must be enabled."
        )

    linked_customers = list(get_customer(recipient))

    recipient_kind = classify_actor_roles(
        frappe.get_roles(recipient),
        linked_hd_customers=linked_customers,
    )

    if not (
        recipient_kind == "customer"
        and len(linked_customers) == 1
        and linked_customers[0] == ticket["customer"]
    ):
        raise frappe.PermissionError(
            "Recipient does not belong to the ticket Customer."
        )

    # Reuse the existing Telectro assignment/pool edit policy.
    # This checks the authenticated user and persisted assignment,
    # before any Customer Communication insertion begins.
    ticket_doc = frappe.get_doc("HD Ticket", ticket_name)
    validate_ticket_edit_rights(ticket_doc)

    return recipient

@contextmanager
def customer_outbound_communication_scope(ticket_name, recipient):
    """Allow one trusted Customer-directed Communication operation.

    The scope is server-side, request-local and cannot be supplied
    through a Communication field or HTTP request parameter.
    """

    ticket_name = str(ticket_name or "").strip()

    verified_recipient = require_customer_update_authority(
        ticket_name,
        recipient,
    )

    actor = str(
        getattr(frappe.session, "user", "") or ""
    ).strip()

    intent = (
        ticket_name,
        verified_recipient,
        actor,
    )

    token = _customer_outbound_intent.set(intent)

    try:
        yield
    finally:
        _customer_outbound_intent.reset(token)
