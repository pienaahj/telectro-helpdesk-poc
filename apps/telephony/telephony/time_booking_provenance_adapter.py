"""Private live Mapping bridge; no lifecycle or database integration."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from frappe.model.docstatus import DocStatus

from telephony.time_booking_provenance import BookingProvenanceError


_FIELDS = (
    "doctype", "name", "custom_telectro_booking_origin",
    "employee", "company", "user", "docstatus",
)


def _normalize_docstatus(value: object) -> int:
    """Accept only built-in int or the exact installed Frappe DocStatus type."""
    if type(value) is int:
        status = value
    elif type(value) is DocStatus:
        status = int(value)
    else:
        raise BookingProvenanceError()
    if status not in (0, 1, 2):
        raise BookingProvenanceError()
    return status


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class _TimesheetDocumentView(Mapping[str, object]):
    """Read-only live projection with a fixed underlying object reference.

    The underlying Document remains mutable. Retain this exact view instance
    throughout any pure-policy creation grant; constructing another view does
    not transfer authorization. This view does not establish snapshot trust.
    """

    _document: object

    def __post_init__(self) -> None:
        if not callable(getattr(self._document, "get", None)):
            raise BookingProvenanceError()

    def __getitem__(self, key: str) -> object:
        if type(key) is not str or key not in _FIELDS:
            raise KeyError(key)
        value = self._document.get(key)
        if key == "docstatus":
            return _normalize_docstatus(value)
        return value

    def __iter__(self) -> Iterator[str]:
        return iter(_FIELDS)

    def __len__(self) -> int:
        return len(_FIELDS)
