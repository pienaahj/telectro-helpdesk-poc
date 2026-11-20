"""Pure validation of Phase 2 booking metadata.

Permitted Service Areas are supplied by a trusted caller.
This module does not access Frappe or authorize document references.
"""


class BookingMetadataValidationError(ValueError):
    """Booking metadata violates the permitted field contract."""


def validate_service_area(
    *,
    work_context,
    service_area,
    allowed_service_areas,
) -> None:
    """Validate Service Area across all four supported Work Contexts."""

    if work_context not in (
        "Customer Support",
        "Project",
        "Helpdesk",
        "Internal",
    ):
        raise BookingMetadataValidationError(
            "Unsupported Work Context for Service Area validation"
        )

    if (
        type(allowed_service_areas) is not tuple
        or not allowed_service_areas
        or any(
            type(value) is not str or not value.strip()
            for value in allowed_service_areas
        )
    ):
        raise BookingMetadataValidationError(
            "Invalid permitted Service Area configuration"
        )

    # Internal technical work may be unclassified.
    # Explicit values must still pass the authoritative dropdown check.
    if work_context == "Internal" and service_area in (None, ""):
        return

    if (
        type(service_area) is not str
        or not service_area.strip()
        or service_area != service_area.strip()
        or service_area not in allowed_service_areas
    ):
        raise BookingMetadataValidationError(
            "Invalid or missing Service Area"
        )

_WORK_LOCATIONS = (
    "On-site",
    "Remote",
    "Workshop / Internal",
)


def validate_work_location(
    *,
    activity_type,
    work_location,
) -> None:
    """Validate Work Location, including the Travel exception."""

    if type(activity_type) is not str or not activity_type.strip():
        raise BookingMetadataValidationError(
            "Activity Type is required"
        )

    # Travel is recorded as a separate activity and has no Work Location.
    if activity_type == "Travel":
        if work_location is None or (
            type(work_location) is str and work_location == ""
        ):
            return

        raise BookingMetadataValidationError(
            "Work Location is prohibited for Travel"
        )

    if (
        type(work_location) is not str
        or work_location not in _WORK_LOCATIONS
    ):
        raise BookingMetadataValidationError(
            "Invalid or missing Work Location"
        )

def validate_work_origin(
    *,
    work_origin,
    external_reference,
    other_origin_description,
) -> None:
    """Validate Work Origin and its associated metadata."""

    if work_origin == "Snapfix":
        # Snapfix requires a meaningful external reference.
        if (
            type(external_reference) is not str
            or not external_reference.strip()
            or external_reference != external_reference.strip()
        ):
            raise BookingMetadataValidationError(
                "Snapfix requires a valid external reference"
            )

        # Snapfix must not retain metadata from another origin.
        if other_origin_description is not None and (
            type(other_origin_description) is not str
            or other_origin_description != ""
        ):
            raise BookingMetadataValidationError(
                "Snapfix cannot have an Other origin description"
            )

        return

    if work_origin == "Other":
        # Other requires a meaningful description.
        if (
            type(other_origin_description) is not str
            or not other_origin_description.strip()
            or other_origin_description != other_origin_description.strip()
        ):
            raise BookingMetadataValidationError(
                "Other requires a valid origin description"
            )

        # Other must not retain a Snapfix external reference.
        if external_reference is not None and (
            type(external_reference) is not str
            or external_reference != ""
        ):
            raise BookingMetadataValidationError(
                "Other cannot have an external reference"
            )

        return

    if work_origin != "Direct / Ad-hoc":
        raise BookingMetadataValidationError(
            "Unsupported Work Origin"
        )

    # Direct work must not retain metadata from another origin.
    for value in (external_reference, other_origin_description):
        if value is not None and (
            type(value) is not str or value != ""
        ):
            raise BookingMetadataValidationError(
                "Direct work cannot have external origin metadata"
            )

def normalize_emergency(value) -> int:
    """Normalize an explicit Emergency Check to integer 0 or 1."""

    if type(value) is bool:
        return int(value)

    if type(value) is int and value in (0, 1):
        return value

    raise BookingMetadataValidationError(
        "Emergency must be explicitly supplied as 0 or 1"
    )
