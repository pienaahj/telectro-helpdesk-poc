import frappe
from frappe import _
from helpdesk.utils import get_customer

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

CUSTOMER_EQUIPMENT_PAGE_LEN_MAX = 64

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
            "custom_affected_equipment",
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
    equipment = None

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

    if ticket.custom_affected_equipment and location_name:
        equipment = frappe.db.get_value(
            "TELECTRO Equipment",
            ticket.custom_affected_equipment,
            [
                "name",
                "equipment_name",
                "location",
                "equipment_type",
                "manufacturer",
                "model",
                "customer_visibility",
            ],
            as_dict=True,
        )

        if (
            not equipment
            or equipment.location != location_name
            or equipment.customer_visibility != "Customer-safe"
        ):
            equipment = None

    return {
        "ticket": ticket.name,
        "customer": ticket.customer,
        "campus": ticket.custom_site_group,
        "category": ticket.custom_fault_category,
        "service_area": ticket.custom_service_area,
        "equipment_ref": ticket.custom_equipment_ref,
        "affected_equipment": (
            equipment.equipment_name if equipment else ""
        ),
        "affected_equipment_id": (
            equipment.name if equipment else ""
        ),
        "affected_equipment_type": (
            equipment.equipment_type if equipment else ""
        ),
        "affected_equipment_manufacturer": (
            equipment.manufacturer if equipment else ""
        ),
        "affected_equipment_model": (
            equipment.model if equipment else ""
        ),
        "fault_point": (
            location.location_name if location else ""
        ),
        "fault_point_id": (
            location.name if location else location_name
        ),
        "parent_location": (
            location.parent_location if location else ""
        ),
        "latitude": (
            location.latitude if location else None
        ),
        "longitude": (
            location.longitude if location else None
        ),
        "geometry_type": (
            location.custom_kmz_geometry_type if location else ""
        ),
    }


@frappe.whitelist()
def get_customer_allowed_campuses():
    """Return Customer-owned Campus Locations for the logged-in user."""
    return _get_customer_allowed_campuses_for_user(
        frappe.session.user
    )


@frappe.whitelist()
def get_customer_allowed_campus():
    """Return the current Customer user's allowed Campus Location."""
    return _get_customer_allowed_campus_for_user(frappe.session.user)


@frappe.whitelist()
def search_customer_fault_points(
    campus=None,
    txt=None,
    category=None,
    page_len=20,
):
    """
    Return Customer-scoped fault point Location rows for the logged-in
    Customer user.

    When Campus is supplied explicitly, it must be one of the top-level
    Campus Locations owned by the user's resolved Customer organisation.

    The legacy single-Campus resolver remains temporarily available when
    Campus is omitted so existing portal callers continue to work while
    the multi-Campus UI is introduced.
    """
    requested_campus = (campus or "").strip()

    if requested_campus:
        allowed_campuses = (
            _get_customer_allowed_campuses_for_user(
                frappe.session.user
            )
        )

        allowed_names = {
            row["name"]
            for row in allowed_campuses
        }

        if requested_campus not in allowed_names:
            return []

        campus = requested_campus
    else:
        campus = _get_customer_allowed_campus_for_user(
            frappe.session.user
        )

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

def _get_customer_owned_campus_for_location(
    user: str,
    location_name: str,
):
    """
    Resolve one leaf Location to the Customer-owned Campus
    that contains it.

    Customer ownership comes from the authenticated user's
    HD Customer -> ERP Customer bridge. The requested Location
    is never trusted merely because it came from the client.
    """
    location_name = (location_name or "").strip()
    if not location_name:
        return None, None

    allowed_campuses = _get_customer_allowed_campuses_for_user(user)
    if not allowed_campuses:
        return None, None

    location_row = frappe.db.get_value(
        "Location",
        location_name,
        [
            "name",
            "location_name",
            "parent_location",
            "lft",
            "rgt",
            "is_group",
            "latitude",
            "longitude",
            "custom_kmz_geometry_type",
        ],
        as_dict=True,
    )

    if not location_row or location_row.is_group:
        return None, None

    for allowed_campus in allowed_campuses:
        campus_name = allowed_campus["name"]

        campus_row = frappe.db.get_value(
            "Location",
            campus_name,
            [
                "name",
                "lft",
                "rgt",
                "is_group",
            ],
            as_dict=True,
        )

        if not campus_row or not campus_row.is_group:
            continue

        if (
            location_row.lft >= campus_row.lft
            and location_row.rgt <= campus_row.rgt
        ):
            return campus_row, location_row

    return None, None

@frappe.whitelist()
def search_customer_equipment(location=None, txt=None, page_len=20):
    """
    Return Customer-safe, ticket-selectable Equipment for one allowed Location.

    The selected Location is not trusted merely because it came from the client.
    It must be a leaf Location inside one of the logged-in Customer user's
    owned Campuses.
    """
    location = (location or "").strip()
    if not location:
        return []

    campus_row, location_row = (
        _get_customer_owned_campus_for_location(
            frappe.session.user,
            location,
        )
    )

    if not campus_row or not location_row:
        return []

    txt = (txt or "").strip()
    page_len = min(
        max(int(page_len or 20), 1),
        CUSTOMER_EQUIPMENT_PAGE_LEN_MAX,
    )

    params = {
        "location": location,
        "txt": f"%{txt}%",
        "page_len": page_len,
    }

    return frappe.db.sql(
        """
        SELECT
            name,
            equipment_name,
            equipment_type,
            manufacturer,
            model
        FROM `tabTELECTRO Equipment`
        WHERE location = %(location)s
          AND customer_visibility = 'Customer-safe'
          AND ticket_selectability = 'Selectable'
          AND (
              %(txt)s = '%%'
              OR name LIKE %(txt)s
              OR equipment_name LIKE %(txt)s
              OR equipment_type LIKE %(txt)s
              OR manufacturer LIKE %(txt)s
              OR model LIKE %(txt)s
          )
        ORDER BY equipment_name, name
        LIMIT %(page_len)s
        """,
        params,
        as_dict=True,
    )


@frappe.whitelist()
def get_customer_location_map_context(location=None):
    """
    Return Customer-safe map context for one Location.

    The Location is not trusted merely because it came from the client.
    It must be a leaf Location inside one of the logged-in Customer user's
    owned Campuses.
    """
    location = (location or "").strip()
    if not location:
        return {}

    campus_row, location_row = (
        _get_customer_owned_campus_for_location(
            frappe.session.user,
            location,
        )
    )

    if not campus_row or not location_row:
        return {}

    return {
        "location": location_row.name,
        "location_name": (
            location_row.location_name
            or location_row.name
        ),
        "campus": campus_row.name,
        "parent_location": (
            location_row.parent_location or ""
        ),
        "latitude": location_row.latitude,
        "longitude": location_row.longitude,
        "geometry_type": (
            location_row.custom_kmz_geometry_type or ""
        ),
    }


def _get_customer_allowed_campuses_for_user(
    user: str,
) -> list[dict]:
    """
    Return top-level Campus Locations owned by the logged-in
    Customer user's ERP Customer organisation.

    Native Helpdesk customer resolution returns HD Customer
    identities. The durable HD Customer.custom_erp_customer
    bridge resolves that Helpdesk identity to the ERPNext
    Customer used by Location.custom_customer.

    If the user resolves to zero or multiple HD Customers, or
    the HD Customer has no ERP Customer bridge, do not guess.
    """
    if not user or user == "Guest":
        return []

    hd_customers = get_customer(user)

    if len(hd_customers) != 1:
        return []

    hd_customer = hd_customers[0]

    erp_customer = frappe.db.get_value(
        "HD Customer",
        hd_customer,
        "custom_erp_customer",
    )

    if not erp_customer:
        return []

    return frappe.get_all(
        "Location",
        filters={
            "parent_location": "Pilot Sites",
            "is_group": 1,
            "custom_customer": erp_customer,
        },
        fields=[
            "name",
            "location_name",
        ],
        order_by="location_name asc, name asc",
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
