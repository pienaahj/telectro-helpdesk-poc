import frappe

from telephony.partner_identity import get_enabled_partner_names_for_user

PARTNER_ROLES = {
    "TELECTRO-POC Role - Partner",
    "TELECTRO-POC Role - Partner Creator",
}

CUSTOMER_PORTAL_ROLES = {
    "Customer",
}

INTERNAL_BYPASS_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
}

INTERNAL_PARTNER_REPORT_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Tech",
    "TELECTRO-POC Ops Role",
    "TELECTRO-POC Coordinator-Tech Role",
    "TELECTRO-POC Coordinator Role",
    "TELECTRO-POC Role - Tech",
    "TELECTRO-POC Role - PABX Tech",
    "TELECTRO-POC Role - Faults Tech",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
}


def _get_roles(user: str) -> set[str]:
    if not user:
        return set()
    return set(frappe.get_roles(user))


def _is_internal_bypass_user(user: str) -> bool:
    if not user:
        return False
    if user == "Administrator":
        return True
    roles = _get_roles(user)
    return bool(roles & INTERNAL_BYPASS_ROLES)


def _is_internal_partner_report_user(
    user: str,
) -> bool:
    if not user or user == "Guest":
        return False

    if user == "Administrator":
        return True

    roles = _get_roles(user)

    return bool(
        roles & INTERNAL_PARTNER_REPORT_ROLES
    )


def _is_partner_user(user: str) -> bool:
    if not user or user == "Guest":
        return False
    roles = _get_roles(user)
    return bool(roles & PARTNER_ROLES)


def get_partner_ticket_report_condition(
    user: str | None = None,
    side: str = "either",
) -> str:
    """
    Return the Partner tenant condition for Partner-facing HD Ticket reports.

    Explicit internal Telectro users retain the report's existing
    operational scope. Unrelated non-Partner users receive no rows.

    Partner Creator only:
        owner-only containment.

    Full Partner:
        request     -> matching Request Partner organisation;
        fulfilment -> matching Fulfilment Partner organisation;
        either      -> matching organisation on either legitimate Partner side.

    A Partner user with no enabled organisation memberships receives no rows.
    """
    user = user or frappe.session.user

    if side not in {
        "request",
        "fulfilment",
        "either",
    }:
        raise ValueError(
            f"Unsupported Partner report side: {side}"
        )

    if _is_internal_partner_report_user(user):
        return ""

    roles = _get_roles(user)

    if not roles & PARTNER_ROLES:
        return "1 = 0"

    partner_role = "TELECTRO-POC Role - Partner"
    creator_role = "TELECTRO-POC Role - Partner Creator"

    if creator_role in roles and partner_role not in roles:
        return (
            f"t.owner = {frappe.db.escape(user)}"
        )

    partner_names = get_enabled_partner_names_for_user(user)

    if not partner_names:
        return "1 = 0"

    escaped_partners = ", ".join(
        frappe.db.escape(partner_name)
        for partner_name in partner_names
    )

    request_condition = f"""(
        coalesce(t.custom_request_source, '') = 'Partner'
        and t.custom_request_partner in ({escaped_partners})
    )"""

    fulfilment_condition = f"""(
        coalesce(t.custom_fulfilment_party, '') = 'Partner'
        and t.custom_fulfilment_partner in ({escaped_partners})
    )"""

    if side == "request":
        return request_condition

    if side == "fulfilment":
        return fulfilment_condition

    return f"""(
        {request_condition}
        or {fulfilment_condition}
    )"""


def _is_customer_portal_user(user: str) -> bool:
    if not user or user == "Guest":
        return False
    roles = _get_roles(user)
    return bool(roles & CUSTOMER_PORTAL_ROLES)


def _get_contact_names_for_user(user: str) -> list[str]:
    if not user:
        return []

    direct_contacts = frappe.get_all(
        "Contact",
        filters={"email_id": user},
        pluck="name",
    )

    email_child_contacts = frappe.get_all(
        "Contact Email",
        filters={"email_id": user},
        pluck="parent",
    )

    return sorted(set(direct_contacts + email_child_contacts))


def get_customer_names_for_user(user: str | None = None) -> list[str]:
    """
    Return Customer / HD Customer names linked to the current Website User.

    Helpdesk Customer portal users resolve through:

        User email
        -> Contact
        -> Dynamic Link
        -> HD Customer

    We also accept Customer links to keep this helper tolerant if future data
    links Contacts to ERPNext Customer instead of HD Customer.
    """
    user = user or frappe.session.user

    contacts = _get_contact_names_for_user(user)
    if not contacts:
        return []

    links = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Contact",
            "parent": ["in", contacts],
            "link_doctype": ["in", ["HD Customer", "Customer"]],
        },
        fields=["link_name"],
    )

    return sorted({row.link_name for row in links if row.link_name})


def _customer_ticket_query_conditions(user: str) -> str:
    escaped_user = frappe.db.escape(user)
    customer_names = get_customer_names_for_user(user)

    # Safe fallback:
    # If the Customer user is not linked to a Customer organisation yet, they
    # should still see tickets they personally created / raised, but no broader
    # customer-level visibility is granted.
    personal_condition = f"""(
        `tabHD Ticket`.`owner` = {escaped_user}
        OR `tabHD Ticket`.`raised_by` = {escaped_user}
    )"""

    if not customer_names:
        return personal_condition

    escaped_customers = ", ".join(frappe.db.escape(name) for name in customer_names)

    return f"""(
        `tabHD Ticket`.`owner` = {escaped_user}
        OR `tabHD Ticket`.`raised_by` = {escaped_user}
        OR `tabHD Ticket`.`customer` IN ({escaped_customers})
    )"""


def hd_ticket_query_conditions(user: str | None = None) -> str:
    user = user or frappe.session.user

    if _is_internal_bypass_user(user):
        return ""

    if _is_partner_user(user):
        # Conservative v1 rule:
        # Partner users only see tickets they own through generic HD Ticket access.
        return f"`tabHD Ticket`.`owner` = {frappe.db.escape(user)}"

    if _is_customer_portal_user(user):
        # Customer users are contained by Customer organisation, not only by
        # individual ticket ownership. This allows multiple named Customer-side
        # users linked to the same Customer to see that Customer's tickets.
        return _customer_ticket_query_conditions(user)

    return ""
