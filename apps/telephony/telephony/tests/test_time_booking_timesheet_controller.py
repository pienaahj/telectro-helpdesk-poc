"""Isolated wrapper tests: real class inheritance, mocked native insert, no site."""

import copy
import inspect
import unittest
from unittest.mock import Mock, call, patch

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
from telephony.time_booking_timesheet_controller import _ManagedSavepointCleanupError
from telephony import time_booking_provenance_adapter as adapter
from telephony import time_booking_provenance_lifecycle as lifecycle


class TestTimesheetInsertWrapper(unittest.TestCase):
    def setUp(self):
        self.assertFalse(getattr(frappe.local, "site", None))
        self.db = Mock(spec_set=["savepoint", "rollback", "release_savepoint", "commit"])
        db_patch = patch.object(frappe.local, "db", self.db, create=True)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        reader_patch = patch.object(adapter, "_load_persisted_provenance", return_value=None)
        self.reader = reader_patch.start()
        self.addCleanup(reader_patch.stop)
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
            self.lifecycle_success(document, **kwargs)
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
                              side_effect=self.lifecycle_success) as native:
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
                                  side_effect=self.lifecycle_success) as native:
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
            self.lifecycle_success(document, **kwargs)
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
            self.lifecycle_success(document, **kwargs)
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
                              side_effect=self.lifecycle_success) as native:
                self.assertIs(self.document.insert(), self.document)
                native.assert_called_once()
        self.assertEqual(self.document.__dict__, before)
        self.assertEqual(self.identity, TechnicianBookingIdentity("tech", "EMP", "Company"))
        self.assertFalse(getattr(frappe.local, "site", None))

    def lifecycle_success(self, document, **kwargs):
        """Mock native lifecycle only; no real naming, insertion or transaction."""
        for event in ["before_insert", "before_validate", "before_save"]:
            lifecycle._validate_timesheet_provenance(document, event)
        return document

    def test_managed_missing_evidence_denied_after_native_return_without_completion(self):
        captured = []

        def insert(document, **kwargs):
            captured.append(_current_insertion(document))
            return document

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.denied():
                        self.document.insert()
                    native.assert_called_once()
                    complete.assert_not_called()
                    self.reader.assert_not_called()
                    with self.denied():
                        self.document.insert()
            self.assertFalse(captured[0].state.active)
            with self.denied():
                self.check(captured[0])

    def test_native_return_then_real_evidence_verification_then_completion(self):
        events = []
        captured = []

        def insert(document, **kwargs):
            self.lifecycle_success(document, **kwargs)
            captured.append(_current_insertion(document))
            events.append("native return")
            return document

        def require(frame, document):
            self.assertEqual(events, ["native return"])
            self.assertIs(frame, captured[0])
            self.assertIsNone(adapter._require_final_name_absence(frame, document))
            events.append("evidence verified")

        def complete(frame, document, identity):
            self.assertEqual(events, ["native return", "evidence verified"])
            self.assertIsNone(_complete_insertion(frame, document, identity))
            events.append("completed")

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with patch("telephony.time_booking_timesheet_controller._require_final_name_absence",
                           side_effect=require) as guard:
                    with patch("telephony.time_booking_timesheet_controller._complete_insertion",
                               side_effect=complete) as completed:
                        self.assertIs(self.document.insert(), self.document)
                        native.assert_called_once()
                        guard.assert_called_once()
                        completed.assert_called_once()
        self.reader.assert_called_once_with("TS")
        self.assertEqual(events, ["native return", "evidence verified", "completed"])
        self.assertTrue(captured[0].state.completed)

    def test_name_changed_after_lifecycle_absence_denied_at_completion(self):
        captured = []

        def insert(document, **kwargs):
            self.lifecycle_success(document, **kwargs)
            captured.append(_current_insertion(document))
            document.name = "CHANGED-AFTER-CHECK"
            return document

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.denied():
                        self.document.insert()
                    native.assert_called_once()
                    complete.assert_not_called()
        self.reader.assert_called_once_with("TS")
        self.assertIsNone(captured[0].absence.evidence)
        self.assertFalse(captured[0].state.active)
        self.assertFalse(captured[0].state.completed)

    def test_lifecycle_collision_denies_without_completion(self):
        self.reader.return_value = {
            "name": "TS", "custom_telectro_booking_origin": "Phase 2",
            "employee": "EMP", "company": "Company", "user": "tech", "docstatus": 0,
        }
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True,
                              side_effect=self.lifecycle_success) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.denied():
                        self.document.insert()
                    native.assert_called_once()
                    complete.assert_not_called()
                    with self.denied():
                        self.document.insert()
        self.reader.assert_called_once_with("TS")
        self.assertIsNone(_current_insertion(self.document))

    def test_lifecycle_database_and_lock_errors_propagate_without_completion(self):
        for error in [RuntimeError("database failure"), TimeoutError("lock timeout")]:
            self.reader.reset_mock()
            self.reader.side_effect = error
            with self.subTest(error=error):
                with _phase2_creation_intent(self.document, self.identity):
                    with patch.object(Timesheet, "insert", autospec=True,
                                      side_effect=self.lifecycle_success) as native:
                        with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                            with self.assertRaises(type(error)) as caught:
                                self.document.insert()
                            self.assertIs(caught.exception, error)
                            native.assert_called_once()
                            complete.assert_not_called()
                self.reader.assert_called_once_with("TS")
                self.assertIsNone(_current_insertion(self.document))

    def test_invalidated_evidence_stays_invalid_after_name_restored(self):
        def insert(document, **kwargs):
            self.lifecycle_success(document, **kwargs)
            document.name = "OTHER"
            with self.denied():
                lifecycle._validate_timesheet_provenance(document, "before_save")
            document.name = "TS"
            return document

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.denied():
                        self.document.insert()
                    native.assert_called_once()
                    complete.assert_not_called()
        self.reader.assert_called_once_with("TS")

    def test_expired_attempt_evidence_cannot_supply_new_attempt(self):
        captured = []

        def first(document, **kwargs):
            self.lifecycle_success(document, **kwargs)
            captured.append(_current_insertion(document))
            return document

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=first) as native:
                self.assertIs(self.document.insert(), self.document)
                native.assert_called_once()
        with self.denied():
            adapter._require_final_name_absence(captured[0], self.document)
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True,
                              return_value=self.document) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.denied():
                        self.document.insert()
                    native.assert_called_once()
                    complete.assert_not_called()
        self.reader.assert_called_once_with("TS")

    def test_unexpected_native_return_after_absence_still_cannot_complete(self):
        for returned in [None, object()]:
            self.reader.reset_mock()

            def insert(document, **kwargs):
                self.lifecycle_success(document, **kwargs)
                return returned

            with self.subTest(returned=returned):
                with _phase2_creation_intent(self.document, self.identity):
                    with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                        with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                            with self.denied():
                                self.document.insert()
                            native.assert_called_once()
                            complete.assert_not_called()
                self.reader.assert_called_once_with("TS")

    def test_native_operation_does_not_require_or_manufacture_absence(self):
        returned = object()
        with patch.object(Timesheet, "insert", autospec=True, return_value=returned) as native:
            with patch("telephony.time_booking_timesheet_controller._require_final_name_absence") as require:
                with patch("telephony.time_booking_identity.resolve_current_technician_identity",
                           side_effect=AssertionError("Must not resolve identity")) as resolver:
                    self.assertIs(self.document.insert(ignore_if_duplicate=True), returned)
                    native.assert_called_once()
                    require.assert_not_called()
                    resolver.assert_not_called()
        self.reader.assert_not_called()

    def test_native_exception_after_absence_revokes_grant_without_completion(self):
        error = RuntimeError("failed after lifecycle checkpoint")
        captured = []

        def insert(document, **kwargs):
            self.lifecycle_success(document, **kwargs)
            captured.append(_current_insertion(document))
            raise error

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.assertRaises(RuntimeError) as caught:
                        self.document.insert()
                    self.assertIs(caught.exception, error)
                    complete.assert_not_called()
                    with self.denied():
                        self.check(captured[0])
                    with self.denied():
                        self.document.insert()
                    native.assert_called_once()
        self.assertFalse(captured[0].state.active)
        self.assertIsNone(captured[0].absence.evidence)

    def assert_rollback_release(self):
        name = self.db.savepoint.call_args.args[0]
        self.assertEqual(self.db.mock_calls, [
            call.savepoint(name), call.rollback(save_point=name), call.release_savepoint(name)
        ])
        self.db.commit.assert_not_called()

    def test_savepoint_encloses_native_evidence_completion_then_release(self):
        events, frames = [], []

        def savepoint(name):
            events.append("savepoint")

        def native_insert(document, **kwargs):
            self.assertEqual(events, ["savepoint"])
            frames.append(_current_insertion(document))
            self.lifecycle_success(document, **kwargs)
            events.append("native return")
            return document

        def require(frame, document):
            self.assertEqual(events, ["savepoint", "native return"])
            adapter._require_final_name_absence(frame, document)
            events.append("evidence")

        def complete(frame, document, identity):
            self.assertEqual(events, ["savepoint", "native return", "evidence"])
            _complete_insertion(frame, document, identity)
            events.append("complete")

        def release(name):
            self.assertEqual(events, ["savepoint", "native return", "evidence", "complete"])
            self.assertTrue(frames[0].state.active)
            self.assertTrue(frames[0].state.completed)
            events.append("release")

        self.db.savepoint.side_effect = savepoint
        self.db.release_savepoint.side_effect = release
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=native_insert) as native:
                with patch("telephony.time_booking_timesheet_controller._require_final_name_absence",
                           side_effect=require):
                    with patch("telephony.time_booking_timesheet_controller._complete_insertion",
                               side_effect=complete):
                        self.assertIs(self.document.insert(), self.document)
                        native.assert_called_once()
        self.assertEqual(events, ["savepoint", "native return", "evidence", "complete", "release"])
        name = self.db.savepoint.call_args.args[0]
        self.assertEqual(self.db.mock_calls, [call.savepoint(name), call.release_savepoint(name)])
        self.reader.assert_called_once_with("TS")
        self.assertFalse(frames[0].state.active)

    def test_native_error_rolls_back_releases_and_preserves_exception(self):
        error = RuntimeError("native failed")
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=error) as native:
                with self.assertRaises(RuntimeError) as caught:
                    self.document.insert()
                self.assertIs(caught.exception, error)
                native.assert_called_once()
                with self.denied():
                    self.document.insert()
        self.assert_rollback_release()
        self.assertIsNone(_current_insertion(self.document))

    def test_lifecycle_collision_rolls_back_and_releases(self):
        self.reader.return_value = {"name": "TS"}
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True,
                              side_effect=self.lifecycle_success) as native:
                with self.denied():
                    self.document.insert()
                native.assert_called_once()
        self.assert_rollback_release()

    def test_checkpoint_database_and_lock_failures_roll_back_and_release(self):
        for error in [RuntimeError("database failed"), TimeoutError("locking failed")]:
            self.db.reset_mock()
            self.reader.side_effect = error
            with self.subTest(error=error):
                with _phase2_creation_intent(self.document, self.identity):
                    with patch.object(Timesheet, "insert", autospec=True,
                                      side_effect=self.lifecycle_success) as native:
                        with self.assertRaises(type(error)) as caught:
                            self.document.insert()
                        self.assertIs(caught.exception, error)
                        native.assert_called_once()
                self.assert_rollback_release()

    def test_missing_evidence_after_native_return_rolls_back(self):
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True,
                              return_value=self.document) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion") as complete:
                    with self.denied():
                        self.document.insert()
                    complete.assert_not_called()
                    native.assert_called_once()
        self.assert_rollback_release()

    def test_changed_name_after_lifecycle_rolls_back(self):
        def insert(document, **kwargs):
            self.lifecycle_success(document, **kwargs)
            document.name = "CHANGED"
            return document

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with self.denied():
                    self.document.insert()
                native.assert_called_once()
        self.assert_rollback_release()

    def test_unexpected_native_result_rolls_back(self):
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, return_value=object()) as native:
                with self.denied():
                    self.document.insert()
                native.assert_called_once()
        self.assert_rollback_release()

    def test_completion_failure_rolls_back_preserving_error_and_revokes_grant(self):
        error, frames = RuntimeError("completion failed"), []

        def insert(document, **kwargs):
            self.lifecycle_success(document, **kwargs)
            frames.append(_current_insertion(document))
            return document

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with patch("telephony.time_booking_timesheet_controller._complete_insertion",
                           side_effect=error) as complete:
                    with self.assertRaises(RuntimeError) as caught:
                        self.document.insert()
                    self.assertIs(caught.exception, error)
                    complete.assert_called_once()
                    native.assert_called_once()
                    with self.denied():
                        self.check(frames[0])
                    with self.denied():
                        self.document.insert()
        self.assert_rollback_release()
        self.assertFalse(frames[0].state.active)

    def test_savepoint_creation_failure_prevents_native_and_unknown_rollback(self):
        error = RuntimeError("savepoint failed")
        self.db.savepoint.side_effect = error
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True) as native:
                with self.assertRaises(RuntimeError) as caught:
                    self.document.insert()
                self.assertIs(caught.exception, error)
                native.assert_not_called()
                with self.denied():
                    self.document.insert()
        self.db.savepoint.assert_called_once()
        self.db.rollback.assert_not_called()
        self.db.release_savepoint.assert_not_called()
        self.db.commit.assert_not_called()
        self.assertIsNone(_current_insertion(self.document))

    def test_rollback_failure_explicitly_retains_original_error_chain(self):
        original, rollback_error = RuntimeError("native failed"), RuntimeError("rollback failed")
        self.db.rollback.side_effect = rollback_error
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=original) as native:
                with self.assertRaises(_ManagedSavepointCleanupError) as caught:
                    self.document.insert()
                self.assertIs(caught.exception.__cause__, rollback_error)
                self.assertIs(rollback_error.__context__, original)
                self.assertIn("transaction state is uncertain", str(caught.exception))
                native.assert_called_once()
        self.db.rollback.assert_called_once_with(save_point=self.db.savepoint.call_args.args[0])
        self.db.release_savepoint.assert_not_called()
        self.db.commit.assert_not_called()

    def test_release_failure_during_error_cleanup_preserves_both_failures(self):
        original, release_error = RuntimeError("native failed"), RuntimeError("release failed")
        self.db.release_savepoint.side_effect = release_error
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=original):
                with self.assertRaises(_ManagedSavepointCleanupError) as caught:
                    self.document.insert()
                self.assertIs(caught.exception.__cause__, release_error)
                self.assertIs(release_error.__context__, original)
        self.assert_rollback_release()

    def test_release_failure_after_success_rolls_back_without_retrying_release(self):
        error, frames = RuntimeError("release failed"), []
        self.db.release_savepoint.side_effect = error

        def insert(document, **kwargs):
            self.lifecycle_success(document, **kwargs)
            frames.append(_current_insertion(document))
            return document

        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert) as native:
                with self.assertRaises(RuntimeError) as caught:
                    self.document.insert()
                self.assertIs(caught.exception, error)
                native.assert_called_once()
                with self.denied():
                    self.document.insert()
        name = self.db.savepoint.call_args.args[0]
        self.assertEqual(self.db.mock_calls, [call.savepoint(name), call.release_savepoint(name),
                                              call.rollback(save_point=name)])
        self.assertTrue(frames[0].state.completed)
        self.assertFalse(frames[0].state.active)
        with self.denied():
            self.check(frames[0])

    def test_release_then_rollback_failure_is_explicit_and_chained(self):
        release_error, rollback_error = RuntimeError("release failed"), RuntimeError("rollback failed")
        self.db.release_savepoint.side_effect = release_error
        self.db.rollback.side_effect = rollback_error
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=self.lifecycle_success):
                with self.assertRaises(_ManagedSavepointCleanupError) as caught:
                    self.document.insert()
                self.assertIs(caught.exception.__cause__, rollback_error)
                self.assertIs(rollback_error.__context__, release_error)
        self.db.release_savepoint.assert_called_once()
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()

    def test_distinct_attempts_use_unique_safe_savepoint_names(self):
        with patch.object(Timesheet, "insert", autospec=True, side_effect=self.lifecycle_success) as native:
            for _ in range(2):
                with _phase2_creation_intent(self.document, self.identity):
                    self.assertIs(self.document.insert(), self.document)
            self.assertEqual(native.call_count, 2)
        names = [c.args[0] for c in self.db.savepoint.call_args_list]
        self.assertEqual(len(set(names)), 2)
        for name in names:
            self.assertRegex(name, r"^p2_ts_[0-9a-f]{32}$")
        self.assertEqual([c.args[0] for c in self.db.release_savepoint.call_args_list], names)
        self.db.commit.assert_not_called()
        self.db.rollback.assert_not_called()

    def test_native_print_duplicate_return_and_error_never_touch_transactions(self):
        self.document.flags.in_print = True
        returned = object()
        with patch.object(Timesheet, "insert", autospec=True, return_value=returned) as native:
            self.assertIs(self.document.insert(ignore_if_duplicate=True), returned)
            native.assert_called_once()
            self.assertTrue(native.call_args.kwargs["ignore_if_duplicate"])
        error = RuntimeError("native error")
        with patch.object(Timesheet, "insert", autospec=True, side_effect=error) as native:
            with self.assertRaises(RuntimeError) as caught:
                self.document.insert()
            self.assertIs(caught.exception, error)
            native.assert_called_once()
        self.assertEqual(self.db.mock_calls, [])
        self.reader.assert_not_called()

    def test_base_exception_also_rolls_back_and_releases(self):
        error = KeyboardInterrupt("interrupted")
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=error):
                with self.assertRaises(KeyboardInterrupt) as caught:
                    self.document.insert()
                self.assertIs(caught.exception, error)
        self.assert_rollback_release()

    def test_managed_print_and_duplicate_guards_precede_savepoint(self):
        for in_print, duplicate in [(True, False), (False, True)]:
            self.document.flags.in_print = in_print
            with _phase2_creation_intent(self.document, self.identity):
                with patch.object(Timesheet, "insert", autospec=True) as native:
                    with self.denied():
                        self.document.insert(ignore_if_duplicate=duplicate)
                    native.assert_not_called()
        self.assertEqual(self.db.mock_calls, [])

    def test_failure_rollback_and_release_run_before_frame_revocation(self):
        error, frames = RuntimeError("native failed"), []

        def insert(document, **kwargs):
            frames.append(_current_insertion(document))
            raise error

        def cleanup(*args, **kwargs):
            self.assertIs(_current_insertion(self.document), frames[0])
            self.assertTrue(frames[0].state.active)
            self.assertIsNone(self.check(frames[0]))

        self.db.rollback.side_effect = cleanup
        self.db.release_savepoint.side_effect = cleanup
        with _phase2_creation_intent(self.document, self.identity):
            with patch.object(Timesheet, "insert", autospec=True, side_effect=insert):
                with self.assertRaises(RuntimeError) as caught:
                    self.document.insert()
                self.assertIs(caught.exception, error)
        self.assertFalse(frames[0].state.active)
        self.assert_rollback_release()


if __name__ == "__main__":
    unittest.main()
