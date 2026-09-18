import frappe
from frappe import _

from helpdesk.utils import is_agent


def _norm(value) -> str:
    return str(value or "").strip()


def _ticket_location(doc) -> str:
    """
    Return the Location against which structured Equipment must be validated.

    Point-based ticket flows use custom_site. Asset-driven Location flows
    may use custom_fault_asset instead.
    """
    return _norm(doc.get("custom_site")) or _norm(
        doc.get("custom_fault_asset")
    )


def _is_customer_portal_actor(doc) -> bool:
    """
    Return True only for a non-agent submission through the Helpdesk
    customer portal path.

    Helpdesk api.new sets via_customer_portal before insert. Agent users
    may also use that API, so via_customer_portal alone is not sufficient.
    """
    return bool(doc.get("via_customer_portal")) and not is_agent()


def validate_affected_equipment(doc, method=None):
    """
    Validate HD Ticket.custom_affected_equipment.

    Contract:
    - blank structured Equipment is allowed;
    - selected Equipment must exist;
    - selected Equipment must belong to the ticket's exact Location;
    - Customer portal users may select only Customer-safe, Selectable
      Equipment.
    """
    equipment_name = _norm(
        doc.get("custom_affected_equipment")
    )

    if not equipment_name:
        return

    equipment = frappe.db.get_value(
        "TELECTRO Equipment",
        equipment_name,
        [
            "name",
            "location",
            "customer_visibility",
            "ticket_selectability",
        ],
        as_dict=True,
    )

    if not equipment:
        frappe.throw(
            _("Affected Equipment does not exist: {0}").format(
                equipment_name
            )
        )

    ticket_location = _ticket_location(doc)

    if not ticket_location:
        frappe.throw(
            _(
                "Affected Equipment requires a selected "
                "Fault Point or Fault Asset."
            )
        )

    equipment_location = _norm(equipment.location)

    if equipment_location != ticket_location:
        frappe.throw(
            _(
                "Affected Equipment must belong to the "
                "selected fault location."
            )
        )

    if not _is_customer_portal_actor(doc):
        return

    if _norm(equipment.customer_visibility) != "Customer-safe":
        frappe.throw(
            _(
                "This equipment is not available to "
                "Customer portal users."
            )
        )

    if _norm(equipment.ticket_selectability) != "Selectable":
        frappe.throw(
            _(
                "This equipment cannot be selected on "
                "a Customer support request."
            )
        )
