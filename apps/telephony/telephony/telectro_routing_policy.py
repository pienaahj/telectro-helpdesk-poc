import frappe


# Pilot-only hardcoded policy.
# Keep isolated so it can later become a DocType-backed routing policy.
#
# Primary routing anchor is Campus / custom_site_group.
# telectro_site_guard.py already applies Customer.custom_default_campus
# before after_insert assignment runs.
#
# Current pilot proof:
# - Customer B.custom_default_campus = Boschendal
# - Boschendal is the exact Location / custom_site_group value.
#
# Replace this user when Telectro confirms the real Boschendal technician.
CAMPUS_DEDICATED_USERS = {
    "boschendal": "hendrik@local.test",
}


def _clean(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _norm_key(val) -> str:
    return _clean(val).casefold()


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
    - campus/service-area/RR/pool routing remains intact

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
    Resolve pilot-specific ownership routing for an HD Ticket.

    Read-only decision function:
    - does not mutate the ticket
    - does not create ToDos
    - does not write _assign

    Priority context:
    - Partner fulfilment override is handled before this function.
    - Partner-originated tickets are excluded for now to preserve the
      Partner -> Telectro workflow semantics.
    - Explicit creator take-ownership applies only when selected.
    - Campus policy applies before Service Area RR/fallback.
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

    campus = _clean(doc.get("custom_site_group"))
    campus_key = _norm_key(campus)

    if not campus_key:
        return None

    target_user = _clean(CAMPUS_DEDICATED_USERS.get(campus_key))
    if not target_user:
        return None

    if not _user_exists(target_user):
        frappe.log_error(
            message=(
                f"Campus routing policy matched campus={campus!r}, "
                f"but user {target_user!r} does not exist."
            ),
            title="TELECTRO routing policy user missing",
        )
        return None

    return {
        "target_user": target_user,
        "reason": f"Campus routing policy matched Campus '{campus}'",
        "policy_key": f"campus:{campus_key}",
    }