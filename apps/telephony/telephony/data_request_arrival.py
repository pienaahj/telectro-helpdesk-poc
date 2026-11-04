"""Pure planning contract for Data Request arrival notifications."""

from hashlib import sha256


SERVICE_AREA = "Data Request"
EVENT = "arrival"


def intent_name(ticket_name, recipient):
    ticket = str(ticket_name or "").strip()
    user = str(recipient or "").strip()

    if not ticket or not user:
        raise ValueError("Ticket and recipient are required")

    # Length prefixes avoid ambiguous concatenation.
    identity = (
        f"{EVENT}:{len(ticket)}:{ticket}:"
        f"{len(user)}:{user}"
    )

    digest = sha256(identity.encode("utf-8")).hexdigest()

    return "TDRN-" + digest[:40]


def plan_arrival_intents(
    *,
    ticket_name,
    service_area,
    members,
    eligible_user,
):
    """Build unique intents without persistence or delivery.

    eligible_user(user) is supplied by the integration layer.
    It must verify the intended recipient's current eligibility.
    """
    if str(service_area or "").strip() != SERVICE_AREA:
        return []

    ticket = str(ticket_name or "").strip()

    if not ticket:
        return []

    candidates = set()

    for member in members or []:
        user = str(member or "").strip()

        if user and user not in {"Administrator", "Guest"}:
            candidates.add(user)

    intents = []

    for user in sorted(candidates):
        if not eligible_user(user):
            continue

        intents.append({
            "name": intent_name(ticket, user),
            "ticket": ticket,
            "recipient": user,
            "event": EVENT,
        })

    return intents
