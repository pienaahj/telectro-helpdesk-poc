import frappe


# Pilot-specific direct-owner routing policy.
#
# Keep exceptional ownership decisions isolated from normal team routing.
#
# Normal internal routing remains:
#
#     Service Area
#         -> agent_group / HD Team
#         -> native HD Team Assignment Rule
#         -> one accountable team member
#
# Current direct-owner exception:
# - an internal technician may explicitly choose Take Ownership on creation
#
# Boschendal is not a direct-owner exception. Boschendal tickets must continue
# through their Service Area / HD Team assignment path.


def _clean(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _as_bool(val) -> bool:
    return str(val or "").strip().lower() in {"1", "true", "yes", "on"}


def _user_exists(user: str) -> bool:
    user = _clean(user)
    if not user:
        return False

    return bool(frappe.db.exists("User", user))


def _roles_for(user: str) -> set[str]:
    user = _clean(user)
    if not user:
        return set()

    try:
        return set(frappe.get_roles(user))
    except Exception:
        return set()


def _is_partner_user(user: str) -> bool:
    roles = _roles_for(user)

    return bool(
        roles
        & {
            "TELECTRO-POC Role - Partner",
            "TELECTRO-POC Role - Partner Creator",
        }
    )


def _is_internal_technician_user(user: str) -> bool:
    roles = _roles_for(user)

    if _is_partner_user(user):
        return False

    return bool(
        roles
        & {
            "TELECTRO-POC Role - Tech",
            "Agent",
            "Support Team",
        }
    )


def _resolve_creator_take_ownership_policy(doc) -> dict | None:
    """
    Route a new internal manual ticket to its creator only when the creator
    explicitly chose to take ownership.

    This is intentionally not automatic.

    Normal behaviour:
    - email-created tickets route as normal
    - manual internal tickets route as normal
    - service-area / HD Team routing remains intact

    Opt-in behaviour:
    - if custom_take_ownership_on_create is checked
    - and the creator is an internal technician-like user
    - and this is not Partner-originated / Partner-fulfilled
    - then assign to the creator
    """
    if not _as_bool(doc.get("custom_take_ownership_on_create")):
        return None

    owner = _clean(getattr(doc, "owner", "") or doc.get("owner"))
    if not owner or owner in {"Administrator", "Guest"}:
        return None

    if not _user_exists(owner):
        return None

    fulfilment_party = _clean(doc.get("custom_fulfilment_party"))
    if fulfilment_party == "Partner":
        return None

    request_source = _clean(doc.get("custom_request_source"))
    if request_source == "Partner":
        return None

    if not _is_internal_technician_user(owner):
        return None

    return {
        "target_user": owner,
        "reason": f"Ticket creator chose to take ownership: {owner}",
        "policy_key": "creator_take_ownership",
    }


def resolve_ticket_routing_policy(doc) -> dict | None:
    """
    Resolve pilot-specific exceptional direct-owner routing for an HD Ticket.

    Read-only decision function:
    - does not mutate the ticket
    - does not create ToDos
    - does not write _assign

    Priority context:
    - Partner fulfilment override is handled before this function.
    - Partner-originated tickets are excluded to preserve Partner workflow.
    - Explicit creator take-ownership applies only when selected.
    - All other internal tickets return None so normal Service Area -> HD Team
      -> native Assignment Rule routing can proceed.
    """
    fulfilment_party = _clean(doc.get("custom_fulfilment_party"))
    if fulfilment_party == "Partner":
        return None

    request_source = _clean(doc.get("custom_request_source"))
    if request_source == "Partner":
        return None

    creator_policy = _resolve_creator_take_ownership_policy(doc)
    if creator_policy:
        return creator_policy

    return None
