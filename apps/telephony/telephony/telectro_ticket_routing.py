import frappe


MAILBOX_TO_AREA = {
    "PABX": "PABX",
    "Routing": "Routing",
    "SIM": "SIM",
    "Fiber": "Fiber",
    "Faults": "Faults",
    # Helpdesk intentionally not mapped -> DEFAULT_AREA
}

AREA_TO_TEAM = {
    "Routing": "Routing",
    "PABX": "PABX",
}

DEFAULT_AREA = "Other"
DEFAULT_TEAM = "Helpdesk Team"


def _clean(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def seed_ticket_routing(doc, method=None) -> None:
    """
    Shared routing seeding for both intake paths.

    Current intended behavior preserved from the Server Script:
    - Email-created tickets: mailbox wins for service area, then area seeds team.
    - Manual-created tickets: preserve chosen area, default only if blank,
      and seed team only if empty.
    """
    email_acct = _clean(doc.get("email_account"))
    area = _clean(doc.get("custom_service_area"))
    team = _clean(doc.get("agent_group"))

    if email_acct:
        resolved_area = MAILBOX_TO_AREA.get(email_acct) or DEFAULT_AREA
        resolved_team = AREA_TO_TEAM.get(resolved_area) or DEFAULT_TEAM

        if area != resolved_area:
            doc.custom_service_area = resolved_area

        if team != resolved_team:
            doc.agent_group = resolved_team
        return

    # Manual path: preserve user's chosen area; only seed defaults if missing
    if not area:
        area = DEFAULT_AREA
        doc.custom_service_area = area

    if not team:
        resolved_team = AREA_TO_TEAM.get(area) or DEFAULT_TEAM
        doc.agent_group = resolved_team


def debug_ticket_routing(doc, title: str = "HD Ticket routing debug") -> None:
    """
    Optional helper for one-off debugging from bench / temporary hook use.
    Keep unused in normal flow.
    """
    msg = (
        "name=" + str(getattr(doc, "name", "")) +
        "\nemail_account=" + str(doc.get("email_account")) +
        "\ncustom_service_area=" + str(doc.get("custom_service_area")) +
        "\nagent_group=" + str(doc.get("agent_group")) +
        "\nraised_by=" + str(doc.get("raised_by")) +
        "\nsubject=" + str(doc.get("subject"))
    )
    frappe.log_error(message=msg, title=title)