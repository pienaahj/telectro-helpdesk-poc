"""Grant-scoped summary and paginated detail for the Technician Work Overview."""

from collections import defaultdict
from datetime import date, timedelta
from hashlib import sha256
import json

import frappe
from frappe import _
from frappe.desk.query_report import get_report_doc
from frappe.utils import nowdate

from telephony.booked_hours import date_window, duration_rows
from telephony.ftelephony.report.supervisor_booked_hours.supervisor_booked_hours import (
    _REFERENCE_KINDS,
    _matches,
    authorized_bookings,
    employee_labels,
)
from telephony.supervisor_report_runtime import REPORT_NAME
from telephony.supervisor_reporting_grant import resolve_supervisor_reporting_scope

CONTEXTS = ("Helpdesk", "Project", "Customer Support", "Internal")
DIMENSIONS = ("technician", "customer", "service_area", "work_context", "project", "activity_type", "reference")
DETAIL_FIELDS = (
    "booking", "day", "from_time", "to_time", "booked_us", "work_context", "service_area", "activity_type",
    "customer", "unlisted_customer", "customer_type", "project", "project_name", "task", "ticket",
    "snapfix_reference", "reference_state", "status", "description",
)
MAX_DAYS = 93
PAGE_SIZE = 12


def _authorized_scope():
    if frappe.conf.get("telectro_time_booking_enabled") not in (1, True, "1"):
        frappe.throw(_("Technician Work Overview is unavailable."), frappe.PermissionError)
    get_report_doc(REPORT_NAME)
    return resolve_supervisor_reporting_scope()


def _period(preset, from_date, to_date):
    today = date.fromisoformat(nowdate())
    monday = today - timedelta(days=today.weekday())
    presets = {
        "today": (today, today),
        "this_week": (monday, today),
        "last_week": (monday - timedelta(days=7), monday - timedelta(days=1)),
        "this_month": (today.replace(day=1), today),
    }
    if preset in presets and from_date is None and to_date is None:
        first, last = presets[preset]
        from_date, to_date = first.isoformat(), last.isoformat()
    elif preset != "custom":
        frappe.throw(_("Select a valid reporting period."))
    try:
        start, end = date_window(from_date, to_date)
    except (ValueError, OverflowError):
        frappe.throw(_("Enter a valid date range."))
    if (end - start).days > MAX_DAYS:
        frappe.throw(_("Choose a period of 93 days or fewer."))
    return start, end, today.isoformat()


def _employee_labels(bookings):
    return employee_labels({row["employee"] for row in bookings})


def _group_for(row, dimension, labels):
    if dimension == "technician":
        return labels.get(row["employee"], _("Technician")), row["company"], {
            "company": row["company"], "employee": row["employee"],
        }
    if dimension == "customer":
        name = row["customer"] or row["unlisted_customer"]
        attribution = row["customer_type"]
        return name or _(attribution), _(attribution) if name else None, (
            {"customer_type": attribution, "customer": name} if name else {"customer_type": attribution}
        )
    if dimension == "project":
        if row["work_context"] != "Project":
            return None
        if row["project"]:
            return row["project_name"] or row["project"], None, {
                "work_context": "Project", "project": row["project"],
            }
        return _(row["reference_state"]), None, {
            "work_context": "Project", "reference_state": row["reference_state"],
            "reference_kind": "No visible reference",
        }
    if dimension == "reference":
        kind = row["reference_kind"]
        if kind in _REFERENCE_KINDS:
            field = _REFERENCE_KINDS[kind]
            value = row[field]
            label = (row["project_name"] or value) if kind == "Project" else value
            return label, _(kind), {
                "reference_kind": kind, field: value,
            }
        return _(row["reference_state"]), None, {
            "reference_kind": kind, "reference_state": row["reference_state"],
        }
    value = row[dimension]
    if not value:
        return None
    return _(value), None, {dimension: value}


def _selection_criteria(filters):
    return {field: value.strip().casefold() for field, value in filters.items()}


def _groups(bookings, dimension, labels, start, end):
    metadata = {}
    grouped = []
    for row in bookings:
        group = _group_for(row, dimension, labels)
        if group is None:
            continue
        label, secondary, filters = group
        # A selection is resolved against this request's authorized projection.
        criteria = _selection_criteria(filters)
        key = sha256(json.dumps(criteria, sort_keys=True).encode()).hexdigest()
        metadata.setdefault(key, dict(key=key, label=label, secondary=secondary, filters=filters))
        grouped.append(dict(row, group=key))
    amounts = duration_rows(grouped, start, end, group_by=("group", "work_context"), by_day=False)
    totals = defaultdict(dict)
    for row in amounts:
        totals[row["group"]][row["work_context"]] = row["booked_us"]
    result = [
        dict(metadata[key], booked_us=sum(contexts.values()), contexts=contexts)
        for key, contexts in totals.items()
    ]
    return sorted(result, key=lambda row: (row["label"].casefold(), row["secondary"] or "", row["key"]))


@frappe.whitelist(methods=["GET"])
def get_overview(preset="this_week", from_date=None, to_date=None, dimension="technician", group=None, offset=0):
    roster = _authorized_scope()
    if (
        not isinstance(preset, str) or dimension not in DIMENSIONS
        or (group is not None and (not isinstance(group, str) or len(group) != 64))
        or not isinstance(offset, (str, int)) or not str(offset).isascii()
        or not str(offset).isdigit() or len(str(offset)) > 8
    ):
        frappe.throw(_("Select a valid work view."))
    offset = int(offset)
    start, end, today = _period(preset, from_date, to_date)
    bookings = authorized_bookings(roster, start, end)
    labels = _employee_labels(bookings)
    totals = duration_rows(bookings, start, end, group_by=("work_context",), by_day=False)
    by_context = {row["work_context"]: row["booked_us"] for row in totals}
    groups = _groups(bookings, dimension, labels, start, end)
    selected = next((item for item in groups if item["key"] == group), None)
    if group is not None and selected is None:
        frappe.throw(_("This selection is unavailable. Choose another group."), frappe.PermissionError)
    if selected:
        criteria = _selection_criteria(selected["filters"])
        matching = [row for row in bookings if _matches(row, criteria)]
    elif dimension == "project":
        matching = [row for row in bookings if row["work_context"] == "Project"]
    else:
        matching = bookings
    detail = duration_rows(matching, start, end, detail=True)
    page = list(reversed(detail))[offset:offset + PAGE_SIZE]
    customers = {(row["customer_type"], row["customer"] or row["unlisted_customer"])
                 for row in bookings if row["customer"] or row["unlisted_customer"]}
    return {
        "period": {
            "from_date": start.date().isoformat(), "to_date": (end.date() - timedelta(days=1)).isoformat(),
            "today": today,
        },
        "booked_us": sum(by_context.values()),
        "technician_count": len({(row["employee"], row["company"]) for row in bookings}),
        "customer_count": len(customers),
        "contexts": [
            {"name": name, "booked_us": by_context.get(name, 0)}
            for name in (*CONTEXTS, *(name for name in by_context if name not in CONTEXTS))
        ],
        "groups": groups,
        "selected": selected,
        "detail_count": len(detail),
        "detail": [
            dict({field: row[field] for field in DETAIL_FIELDS},
                 technician=labels.get(row["employee"], _("Technician")), company=row["company"])
            for row in page
        ],
        "previous_offset": max(0, offset - PAGE_SIZE) if offset else None,
        "next_offset": offset + PAGE_SIZE if offset + PAGE_SIZE < len(detail) else None,
        "report_filters": {
            "from_date": start.date().isoformat(), "to_date": (end.date() - timedelta(days=1)).isoformat(),
            "view": "Booking Detail",
            **(selected["filters"] if selected else {"work_context": "Project"} if dimension == "project" else {}),
        },
    }
