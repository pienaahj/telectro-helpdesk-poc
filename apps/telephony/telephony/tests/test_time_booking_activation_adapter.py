import dataclasses
import types
import unittest
from unittest.mock import patch

from telephony.time_booking_activation_adapter import (
    _Dependencies,
    _collect_activation_configuration,
    _require_activation_configuration,
)
from telephony.time_booking_activation_policy import (
    ACTIVE_RUNTIME,
    PRE_ACTIVATION,
    ActivationConfigurationError,
    validate_activation_configuration,
)


class NativeTimesheet:
    pass


NativeTimesheet.__module__ = "erpnext.projects.doctype.timesheet.timesheet"
NativeTimesheet.__qualname__ = "Timesheet"


class ManagedTimesheet(NativeTimesheet):
    pass


ManagedTimesheet.__module__ = "telephony.time_booking_timesheet_controller"
ManagedTimesheet.__qualname__ = "TelectroBookingTimesheet"


class SQLiteBase:
    def _build_doc_configs(self):
        pass


class HelpdeskSearch(SQLiteBase):
    INDEXABLE_DOCTYPES = {"HD Ticket": {"fields": ["name"]}}


HelpdeskSearch.__module__ = "helpdesk.search_sqlite"
HelpdeskSearch.__qualname__ = "HelpdeskSearch"


WILDCARD = {
    "validate": [
        "erpnext.support.doctype.service_level_agreement.service_level_agreement.apply",
        "erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record."
        "check_for_running_deletion_job",
    ],
    "on_update": [
        "frappe.desk.notifications.clear_doctype_notifications",
        "frappe.workflow.doctype.workflow_action.workflow_action.process_workflow_actions",
        "frappe.core.doctype.file.utils.attach_files_to_document",
        "frappe.automation.doctype.assignment_rule.assignment_rule.apply",
        "frappe.automation.doctype.assignment_rule.assignment_rule.update_due_date",
        "frappe.core.doctype.user_type.user_type.apply_permissions_for_non_standard_user_type",
        "frappe.search.sqlite_search.update_doc_index",
    ],
    "on_change": [
        "frappe.social.doctype.energy_point_rule.energy_point_rule.process_energy_points",
        "frappe.automation.doctype.milestone_tracker.milestone_tracker.evaluate_milestone",
    ],
}
LIFECYCLE = "telephony.time_booking_provenance_lifecycle._validate_timesheet_provenance"
LIFECYCLE_EVENTS = (
    "before_insert", "before_validate", "before_save", "before_submit",
    "before_cancel", "before_update_after_submit", "before_change",
)


class FakeFrappe:
    def __init__(self):
        self.rows = {
            "Notification": [], "Webhook": [], "Server Script": [],
            "Workflow": [], "Assignment Rule": [], "Energy Point Rule": [],
            "Milestone Tracker": [],
        }
        self.hooks = {"override_doctype_class": {}, "extend_doctype_class": {}}
        self.doc_hooks = {
            "Timesheet": {},
            "*": {event: list(handlers) for event, handlers in WILDCARD.items()},
        }
        self.calls = []

    def get_hooks(self, hook, default):
        return self.hooks.get(hook, default)

    def get_doc_hooks(self):
        return self.doc_hooks

    def get_all(self, doctype, **kwargs):
        self.calls.append((doctype, kwargs))
        value = self.rows[doctype]
        if isinstance(value, BaseException):
            raise value
        return value


def field(name, fieldtype="Data"):
    return types.SimpleNamespace(fieldname=name, fieldtype=fieldtype)


class Harness:
    def __init__(self, mode=PRE_ACTIVATION):
        self.mode = mode
        self.frappe = FakeFrappe()
        self.controller = NativeTimesheet
        self.meta = types.SimpleNamespace(fields=[field("name")])
        self.search_classes = [HelpdeskSearch]
        if mode == ACTIVE_RUNTIME:
            self.controller = ManagedTimesheet
            path = "telephony.time_booking_timesheet_controller.TelectroBookingTimesheet"
            self.frappe.hooks["override_doctype_class"] = {"Timesheet": [path]}
            self.frappe.doc_hooks["Timesheet"] = {
                event: [LIFECYCLE] for event in LIFECYCLE_EVENTS
            }

    def dependencies(self):
        return _Dependencies(
            frappe=self.frappe,
            get_controller=lambda doctype: self.controller,
            load_meta=lambda doctype: self.meta,
            get_search_classes=lambda: self.search_classes,
            sqlite_base=SQLiteBase,
            native_controller=NativeTimesheet,
            managed_controller=ManagedTimesheet,
        )

    def collect(self):
        with patch(
            "telephony.time_booking_activation_adapter._load_dependencies",
            return_value=self.dependencies(),
        ):
            return _collect_activation_configuration(mode=self.mode)


class TestTrustedActivationCollector(unittest.TestCase):
    def assert_denied(self, harness):
        with self.assertRaisesRegex(
            ActivationConfigurationError,
            r"^Managed time booking is not available\.$",
        ):
            harness.collect()

    def test_valid_pre_activation_collection(self):
        snapshot = Harness().collect()
        self.assertIsNone(validate_activation_configuration(snapshot, mode=PRE_ACTIVATION))
        self.assertEqual(snapshot.controller, "erpnext.projects.doctype.timesheet.timesheet.Timesheet")

    def test_valid_active_runtime_collection(self):
        harness = Harness(ACTIVE_RUNTIME)
        snapshot = harness.collect()
        self.assertIsNone(validate_activation_configuration(snapshot, mode=ACTIVE_RUNTIME))
        self.assertEqual(tuple(item.event for item in snapshot.timesheet_hooks), LIFECYCLE_EVENTS)

    def test_require_collects_and_validates(self):
        harness = Harness()
        with patch("telephony.time_booking_activation_adapter._load_dependencies", return_value=harness.dependencies()):
            self.assertIsNone(_require_activation_configuration(mode=PRE_ACTIVATION))

    def test_exact_seven_category_order_and_queries(self):
        harness = Harness()
        snapshot = harness.collect()
        self.assertEqual(
            tuple(item.category for item in snapshot.configuration_categories),
            ("notification", "webhook", "server_script", "workflow", "assignment_rule", "energy_point_rule", "milestone_tracker"),
        )
        expected = (
            ("Notification", {"document_type": "Timesheet"}, ["enabled"]),
            ("Webhook", {"webhook_doctype": "Timesheet"}, ["enabled"]),
            ("Server Script", {"reference_doctype": "Timesheet"}, ["script_type", "disabled"]),
            ("Workflow", {"document_type": "Timesheet"}, ["is_active"]),
            ("Assignment Rule", {"document_type": "Timesheet"}, ["disabled"]),
            ("Energy Point Rule", {"reference_doctype": "Timesheet"}, ["enabled"]),
            ("Milestone Tracker", {"document_type": "Timesheet"}, ["disabled"]),
        )
        self.assertEqual(len(harness.frappe.calls), len(expected))
        for (doctype, arguments), (expected_doctype, filters, fields) in zip(
            harness.frappe.calls, expected, strict=True
        ):
            self.assertEqual(doctype, expected_doctype)
            self.assertEqual(arguments["filters"], filters)
            self.assertEqual(arguments["fields"], fields)
            self.assertEqual(arguments["order_by"], "name asc")
            self.assertEqual(arguments["limit_page_length"], 0)

    def test_enabled_and_disabled_status_interpretation(self):
        harness = Harness()
        harness.frappe.rows["Notification"] = [{"enabled": 1}, {"enabled": 0}]
        harness.frappe.rows["Assignment Rule"] = [{"disabled": 0}, {"disabled": 1}]
        snapshot = harness.collect()
        values = {item.category: (item.enabled_count, item.disabled_count) for item in snapshot.configuration_categories}
        self.assertEqual(values["notification"], (1, 1))
        self.assertEqual(values["assignment_rule"], (1, 1))

    def test_zero_rows_are_complete_evidence(self):
        snapshot = Harness().collect()
        self.assertTrue(all((item.enabled_count, item.disabled_count) == (0, 0) for item in snapshot.configuration_categories))

    def test_failed_query_never_becomes_zero(self):
        harness = Harness()
        harness.frappe.rows["Workflow"] = RuntimeError("private detail")
        self.assert_denied(harness)

    def test_malformed_missing_and_unsupported_statuses(self):
        for value in (None, True, "0", 2):
            with self.subTest(value=value):
                harness = Harness()
                harness.frappe.rows["Notification"] = [{"enabled": value}]
                self.assert_denied(harness)
        harness = Harness()
        harness.frappe.rows["Notification"] = [{}]
        self.assert_denied(harness)

    def test_server_script_doc_event_is_classified(self):
        harness = Harness()
        harness.frappe.rows["Server Script"] = [{"script_type": "DocType Event", "disabled": 0}]
        snapshot = harness.collect()
        item = snapshot.configuration_categories[2]
        self.assertEqual((item.enabled_count, item.disabled_count), (1, 0))

    def test_unexpected_server_script_type_is_denied(self):
        for value in (None, "Unknown", "Permission Query"):
            with self.subTest(value=value):
                harness = Harness()
                harness.frappe.rows["Server Script"] = [{"script_type": value, "disabled": 0}]
                self.assert_denied(harness)

    def test_all_insertion_wildcard_events_are_examined_in_order(self):
        event_order = (
            "before_insert", "before_naming", "autoname", "before_validate",
            "validate", "before_save", "after_insert", "on_update", "on_change",
        )
        for event in event_order:
            with self.subTest(event=event):
                harness = Harness()
                handler = f"example.{event}"
                harness.frappe.doc_hooks["*"].setdefault(event, []).append(handler)
                snapshot = harness.collect()
                bindings = {item.event: item.handlers for item in snapshot.wildcard_hooks}
                self.assertIn(event, bindings)
                self.assertEqual(bindings[event][-1], handler)
                self.assertEqual(
                    tuple(item.event for item in snapshot.wildcard_hooks),
                    tuple(name for name in event_order if name in bindings),
                )

    def test_hook_handler_order_is_preserved(self):
        harness = Harness()
        snapshot = harness.collect()
        self.assertEqual(snapshot.wildcard_hooks[0].handlers, tuple(WILDCARD["validate"]))

    def test_unexpected_timesheet_hook_remains_visible(self):
        harness = Harness()
        harness.frappe.doc_hooks["Timesheet"] = {"after_insert": ["example.handler"]}
        snapshot = harness.collect()
        self.assertEqual(snapshot.timesheet_hooks[0].event, "after_insert")
        with self.assertRaises(ActivationConfigurationError):
            validate_activation_configuration(snapshot, mode=PRE_ACTIVATION)

    def test_malformed_hook_structures_are_denied(self):
        for value in ([], {"validate": "handler"}, {1: ["handler"]}):
            with self.subTest(value=value):
                harness = Harness()
                harness.frappe.doc_hooks["*"] = value
                self.assert_denied(harness)

    def test_controller_override_ambiguity_is_denied(self):
        harness = Harness(ACTIVE_RUNTIME)
        path = harness.frappe.hooks["override_doctype_class"]["Timesheet"][0]
        harness.frappe.hooks["override_doctype_class"]["Timesheet"] = ["old.Controller", path]
        self.assert_denied(harness)

    def test_controller_override_mismatch_is_denied(self):
        harness = Harness(ACTIVE_RUNTIME)
        harness.frappe.hooks["override_doctype_class"] = {"Timesheet": ["wrong.Controller"]}
        self.assert_denied(harness)

    def test_managed_controller_must_inherit_native(self):
        harness = Harness(ACTIVE_RUNTIME)
        class Unrelated:
            pass
        Unrelated.__module__ = ManagedTimesheet.__module__
        Unrelated.__qualname__ = ManagedTimesheet.__qualname__
        harness.controller = Unrelated
        harness_deps = dataclasses.replace(harness.dependencies(), managed_controller=Unrelated)
        with patch("telephony.time_booking_activation_adapter._load_dependencies", return_value=harness_deps):
            with self.assertRaises(ActivationConfigurationError):
                _collect_activation_configuration(mode=ACTIVE_RUNTIME)

    def test_controller_extensions_are_collected_for_policy_denial(self):
        harness = Harness()
        harness.frappe.hooks["extend_doctype_class"] = {"Timesheet": ["example.Mixin"]}
        snapshot = harness.collect()
        self.assertEqual(snapshot.controller_extensions, ("example.Mixin",))
        with self.assertRaises(ActivationConfigurationError):
            validate_activation_configuration(snapshot, mode=PRE_ACTIVATION)

    def test_fresh_metadata_extracts_both_attachment_types(self):
        harness = Harness()
        harness.meta.fields = [field("name"), field("file", "Attach"), field("image", "Attach Image")]
        snapshot = harness.collect()
        self.assertEqual(snapshot.attachment_fields, ("file", "image"))

    def test_duplicate_or_malformed_metadata_is_denied(self):
        for fields in ([field("same"), field("same")], [field("", "Data")], [types.SimpleNamespace(fieldname="x")]):
            with self.subTest(fields=fields):
                harness = Harness()
                harness.meta.fields = fields
                self.assert_denied(harness)

    def test_sqlite_timesheet_applicability_is_collected(self):
        harness = Harness()
        class TimesheetSearch(SQLiteBase):
            INDEXABLE_DOCTYPES = {"Timesheet": {"fields": ["name"]}}
        TimesheetSearch.__module__ = "example.search"
        TimesheetSearch.__qualname__ = "TimesheetSearch"
        harness.search_classes = [TimesheetSearch]
        self.assertEqual(harness.collect().sqlite_search_integrations, ("example.search.TimesheetSearch",))

    def test_sqlite_overridden_initializer_is_denied_without_instantiation(self):
        class RuntimeMutationSearch(SQLiteBase):
            INDEXABLE_DOCTYPES = {"HD Ticket": {"fields": ["name"]}}
            initialized = False

            def __init__(self):
                type(self).initialized = True
                self.doc_configs = {"Timesheet": {"fields": ["name"]}}

        harness = Harness()
        harness.search_classes = [RuntimeMutationSearch]
        self.assert_denied(harness)
        self.assertFalse(RuntimeMutationSearch.initialized)

    def test_sqlite_inherited_initializer_remains_accepted(self):
        harness = Harness()
        harness.search_classes = [HelpdeskSearch]
        snapshot = harness.collect()
        self.assertEqual(snapshot.sqlite_search_integrations, ())

    def test_malformed_or_ambiguous_sqlite_configuration_is_denied(self):
        class Missing(SQLiteBase):
            pass
        class Override(SQLiteBase):
            INDEXABLE_DOCTYPES = {}
            def _build_doc_configs(self):
                return {}
        for search in (Missing, Override, object):
            with self.subTest(search=search):
                harness = Harness()
                harness.search_classes = [search]
                self.assert_denied(harness)

    def test_partial_collection_never_returns_snapshot(self):
        harness = Harness()
        harness.meta = RuntimeError("not metadata")
        dependencies = dataclasses.replace(harness.dependencies(), load_meta=lambda doctype: (_ for _ in ()).throw(RuntimeError("failed")))
        with patch("telephony.time_booking_activation_adapter._load_dependencies", return_value=dependencies):
            with self.assertRaises(ActivationConfigurationError):
                _collect_activation_configuration(mode=PRE_ACTIVATION)

    def test_infrastructure_error_is_generic_and_chained(self):
        harness = Harness()
        error = RuntimeError("sensitive configuration detail")
        harness.frappe.rows["Webhook"] = error
        try:
            harness.collect()
        except ActivationConfigurationError as exc:
            self.assertEqual(str(exc), "Managed time booking is not available.")
            self.assertIs(exc.__cause__, error)
        else:
            self.fail("collection unexpectedly succeeded")

    def test_invalid_mode_is_denied_before_collection(self):
        harness = Harness()
        with patch("telephony.time_booking_activation_adapter._load_dependencies", return_value=harness.dependencies()):
            with self.assertRaises(ActivationConfigurationError):
                _collect_activation_configuration(mode="client-choice")


if __name__ == "__main__":
    unittest.main()
