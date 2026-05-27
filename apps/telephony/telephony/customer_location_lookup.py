import frappe
from frappe import _

from telephony.telectro_site_guard import _get_default_campus_for_ticket


CATEGORY_BUCKETS = {
    "Buildings": "Buildings",
    "Network Nodes": "Network Nodes",
    "Other": "Other",
    "Residents": "Residents",
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
    page_len = min(int(page_len or 20), 50)

    bucket = CATEGORY_BUCKETS.get(category)
    if not bucket:
        return []

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
    }

    return frappe.db.sql(
        """
        SELECT
            name,
            location_name,
            parent_location,
            custom_kmz_geometry_type
        FROM `tabLocation`
        WHERE lft >= %(lft)s
          AND rgt <= %(rgt)s
          AND is_group = 0
          AND custom_kmz_geometry_type = 'Point'
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