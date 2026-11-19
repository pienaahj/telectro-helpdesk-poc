"""Pure reference-shape checks for time bookings.

Passing these checks does not establish authorization, customer consistency,
Project/Task membership, employee identity or native Timesheet validity.
"""

from collections.abc import Mapping


class WorkContextValidationError(ValueError):
    """A work context has missing or prohibited references."""


_RULES = {
    "Helpdesk": (("custom_hd_ticket",), ("project", "task")),
    "Project": (("project",), ("custom_hd_ticket",)),
    "Customer Support": (
        (), ("custom_hd_ticket", "project", "task")
    ),
    "Internal": (
        (), ("custom_hd_ticket", "custom_hd_customer", "project", "task")
    ),
}


def validate_work_context(
    row: Mapping[str, object], *, untouched_historical: bool = False
) -> None:
    """Validate reference shape without changing row or creating bookings.

    New/changed rows require a recognized context. Only a blank-context row
    independently established as untouched historical data may be skipped.
    This function cannot establish whether a row is historical and untouched.
    That decision belongs to a future trusted integration, never client input.
    Emergency, Activity Type and Description do not affect reference shape.
    Reference identities and membership must be checked separately.
    """
    if type(untouched_historical) is not bool:
        raise WorkContextValidationError("untouched_historical must be a bool")
    context = row.get("custom_work_context")
    blank = context is None or (
        isinstance(context, str) and not context.strip()
    )
    if blank:
        if untouched_historical:
            return
        raise WorkContextValidationError("custom_work_context is required")
    if not isinstance(context, str) or context not in _RULES:
        raise WorkContextValidationError("custom_work_context is not recognized")

    required, prohibited = _RULES[context]
    for field in ("custom_hd_ticket", "custom_hd_customer", "project", "task"):
        value = row.get(field)
        if value is not None and not isinstance(value, str):
            raise WorkContextValidationError(f"{field} must be a string or None")
    for field in (*required, *prohibited):
        value = row.get(field)
        present = isinstance(value, str) and bool(value.strip())
        if field in required and not present:
            raise WorkContextValidationError(f"{field} is required for {context}")
        if field in prohibited and present:
            raise WorkContextValidationError(f"{field} is prohibited for {context}")
    unlisted = row.get("custom_unlisted_customer_name")

    if unlisted is not None and not isinstance(unlisted, str):
        raise WorkContextValidationError(
            "custom_unlisted_customer_name must be a string or None"
        )

    unlisted_present = (
        isinstance(unlisted, str) and bool(unlisted.strip())
    )

    if context == "Customer Support":
        customer = row.get("custom_hd_customer")
        customer_present = (
            isinstance(customer, str) and bool(customer.strip())
        )

        if not customer_present and not unlisted_present:
            raise WorkContextValidationError(
                "custom_hd_customer or custom_unlisted_customer_name "
                "is required for Customer Support"
            )

        if customer_present and unlisted_present:
            raise WorkContextValidationError(
                "custom_hd_customer and custom_unlisted_customer_name "
                "are mutually exclusive"
            )

    elif unlisted_present:
        raise WorkContextValidationError(
            f"custom_unlisted_customer_name is prohibited for {context}"
        )
