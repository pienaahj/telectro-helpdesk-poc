"""Isolated wrapper tests: real class inheritance, mocked native insert, no site."""

import copy
import inspect
import unittest
from unittest.mock import patch

import frappe
from erpnext.projects.doctype.timesheet.timesheet import Timesheet

from telephony.time_booking_identity import TechnicianBookingIdentity
from telephony.time_booking_provenance import (
    BookingProvenanceError,
    validate_provenance_transition,
)
from telephony.time_booking_provenance_adapter import (
    _complete_insertion,
    _current_insertion,
    _phase2_creation_intent,
)
from telephony.time_booking_timesheet_controller import TelectroBookingTimesheet


class TestTimesheetInsertWrapper(unittest.TestCase):
    def setUp(self):
        self.assertFalse(getattr(frappe.local, "site", None))
        self.identity = TechnicianBookingIdentity("tech", "EMP", "Company")
        # Bypass Document construction/metadata loading, retaining its real get().
        self.document = object.__new__(TelectroBookingTimesheet)
        self.document.__dict__.update(
            doctype="Timesheet", name="TS", employee="EMP", company="Company",
            user="tech", docstatus=0, custom_telectro_booking_origin="Phase 2",
            flags=frappe._dict(),
        )

    def denied(self):
        return self.assertRaisesRegex(
            BookingProvenanceError, r"^Booking provenance is not permitted\.$"
        )

    def check(self, frame):
        return validate_provenance_transition(
            frame.view, persisted=None, identity=frame.identity
        )

    def test_actual_native_inheritance_and_only_insert_override(self):
        self.assertIs(TelectroBookingTimesheet.__bases__[0], Timesheet)
        self.assertEqual(Timesheet.__module__, "erpnext.projects.doctype.timesheet.timesheet")
        self.assertEqual(
            {k for k, v in TelectroBookingTimesheet.__dict__.items() if callable(v)},
            {"insert"},
        )
        self.assertFalse(getattr(frappe.local, "site", None))

    def test_exact_native_parameter_signature(self):
        actual = inspect.signature(TelectroBookingTimesheet.insert).parameters
        native = inspect.signature(Timesheet.insert).parameters
        self.assertEqual(actual, native)

    def test_all_explicit_arguments_forwarded_without_rewriting(self):
        values = [object() for _ in range(6)]
        expected = dict(zip(
            ["ignore_permissions", "ignore_links", "ignore_if_duplicate",
             "ignore_mandatory", "set_name", "set_child_names"], values
        ))
        returned = object()
        with patch.object(Timesheet, "insert", autospec=True, return_value=returned) as native:
            self.assertIs(self.document.insert(*values), returned)
            native.assert_called_once_with(self.document, **expected)
        self.assertIsNone(_current_insertion(self.document))

    def test_defaults_forwarded_and_native_return_preserved(self):
        returned = object()
        with patch.object(Timesheet, "insert", autospec=True, return_value=returned) as native:
            self.assertIs(self.document.insert(), returned)
            native.assert_called_once_with(
                self.document, ignore_permissions=None, ignore_links=None,
                ignore_if_duplicate=False, ignore_mandatory=None,
                set_name=None, set_child_names=True,
            )

    def test_native_none_return_preserved(self):
        with patch.object(Timesheet, "insert", autospec=True, return_value=None) as native:
            self.assertIsNone(self.document.insert())
            native.assert_called_once()

    def test_native_exception_propagates_unchanged_and_cleans_frame(self):
        error = RuntimeError("native failure")
        captured = []

        def insert(document, **kwargs):
            captured.append(_current_insertion(document))
            raise error

        with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
            with self.assertRaises(RuntimeError) as caught:
                self.document.insert()
            self.assertIs(caught.exception, error)
            native.assert_called_once()
        self.assertFalse(captured[0].state.active)
        self.assertIsNone(_current_insertion(self.document))

    def test_unmarked_native_attempt_has_no_grant_or_completion(self):
        self.document.custom_telectro_booking_origin = None

        def insert(document, **kwargs):
            frame = _current_insertion(document)
            self.assertIsNone(frame.identity)
            self.assertIsNone(self.check(frame))
            return document

        with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
            with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                self.assertIs(self.document.insert(), self.document)
                native.assert_called_once()
                complete.assert_not_called()

    def test_marker_and_client_flags_do_not_create_managed_grant(self):
        self.document.__dict__["__islocal"] = True
        self.document.flags.phase2_creation = True

        def insert(document, **kwargs):
            frame = _current_insertion(document)
            self.assertIsNone(frame.identity)
            with self.denied():
                self.check(frame)
            return document

        with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
            with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                self.assertIs(self.document.insert(), self.document)
                complete.assert_not_called()
                native.assert_called_once()

    def test_managed_exact_view_repeated_checks_then_explicit_completion(self):
        captured, events = [], []

        def insert(document, **kwargs):
            frame = _current_insertion(document)
            captured.append(frame)
            self.assertIs(frame.document, document)
            self.assertIs(frame.identity, self.identity)
            view = frame.view
            for _ in range(3):
                self.assertIs(_current_insertion(document).view, view)
                self.assertIsNone(self.check(frame))
            self.assertFalse(frame.state.completed)
            events.append("native return")
            return document

        def complete(frame, document, identity):
            self.assertEqual(events, ["native return"])
            self.assertIs(frame, captured[0])
            self.assertIs(document, self.document)
            self.assertIs(identity, self.identity)
            self.assertIsNone(_complete_insertion(frame, document, identity))
            events.append("complete")

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion",
                           side_effect=complete) as completion:
                    self.assertIs(self.document.insert(), self.document)
                    native.assert_called_once()
                    completion.assert_called_once()
            self.assertTrue(captured[0].state.completed)
            self.assertFalse(captured[0].state.active)
            with self.denied():
                self.check(captured[0])
            with self.denied():
                self.document.insert()
        self.assertEqual(events, ["native return", "complete"])

    def test_managed_arguments_forwarded_unchanged(self):
        values = dict(ignore_permissions=True, ignore_links=False, ignore_if_duplicate=False,
                      ignore_mandatory=None, set_name="EXPLICIT", set_child_names=False)
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True,
                              return_value=self.document) as native:
                self.assertIs(self.document.insert(**values), self.document)
                native.assert_called_once_with(self.document, **values)

    def test_managed_duplicate_ignore_and_unsupported_values_rejected(self):
        for value in [True, 1, "yes", None, 0, [], {}]:
            with self.subTest(value=value):
                with _phase2_creation_intent(self.document, self.identity):
                    with patch.object(Timesheet, "insert", autospec=True) as native:
                        with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                            with self.denied():
                                self.document.insert(ignore_if_duplicate=value)
                            native.assert_not_called()
                            complete.assert_not_called()
                            with self.denied():
                                self.document.insert()
                self.assertIsNone(_current_insertion(self.document))

    def test_managed_document_print_mode_rejected_before_native_call(self):
        self.document.flags.in_print = True
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.denied():
                        self.document.insert()
                    native.assert_not_called()
                    complete.assert_not_called()
        self.assertTrue(self.document.flags.in_print)
        self.assertIsNone(_current_insertion(self.document))

    def test_global_print_flag_is_not_document_print_flag(self):
        with patch.object(frappe, "flags", frappe._dict(in_print=True)):
            with _phase2_creation_intent(self.document, self.identity):
                with patch.object(Timesheet, "insert", autospec=True,
                                  return_value=self.document) as native:
                    self.assertIs(self.document.insert(), self.document)
                    native.assert_called_once()

    def test_native_document_print_mode_delegated_unchanged(self):
        self.document.flags.in_print = True

        def insert(document, **kwargs):
            self.assertTrue(document.flags.in_print)
            self.assertIsNone(_current_insertion(document).identity)
            return document

        with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
            self.assertIs(self.document.insert(), self.document)
            native.assert_called_once()
        self.assertTrue(self.document.flags.in_print)

    def test_native_duplicate_ignore_delegated_unchanged(self):
        with patch.object(Timesheet, "insert", autospec=True,
                          return_value=self.document) as native:
            self.assertIs(self.document.insert(ignore_if_duplicate=True), self.document)
            self.assertIs(native.call_args.kwargs["ignore_if_duplicate"], True)
            native.assert_called_once()

    def test_managed_unexpected_return_rejected_without_completion(self):
        for result in [None, object()]:
            with self.subTest(result=result):
                with _phase2_creation_intent(self.document, self.identity):
                    with patch.object(Timesheet, "insert", autospec=True,
                                      return_value=result) as native:
                        with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                            with self.denied():
                                self.document.insert()
                            native.assert_called_once()
                            complete.assert_not_called()
                            with self.denied():
                                self.document.insert()
                self.assertIsNone(_current_insertion(self.document))

    def test_managed_exception_revokes_grant_and_prevents_intent_reuse(self):
        captured = []
        error = RuntimeError("native failure")

        def insert(document, **kwargs):
            frame = _current_insertion(document)
            captured.append(frame)
            self.assertIsNone(self.check(frame))
            raise error

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.assertRaises(RuntimeError) as caught:
                        self.document.insert()
                    self.assertIs(caught.exception, error)
                    complete.assert_not_called()
                    self.assertIsNone(_current_insertion(self.document))
                    self.assertFalse(captured[0].state.active)
                    with self.denied():
                        self.check(captured[0])
                    with self.denied():
                        self.document.insert()
                    native.assert_called_once()

    def test_same_document_reentrancy_never_calls_native_twice(self):
        def insert(document, **kwargs):
            with self.denied():
                document.insert()
            self.assertIsNone(self.check(_current_insertion(document)))
            return document

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                self.assertIs(self.document.insert(), self.document)
                native.assert_called_once()

    def test_later_managed_attempt_requires_fresh_intent_and_view(self):
        captured = []

        def insert(document, **kwargs):
            captured.append(_current_insertion(document))
            self.assertIsNone(self.check(captured[-1]))
            return document

        with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
            for _ in range(2):
                with _phase2_creation_intent(self.document, self.identity):
                    self.assertIs(self.document.insert(), self.document)
            self.assertEqual(native.call_count, 2)
        self.assertIsNot(captured[0].view, captured[1].view)
        for frame in captured:
            self.assertFalse(frame.state.active)
            with self.denied():
                self.check(frame)

    def test_wrapper_preserves_document_fields_and_identity(self):
        before = copy.deepcopy(self.document.__dict__)
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True,
                              return_value=self.document) as native:
                self.assertIs(self.document.insert(), self.document)
                native.assert_called_once()
        self.assertEqual(self.document.__dict__, before)
        self.assertEqual(self.identity, TechnicianBookingIdentity("tech", "EMP", "Company"))
        self.assertFalse(getattr(frappe.local, "site", None))


if __name__ == "__main__":
    unittest.main()
