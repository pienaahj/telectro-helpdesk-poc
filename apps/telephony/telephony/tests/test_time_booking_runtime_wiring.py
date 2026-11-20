"""No-site registration and managed-only activation guard checks."""

from contextlib import contextmanager
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from erpnext.projects.doctype.timesheet.timesheet import Timesheet
from telephony.time_booking_activation_adapter import (
    _Dependencies, _collect_controller, _collect_hooks,
)
from telephony.time_booking_activation_policy import (
    ACTIVE_RUNTIME, PRE_ACTIVATION, ActivationConfigurationError,
    ActivationConfigurationSnapshot, ConfigurationCategory,
    _APPROVED_WILDCARD_HOOKS, _CONFIGURATION_CATEGORIES,
    validate_activation_configuration,
)
from telephony.time_booking_provenance import BookingProvenanceError
from telephony.time_booking_timesheet_controller import TelectroBookingTimesheet


ROOT = Path(__file__).resolve().parents[1]
HANDLER = "telephony.time_booking_provenance_lifecycle._validate_timesheet_provenance"
EVENTS = ("before_insert", "before_validate", "before_save", "before_submit",
          "before_cancel", "before_update_after_submit", "before_change")


class TestRuntimeWiring(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType("frappe")
        self.frappe.conf = {}
        module_patch = patch.dict(sys.modules, {"frappe": self.frappe})
        module_patch.start()
        self.addCleanup(module_patch.stop)
        self.hooks = runpy.run_path(str(ROOT / "hooks.py"))

    def fake_frappe(self):
        hooks = self.hooks
        wildcard = {binding.event: list(binding.handlers) for binding in _APPROVED_WILDCARD_HOOKS}
        return types.SimpleNamespace(
            get_hooks=lambda key, default=None: {
                name: [value] if isinstance(value, str) else value
                for name, value in hooks.get(key, default).items()
            },
            get_doc_hooks=lambda: {"Timesheet": {
                event: [handler] for event, handler in hooks["doc_events"]["Timesheet"].items()
            }, "*": wildcard},
        )

    def test_exact_controller_and_lifecycle_declarations(self):
        self.assertEqual(self.hooks["override_doctype_class"]["Timesheet"],
                         "telephony.time_booking_timesheet_controller.TelectroBookingTimesheet")
        self.assertEqual(list(self.hooks["doc_events"]["Timesheet"]), list(EVENTS))
        self.assertEqual(list(self.hooks["doc_events"]["Timesheet"].values()), [HANDLER]*7)
        self.assertNotIn("Timesheet", self.hooks.get("extend_doctype_class", {}))

    def test_activation_collector_recognizes_source_wiring(self):
        fake = self.fake_frappe()
        deps = _Dependencies(fake, lambda doctype: TelectroBookingTimesheet,
                             lambda doctype: None, lambda: [], object,
                             Timesheet, TelectroBookingTimesheet)
        controller, extensions = _collect_controller(deps, ACTIVE_RUNTIME)
        timesheet_hooks, wildcard_hooks = _collect_hooks(fake)
        snapshot = ActivationConfigurationSnapshot(
            controller=controller, controller_extensions=extensions,
            timesheet_hooks=timesheet_hooks, wildcard_hooks=wildcard_hooks,
            configuration_categories=tuple(ConfigurationCategory(c, 0, 0) for c in _CONFIGURATION_CATEGORIES),
            attachment_fields=(), sqlite_search_integrations=(),
        )
        validate_activation_configuration(snapshot, mode=ACTIVE_RUNTIME)
        with self.assertRaises(ActivationConfigurationError):
            _collect_controller(deps, PRE_ACTIVATION)

    def test_incomplete_runtime_is_denied_by_contract(self):
        fake = self.fake_frappe()
        fake.get_doc_hooks = lambda: {"Timesheet": {}, "*": {}}
        deps = _Dependencies(fake, lambda doctype: TelectroBookingTimesheet,
                             lambda doctype: None, lambda: [], object,
                             Timesheet, TelectroBookingTimesheet)
        hooks, wildcard = _collect_hooks(fake)
        snapshot = ActivationConfigurationSnapshot(
            controller="telephony.time_booking_timesheet_controller.TelectroBookingTimesheet",
            controller_extensions=(), timesheet_hooks=hooks, wildcard_hooks=wildcard,
            configuration_categories=tuple(ConfigurationCategory(c, 0, 0) for c in _CONFIGURATION_CATEGORIES),
            attachment_fields=(), sqlite_search_integrations=(),
        )
        with self.assertRaises(ActivationConfigurationError):
            validate_activation_configuration(snapshot, mode=ACTIVE_RUNTIME)

    def test_unmanaged_insert_delegates_to_native(self):
        doc = TelectroBookingTimesheet.__new__(TelectroBookingTimesheet)
        frame = types.SimpleNamespace(identity=None)
        @contextmanager
        def attempt(document):
            yield frame
        with patch("telephony.time_booking_timesheet_controller._insertion_attempt", attempt), patch.object(
            Timesheet, "insert", return_value=doc
        ) as native:
            self.assertIs(doc.insert(), doc)
        native.assert_called_once()

    def test_managed_disabled_and_incomplete_fail_before_native_insert(self):
        doc = TelectroBookingTimesheet.__new__(TelectroBookingTimesheet)
        frame = types.SimpleNamespace(identity=object())
        @contextmanager
        def attempt(document):
            yield frame
        from telephony import time_booking_activation_adapter as adapter
        with patch("telephony.time_booking_timesheet_controller._insertion_attempt", attempt), patch.object(
                Timesheet, "insert", return_value=doc
            ) as native, patch.object(adapter, "_require_activation_configuration", side_effect=ActivationConfigurationError()) as require:
                self.frappe.conf = {}
                with self.assertRaises(BookingProvenanceError): doc.insert()
                require.assert_not_called()
                self.frappe.conf = {"telectro_time_booking_enabled": 1}
                with self.assertRaises(ActivationConfigurationError): doc.insert()
                native.assert_not_called()

    def test_existing_hook_maps_are_preserved(self):
        doc_events = {"Timesheet": {"before_insert": "existing.handler"},
                      "HD Ticket": {"validate": "existing.ticket"}}
        overrides = {"Timesheet": "existing.Controller", "Other": "existing.Other"}
        hooks = runpy.run_path(str(ROOT / "hooks.py"), init_globals={
            "doc_events": doc_events, "override_doctype_class": overrides,
        })
        self.assertEqual(hooks["doc_events"]["Timesheet"]["before_insert"], "existing.handler")
        self.assertEqual(hooks["override_doctype_class"]["Timesheet"], "existing.Controller")
        self.assertEqual(hooks["override_doctype_class"]["Other"], "existing.Other")
