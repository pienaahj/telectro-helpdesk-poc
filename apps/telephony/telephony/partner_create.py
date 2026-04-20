import frappe

PARTNER_ROLE = "TELECTRO-POC Role - Partner"
PARTNER_CREATOR_ROLE = "TELECTRO-POC Role - Partner Creator"
SERVICE_REQUEST = "Service Request"

PARTNER_DETAIL_FIELDS = [
    "name",
    "subject",
    "status",
    "priority",
    "ticket_type",
    "summary",
    "creation",
    "modified",
    "custom_customer",
    "custom_site_group",
    "custom_fault_category",
    "custom_fault_asset",
    "custom_site",
    "custom_ownership_model",
    "custom_request_type",
    "custom_due_date",
    "custom_service_area",
    "custom_severity",
    "custom_request_source",
    "custom_fulfilment_party",
]


def _is_partner_creator(user: str) -> bool:
    if not user or user == "Guest":
        return False
    return PARTNER_CREATOR_ROLE in set(frappe.get_roles(user))


def _is_partner_user(user: str) -> bool:
    if not user or user == "Guest":
        return False
    roles = set(frappe.get_roles(user))
    return PARTNER_ROLE in roles or PARTNER_CREATOR_ROLE in roles


def _assert_partner_ticket_access(ticket_name: str, user: str):
    if not _is_partner_user(user):
        frappe.throw("Not permitted", frappe.PermissionError)

    row = frappe.db.get_value(
        "HD Ticket",
        ticket_name,
        ["name", "owner", "custom_request_source"],
        as_dict=True,
    )
    if not row:
        frappe.throw("Ticket not found")

    if row.custom_request_source != "Partner":
        frappe.throw("Not permitted", frappe.PermissionError)

    # Conservative v1 rule:
    # creator can see their own submitted ticket,
    # broader partner role can see partner-origin tickets.
    if _is_partner_creator(user) and PARTNER_ROLE not in set(frappe.get_roles(user)):
        if row.owner != user:
            frappe.throw("Not permitted", frappe.PermissionError)


def _set_if_field_exists(doc, fieldname: str, value):
    if frappe.get_meta(doc.doctype).has_field(fieldname):
        doc.set(fieldname, value)


def enforce_partner_create_v1(doc, method=None):
    user = frappe.session.user
    if not _is_partner_creator(user):
        return

    doc.custom_request_source = "Partner"
    doc.custom_fulfilment_party = "Telectro"

    if not doc.ticket_type and frappe.db.exists("HD Ticket Type", SERVICE_REQUEST):
        doc.ticket_type = SERVICE_REQUEST

    doc.agent_group = None


@frappe.whitelist()
def create_partner_ticket(
    custom_customer=None,
    custom_site_group=None,
    custom_fault_category=None,
    custom_fault_asset=None,
    custom_site=None,
    custom_ownership_model=None,
    subject=None,
    summary=None,
    custom_request_type=None,
    custom_due_date=None,
    ticket_type=None,
    custom_service_area=None,
    custom_severity=None,
):
    user = frappe.session.user
    if not _is_partner_creator(user):
        frappe.throw("Not permitted", frappe.PermissionError)

    if not summary and subject:
        summary = subject

    doc = frappe.new_doc("HD Ticket")
    doc.custom_customer = custom_customer
    doc.custom_site_group = custom_site_group
    doc.custom_fault_category = custom_fault_category
    doc.custom_fault_asset = custom_fault_asset
    doc.custom_site = custom_site
    doc.custom_ownership_model = custom_ownership_model
    doc.subject = subject
    doc.summary = summary
    doc.custom_request_type = custom_request_type
    doc.custom_due_date = custom_due_date
    doc.custom_service_area = custom_service_area
    doc.custom_severity = custom_severity

    doc.custom_request_source = "Partner"
    doc.custom_fulfilment_party = "Telectro"
    doc.ticket_type = ticket_type or SERVICE_REQUEST

    doc.insert()
    return {"name": doc.name}


@frappe.whitelist()
def get_partner_ticket_detail(ticket_name: str):
    user = frappe.session.user
    _assert_partner_ticket_access(ticket_name, user)

    doc = frappe.get_doc("HD Ticket", ticket_name)
    return {field: doc.get(field) for field in PARTNER_DETAIL_FIELDS}


@frappe.whitelist()
def submit_partner_completion_note(ticket_name: str, note: str, completed_on: str | None = None):
    user = frappe.session.user
    _assert_partner_ticket_access(ticket_name, user)

    note = (note or "").strip()
    if not note:
        frappe.throw("Completion note is required")

    doc = frappe.get_doc("HD Ticket", ticket_name)

    # Optional structured markers if the fields exist
    _set_if_field_exists(doc, "custom_partner_completion_state", "Completed by Partner")
    if completed_on:
        _set_if_field_exists(doc, "custom_partner_completed_on", completed_on)

    doc.add_comment(
        "Comment",
        f"Partner completion note by {user}:\n{note}",
    )

    doc.save(ignore_permissions=True)

    return {
        "name": doc.name,
        "custom_partner_completion_state": doc.get("custom_partner_completion_state"),
        "custom_partner_completed_on": doc.get("custom_partner_completed_on"),
    }