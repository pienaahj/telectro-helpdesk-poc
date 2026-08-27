from __future__ import annotations

import frappe


CUSTOMER_PORTAL_HOME = "helpdesk/my-tickets"
CUSTOMER_ROLE = "Customer"


def get_website_user_home_page(user: str) -> str | None:
    """
    Return the contained Helpdesk portal home for Customer Website Users.

    System Users, Guest, and non-Customer Website Users are deliberately
    left to Frappe's normal home-page resolution.
    """
    if not user or user == "Guest":
        return None

    user_type = frappe.db.get_value(
        "User",
        user,
        "user_type",
    )

    if user_type != "Website User":
        return None

    if CUSTOMER_ROLE not in frappe.get_roles(user):
        return None

    return CUSTOMER_PORTAL_HOME
