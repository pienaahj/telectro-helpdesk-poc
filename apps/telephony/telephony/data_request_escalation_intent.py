"""Pure planning for Data Request Coordinator escalation intents.

No Frappe dependencies, database writes or notification delivery.
"""

from hashlib import sha256

EVENT = "escalation"


def escalation_intent_name(ticket_name, recipient):
    ticket = str(ticket_name or "").strip()
    user = str(recipient or "").strip()

    if not ticket or not user:
        raise ValueError("Ticket and recipient are required")

    identity = (
        f"{EVENT}:{len(ticket)}:{ticket}:"
        f"{len(user)}:{user}"
    )

    return "TDRN-" + sha256(
        identity.encode("utf-8")
    ).hexdigest()[:40]


def plan_escalation_intents(
    *,
    ticket_name,
    recipients,
    eligible_user,
):
    ticket = str(ticket_name or "").strip()

    if not ticket:
        raise ValueError("Ticket is required")

    if not callable(eligible_user):
        raise TypeError("Recipient eligibility callback required")

    users = set()

    for recipient in recipients or []:
        user = str(recipient or "").strip()
        if user and user not in {"Administrator", "Guest"}:
            users.add(user)

    result = []

    for user in sorted(users):
        if not eligible_user(user):
            continue

        result.append({
            "name": escalation_intent_name(ticket, user),
            "ticket": ticket,
            "recipient": user,
            "event": EVENT,
        })

    return result
