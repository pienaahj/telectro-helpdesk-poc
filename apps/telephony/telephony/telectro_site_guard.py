import frappe

# Categories stored by Select field (exact labels)
CAT_BUILDINGS = "buildings"
CAT_NETWORK_NODES = "network nodes"
CAT_LINKS = "links"
CAT_AREAS = "areas"
CAT_OTHER = "other"
CAT_RESIDENTS = "residents"

# Category -> bucket suffix (as it appears in Location names)
CATEGORY_BUCKET = {
    CAT_BUILDINGS: "Buildings",
    CAT_NETWORK_NODES: "Network Nodes",
    CAT_OTHER: "Other",
    CAT_RESIDENTS: "Residents",
}

# Asset-driven categories: skip bucket enforcement (pilot-friendly)
ASSET_ONLY_CATS = {CAT_LINKS, CAT_AREAS}

# Ticket Types considered "fault-like" (strict validation)
FAULT_TICKET_TYPES = {"Faults", "Incident"}

def _is_email_intake(doc) -> bool:
    # 1) Explicit source wins
    src = (doc.get("custom_request_source") or "").strip().lower()
    if src in ("email", "mail", "inbound email"):
        return True

    # 2) Email-created tickets: raised_by/contact_email commonly set by Frappe
    raised_by = (doc.get("raised_by") or "").strip().lower()
    contact_email = (doc.get("contact_email") or "").strip().lower()

    # If it looks like an email address, treat as email intake
    def looks_like_email(s: str) -> bool:
        return ("@" in s) and (" " not in s) and (len(s) >= 5)

    if looks_like_email(raised_by) or looks_like_email(contact_email):
        return True

    return False

def _apply_customer_default_campus(doc) -> None:
    """
    If custom_customer is set and custom_site_group is blank,
    auto-fill campus from Customer.custom_default_campus.
    """
    if not _is_blank(doc.get("custom_site_group")):
        return

    cust = _norm(doc.get("custom_customer"))
    if not cust:
        return

    default_campus = frappe.db.get_value("Customer", cust, "custom_default_campus")
    if default_campus:
        doc.custom_site_group = default_campus
        
def _require_campus(doc) -> None:
    if _is_email_intake(doc):
        # allow email tickets to be created without campus; triage can fill it
        return
    _require(doc, "custom_site_group", "Campus")
    
def _require_site_within_campus(doc) -> None:
    """
    If both Campus (custom_site_group) and Fault Point (custom_site) are present,
    ensure the site is within the campus subtree.
    Skip for email intake when fields are missing; enforce only when both present.
    """
    site_group = _norm(doc.get("custom_site_group"))
    site = _norm(doc.get("custom_site"))

    # If either is missing, don't enforce containment (email triage path)
    if not site_group or not site:
        return

    if not _is_descendant(site_group, site):
        parent = frappe.db.get_value("Location", site, "parent_location") or ""
        frappe.throw(
            f"Fault Point must be under Campus '{site_group}'. "
            f"Selected site parent is '{parent}'."
        )

def _require_fault_point_for_faults(doc) -> None:
    if _is_email_intake(doc):
        return
    if _is_fault_ticket(doc):
        _require(doc, "custom_site", "Fault Point")

def _ticket_type(doc) -> str:
    return (doc.get("ticket_type") or "").strip()

def _is_fault_ticket(doc) -> bool:
    t = _ticket_type(doc)
    # Back-compat: blank type treated as fault-like
    return (not t) or (t in FAULT_TICKET_TYPES)

def _is_blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    return False

def _require(doc, fieldname: str, label: str) -> None:
    if _is_blank(doc.get(fieldname)):
        frappe.throw(f"Please select {label}.")

def _norm(s: str) -> str:
    return (s or "").strip()

def _norm_lower(s: str) -> str:
    return _norm(s).lower()

def _is_descendant(root_name: str, node_name: str) -> bool:
    """Return True if node_name is within root_name subtree (nested set containment)."""
    root = frappe.db.get_value("Location", root_name, ["lft", "rgt"], as_dict=True)
    node = frappe.db.get_value("Location", node_name, ["lft", "rgt"], as_dict=True)
    if not root or not node:
        return False
    return node.lft >= root.lft and node.rgt <= root.rgt

def validate_site_fields(doc, method=None):
    """
    Enforce:
    - custom_site_group must be a group Location (is_group=1) when provided
    - custom_site must be a leaf Location (is_group=0) when provided
    - For Fault-like tickets only: site must live under the matching bucket under site_group.
    - Links/Areas are asset-driven; bucket enforcement is skipped.
    """

    frappe.cache().set_value(
        "telephony:debug:last_site_guard",
        {
            "ts": str(frappe.utils.now_datetime()),
            "name": doc.name,
            "is_new": getattr(doc, "is_new", None) and doc.is_new(),
            "ticket_type": doc.get("ticket_type"),
            "custom_request_source": doc.get("custom_request_source"),
            "custom_customer": doc.get("custom_customer"),
            "custom_site_group": doc.get("custom_site_group"),
            "custom_site": doc.get("custom_site"),
            "subject": doc.get("subject"),
            "raised_by": doc.get("raised_by"),
            "contact_email": doc.get("contact_email"),
            "contact": doc.get("contact"),
            "sender": doc.get("sender"),
        },
    )

    # Slice B: default + required campus anchor
    _apply_customer_default_campus(doc)
    _require_campus(doc)

    # Fault-like: require fault point early (so we don't silently skip)
    _require_fault_point_for_faults(doc)

    site_group = _norm(doc.get("custom_site_group"))
    site = _norm(doc.get("custom_site"))
    cat_norm = _norm_lower(doc.get("custom_fault_category"))
    
    # ✅ NEW: Fault-like tickets must have these fields (server truth)
    if _is_fault_ticket(doc) and not _is_email_intake(doc):
        _require(doc, "custom_fault_category", "Fault Category")
        _require(doc, "custom_severity", "Severity")
        _require(doc, "custom_service_area", "Service Area")

    site_group = _norm(doc.get("custom_site_group"))
    site = _norm(doc.get("custom_site"))
    cat_norm = _norm_lower(doc.get("custom_fault_category"))

    # --- Site Group must be a group node (if provided) ---
    if site_group:
        is_group = frappe.db.get_value("Location", site_group, "is_group")
        if is_group is None:
            frappe.throw(f"Site Group does not exist: {site_group}")
        if not is_group:
            frappe.throw(f"Site Group must be a group Location (not a leaf): {site_group}")

    # --- Site must be a leaf node (if provided) ---
    if site:
        is_group = frappe.db.get_value("Location", site, "is_group")
        if is_group is None:
            frappe.throw(f"Site does not exist: {site}")
        if is_group:
            frappe.throw(f"Site must be a leaf Location (not a group): {site}")
            
    # Campus containment (applies when site is present; fault-like already required it)
    _require_site_within_campus(doc)

    # ✅ NEW: Only enforce bucket rules for Fault-like ticket types
    if not _is_fault_ticket(doc):
        return

    # For fault-like, campus+site already required above. For request-like, stop here if missing.
    if not site_group or not site:
        return

    # Links/Areas are asset-first; bucket enforcement skipped
    if cat_norm in ASSET_ONLY_CATS:
        return

    bucket = CATEGORY_BUCKET.get(cat_norm)
    if not bucket:
        frappe.throw(
            f"Unknown Fault Category '{doc.get('custom_fault_category')}'. "
            "Please update site guard mapping."
        )

    bucket_root = f"{site_group} - {bucket}"
    if not frappe.db.exists("Location", bucket_root):
        frappe.throw(f"Missing bucket Location: '{bucket_root}'")

    if not _is_descendant(bucket_root, site):
        parent = frappe.db.get_value("Location", site, "parent_location") or ""
        frappe.throw(
            f"Site must be under '{bucket_root}'. "
            f"Selected site parent is '{parent}'."
        )