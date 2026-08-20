import frappe
from frappe.utils import cint


PARTNER_ROLES = {
    "TELECTRO-POC Role - Partner",
    "TELECTRO-POC Role - Partner Creator",
}


def _clean(value) -> str:
    return str(value or "").strip()


def get_enabled_partner_names_for_user(user: str) -> list[str]:
    """
    Return enabled TELECTRO Partner organisations for which the User has an
    enabled membership.

    Membership determines organisation / tenant identity. Roles are checked
    separately when evaluating capability.
    """
    user = _clean(user)

    if not user or user == "Guest":
        return []

    partner_names = frappe.get_all(
        "TELECTRO Partner Member",
        filters={
            "user": user,
            "enabled": 1,
            "parenttype": "TELECTRO Partner",
            "parentfield": "members",
        },
        pluck="parent",
    )

    partner_names = sorted(
        {
            _clean(partner_name)
            for partner_name in partner_names
            if _clean(partner_name)
        }
    )

    if not partner_names:
        return []

    return frappe.get_all(
        "TELECTRO Partner",
        filters={
            "name": ["in", partner_names],
            "enabled": 1,
        },
        pluck="name",
        order_by="name asc",
    )


def is_enabled_partner_member(
    user: str,
    partner_name: str,
) -> bool:
    user = _clean(user)
    partner_name = _clean(partner_name)

    if not user or not partner_name:
        return False

    return partner_name in set(
        get_enabled_partner_names_for_user(user)
    )


def resolve_partner_dispatch_user(partner_name: str) -> str:
    """
    Resolve the deterministic dispatch User for an enabled Partner.

    The dispatch User must:
      - be configured as Default Dispatch User;
      - be an enabled member of this Partner;
      - be an enabled Frappe User;
      - have at least one Partner capability role.
    """
    partner_name = _clean(partner_name)

    if not partner_name:
        frappe.throw(
            "Partner organisation is required for Partner dispatch.",
            frappe.ValidationError,
        )

    partner = frappe.db.get_value(
        "TELECTRO Partner",
        partner_name,
        [
            "name",
            "enabled",
            "default_dispatch_user",
        ],
        as_dict=True,
    )

    if not partner:
        frappe.throw(
            f"Partner organisation {frappe.bold(partner_name)} does not exist.",
            frappe.ValidationError,
        )

    if not cint(partner.enabled):
        frappe.throw(
            f"Partner organisation {frappe.bold(partner_name)} is disabled.",
            frappe.ValidationError,
        )

    dispatch_user = _clean(partner.default_dispatch_user)

    if not dispatch_user:
        frappe.throw(
            f"Partner organisation {frappe.bold(partner_name)} "
            "has no Default Dispatch User.",
            frappe.ValidationError,
        )

    membership_exists = frappe.db.exists(
        "TELECTRO Partner Member",
        {
            "parent": partner_name,
            "parenttype": "TELECTRO Partner",
            "parentfield": "members",
            "user": dispatch_user,
            "enabled": 1,
        },
    )

    if not membership_exists:
        frappe.throw(
            f"Default Dispatch User {frappe.bold(dispatch_user)} "
            f"is not an enabled member of {frappe.bold(partner_name)}.",
            frappe.ValidationError,
        )

    user = frappe.db.get_value(
        "User",
        dispatch_user,
        [
            "name",
            "enabled",
        ],
        as_dict=True,
    )

    if not user or not cint(user.enabled):
        frappe.throw(
            f"Default Dispatch User {frappe.bold(dispatch_user)} "
            "is not an enabled User.",
            frappe.ValidationError,
        )

    roles = set(frappe.get_roles(dispatch_user))

    if not roles & PARTNER_ROLES:
        frappe.throw(
            f"Default Dispatch User {frappe.bold(dispatch_user)} "
            "does not have a Partner capability role.",
            frappe.ValidationError,
        )

    return dispatch_user


def resolve_partner_name_for_user(
    user: str,
    requested_partner: str | None = None,
) -> str:
    """
    Resolve the Partner organisation represented by an authenticated user.

    Rules:
      - no enabled memberships: reject;
      - one enabled membership: auto-resolve when no Partner was supplied;
      - multiple enabled memberships: require explicit selection;
      - an explicit Partner must be one of the user's enabled memberships.

    This resolves tenant identity only. Partner roles remain the separate
    capability gate enforced by the calling workflow.
    """
    user = _clean(user)
    requested_partner = _clean(requested_partner)

    if not user or user == "Guest":
        frappe.throw(
            "Partner organisation could not be resolved.",
            frappe.PermissionError,
        )

    partner_names = get_enabled_partner_names_for_user(user)
    allowed_partners = set(partner_names)

    if not partner_names:
        frappe.throw(
            "Your user is not an enabled member of a Partner organisation.",
            frappe.PermissionError,
        )

    if requested_partner:
        if requested_partner not in allowed_partners:
            frappe.throw(
                "You are not an enabled member of the selected Partner organisation.",
                frappe.PermissionError,
            )

        return requested_partner

    if len(partner_names) == 1:
        return partner_names[0]

    frappe.throw(
        "Partner organisation must be selected because your user belongs "
        "to more than one enabled Partner organisation.",
        frappe.ValidationError,
    )


def get_partner_names_for_ticket(
    ticket_name: str,
) -> list[str]:
    """
    Return the Partner organisations that are legitimate parties to a ticket.

    Organisation fields count only when their corresponding party dimension
    is actually Partner:

      Request Source = Partner
          -> custom_request_partner

      Fulfilment Party = Partner
          -> custom_fulfilment_partner

    Missing Partner identity fails closed by producing no organisation for
    that side.
    """
    ticket_name = _clean(ticket_name)

    if not ticket_name:
        return []

    row = frappe.db.get_value(
        "HD Ticket",
        ticket_name,
        [
            "custom_request_source",
            "custom_request_partner",
            "custom_fulfilment_party",
            "custom_fulfilment_partner",
        ],
        as_dict=True,
    )

    if not row:
        return []

    partner_names = set()

    if _clean(row.custom_request_source) == "Partner":
        request_partner = _clean(
            row.custom_request_partner
        )
        if request_partner:
            partner_names.add(request_partner)

    if _clean(row.custom_fulfilment_party) == "Partner":
        fulfilment_partner = _clean(
            row.custom_fulfilment_partner
        )
        if fulfilment_partner:
            partner_names.add(fulfilment_partner)

    return sorted(partner_names)


def user_has_partner_ticket_membership(
    user: str,
    ticket_name: str,
) -> bool:
    """
    Return True only when the User is an enabled member of at least one
    enabled Partner organisation that is legitimately party to the ticket.
    """
    user = _clean(user)
    ticket_name = _clean(ticket_name)

    if not user or user == "Guest" or not ticket_name:
        return False

    ticket_partners = set(
        get_partner_names_for_ticket(
            ticket_name
        )
    )

    if not ticket_partners:
        return False

    user_partners = set(
        get_enabled_partner_names_for_user(
            user
        )
    )

    return bool(
        ticket_partners & user_partners
    )
