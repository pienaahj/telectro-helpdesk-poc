"""Private Frappe evidence collector for the Phase 2 activation policy.

This module does not authorize bookings, own transactions, or activate hooks.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from telephony.time_booking_activation_policy import (
    ACTIVE_RUNTIME,
    PRE_ACTIVATION,
    ActivationConfigurationError,
    ActivationConfigurationSnapshot,
    ConfigurationCategory,
    HookBinding,
    validate_activation_configuration,
)


_LIFECYCLE_EVENT_ORDER = (
    "before_insert",
    "before_validate",
    "before_save",
    "before_submit",
    "before_cancel",
    "before_update_after_submit",
    "before_change",
)
_INSERT_EVENT_ORDER = (
    "before_insert",
    "before_naming",
    "autoname",
    "before_validate",
    "validate",
    "before_save",
    "after_insert",
    "on_update",
    "on_change",
)
_SERVER_SCRIPT_TYPES = (
    "DocType Event",
    "Scheduler Event",
    "Permission Query",
    "API",
)
_CATEGORY_SPECS = (
    ("notification", "Notification", {"document_type": "Timesheet"}, "enabled", 1),
    ("webhook", "Webhook", {"webhook_doctype": "Timesheet"}, "enabled", 1),
    ("server_script", "Server Script", {"reference_doctype": "Timesheet"}, "disabled", 0),
    ("workflow", "Workflow", {"document_type": "Timesheet"}, "is_active", 1),
    ("assignment_rule", "Assignment Rule", {"document_type": "Timesheet"}, "disabled", 0),
    ("energy_point_rule", "Energy Point Rule", {"reference_doctype": "Timesheet"}, "enabled", 1),
    ("milestone_tracker", "Milestone Tracker", {"document_type": "Timesheet"}, "disabled", 0),
)


@dataclass(frozen=True, slots=True)
class _Dependencies:
    frappe: object
    get_controller: object
    load_meta: object
    get_search_classes: object
    sqlite_base: type
    native_controller: type
    managed_controller: type


def _load_dependencies() -> _Dependencies:
    import frappe
    from erpnext.projects.doctype.timesheet.timesheet import Timesheet
    from frappe.model.base_document import get_controller
    from frappe.model.meta import load_meta
    from frappe.search.sqlite_search import SQLiteSearch, get_search_classes
    from telephony.time_booking_timesheet_controller import TelectroBookingTimesheet

    return _Dependencies(
        frappe=frappe,
        get_controller=get_controller,
        load_meta=load_meta,
        get_search_classes=get_search_classes,
        sqlite_base=SQLiteSearch,
        native_controller=Timesheet,
        managed_controller=TelectroBookingTimesheet,
    )


def _collect_activation_configuration(
    *, mode: str,
) -> ActivationConfigurationSnapshot:
    """Collect a complete fresh snapshot or raise the generic policy denial."""
    try:
        return _collect(mode=mode, dependencies=_load_dependencies())
    except ActivationConfigurationError:
        raise
    except Exception as exc:
        raise ActivationConfigurationError() from exc


def _require_activation_configuration(*, mode: str) -> None:
    """Collect and immediately enforce the existing pure invariant."""
    try:
        snapshot = _collect_activation_configuration(mode=mode)
        validate_activation_configuration(snapshot, mode=mode)
    except ActivationConfigurationError:
        raise
    except Exception as exc:
        raise ActivationConfigurationError() from exc


def _collect(*, mode: str, dependencies: _Dependencies) -> ActivationConfigurationSnapshot:
    if type(mode) is not str or mode not in (PRE_ACTIVATION, ACTIVE_RUNTIME):
        raise ActivationConfigurationError()

    controller, extensions = _collect_controller(dependencies, mode)
    timesheet_hooks, wildcard_hooks = _collect_hooks(dependencies.frappe)
    categories = _collect_categories(dependencies.frappe)
    attachments = _collect_attachments(dependencies.load_meta)
    sqlite = _collect_sqlite(dependencies)

    return ActivationConfigurationSnapshot(
        controller=controller,
        controller_extensions=extensions,
        timesheet_hooks=timesheet_hooks,
        wildcard_hooks=wildcard_hooks,
        configuration_categories=categories,
        attachment_fields=attachments,
        sqlite_search_integrations=sqlite,
    )


def _collect_controller(dependencies: _Dependencies, mode: str) -> tuple[str, tuple[str, ...]]:
    controller = dependencies.get_controller("Timesheet")
    if not isinstance(controller, type):
        raise ActivationConfigurationError()
    path = _class_path(controller)
    overrides = _hook_declarations(dependencies.frappe, "override_doctype_class")
    extensions = _hook_declarations(dependencies.frappe, "extend_doctype_class")

    if mode == PRE_ACTIVATION:
        if overrides or controller is not dependencies.native_controller:
            raise ActivationConfigurationError()
    elif (
        len(overrides) != 1
        or overrides[0] != path
        or controller is not dependencies.managed_controller
        or not issubclass(controller, dependencies.native_controller)
    ):
        raise ActivationConfigurationError()
    return path, extensions


def _hook_declarations(frappe, hook: str) -> tuple[str, ...]:
    hooks = frappe.get_hooks(hook, {})
    if not isinstance(hooks, Mapping):
        raise ActivationConfigurationError()
    values = hooks.get("Timesheet", ())
    return _strings(values)


def _collect_hooks(frappe) -> tuple[tuple[HookBinding, ...], tuple[HookBinding, ...]]:
    hooks = frappe.get_doc_hooks()
    if not isinstance(hooks, Mapping):
        raise ActivationConfigurationError()
    timesheet = _event_map(hooks.get("Timesheet", {}))
    wildcard = _event_map(hooks.get("*", {}))

    ordered = [event for event in _LIFECYCLE_EVENT_ORDER if event in timesheet]
    ordered.extend(sorted(set(timesheet) - set(ordered)))
    timesheet_bindings = tuple(HookBinding(event, timesheet[event]) for event in ordered)
    wildcard_bindings = tuple(
        HookBinding(event, wildcard[event])
        for event in _INSERT_EVENT_ORDER
        if event in wildcard
    )
    return timesheet_bindings, wildcard_bindings


def _event_map(value) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        raise ActivationConfigurationError()
    result = {}
    for event, handlers in value.items():
        if type(event) is not str or not event.strip() or event in result:
            raise ActivationConfigurationError()
        normalized = _strings(handlers)
        if normalized:
            result[event] = normalized
    return result


def _collect_categories(frappe) -> tuple[ConfigurationCategory, ...]:
    result = []
    for category, doctype, filters, status_field, active_value in _CATEGORY_SPECS:
        fields = [status_field]
        if category == "server_script":
            fields.insert(0, "script_type")
        rows = frappe.get_all(
            doctype,
            filters=filters,
            fields=fields,
            order_by="name asc",
            limit_page_length=0,
        )
        if type(rows) is not list:
            raise ActivationConfigurationError()
        enabled = disabled = 0
        for row in rows:
            if not isinstance(row, Mapping):
                raise ActivationConfigurationError()
            if category == "server_script":
                script_type = row.get("script_type")
                if type(script_type) is not str or script_type not in _SERVER_SCRIPT_TYPES:
                    raise ActivationConfigurationError()
                if script_type != "DocType Event":
                    raise ActivationConfigurationError()
            if status_field not in row:
                raise ActivationConfigurationError()
            status = row[status_field]
            if type(status) is not int or status not in (0, 1):
                raise ActivationConfigurationError()
            if status == active_value:
                enabled += 1
            else:
                disabled += 1
        result.append(ConfigurationCategory(category, enabled, disabled))
    return tuple(result)


def _collect_attachments(load_meta) -> tuple[str, ...]:
    meta = load_meta("Timesheet")
    fields = getattr(meta, "fields", None)
    if type(fields) is not list:
        raise ActivationConfigurationError()
    seen = set()
    attachments = []
    for field in fields:
        fieldname = _field_value(field, "fieldname")
        fieldtype = _field_value(field, "fieldtype")
        if (
            type(fieldname) is not str
            or not fieldname.strip()
            or type(fieldtype) is not str
            or not fieldtype.strip()
            or fieldname in seen
        ):
            raise ActivationConfigurationError()
        seen.add(fieldname)
        if fieldtype in ("Attach", "Attach Image"):
            attachments.append(fieldname)
    return tuple(attachments)


def _collect_sqlite(dependencies: _Dependencies) -> tuple[str, ...]:
    classes = dependencies.get_search_classes()
    if type(classes) is not list:
        raise ActivationConfigurationError()
    integrations = []
    seen = set()
    for search_class in classes:
        if (
            not isinstance(search_class, type)
            or not issubclass(search_class, dependencies.sqlite_base)
            or search_class.__init__ is not dependencies.sqlite_base.__init__
            or search_class._build_doc_configs is not dependencies.sqlite_base._build_doc_configs
        ):
            raise ActivationConfigurationError()
        path = _class_path(search_class)
        if path in seen:
            raise ActivationConfigurationError()
        seen.add(path)
        config = getattr(search_class, "INDEXABLE_DOCTYPES", None)
        if type(config) is not dict:
            raise ActivationConfigurationError()
        for doctype, settings in config.items():
            if type(doctype) is not str or not doctype.strip() or not isinstance(settings, Mapping):
                raise ActivationConfigurationError()
        if "Timesheet" in config:
            integrations.append(path)
    return tuple(integrations)


def _field_value(field, name: str):
    if isinstance(field, Mapping):
        if name not in field:
            raise ActivationConfigurationError()
        return field[name]
    if not hasattr(field, name):
        raise ActivationConfigurationError()
    return getattr(field, name)


def _class_path(value: type) -> str:
    module = getattr(value, "__module__", None)
    qualname = getattr(value, "__qualname__", None)
    if type(module) is not str or not module.strip() or type(qualname) is not str or not qualname.strip():
        raise ActivationConfigurationError()
    return f"{module}.{qualname}"


def _strings(values) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ActivationConfigurationError()
    result = []
    seen = set()
    for value in values:
        if type(value) is not str or not value.strip() or value in seen:
            raise ActivationConfigurationError()
        seen.add(value)
        result.append(value)
    return tuple(result)
