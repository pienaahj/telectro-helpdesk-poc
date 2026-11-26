"""Access policy for the confidential Customer Labour Cost Analysis."""

from datetime import date

import frappe
from frappe import _
from frappe.core.doctype.page.page import Page
from frappe.desk.desktop import get_desktop_page as native_desktop_page

from telephony.ftelephony.page.technician_work_overview.technician_work_overview import _authorized_scope
from telephony.time_booking_identity import (
    TechnicianBookingIdentity,
    TechnicianIdentityError,
    _resolve_technician_identity,
)

PAGE = "customer-labour-cost-analysis"
ROLE = "TELECTRO-POC Role - Commercial Reporting"
PIERRE_KEY = "telectro_cost_pierre_user"
ADMIN_TEST_KEY = "telectro_cost_admin_dev_test"
DEV_FIRST_DATE = date(2026, 11, 20)
DEV_LAST_DATE = date(2026, 11, 26)
DEV_TECHNICIAN = TechnicianBookingIdentity("tech.bravo@local.test", "HR-EMP-00001", "Telectro (Demo)")


def _deny():
    raise frappe.PermissionError(_("Customer Labour Cost Analysis is unavailable."))


def _enabled_system_user(user):
    account = frappe.db.get_value("User", user, ["name", "enabled", "user_type"], as_dict=True)
    return bool(account and (account.name, account.enabled, account.user_type) == (user, 1, "System User"))


def _commercial_role_is_enabled():
    role = frappe.db.get_value("Role", ROLE, ["name", "disabled"], as_dict=True)
    return bool(role and (role.name, role.disabled) == (ROLE, 0))


def _admin_dev_scope():
    # The switch alone cannot enable a test scope on another site, or on a non-DEV bench.
    setting = frappe.conf.get(ADMIN_TEST_KEY)
    if (
        type(setting) is not int
        or setting != 1
        or frappe.local.site != "frontend"
        or frappe.conf.get("developer_mode") != 1
        or frappe.conf.get("db_host") != "db"
        or not _enabled_system_user("Administrator")
    ):
        _deny()
    try:
        current = _resolve_technician_identity(DEV_TECHNICIAN.user)
    except TechnicianIdentityError:
        _deny()
    if current != DEV_TECHNICIAN:
        _deny()
    return frozenset((current,))


def require_cost_scope():
    """Reevaluate live identity, role and reporting authority for the session."""
    if frappe.conf.get("telectro_time_booking_enabled") not in (1, True, "1"):
        _deny()
    user = frappe.session.user
    if user == "Administrator":
        return _admin_dev_scope()

    approved = frappe.conf.get(PIERRE_KEY)
    if (
        type(approved) is not str
        or not 0 < len(approved) <= 140
        or any(char.isspace() for char in approved)
        or approved in ("Guest", "Administrator")
        or user != approved
        or not _enabled_system_user(user)
        or not _commercial_role_is_enabled()
        or not frappe.db.exists("Has Role", {
            "parent": user, "parenttype": "User", "parentfield": "roles", "role": ROLE,
        })
    ):
        _deny()
    return _authorized_scope()


def can_access_cost():
    try:
        require_cost_scope()
    except frappe.PermissionError:
        return False
    return True


class CommercialReportingPage(Page):
    def is_permitted(self):
        if self.name == PAGE:
            frappe.flags.cost_private_response = True
            return can_access_cost()
        return super().is_permitted()

    def has_permission(self, permtype="read", *, debug=False, user=None):
        if self.name == PAGE and permtype in ("read", "select") and not self.flags.ignore_permissions:
            if user not in (None, frappe.session.user) or not can_access_cost():
                return False
        return super().has_permission(permtype, debug=debug, user=user)


def page_query_condition(user=None):
    if user not in (None, frappe.session.user) or not can_access_cost():
        return "`tabPage`.`name` != " + frappe.db.escape(PAGE)


def filter_cost_page_discovery(bootinfo):
    # extend_bootinfo also runs when Frappe serves a cached boot payload.
    pages = bootinfo.get("page_info", {})
    if PAGE in pages and not can_access_cost():
        bootinfo.page_info = {name: page for name, page in pages.items() if name != PAGE}


@frappe.whitelist()
def get_desktop_page(page):
    workspace = native_desktop_page(page)
    cards = workspace.get("cards", {}).get("items", [])
    shortcuts = workspace.get("shortcuts", {}).get("items", [])
    if not any(
        item.get("link_to") == PAGE
        for item in (*shortcuts, *(link for card in cards for link in card["links"]))
    ) or can_access_cost():
        return workspace

    # Native Workspace visibility trusts cached allowed pages and bypasses roles
    # for Administrator. Keep all other links and their order untouched.
    for card in cards:
        card["links"] = [link for link in card["links"] if link.get("link_to") != PAGE]
    workspace["cards"]["items"] = [card for card in cards if card["links"]]
    workspace["shortcuts"]["items"] = [link for link in shortcuts if link.get("link_to") != PAGE]
    return workspace


def set_cost_cache_control(response, request):
    if frappe.flags.cost_private_response:
        response.headers["Cache-Control"] = "private, no-store"
