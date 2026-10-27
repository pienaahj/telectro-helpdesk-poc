"""Customer-safe projection of Helpdesk ticket activities.

This module does not determine which Communications are authorised.
The permitted Communication names must come from a trusted
server-side lookup, never from request parameters.
"""

PUBLIC_COMMUNICATION_FIELDS = (
    "name",
    "content",
    "creation",
    "communication_date",
    "sender",
    "subject",
)


def project_customer_activities(
    activities,
    visible_communication_names,
):
    """Return only approved Customer conversation information."""

    activities = activities or {}
    allowed = set(visible_communication_names or ())

    communications = []

    for original in activities.get("communications") or []:
        name = original.get("name")

        if not name or name not in allowed:
            continue

        public = {
            field: original[field]
            for field in PUBLIC_COMMUNICATION_FIELDS
            if field in original
        }

        # The Customer UI uses user.name for display.
        # Do not forward the complete user profile.
        user = original.get("user")

        if isinstance(user, dict) and user.get("name"):
            public["user"] = {
                "name": user["name"],
            }

        # Attachment access must be verified separately.
        # Do not expose unverified file URLs at this stage.
        public["attachments"] = []

        communications.append(public)

    return {
        "communications": communications,
        "comments": [],
        "history": [],
        "views": [],
        "calls": [],
    }

CUSTOMER_TICKET_FIELDS = frozenset({
    "name",
    "subject",
    "description",
    "status",
    "priority",
    "customer",
    "ticket_type",
    "raised_by",
    "creation",
    "response_by",
    "resolution_by",
    "first_responded_on",
    "resolution_date",
})

CUSTOMER_DYNAMIC_FIELD_TYPES = frozenset({
    "Data",
    "Select",
    "Link",
    "Small Text",
    "Text",
    "Long Text",
    "Text Editor",
    "Check",
    "Date",
    "Datetime",
    "Time",
    "Int",
    "Float",
    "Currency",
    "Duration",
    "Read Only",
})

PROTECTED_DYNAMIC_FIELD_NAMES = frozenset({
    "owner",
    "modified_by",
    "modified",
    "agent_group",
    "team",
    "assigned_to",
    "custom_customer",
})

PROTECTED_DYNAMIC_PREFIXES = (
    "custom_internal_",
    "custom_partner_",
    "custom_assignment_",
    "custom_dispatch_",
    "custom_private_",
)


def _customer_field_descriptor(field):
    """Validate and reduce Customer-visible template metadata."""

    if not isinstance(field, dict):
        return None

    name = field.get("fieldname")
    fieldtype = field.get("fieldtype")

    if not isinstance(name, str):
        return None

    if not name or not name.replace("_", "").isalnum():
        return None

    if name.startswith("_"):
        return None

    if name in PROTECTED_DYNAMIC_FIELD_NAMES:
        return None

    if name.startswith(PROTECTED_DYNAMIC_PREFIXES):
        return None

    if fieldtype not in CUSTOMER_DYNAMIC_FIELD_TYPES:
        return None

    if field.get("hide_from_customer") in (
        True, 1, "1", "true", "True"
    ):
        return None

    if field.get("hidden") in (
        True, 1, "1", "true", "True"
    ):
        return None

    allowed_metadata = (
        "fieldname",
        "label",
        "fieldtype",
        "hide_from_customer",
        "required",
        "placeholder",
        "idx",
    )

    result = {
        key: field[key]
        for key in allowed_metadata
        if key in field
    }

    if fieldtype in {"Select", "Link"}:
        options = field.get("options")

        if isinstance(options, str):
            result["options"] = options

    return result


def project_customer_ticket_detail(
    detail,
    visible_communication_names,
    *,
    viewer_email=None,
):
    """Build an explicit Customer-safe HD Ticket detail response.

    The caller must independently verify the authenticated actor
    and HD Ticket read permission.

    Communication names must originate from a trusted server-side
    audience and document-permission lookup.
    """

    detail = detail or {}

    result = {
        key: detail[key]
        for key in CUSTOMER_TICKET_FIELDS
        if key in detail
    }

    template = detail.get("template") or {}
    if not isinstance(template, dict):
        template = {}

    public_template_fields = []
    permitted_fieldnames = set()

    for field in template.get("fields") or []:
        safe_field = _customer_field_descriptor(field)

        if safe_field is None:
            continue

        name = safe_field["fieldname"]

        public_template_fields.append(safe_field)
        permitted_fieldnames.add(name)

        if name in detail and name not in result:
            value = detail[name]

            if value is None or isinstance(
                value, (str, int, float, bool)
            ):
                result[name] = value

    result["template"] = {
        "fields": public_template_fields,
    }

    if isinstance(template.get("name"), str):
        result["template"]["name"] = template["name"]

    public_metadata = []

    for field in detail.get("fields") or []:
        safe_field = _customer_field_descriptor(field)

        if safe_field is None:
            continue

        name = safe_field["fieldname"]

        if (
            name in CUSTOMER_TICKET_FIELDS
            or name in permitted_fieldnames
        ):
            public_metadata.append(safe_field)

    result["fields"] = public_metadata

    result.update(
        project_customer_activities(
            detail,
            visible_communication_names,
        )
    )

    # Preserve expected response shapes without exposing
    # internal ticket tags, contact metadata or scripts.
    result["tags"] = []
    result["_form_script"] = ""

    # The Customer sidebar requires a contact object.
    # Never forward the native ticket contact, which may
    # identify an internal employee or unrelated person.
    if viewer_email:
        result["contact"] = {
            "name": viewer_email,
            "email_id": viewer_email,
            "image": None,
        }

    return result