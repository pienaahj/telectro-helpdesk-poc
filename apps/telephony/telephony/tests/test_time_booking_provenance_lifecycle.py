"""Isolated unregistered lifecycle tests; no site or real database operations."""

import copy
import unittest
from contextvars import copy_context
from types import SimpleNamespace
from unittest.mock import patch

from frappe.model.document import Document

from telephony import time_booking_provenance_adapter as adapter
from telephony import time_booking_provenance_lifecycle as lifecycle
from telephony.time_booking_identity import TechnicianBookingIdentity
from telephony.time_booking_provenance import BookingProvenanceError, validate_provenance_transition


class FakeDocument:
    def __init__(self, values):
        self.values = values
        self.flags = {}

    def get(self, key):
        return self.values.get(key)


class TestProvenanceLifecycle(unittest.TestCase):
    def setUp(self):
        self.identity = TechnicianBookingIdentity("tech", "EMP", "Company")
        self.values = {
            "doctype": "Timesheet", "name": "TS", "custom_telectro_booking_origin": "Phase 2",
            "employee": "EMP", "company": "Company", "user": "tech", "docstatus": 0,
        }
        self.doc = FakeDocument(self.values)
        p = patch.object(adapter, "_load_persisted_provenance", return_value=None)
        self.reader = p.start()
        self.addCleanup(p.stop)
        p = patch("telephony.time_booking_attribution._native_schema_ready", return_value=False)
        p.start()
        self.addCleanup(p.stop)

    def denied(self):
        return self.assertRaisesRegex(BookingProvenanceError, r"^Booking provenance is not permitted\.$")

    def event(self, name, doc=None):
        return lifecycle._validate_timesheet_provenance(self.doc if doc is None else doc, name)

    def snapshot(self, **changes):
        result = {k: self.values[k] for k in adapter._PERSISTED_FIELDS}
        result.update(changes)
        return result

    def test_unknown_and_malformed_events_fail_closed(self):
        class EventString(str):
            pass

        class EqualEvent:
            def __eq__(self, other):
                return True

        for event in [None, "validate", "after_insert", "", 1, [], EventString("before_save"), EqualEvent()]:
            with self.subTest(event=event), self.denied():
                self.event(event)
        self.reader.assert_not_called()

    def test_unframed_before_insert_fails_even_with_spoofed_flags(self):
        self.doc.values["__islocal"] = True
        self.doc.flags["in_insert"] = True
        self.doc.is_new = lambda: True
        with self.denied():
            self.event("before_insert")
        self.reader.assert_not_called()

    def test_native_unmarked_insertion_no_absence_evidence_or_identity_resolution(self):
        self.values["custom_telectro_booking_origin"] = None
        with patch("telephony.time_booking_identity.resolve_current_technician_identity",
                   side_effect=AssertionError("Must not resolve HR identity")) as resolver:
            with adapter._insertion_attempt(self.doc) as frame:
                for event in ["before_insert", "before_validate", "before_save"]:
                    self.assertIsNone(self.event(event))
                self.assertIsNone(frame.identity)
                self.assertFalse(frame.absence.attempted)
            resolver.assert_not_called()
        self.reader.assert_not_called()

    def test_marked_native_insertion_fails_without_grant(self):
        with adapter._insertion_attempt(self.doc):
            for event in ["before_insert", "before_validate", "before_save"]:
                with self.subTest(event=event), self.denied():
                    self.event(event)
        self.reader.assert_not_called()

    def test_managed_uses_exact_frame_view_and_identity(self):
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                with patch.object(lifecycle, "validate_provenance_transition",
                                  wraps=validate_provenance_transition) as policy:
                    self.assertIsNone(self.event("before_validate"))
                    policy.assert_called_once_with(frame.view, persisted=None, identity=self.identity)
                self.assertIs(frame.view._document, self.doc)
                self.assertFalse(frame.absence.attempted)
        self.reader.assert_not_called()

    def test_before_insert_requires_no_final_name_or_database_read(self):
        self.values["name"] = None
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                self.assertIsNone(self.event("before_insert"))
                self.assertFalse(frame.absence.attempted)
        self.reader.assert_not_called()

    def test_absence_checked_only_at_before_save_after_naming(self):
        self.values["name"] = None
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                self.assertIsNone(self.event("before_insert"))
                self.values["name"] = "GENERATED-OR-EXPLICIT"
                self.assertIsNone(self.event("before_validate"))
                self.reader.assert_not_called()
                self.assertIsNone(self.event("before_save"))
                self.reader.assert_called_once_with("GENERATED-OR-EXPLICIT")
                self.assertIsNone(adapter._require_final_name_absence(frame, self.doc))
                self.assertIs(frame.absence.evidence.frame, frame)
                self.assertIs(frame.absence.evidence.document, self.doc)

    def test_collision_creates_no_evidence_and_cannot_retry(self):
        self.reader.return_value = self.snapshot()
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                with self.denied():
                    self.event("before_save")
                self.assertTrue(frame.absence.attempted)
                self.assertIsNone(frame.absence.evidence)
                self.reader.return_value = None
                with self.denied():
                    self.event("before_save")
                self.reader.assert_called_once_with("TS")

    def test_repeated_same_name_reuses_same_evidence_and_one_read(self):
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                self.assertIsNone(self.event("before_save"))
                evidence = frame.absence.evidence
                for event in ["before_save", "before_validate", "before_save"]:
                    self.assertIsNone(self.event(event))
                    self.assertIs(frame.absence.evidence, evidence)
                self.reader.assert_called_once_with("TS")

    def test_name_change_invalidates_evidence_even_if_name_restored(self):
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                self.event("before_save")
                self.values["name"] = "OTHER"
                with self.denied():
                    self.event("before_save")
                self.assertIsNone(frame.absence.evidence)
                self.values["name"] = "TS"
                with self.denied():
                    self.event("before_save")
                self.reader.assert_called_once()

    def test_invalid_final_names_rejected_without_read(self):
        class NameString(str):
            pass
        for name in [None, "", " \t", 1, NameString("TS")]:
            self.values["name"] = name
            with self.subTest(name=name):
                with adapter._phase2_creation_intent(self.doc, self.identity):
                    with adapter._insertion_attempt(self.doc):
                        with self.denied():
                            self.event("before_save")
        self.reader.assert_not_called()

    def test_changed_name_during_read_cannot_create_evidence(self):
        def read(name):
            self.values["name"] = "OTHER"
            return None

        self.reader.side_effect = read
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                with self.denied():
                    self.event("before_save")
                self.assertIsNone(frame.absence.evidence)

    def test_frame_exit_clears_evidence_and_revokes_copied_context(self):
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                self.event("before_save")
                copied = copy_context()
                self.assertIsNone(copied.run(adapter._require_final_name_absence, frame, self.doc))
            self.assertIsNone(frame.absence.evidence)
            with self.denied():
                copied.run(adapter._require_final_name_absence, frame, self.doc)
        with self.denied():
            adapter._require_final_name_absence(frame, self.doc)

    def test_failed_attempt_cannot_reuse_evidence_or_intent(self):
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with self.assertRaises(RuntimeError):
                with adapter._insertion_attempt(self.doc) as old:
                    self.event("before_save")
                    raise RuntimeError("native failure")
            self.assertIsNone(old.absence.evidence)
            with self.denied():
                with adapter._insertion_attempt(self.doc):
                    self.fail("Consumed intent reused")
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as fresh:
                self.assertFalse(fresh.absence.attempted)
                self.event("before_save")
                with self.denied():
                    adapter._require_final_name_absence(old, self.doc)
        self.assertEqual(self.reader.call_count, 2)

    def test_evidence_cannot_transfer_between_frames_or_documents(self):
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as old:
                self.event("before_save")
                evidence = old.absence.evidence
        other = FakeDocument(dict(self.values))
        with adapter._phase2_creation_intent(other, self.identity):
            with adapter._insertion_attempt(other) as frame:
                frame.absence.attempted = True
                frame.absence.evidence = evidence
                with self.denied():
                    adapter._require_final_name_absence(frame, other)
                self.assertIsNone(frame.absence.evidence)
                with self.denied():
                    adapter._verify_final_name_absence(frame, self.doc)

    def test_evidence_helpers_enforce_thread_and_task_ownership(self):
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def access(frame):
            with self.denied():
                adapter._require_final_name_absence(frame, self.doc)
            return True

        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                self.event("before_save")
                copied = copy_context()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    self.assertTrue(pool.submit(copied.run, access, frame).result())
                async def child():
                    return access(frame)
                async def parent():
                    self.assertTrue(await asyncio.create_task(child()))
                asyncio.run(parent())
                self.assertIsNone(adapter._require_final_name_absence(frame, self.doc))

    def test_database_and_lock_failures_propagate_without_retry(self):
        for error in [RuntimeError("database error"), TimeoutError("lock timeout")]:
            self.reader.reset_mock()
            self.reader.side_effect = error
            with self.subTest(error=error):
                with adapter._phase2_creation_intent(self.doc, self.identity):
                    with adapter._insertion_attempt(self.doc) as frame:
                        with self.assertRaises(type(error)) as caught:
                            self.event("before_save")
                        self.assertIs(caught.exception, error)
                        self.assertIsNone(frame.absence.evidence)
                        with self.denied():
                            self.event("before_save")
                        self.reader.assert_called_once()

    def test_managed_validation_bypass_rejected_at_all_insert_checkpoints(self):
        self.doc.flags["ignore_validate"] = True
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc):
                for event in ["before_insert", "before_validate", "before_save"]:
                    with self.subTest(event=event), self.denied():
                        self.event(event)
        self.reader.assert_not_called()

    def test_native_unmarked_validation_bypass_retains_before_validate_support(self):
        self.values["custom_telectro_booking_origin"] = ""
        self.doc.flags["ignore_validate"] = True
        with adapter._insertion_attempt(self.doc) as frame:
            self.assertIsNone(self.event("before_insert"))
            self.assertIsNone(self.event("before_validate"))
            self.assertFalse(frame.absence.attempted)
        self.reader.assert_not_called()

    def test_existing_draft_requires_row_despite_client_previous_state(self):
        self.doc._doc_before_save = self.snapshot()
        self.values["__islocal"] = True
        with self.denied():
            self.event("before_save")
        self.reader.assert_called_once_with("TS")

    def test_existing_managed_identity_and_marker_changes_denied(self):
        original = dict(self.values)
        self.reader.return_value = self.snapshot()
        for key in ["employee", "company", "user", "custom_telectro_booking_origin"]:
            self.values.clear()
            self.values.update(original)
            self.values[key] = "OTHER" if key != "custom_telectro_booking_origin" else ""
            with self.subTest(field=key), self.denied():
                self.event("before_save")

    def test_existing_native_unmarked_identity_changes_remain_compatible(self):
        self.reader.return_value = self.snapshot(custom_telectro_booking_origin=None)
        self.values.update(custom_telectro_booking_origin="", employee="OTHER", company="OTHER", user="OTHER")
        with patch("telephony.time_booking_identity.resolve_current_technician_identity",
                   side_effect=AssertionError("No HR identity read")) as resolver:
            self.assertIsNone(self.event("before_save"))
            resolver.assert_not_called()

    def test_existing_normal_lifecycle_events_use_fresh_snapshot(self):
        self.reader.return_value = self.snapshot()
        for event in ["before_validate", "before_save", "before_submit", "before_cancel", "before_update_after_submit"]:
            self.assertIsNone(self.event(event))
        self.assertEqual(self.reader.call_count, 5)

    def test_before_change_is_existing_even_with_active_insertion_frame(self):
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                with self.denied():
                    self.event("before_change")
                self.reader.return_value = self.snapshot()
                self.assertIsNone(self.event("before_change"))
                self.assertFalse(frame.absence.attempted)
        self.assertEqual(self.reader.call_count, 2)

    def test_before_change_ignores_cached_previous_row_and_reads_each_time(self):
        self.doc._doc_before_save = self.snapshot()
        self.reader.side_effect = [self.snapshot(), self.snapshot(employee="FOREIGN")]
        self.assertIsNone(self.event("before_change"))
        with self.denied():
            self.event("before_change")
        self.assertEqual(self.reader.call_count, 2)

    def test_missing_existing_row_never_becomes_creation_for_any_event(self):
        for event in ["before_validate", "before_save", "before_submit", "before_cancel", "before_update_after_submit", "before_change"]:
            with self.subTest(event=event), self.denied():
                self.event(event)

    def test_malformed_and_mismatched_existing_snapshots_fail(self):
        invalid = [False, [], {}, self.snapshot(name="FOREIGN"), self.snapshot(docstatus=True),
                   self.snapshot(employee=[]), self.snapshot(user={}), self.snapshot(company=1),
                   self.snapshot(custom_telectro_booking_origin="unknown"),
                   dict(self.snapshot(), unexpected="private")]
        invalid += [{k: v for k, v in self.snapshot().items() if k != field} for field in adapter._PERSISTED_FIELDS]
        for row in invalid:
            self.reader.return_value = row
            with self.subTest(row=row), self.denied():
                self.event("before_save")

    def test_existing_database_error_propagates_not_missing(self):
        error = RuntimeError("missing column")
        self.reader.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            self.event("before_save")
        self.assertIs(caught.exception, error)

    def test_no_document_mutation_permission_grant_or_transaction_call(self):
        before, flags = copy.deepcopy(self.values), dict(self.doc.flags)
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                self.event("before_insert")
                self.event("before_save")
                self.assertFalse(frame.state.completed)
                self.assertIsNone(adapter._require_final_name_absence(frame, self.doc))
        self.assertEqual(self.values, before)
        self.assertEqual(self.doc.flags, flags)
        self.reader.assert_called_once_with("TS")

    def test_nested_unrelated_insertion_inherits_no_authorization_or_evidence(self):
        other = FakeDocument(dict(self.values))
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as outer:
                self.event("before_save")
                with adapter._insertion_attempt(other) as inner:
                    with self.denied():
                        self.event("before_save", other)
                    with self.denied():
                        adapter._verify_final_name_absence(inner, other)
                    self.assertFalse(inner.absence.attempted)
                self.assertIsNone(adapter._require_final_name_absence(outer, self.doc))
        self.reader.assert_called_once_with("TS")

    def test_handler_does_not_manufacture_creation_grant(self):
        with self.denied():
            self.event("before_insert")
        self.reader.return_value = self.snapshot(custom_telectro_booking_origin="")
        with self.denied():
            self.event("before_save")
        with self.denied():
            validate_provenance_transition(adapter._TimesheetDocumentView(self.doc),
                                           persisted=None, identity=self.identity)

    def test_absence_evidence_does_not_complete_or_supply_a_grant(self):
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc) as frame:
                with self.denied():
                    adapter._require_final_name_absence(frame, self.doc)
                self.event("before_save")
                self.assertFalse(frame.state.completed)
                replacement_view = adapter._TimesheetDocumentView(self.doc)
                with self.denied():
                    validate_provenance_transition(replacement_view, persisted=None, identity=self.identity)

    def test_unexpected_insertion_events_and_wrong_frame_fail(self):
        with self.denied():
            lifecycle._validate_insertion_provenance(self.doc, "before_save", None)
        with adapter._phase2_creation_intent(self.doc, self.identity):
            with adapter._insertion_attempt(self.doc):
                for event in ["before_cancel", "before_update_after_submit"]:
                    with self.subTest(event=event), self.denied():
                        self.event(event)
                with self.denied():
                    lifecycle._validate_insertion_provenance(self.doc, "before_save", object())

    def test_actual_framework_skips_cancel_and_submitted_update_hooks_under_bypass(self):
        # Execute only installed event dispatch on a fake, never save/insert.
        # A skipped handler is NOT manually invoked and therefore cannot deny.
        calls = []
        fake = SimpleNamespace(flags=SimpleNamespace(ignore_validate=True),
                               reset_seen=lambda: None,
                               run_method=lambda event: calls.append(event),
                               set_title_field=lambda: calls.append("title"))
        for action in ["cancel", "update_after_submit"]:
            fake._action = action
            calls.clear()
            self.assertIsNone(Document.run_before_save_methods(fake))
            self.assertEqual(calls, [])
        self.reader.assert_not_called()

    def test_actual_framework_before_validate_precedes_save_submit_bypass(self):
        calls = []
        fake = SimpleNamespace(flags=SimpleNamespace(ignore_validate=True),
                               reset_seen=lambda: None,
                               run_method=lambda event: calls.append(event),
                               set_title_field=lambda: calls.append("title"))
        for action in ["save", "submit"]:
            fake._action = action
            calls.clear()
            self.assertIsNone(Document.run_before_save_methods(fake))
            self.assertEqual(calls, ["before_validate"])
        self.reader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
