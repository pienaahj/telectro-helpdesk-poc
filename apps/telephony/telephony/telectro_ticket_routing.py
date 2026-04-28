import frappe


MAILBOX_TO_AREA = {
    "PABX": "PABX",
    "Routing": "Routing",
    "SIM": "SIM",
    "Fiber": "Internet Connection",  # legacy mailbox name / old service area
    "Fibre": "Internet Connection",  # spelling compatibility
    "Internet Connection": "Internet Connection",
    "Faults": "Faults",
    # Helpdesk intentionally not mapped -> DEFAULT_AREA
}

AREA_TO_TEAM = {
    "Routing": "Routing",
    "PABX": "PABX",
    "SIM": "SIM",

    # Current pilot behaviour:
    # These are valid Service Areas, but they do not yet have dedicated RR teams.
    # They fall back to Helpdesk Team unless/until explicit teams/pools are created.
    #
    # "Internet Connection": "Internet Connection",
    # "Faults": "Faults",
    # "Quotes & Site Surveys": "Quotes & Site Surveys",
    # "CCTV": "CCTV",
}

DEFAULT_AREA = "Other"
DEFAULT_TEAM = "Helpdesk Team"


def _clean(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _get_old_doc(doc):
    """
    During a real save lifecycle, get_doc_before_save() provides previous values.
    Outside that lifecycle (e.g. plain bench console fetch), it may be None.
    """
    try:
        old_doc = doc.get_doc_before_save()
        if old_doc:
            return old_doc
    except Exception:
        pass
    return None


def seed_ticket_routing(doc, method=None) -> None:
    """
    Shared routing seeding for both intake paths.

    Intended behavior:
    - Email-created/updated tickets: mailbox wins for service area, then area seeds team.
    - Manual-created tickets: preserve chosen area, default only if blank,
      and seed team if empty.
    - Manual-updated tickets: if service area changes, refresh agent_group from area
      so final routing state does not remain stale.
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

    resolved_team = AREA_TO_TEAM.get(area) or DEFAULT_TEAM

    # New doc: seed team only if empty
    if doc.is_new():
        if not team:
            doc.agent_group = resolved_team
        return

    # Existing manual doc:
    # if service area changed during this save, refresh team from current area
    old_doc = _get_old_doc(doc)
    if old_doc:
        old_area = _clean(old_doc.get("custom_service_area"))
        if old_area != area:
            if team != resolved_team:
                doc.agent_group = resolved_team
            return

    # Fallback: if team is blank on an existing manual doc, seed it
    if not team:
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