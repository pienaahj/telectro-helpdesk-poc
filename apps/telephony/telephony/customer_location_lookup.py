import frappe
from frappe import _

from telephony.telectro_site_guard import _get_default_campus_for_ticket


CATEGORY_CONFIG = {
    "Buildings": {
        "bucket": "Buildings",
        "geometry_types": ["Point"],
    },
    "Network Nodes": {
        "bucket": "Network Nodes",
        "geometry_types": ["Point"],
    },
    "Links": {
        "bucket": "Links",
        "geometry_types": ["LineString"],
    },
    "Areas": {
        "bucket": "Areas",
        "geometry_types": ["Polygon"],
    },
    "Other": {
        "bucket": "Other",
        "geometry_types": ["Point"],
    },
    "Residents": {
        "bucket": "Residents",
        "geometry_types": ["Point"],
    },
}

CUSTOMER_FAULT_POINT_PAGE_LEN_MAX = 64

@frappe.whitelist()
def get_customer_ticket_location_context(ticket_name=None):
    """Return Customer-safe location context for a Customer portal ticket."""
    ticket_name = str(ticket_name or "").strip()
    if not ticket_name:
        return {}

    ticket = frappe.db.get_value(
        "HD Ticket",
        ticket_name,
        [
            "name",
            "customer",
            "raised_by",
            "custom_site_group",
            "custom_fault_category",
            "custom_site",
            "custom_fault_asset",
            "custom_service_area",
            "custom_equipment_ref",
            "via_customer_portal",
        ],
        as_dict=True,
    )

    if not ticket:
        return {}

    user = frappe.session.user
    allowed_customers = _get_hd_customers_for_user(user)

    if ticket.raised_by != user and ticket.customer not in allowed_customers:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    location_name = ticket.custom_site or ticket.custom_fault_asset

    location = None
    if location_name:
        location = frappe.db.get_value(
            "Location",
            location_name,
            [
                "name",
                "location_name",
                "parent_location",
                "latitude",
                "longitude",
                "custom_kmz_geometry_type",
            ],
            as_dict=True,
        )

    return {
        "ticket": ticket.name,
        "customer": ticket.customer,
        "campus": ticket.custom_site_group,
        "category": ticket.custom_fault_category,
        "service_area": ticket.custom_service_area,
        "equipment_ref": ticket.custom_equipment_ref,
        "fault_point": location.location_name if location else "",
        "fault_point_id": location.name if location else location_name,
        "parent_location": location.parent_location if location else "",
        "latitude": location.latitude if location else None,
        "longitude": location.longitude if location else None,
        "geometry_type": location.custom_kmz_geometry_type if location else "",
    }

@frappe.whitelist()
def get_customer_allowed_campus():
    """Return the current Customer user's allowed Campus Location."""
    return _get_customer_allowed_campus_for_user(frappe.session.user)


@frappe.whitelist()
def search_customer_fault_points(txt=None, category=None, page_len=20):
    """
    Return Customer-scoped fault point Location rows for the logged-in Customer user.

    This is intentionally server-scoped and does not trust client filters.
    """
    campus = _get_customer_allowed_campus_for_user(frappe.session.user)
    if not campus:
        return []

    txt = (txt or "").strip()
    category = (category or "Buildings").strip()
    page_len = min(int(page_len or 20), CUSTOMER_FAULT_POINT_PAGE_LEN_MAX)

    category_config = CATEGORY_CONFIG.get(category)
    if not category_config:
        return []

    bucket = category_config["bucket"]
    geometry_types = category_config["geometry_types"]

    bucket_root = f"{campus} - {bucket}"

    root = frappe.db.get_value(
        "Location",
        bucket_root,
        ["name", "lft", "rgt", "is_group", "parent_location"],
        as_dict=True,
    )

    if not root or not root.is_group:
        return []

    params = {
        "lft": root.lft,
        "rgt": root.rgt,
        "txt": f"%{txt}%",
        "page_len": page_len,
        "geometry_types": tuple(geometry_types),
    }

    return frappe.db.sql(
        """
        SELECT
            name,
            location_name,
            parent_location,
            custom_kmz_geometry_type,
            latitude,
            longitude
        FROM `tabLocation`
        WHERE lft >= %(lft)s
          AND rgt <= %(rgt)s
          AND is_group = 0
          AND custom_kmz_geometry_type IN %(geometry_types)s
          AND (
              %(txt)s = '%%'
              OR name LIKE %(txt)s
              OR location_name LIKE %(txt)s
          )
        ORDER BY location_name
        LIMIT %(page_len)s
        """,
        params,
        as_dict=True,
    )


def _get_customer_allowed_campus_for_user(user: str) -> str | None:
    """
    Resolve the logged-in Customer Website User to a single allowed Campus.

    Uses existing ticket/campus defaulting logic by constructing a small
    ticket-like object with the resolved HD Customer name.
    """
    if not user or user == "Guest":
        return None

    hd_customers = _get_hd_customers_for_user(user)
    if not hd_customers:
        return None

    # V1: use the first linked Customer organisation.
    hd_customer = hd_customers[0]

    mock_ticket = frappe._dict(
        {
            "customer": hd_customer,
            "custom_customer": None,
            "custom_site_group": None,
        }
    )

    return _get_default_campus_for_ticket(mock_ticket)


def _get_hd_customers_for_user(user: str) -> list[str]:
    contacts = frappe.get_all(
        "Contact",
        filters={"email_id": user},
        pluck="name",
    )

    linked_contact_rows = frappe.get_all(
        "Contact Email",
        filters={"email_id": user},
        fields=["parent"],
    )

    for row in linked_contact_rows:
        if row.parent not in contacts:
            contacts.append(row.parent)

    if not contacts:
        return []

    links = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Contact",
            "parent": ["in", contacts],
            "link_doctype": ["in", ["HD Customer", "Customer"]],
        },
        fields=["link_doctype", "link_name"],
    )

    customers = []
    for link in links:
        if link.link_doctype == "HD Customer":
            customers.append(link.link_name)
        elif link.link_doctype == "Customer" and frappe.db.exists("HD Customer", link.link_name):
            customers.append(link.link_name)

    return sorted(set(customers))