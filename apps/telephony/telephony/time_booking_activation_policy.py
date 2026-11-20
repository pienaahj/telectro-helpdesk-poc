"""Pure activation invariant for managed Phase 2 Timesheet booking.

Passing this policy establishes configuration compatibility only. It does not
establish transaction ownership, authorize a booking, or guarantee rollback of
external effects. Those duties belong to the future trusted booking service.
"""

from dataclasses import dataclass


PRE_ACTIVATION = "pre_activation"
ACTIVE_RUNTIME = "active_runtime"

_NATIVE_TIMESHEET_CONTROLLER = (
    "erpnext.projects.doctype.timesheet.timesheet.Timesheet"
)
_MANAGED_TIMESHEET_CONTROLLER = (
    "telephony.time_booking_timesheet_controller.TelectroBookingTimesheet"
)
_LIFECYCLE_HANDLER = (
    "telephony.time_booking_provenance_lifecycle._validate_timesheet_provenance"
)

_CONFIGURATION_CATEGORIES = (
    "notification",
    "webhook",
    "server_script",
    "workflow",
    "assignment_rule",
    "energy_point_rule",
    "milestone_tracker",
)


@dataclass(frozen=True, slots=True)
class HookBinding:
    """Ordered effective handlers for one document event."""

    event: str
    handlers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfigurationCategory:
    """Complete enabled/disabled record counts for one prohibited category."""

    category: str
    enabled_count: int
    disabled_count: int


@dataclass(frozen=True, slots=True)
class ActivationConfigurationSnapshot:
    """Complete, collector-supplied Timesheet activation evidence.

    Attachment and SQLite values contain only integrations applicable to
    Timesheet. Empty tuples therefore mean that complete inspection found none.
    """

    controller: str
    controller_extensions: tuple[str, ...]
    timesheet_hooks: tuple[HookBinding, ...]
    wildcard_hooks: tuple[HookBinding, ...]
    configuration_categories: tuple[ConfigurationCategory, ...]
    attachment_fields: tuple[str, ...]
    sqlite_search_integrations: tuple[str, ...]


class ActivationConfigurationError(PermissionError):
    """Generic fail-closed activation-policy failure."""

    def __init__(self):
        super().__init__("Managed time booking is not available.")


_APPROVED_WILDCARD_HOOKS = (
    HookBinding(
        "validate",
        (
            "erpnext.support.doctype.service_level_agreement."
            "service_level_agreement.apply",
            "erpnext.setup.doctype.transaction_deletion_record."
            "transaction_deletion_record.check_for_running_deletion_job",
        ),
    ),
    HookBinding(
        "on_update",
        (
            "frappe.desk.notifications.clear_doctype_notifications",
            "frappe.workflow.doctype.workflow_action.workflow_action."
            "process_workflow_actions",
            "frappe.core.doctype.file.utils.attach_files_to_document",
            "frappe.automation.doctype.assignment_rule.assignment_rule.apply",
            "frappe.automation.doctype.assignment_rule.assignment_rule."
            "update_due_date",
            "frappe.core.doctype.user_type.user_type."
            "apply_permissions_for_non_standard_user_type",
            "frappe.search.sqlite_search.update_doc_index",
        ),
    ),
    HookBinding(
        "on_change",
        (
            "frappe.social.doctype.energy_point_rule.energy_point_rule."
            "process_energy_points",
            "frappe.automation.doctype.milestone_tracker.milestone_tracker."
            "evaluate_milestone",
        ),
    ),
)

_APPROVED_RUNTIME_TIMESHEET_HOOKS = tuple(
    HookBinding(event, (_LIFECYCLE_HANDLER,))
    for event in (
        "before_insert",
        "before_validate",
        "before_save",
        "before_submit",
        "before_cancel",
        "before_update_after_submit",
        "before_change",
    )
)


def validate_activation_configuration(
    snapshot: ActivationConfigurationSnapshot,
    *,
    mode: str,
) -> None:
    """Validate a complete snapshot for inspection or active enforcement.

    ``pre_activation`` requires the reviewed native, unregistered state.
    ``active_runtime`` requires the exact approved controller and lifecycle
    handlers. Success says nothing about transaction ownership or authorization.
    """
    if type(snapshot) is not ActivationConfigurationSnapshot:
        raise ActivationConfigurationError()
    if type(mode) is not str or mode not in (PRE_ACTIVATION, ACTIVE_RUNTIME):
        raise ActivationConfigurationError()

    _validate_snapshot_shape(snapshot)

    if mode == PRE_ACTIVATION:
        expected_controller = _NATIVE_TIMESHEET_CONTROLLER
        expected_timesheet_hooks = ()
    else:
        expected_controller = _MANAGED_TIMESHEET_CONTROLLER
        expected_timesheet_hooks = _APPROVED_RUNTIME_TIMESHEET_HOOKS

    if (
        snapshot.controller != expected_controller
        or snapshot.controller_extensions
        or snapshot.timesheet_hooks != expected_timesheet_hooks
        or snapshot.wildcard_hooks != _APPROVED_WILDCARD_HOOKS
        or snapshot.attachment_fields
        or snapshot.sqlite_search_integrations
    ):
        raise ActivationConfigurationError()

    categories = {item.category: item for item in snapshot.configuration_categories}
    if tuple(sorted(categories)) != tuple(sorted(_CONFIGURATION_CATEGORIES)):
        raise ActivationConfigurationError()
    if any(item.enabled_count != 0 for item in categories.values()):
        raise ActivationConfigurationError()


def _validate_snapshot_shape(snapshot: ActivationConfigurationSnapshot) -> None:
    if type(snapshot.controller) is not str or not snapshot.controller.strip():
        raise ActivationConfigurationError()
    _validate_strings(snapshot.controller_extensions)
    _validate_hooks(snapshot.timesheet_hooks)
    _validate_hooks(snapshot.wildcard_hooks)
    _validate_strings(snapshot.attachment_fields)
    _validate_strings(snapshot.sqlite_search_integrations)

    items = snapshot.configuration_categories
    if type(items) is not tuple or any(
        type(item) is not ConfigurationCategory for item in items
    ):
        raise ActivationConfigurationError()
    seen = set()
    for item in items:
        if (
            type(item.category) is not str
            or not item.category.strip()
            or type(item.enabled_count) is not int
            or type(item.disabled_count) is not int
            or item.enabled_count < 0
            or item.disabled_count < 0
            or item.category in seen
        ):
            raise ActivationConfigurationError()
        seen.add(item.category)


def _validate_hooks(bindings: tuple[HookBinding, ...]) -> None:
    if type(bindings) is not tuple or any(
        type(binding) is not HookBinding for binding in bindings
    ):
        raise ActivationConfigurationError()
    seen = set()
    for binding in bindings:
        if (
            type(binding.event) is not str
            or not binding.event.strip()
            or binding.event in seen
        ):
            raise ActivationConfigurationError()
        _validate_strings(binding.handlers)
        if not binding.handlers:
            raise ActivationConfigurationError()
        seen.add(binding.event)


def _validate_strings(values: tuple[str, ...]) -> None:
    if type(values) is not tuple:
        raise ActivationConfigurationError()
    seen = set()
    for value in values:
        if type(value) is not str or not value.strip() or value in seen:
            raise ActivationConfigurationError()
        seen.add(value)
