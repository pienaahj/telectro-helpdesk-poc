"""Persist origin only for the staff Desk manual-create operation."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import re

import frappe
from frappe import _
from frappe.desk.form import save as desk_save
from frappe.model.docstatus import DocStatus

from telephony.customer_communication_privacy import classify_actor_roles


DOCTYPE = "HD Ticket"
FIELD = "custom_telectro_manual_origin"
_TEMPORARY_NAME = re.compile(r"new-hd-ticket-[a-z0-9]+", re.ASCII)
_OTHER_ORIGIN_FIELDS = ("via_customer_portal", "email_account", "ticket_split_from")


@dataclass
class _CreationIntent:
    ticket: object
    consumed: bool = False


_creation_intent = ContextVar("telectro_manual_ticket_creation", default=None)


def _is_internal_staff():
    user = frappe.session.user
    if not user or user == "Guest":
        return False

    account = frappe.db.get_value("User", user, ["enabled", "user_type"], as_dict=True)
    return (
        bool(account)
        and account.get("enabled") == 1
        and account.get("user_type") == "System User"
        and classify_actor_roles(frappe.get_roles(user)) == "internal"
    )


def _origin_installed(meta):
    return meta.has_field(FIELD) and frappe.db.has_column(DOCTYPE, FIELD)


def add_desk_capability(bootinfo):
    """Offer the dedicated first Save only on a ready site and for staff."""
    if _origin_installed(frappe.get_meta(DOCTYPE)) and _is_internal_staff():
        bootinfo.telectro_manual_ticket_create = True


@contextmanager
def _staff_creation(ticket):
    if _creation_intent.get() is not None:
        frappe.throw(_("Manual Ticket creation is already in progress."), frappe.ValidationError)

    intent = _CreationIntent(ticket)
    token = _creation_intent.set(intent)
    try:
        yield intent
    finally:
        # Invalidate even if a nested execution context retained the intent.
        intent.ticket = None
        _creation_intent.reset(token)


@frappe.whitelist(methods=["POST"])
def create(doc):
    """Save one fresh HD Ticket and return the native Desk save response."""
    if not _is_internal_staff():
        frappe.throw(_("Manual Ticket creation is unavailable."), frappe.PermissionError)

    payload = frappe.parse_json(doc)
    if (
        not isinstance(payload, dict)
        or payload.get("doctype") != DOCTYPE
        or not payload.get("__islocal")
        or not isinstance(payload.get("name"), str)
        or _TEMPORARY_NAME.fullmatch(payload["name"]) is None
        or any(payload.get(field) not in (None, "", 0, "0") for field in _OTHER_ORIGIN_FIELDS)
    ):
        frappe.throw(_("A new HD Ticket is required."), frappe.ValidationError)

    meta = frappe.get_meta(DOCTYPE)
    excluded = (*_OTHER_ORIGIN_FIELDS, FIELD)
    values = {
        field.fieldname: payload[field.fieldname]
        for field in meta.fields
        if field.fieldname in payload and field.fieldname not in excluded
    }
    ticket = frappe.get_doc(
        {**values, "doctype": DOCTYPE, "name": payload["name"], "__islocal": 1}
    )
    # Reuse native Desk naming, attachment relinking and response preparation.
    desk_save.capture_doc(ticket, "Save")
    ticket.set("__temporary_name", ticket.name)
    desk_save.set_local_name(ticket)
    ticket.docstatus = DocStatus.DRAFT

    if _origin_installed(meta):
        with _staff_creation(ticket) as intent:
            ticket.save()
            if not intent.consumed:
                frappe.throw(_("Manual Ticket origin could not be recorded."), frappe.ValidationError)
    else:
        # With no marker installed, the native Save still creates the Ticket.
        ticket.save()

    desk_save.run_onload(ticket)
    desk_save.send_updated_docs(ticket)
    desk_save.add_data_to_monitor(doctype=DOCTYPE, action="Save")
    frappe.msgprint(_("Saved"), indicator="green", alert=True)


def enforce_marker(ticket, method=None):
    """Write a server-owned value before native insert or preserve it on save."""
    if not ticket.meta.has_field(FIELD):
        return

    if ticket.flags.in_insert:
        intent = _creation_intent.get()
        manual = intent is not None and intent.ticket is ticket
        if manual:
            if intent.consumed:
                frappe.throw(_("Manual Ticket creation intent was already used."), frappe.ValidationError)
            intent.consumed = True
        ticket.set(FIELD, int(manual))
        return

    previous = ticket.get_doc_before_save()
    if previous is None:
        frappe.throw(_("Could not verify Ticket creation origin."), frappe.ValidationError)
    ticket.set(FIELD, previous.get(FIELD))


def protect_direct_change(ticket, method=None):
    """Guard Document.db_set, which bypasses the normal save validation."""
    if not ticket.meta.has_field(FIELD):
        return

    persisted = frappe.db.get_value(DOCTYPE, ticket.name, FIELD, as_dict=True, for_update=True)
    if persisted is None or ticket.get(FIELD) != persisted.get(FIELD):
        frappe.throw(_("Ticket creation origin is server-managed."), frappe.PermissionError)
