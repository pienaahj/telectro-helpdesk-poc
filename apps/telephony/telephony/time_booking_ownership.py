"""Pure checks over trusted persisted booking snapshots; no database access.

Provenance authenticity and snapshot freshness must be established by future
trusted integration. No marker field, endpoint or lifecycle hook is installed.
"""

from collections.abc import Mapping

from telephony.time_booking_identity import TechnicianBookingIdentity


class BookingOwnershipError(PermissionError):
    """Generic denial without exposing foreign identifiers."""

    def __init__(self):
        super().__init__("Booking access is not permitted.")


def _identifier(value):
    return isinstance(value, str) and bool(value.strip())


def _check_parent(identity, parent):
    if (
        not isinstance(identity, TechnicianBookingIdentity)
        or not all(_identifier(v) for v in (
            identity.user, identity.employee, identity.company
        ))
        or not isinstance(parent, Mapping)
        or parent.get("doctype") != "Timesheet"
        or not _identifier(parent.get("name"))
        or parent.get("custom_telectro_booking_origin") != "Phase 2"
        or parent.get("employee") != identity.employee
        or parent.get("company") != identity.company
        or parent.get("user") != identity.user
        or type(parent.get("docstatus")) is not int
        or parent.get("docstatus") not in (0, 1, 2)
    ):
        raise BookingOwnershipError()


def authorize_parent(
    identity: TechnicianBookingIdentity,
    persisted: Mapping[str, object],
    *,
    operation: str = "read",
    proposed: Mapping[str, object] | None = None,
) -> None:
    """Authorize a persisted parent, optionally checking a full proposed snapshot.

    Read accepts owned marked parents at any native document status. Correct
    accepts Draft only. This checks authorization, not a correction operation.
    Unmarked legacy documents are rejected without adoption or modification.
    Supplied owner fields are never authorization evidence.
    """
    if operation not in (
        "read",
        "correct",
        "cancel_submitted",
        "replace_submitted",
    ):
        raise BookingOwnershipError()

    _check_parent(identity, persisted)

    status = persisted["docstatus"]

    if operation == "correct" and status != 0:
        raise BookingOwnershipError()

    if operation in ("cancel_submitted", "replace_submitted") and status != 1:
        raise BookingOwnershipError()
    if proposed is not None:
        if operation != "correct":
            raise BookingOwnershipError()
        _check_parent(identity, proposed)
        if proposed.get("name") != persisted.get("name") or proposed.get("docstatus") != 0:
            raise BookingOwnershipError()


def _child_names(parent):
    rows = parent.get("time_logs")
    if not isinstance(rows, (list, tuple)):
        raise BookingOwnershipError()
    names = set()
    for row in rows:
        if (
            not isinstance(row, Mapping)
            or row.get("doctype") != "Timesheet Detail"
            or not _identifier(row.get("name"))
            or row.get("parent") != parent.get("name")
            or row.get("parenttype") != "Timesheet"
            or row.get("parentfield") != "time_logs"
            or row.get("name") in names
        ):
            raise BookingOwnershipError()
        names.add(row["name"])
    return names


def authorize_child(
    identity: TechnicianBookingIdentity,
    persisted_parent: Mapping[str, object],
    child: Mapping[str, object],
    *,
    operation: str = "read",
    proposed_parent: Mapping[str, object] | None = None,
) -> None:
    """Require actual membership in an authorized trusted persisted parent.

    The child argument may be untrusted: matching submitted linkage alone is
    insufficient. Existing row identities must be unique and cannot be moved.
    If supplied, proposed_parent is a full snapshot of existing rows only;
    new rows and row deletion are outside this guard's contract.
    """
    authorize_parent(
        identity, persisted_parent, operation=operation, proposed=proposed_parent
    )
    names = _child_names(persisted_parent)
    if not isinstance(child, Mapping):
        raise BookingOwnershipError()
    if _child_names({
        "name": persisted_parent["name"], "time_logs": [child]
    }) - names:
        raise BookingOwnershipError()
    if proposed_parent is not None and _child_names(proposed_parent) != names:
        raise BookingOwnershipError()
