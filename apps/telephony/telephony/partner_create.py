import frappe

PARTNER_ROLE = "TELECTRO-POC Role - Partner"
PARTNER_CREATOR_ROLE = "TELECTRO-POC Role - Partner Creator"
SERVICE_REQUEST = "Service Request"

INTERNAL_ACCEPTANCE_REVIEW_ROLES = {
    "System Manager",
    "Pilot Admin",
    "TELECTRO-POC Ops Role",
    "TELECTRO-POC Coordinator Role",
    "TELECTRO-POC Role - Supervisor Governance",
    "TELECTRO-POC Role - Coordinator Ops",
}

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
    "custom_partner_acceptance_state",
    "custom_partner_accepted_on",
]

def _canonicalize_ticket_assignments_for_doc(doc):
    _canonicalize_ticket_assignments(doc.name)
    
def _canonicalize_ticket_assignments(ticket_name: str):
    todos = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket_name,
            "status": "Open",
        },
        fields=["name", "allocated_to", "creation"],
        order_by="creation asc",
    )

    keep_by_user = {}
    duplicate_names = []

    for todo in todos:
        user = (todo.get("allocated_to") or "").strip()
        if not user:
            duplicate_names.append(todo["name"])
            continue

        if user not in keep_by_user:
            keep_by_user[user] = todo["name"]
        else:
            duplicate_names.append(todo["name"])

    for name in duplicate_names:
        todo = frappe.get_doc("ToDo", name)
        todo.status = "Closed"
        todo.save(ignore_permissions=True)

    cleaned_users = list(keep_by_user.keys())

    frappe.db.set_value(
        "HD Ticket",
        ticket_name,
        "_assign",
        frappe.as_json(cleaned_users),
        update_modified=False,
    )
    
def _format_partner_acceptance_request_comment(note: str | None = None) -> str:
    parts = ["Partner Acceptance Requested"]
    note = (note or "").strip()
    if note:
        parts.append(f"Note: {note}")
    return " | ".join(parts)

def _assert_internal_partner_acceptance_request_access(ticket_name: str, user: str):
    if not _is_internal_acceptance_reviewer(user):
        frappe.throw("Not permitted", frappe.PermissionError)

    row = frappe.db.get_value(
        "HD Ticket",
        ticket_name,
        ["name", "custom_request_source", "custom_partner_acceptance_state", "status"],
        as_dict=True,
    )
    if not row:
        frappe.throw("Ticket not found")

    if row.custom_request_source != "Partner":
        frappe.throw("Not permitted", frappe.PermissionError)

    if row.status in ("Resolved", "Closed", "Archived"):
        frappe.throw("Ticket is already in a terminal status")

    current_state = (row.custom_partner_acceptance_state or "").strip()
    if current_state in {"Pending Partner Acceptance", "Accepted by Partner", "Reviewed by Telectro"}:
        frappe.throw("Partner acceptance has already been requested or processed")
        
def _close_open_todos_for_ticket(ticket_name: str):
    todo_names = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "HD Ticket",
            "reference_name": ticket_name,
            "status": "Open",
        },
        pluck="name",
    )

    for name in todo_names:
        frappe.db.set_value("ToDo", name, "status", "Cancelled", update_modified=False)


def _set_assign_list(doc, users: list[str]):
    cleaned = []
    seen = set()

    for user in users or []:
        user = (user or "").strip()
        if not user:
            continue
        if user in seen:
            continue
        seen.add(user)
        cleaned.append(user)

    doc.set("_assign", frappe.as_json(cleaned))
    
def _is_partner_creator(user: str) -> bool:
    if not user or user == "Guest":
        return False
    return PARTNER_CREATOR_ROLE in set(frappe.get_roles(user))


def _is_partner_user(user: str) -> bool:
    if not user or user == "Guest":
        return False
    roles = set(frappe.get_roles(user))
    return PARTNER_ROLE in roles or PARTNER_CREATOR_ROLE in roles

def _is_internal_acceptance_reviewer(user: str) -> bool:
    if not user or user == "Guest":
        return False
    roles = set(frappe.get_roles(user))
    return bool(roles & INTERNAL_ACCEPTANCE_REVIEW_ROLES)

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

def _assert_internal_partner_acceptance_review_access(ticket_name: str, user: str):
    if not _is_internal_acceptance_reviewer(user):
        frappe.throw("Not permitted", frappe.PermissionError)

    row = frappe.db.get_value(
        "HD Ticket",
        ticket_name,
        ["name", "custom_request_source", "custom_partner_acceptance_state", "status"],
        as_dict=True,
    )
    if not row:
        frappe.throw("Ticket not found")

    if row.custom_request_source != "Partner":
        frappe.throw("Not permitted", frappe.PermissionError)

    if row.custom_partner_acceptance_state != "Accepted by Partner":
        frappe.throw("Ticket is not awaiting Partner acceptance review")

    if row.status in ("Resolved", "Closed", "Archived"):
        frappe.throw("Ticket is already in a terminal status")


def _set_if_field_exists(doc, fieldname: str, value):
    if frappe.get_meta(doc.doctype).has_field(fieldname):
        doc.set(fieldname, value)


def _format_partner_acceptance_review_comment(outcome_label: str, note: str | None = None) -> str:
    parts = [f"Partner Acceptance Review | Outcome: {outcome_label}"]
    note = (note or "").strip()
    if note:
        parts.append(f"Note: {note}")
    return " | ".join(parts)


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
def request_partner_acceptance(ticket_name: str, note: str | None = None):
    user = frappe.session.user
    _assert_internal_partner_acceptance_request_access(ticket_name, user)

    doc = frappe.get_doc("HD Ticket", ticket_name)

    _set_if_field_exists(doc, "custom_partner_acceptance_state", "Pending Partner Acceptance")

    doc.add_comment(
        "Comment",
        _format_partner_acceptance_request_comment(note),
    )

    doc.save(ignore_permissions=True)
    _canonicalize_ticket_assignments(doc.name)
    doc.reload()

    return {
        "name": doc.name,
        "custom_partner_acceptance_state": doc.get("custom_partner_acceptance_state"),
    }
    
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

    doc.insert(ignore_permissions=True)
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

    current_state = (doc.get("custom_partner_acceptance_state") or "").strip()
    if current_state != "Pending Partner Acceptance":
        frappe.throw("Partner acceptance is not currently pending")

    _set_if_field_exists(doc, "custom_partner_acceptance_state", "Accepted by Partner")
    if completed_on:
        _set_if_field_exists(doc, "custom_partner_accepted_on", completed_on)

    doc.add_comment(
        "Comment",
        f"Partner acceptance note by {user}:\n{note}",
    )

    doc.save(ignore_permissions=True)
    _canonicalize_ticket_assignments(doc.name)
    doc.reload()

    return {
        "name": doc.name,
        "custom_partner_acceptance_state": doc.get("custom_partner_acceptance_state"),
        "custom_partner_accepted_on": doc.get("custom_partner_accepted_on"),
    }

@frappe.whitelist()
def review_partner_acceptance(ticket_name: str, outcome: str, note: str | None = None):
    user = frappe.session.user
    _assert_internal_partner_acceptance_review_access(ticket_name, user)

    allowed = {
        "review_only": "Review only",
        "resolve": "Resolved",
        "close": "Closed",
    }
    outcome = (outcome or "").strip()

    if outcome not in allowed:
        frappe.throw("Invalid review outcome")

    doc = frappe.get_doc("HD Ticket", ticket_name)

    if outcome == "resolve":
        _set_if_field_exists(doc, "custom_partner_acceptance_state", "Reviewed by Telectro")
        doc.status = "Resolved"

    elif outcome == "close":
        _set_if_field_exists(doc, "custom_partner_acceptance_state", "Reviewed by Telectro")
        doc.status = "Closed"

    elif outcome == "review_only":
        pass

    doc.add_comment(
        "Comment",
        _format_partner_acceptance_review_comment(allowed[outcome], note),
    )

    doc.save(ignore_permissions=True)

    if outcome in {"resolve", "close"}:
        _close_open_todos_for_ticket(doc.name)
        frappe.db.set_value("HD Ticket", doc.name, "_assign", "[]", update_modified=False)
        doc.reload()

    elif outcome == "review_only":
        _canonicalize_ticket_assignments(doc.name)
        doc.reload()

    return {
        "name": doc.name,
        "status": doc.status,
        "custom_partner_acceptance_state": doc.get("custom_partner_acceptance_state"),
        "_assign": doc.get("_assign"),
    }