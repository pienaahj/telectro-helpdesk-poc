"""Isolated Mapping compatibility tests; no site or database initialization."""

import copy
import unittest
from collections.abc import Mapping
from dataclasses import FrozenInstanceError

from frappe.model.docstatus import DocStatus

from telephony.time_booking_identity import TechnicianBookingIdentity
from telephony.time_booking_provenance import (
    BookingProvenanceError,
    _complete_creation,
    _creation_authorization,
    validate_provenance_transition,
)
from telephony.time_booking_provenance_adapter import _TimesheetDocumentView


class FakeDocument:
    def __init__(self, values):
        self.values = values

    def get(self, key):
        return self.values.get(key)


class TestTimesheetDocumentView(unittest.TestCase):
    def setUp(self):
        self.identity = TechnicianBookingIdentity("tech", "EMP", "Company")
        self.values = {
            "doctype": "Timesheet", "name": "TS",
            "custom_telectro_booking_origin": "Phase 2",
            "employee": "EMP", "company": "Company", "user": "tech",
            "docstatus": DocStatus.DRAFT,
            "owner": "private", "description": "not projected",
        }
        self.document = FakeDocument(self.values)
        self.view = _TimesheetDocumentView(self.document)

    def check(self, view):
        return validate_provenance_transition(
            view, persisted=None, identity=self.identity
        )

    def test_mapping_contract_and_projection(self):
        self.assertIsInstance(self.view, Mapping)
        self.assertEqual(list(self.view), [
            "doctype", "name", "custom_telectro_booking_origin",
            "employee", "company", "user", "docstatus",
        ])
        self.assertEqual(len(self.view), 7)
        self.assertEqual(dict(self.view), {
            k: v for k, v in self.values.items()
            if k not in ("owner", "description")
        })

    def test_only_projection_keys_exposed(self):
        for key in ["owner", "description", "flags", "unknown"]:
            with self.subTest(key=key):
                with self.assertRaises(KeyError):
                    self.view[key]
                self.assertIsNone(self.view.get(key))
                self.assertEqual(self.view.get(key, "fallback"), "fallback")
                self.assertNotIn(key, self.view)

    def test_live_values_without_serialization(self):
        self.assertEqual(self.view["name"], "TS")
        self.values["name"] = "TS-updated"
        self.assertEqual(self.view["name"], "TS-updated")
        self.values["docstatus"] = DocStatus.SUBMITTED
        self.assertEqual(self.view["docstatus"], 1)
        self.assertIs(type(self.view["docstatus"]), int)
        self.assertIs(self.view._document, self.document)

    def test_missing_projected_value_is_none(self):
        del self.values["name"]
        self.assertIsNone(self.view["name"])
        self.assertIn("name", self.view)

    def test_document_reference_cannot_be_reassigned_or_deleted(self):
        with self.assertRaises(FrozenInstanceError):
            self.view._document = FakeDocument({})
        with self.assertRaises(FrozenInstanceError):
            del self.view._document
        self.assertIs(self.view._document, self.document)

    def test_view_does_not_support_item_mutation(self):
        with self.assertRaises(TypeError):
            self.view["employee"] = "OTHER"
        with self.assertRaises(TypeError):
            del self.view["employee"]
        self.assertEqual(self.values["employee"], "EMP")

    def test_builtin_statuses_preserved(self):
        for value in [0, 1, 2]:
            with self.subTest(value=value):
                self.values["docstatus"] = value
                self.assertIs(self.view["docstatus"], value)
                self.assertIs(type(self.view["docstatus"]), int)

    def test_actual_frappe_statuses_converted(self):
        self.assertEqual(DocStatus.__module__, "frappe.model.docstatus")
        for value in [DocStatus.DRAFT, DocStatus.SUBMITTED, DocStatus.CANCELLED]:
            with self.subTest(value=value):
                self.values["docstatus"] = value
                self.assertEqual(self.view["docstatus"], int(value))
                self.assertIs(type(self.view["docstatus"]), int)
                self.assertIs(self.values["docstatus"], value)

    def test_invalid_status_representations_rejected(self):
        class OtherInt(int):
            pass

        class DerivedStatus(DocStatus):
            pass

        class Coercible:
            def __int__(self):
                raise AssertionError("Must not coerce arbitrary objects")

        for value in [True, False, "0", 0.0, None, -1, 3,
                      OtherInt(0), DerivedStatus(0), Coercible(), [], {},
                      DocStatus(-1), DocStatus(3)]:
            with self.subTest(value_type=type(value).__name__, value=value):
                self.values["docstatus"] = value
                with self.assertRaises(BookingProvenanceError) as caught:
                    self.view["docstatus"]
                self.assertEqual(
                    str(caught.exception), "Booking provenance is not permitted."
                )

    def test_one_exact_view_repeated_checks_and_completion(self):
        with _creation_authorization(self.view, self.identity):
            for _ in range(3):
                self.assertIsNone(self.check(self.view))
            _complete_creation(self.view, self.identity)
            with self.assertRaises(BookingProvenanceError):
                self.check(self.view)

    def test_separate_view_same_document_cannot_reuse_grant(self):
        other = _TimesheetDocumentView(self.document)
        with _creation_authorization(self.view, self.identity):
            with self.assertRaises(BookingProvenanceError):
                self.check(other)
            self.assertIsNone(self.check(self.view))

    def test_other_document_identical_values_cannot_reuse_grant(self):
        other = _TimesheetDocumentView(FakeDocument(copy.deepcopy(self.values)))
        with _creation_authorization(self.view, self.identity):
            with self.assertRaises(BookingProvenanceError):
                self.check(other)
            self.assertIsNone(self.check(self.view))

    def test_live_identity_mutation_invalidates_grant(self):
        with _creation_authorization(self.view, self.identity):
            self.assertIsNone(self.check(self.view))
            self.values["employee"] = "OTHER"
            with self.assertRaises(BookingProvenanceError):
                self.check(self.view)

    def test_strict_marker_types_pass_through_unchanged(self):
        class EqualMarker:
            def __eq__(self, other):
                return other in ("", "Phase 2")

        class MarkerString(str):
            pass

        for marker in [EqualMarker(), MarkerString("Phase 2"), " ", 1]:
            with self.subTest(marker_type=type(marker).__name__):
                with _creation_authorization(self.view, self.identity):
                    self.values["custom_telectro_booking_origin"] = marker
                    self.assertIs(self.view["custom_telectro_booking_origin"], marker)
                    with self.assertRaises(BookingProvenanceError):
                        self.check(self.view)
                self.values["custom_telectro_booking_origin"] = "Phase 2"

    def test_invalid_live_status_fails_policy(self):
        with _creation_authorization(self.view, self.identity):
            self.values["docstatus"] = True
            with self.assertRaises(BookingProvenanceError):
                self.check(self.view)

    def test_construction_and_reads_preserve_document(self):
        before = copy.deepcopy(self.values)
        view = _TimesheetDocumentView(self.document)
        self.assertEqual(dict(view)["docstatus"], 0)
        self.assertEqual(self.values, before)
        self.assertIs(type(self.values["docstatus"]), DocStatus)

    def test_invalid_document_interface_rejected(self):
        for document in [None, object(), type("BadDocument", (), {"get": 42})()]:
            with self.subTest(document=document):
                with self.assertRaises(BookingProvenanceError):
                    _TimesheetDocumentView(document)

    def test_get_errors_propagate(self):
        class BrokenDocument:
            def get(self, key):
                raise RuntimeError("read failed")

        view = _TimesheetDocumentView(BrokenDocument())
        with self.assertRaisesRegex(RuntimeError, "read failed"):
            view["employee"]


    def test_rejected_keys_never_reach_document(self):
        class EqualKey:
            def __init__(self, target):
                self.target = target

            def __eq__(self, other):
                return other == self.target

        class FieldString(str):
            pass

        class RecordingDocument(FakeDocument):
            def __init__(self, values):
                super().__init__(values)
                self.calls = []

            def get(self, key):
                self.calls.append(key)
                return super().get(key)

        document = RecordingDocument(self.values)
        view = _TimesheetDocumentView(document)
        for key in [EqualKey("employee"), EqualKey("docstatus"),
                    FieldString("employee"), "owner"]:
            with self.subTest(key_type=type(key).__name__):
                with self.assertRaises(KeyError):
                    view[key]
                self.assertEqual(document.calls, [])
                self.assertIsNone(view.get(key))
                self.assertEqual(document.calls, [])
                self.assertEqual(view.get(key, "fallback"), "fallback")
                self.assertEqual(document.calls, [])
                self.assertNotIn(key, view)
                self.assertEqual(document.calls, [])
        self.assertEqual(view["employee"], "EMP")
        self.assertEqual(view.get("docstatus"), 0)
        self.assertIs(type(view["docstatus"]), int)
        self.assertEqual(document.calls, ["employee", "docstatus", "docstatus"])


from telephony.time_booking_provenance_adapter import (
    _phase2_creation_intent, _insertion_attempt, _current_insertion,
    _complete_insertion, _load_persisted_provenance,
)

class TestTrustedInsertionPrimitives(unittest.TestCase):
    def setUp(self):
        self.identity = TechnicianBookingIdentity("tech", "EMP", "Company")
        self.values = {
            "doctype": "Timesheet", "name": "TS",
            "custom_telectro_booking_origin": "Phase 2",
            "employee": "EMP", "company": "Company", "user": "tech", "docstatus": 0,
        }
        self.document = FakeDocument(self.values)

    def check(self, frame):
        return validate_provenance_transition(
            frame.view, persisted=None, identity=frame.identity
        )

    def denied(self):
        return self.assertRaisesRegex(
            BookingProvenanceError, r"^Booking provenance is not permitted\.$"
        )

    def test_exact_document_stable_view_and_repeated_checks(self):
        with _phase2_creation_intent(self.document, self.identity):
            with _insertion_attempt(self.document) as frame:
                self.assertIs(frame.document, self.document)
                self.assertIs(frame.identity, self.identity)
                for _ in range(3):
                    self.assertIs(_current_insertion(self.document), frame)
                    self.assertIs(_current_insertion(self.document).view, frame.view)
                    self.assertIsNone(self.check(frame))
                self.values["employee"] = "OTHER"
                with self.denied():
                    self.check(frame)
        self.assertIsNone(_current_insertion(self.document))

    def test_intent_alone_grants_no_creation_authorization(self):
        with _phase2_creation_intent(self.document, self.identity):
            self.assertIsNone(_current_insertion(self.document))
            with self.denied():
                validate_provenance_transition(
                    _TimesheetDocumentView(self.document), persisted=None, identity=self.identity
                )

    def test_invalid_identities_and_document_shapes_rejected(self):
        for identity in [None, {}, TechnicianBookingIdentity("", "EMP", "Company"),
                         TechnicianBookingIdentity("Administrator", "EMP", "Company"),
                         TechnicianBookingIdentity("Guest", "EMP", "Company"),
                         TechnicianBookingIdentity("tech", [], "Company"),
                         TechnicianBookingIdentity("other", "EMP", "Company")]:
            with self.subTest(identity=identity), self.denied():
                with _phase2_creation_intent(self.document, identity):
                    self.fail("Invalid identity accepted")
        with self.denied():
            with _phase2_creation_intent(object(), self.identity):
                self.fail("Malformed document accepted")

    def test_different_document_cannot_consume_pending_intent(self):
        other = FakeDocument(dict(self.values))
        with _phase2_creation_intent(self.document, self.identity):
            with self.denied():
                with _insertion_attempt(other):
                    self.fail("Foreign Document consumed intent")
            with _insertion_attempt(self.document) as frame:
                self.assertIsNone(self.check(frame))

    def test_single_use_after_normal_exit_without_completion(self):
        with _phase2_creation_intent(self.document, self.identity):
            with _insertion_attempt(self.document) as frame:
                self.assertIsNone(self.check(frame))
            self.assertFalse(frame.state.active)
            self.assertFalse(frame.state.completed)
            with self.denied():
                self.check(frame)
            with self.denied():
                with _insertion_attempt(self.document):
                    self.fail("Consumed intent reused")

    def test_failed_attempt_consumes_intent_and_revokes_grant(self):
        with _phase2_creation_intent(self.document, self.identity):
            with self.assertRaisesRegex(RuntimeError, "insert failed"):
                with _insertion_attempt(self.document) as frame:
                    self.assertIsNone(self.check(frame))
                    raise RuntimeError("insert failed")
            self.assertIsNone(_current_insertion(self.document))
            with self.denied():
                self.check(frame)
            with self.denied():
                with _insertion_attempt(self.document):
                    self.fail("Failed attempt reused intent")

    def test_fresh_intent_after_failure_requires_new_view(self):
        with self.assertRaises(RuntimeError):
            with _phase2_creation_intent(self.document, self.identity):
                with _insertion_attempt(self.document) as old:
                    raise RuntimeError()
        with _phase2_creation_intent(self.document, self.identity):
            with _insertion_attempt(self.document) as fresh:
                self.assertIsNot(fresh.view, old.view)
                self.assertIsNone(self.check(fresh))
                with self.denied():
                    self.check(old)

    def test_native_attempt_never_grants_managed_authorization(self):
        with _insertion_attempt(self.document) as frame:
            self.assertIsNone(frame.identity)
            with self.denied():
                self.check(frame)
        self.values["custom_telectro_booking_origin"] = None
        with _insertion_attempt(self.document) as native:
            self.assertIsNone(self.check(native))
            self.assertIsNone(native.identity)

    def test_same_document_reentrancy_rejected(self):
        with _insertion_attempt(self.document) as frame:
            with self.denied():
                with _insertion_attempt(self.document):
                    self.fail("Reentrant insert accepted")
            self.assertIs(_current_insertion(self.document), frame)

    def test_nested_managed_intents_and_attempts_rejected(self):
        other = FakeDocument(dict(self.values))
        with _phase2_creation_intent(self.document, self.identity):
            with self.denied():
                with _phase2_creation_intent(other, self.identity):
                    self.fail("Nested intent accepted")
            with _insertion_attempt(self.document) as frame:
                with self.denied():
                    with _phase2_creation_intent(other, self.identity):
                        self.fail("Nested managed creation accepted")
                with _insertion_attempt(other) as nested:
                    self.assertIsNone(nested.identity)
                    with self.denied():
                        self.check(nested)
                self.assertIsNone(self.check(frame))

    def test_nested_native_insert_has_own_frame_and_restores_outer(self):
        other = FakeDocument(dict(self.values, custom_telectro_booking_origin=""))
        with _phase2_creation_intent(self.document, self.identity):
            with _insertion_attempt(self.document) as outer:
                with _insertion_attempt(other) as inner:
                    self.assertIs(_current_insertion(other), inner)
                    self.assertIsNone(_current_insertion(self.document))
                    self.assertIsNot(inner.view, outer.view)
                    self.assertIsNone(inner.identity)
                    self.assertIsNone(self.check(inner))
                self.assertIs(_current_insertion(self.document), outer)
                self.assertIsNone(self.check(outer))

    def test_explicit_completion_single_use_and_scope_lifetime(self):
        with _phase2_creation_intent(self.document, self.identity):
            with _insertion_attempt(self.document) as frame:
                self.assertIsNone(_complete_insertion(frame, self.document, self.identity))
                self.assertTrue(frame.state.completed)
                self.assertTrue(frame.state.active)
                self.assertIs(_current_insertion(self.document), frame)
                with self.denied():
                    self.check(frame)
                with self.denied():
                    _complete_insertion(frame, self.document, self.identity)
        with self.denied():
            _complete_insertion(frame, self.document, self.identity)

    def test_completion_rejects_wrong_document_identity_and_frame(self):
        with _phase2_creation_intent(self.document, self.identity):
            with _insertion_attempt(self.document) as frame:
                for candidate, doc, identity in [
                    (frame, FakeDocument(dict(self.values)), self.identity),
                    (frame, self.document, None),
                    (frame, self.document, TechnicianBookingIdentity("tech", "EMP", "Company")),
                    (object(), self.document, self.identity),
                ]:
                    with self.subTest(candidate=type(candidate).__name__), self.denied():
                        _complete_insertion(candidate, doc, identity)
                self.assertFalse(frame.state.completed)
                self.assertIsNone(self.check(frame))

    def test_native_completion_is_explicit_and_single_use(self):
        with _insertion_attempt(self.document) as frame:
            with self.denied():
                _complete_insertion(frame, self.document, self.identity)
            self.assertIsNone(_complete_insertion(frame, self.document))
            with self.denied():
                _complete_insertion(frame, self.document)

    def test_intent_cleanup_on_exception_without_attempt(self):
        with self.assertRaises(RuntimeError):
            with _phase2_creation_intent(self.document, self.identity):
                raise RuntimeError()
        with _insertion_attempt(self.document) as frame:
            self.assertIsNone(frame.identity)
            with self.denied():
                self.check(frame)

    def test_thread_cannot_access_copied_intent_or_frame(self):
        import contextvars
        from concurrent.futures import ThreadPoolExecutor

        def attempt_access():
            with self.denied():
                _current_insertion(self.document)
            with self.denied():
                with _insertion_attempt(self.document):
                    self.fail("Thread inherited insertion")
            return True

        with ThreadPoolExecutor(max_workers=1) as pool:
            with _phase2_creation_intent(self.document, self.identity):
                context = contextvars.copy_context()
                self.assertTrue(pool.submit(context.run, attempt_access).result())
                with _insertion_attempt(self.document) as frame:
                    context = contextvars.copy_context()
                    self.assertTrue(pool.submit(context.run, attempt_access).result())
                    self.assertIsNone(self.check(frame))

    def test_async_task_cannot_access_inherited_capabilities(self):
        import asyncio

        async def child():
            with self.denied():
                _current_insertion(self.document)
            with self.denied():
                with _insertion_attempt(self.document):
                    self.fail("Task inherited insertion")
            return True

        async def parent():
            with _phase2_creation_intent(self.document, self.identity):
                self.assertTrue(await asyncio.create_task(child()))
                with _insertion_attempt(self.document) as frame:
                    self.assertTrue(await asyncio.create_task(child()))
                    self.assertIsNone(self.check(frame))

        asyncio.run(parent())

    def test_copied_context_revoked_after_frame_and_intent_exit(self):
        from contextvars import copy_context

        with _phase2_creation_intent(self.document, self.identity):
            pending = copy_context()
            with _insertion_attempt(self.document) as frame:
                active = copy_context()
                self.assertIs(active.run(_current_insertion, self.document), frame)
            with self.denied():
                active.run(_current_insertion, self.document)
        for context in [pending, active]:
            with self.subTest(context=context), self.denied():
                context.run(_current_insertion, self.document)
        self.assertIsNone(_current_insertion(self.document))

    def test_copied_pending_context_cannot_reuse_consumed_intent(self):
        from contextvars import copy_context

        def consume():
            with _insertion_attempt(self.document) as frame:
                self.assertIsNone(self.check(frame))
                return frame

        with _phase2_creation_intent(self.document, self.identity):
            copied = copy_context()
            frame = copied.run(consume)
            self.assertFalse(frame.state.active)
            with self.denied():
                consume()

    def test_failed_grant_entry_still_consumes_intent(self):
        with _phase2_creation_intent(self.document, self.identity):
            self.values["employee"] = "OTHER"
            with self.denied():
                with _insertion_attempt(self.document):
                    self.fail("Invalid managed identity accepted")
            self.values["employee"] = "EMP"
            self.assertIsNone(_current_insertion(self.document))
            with self.denied():
                with _insertion_attempt(self.document):
                    self.fail("Consumed intent restored after grant error")

    def test_nested_native_exception_restores_outer_and_revokes_inner(self):
        other = FakeDocument(dict(self.values, custom_telectro_booking_origin=""))
        with _phase2_creation_intent(self.document, self.identity):
            with _insertion_attempt(self.document) as outer:
                with self.assertRaises(RuntimeError):
                    with _insertion_attempt(other) as inner:
                        raise RuntimeError()
                self.assertFalse(inner.state.active)
                self.assertIs(_current_insertion(self.document), outer)
                self.assertIsNone(self.check(outer))

    def test_no_document_or_identity_mutation(self):
        before = copy.deepcopy(self.values)
        with _phase2_creation_intent(self.document, self.identity):
            with _insertion_attempt(self.document) as frame:
                self.assertIsNone(self.check(frame))
                with self.denied():
                    _complete_insertion(frame, self.document, None)
                _complete_insertion(frame, self.document, self.identity)
        self.assertEqual(self.values, before)
        self.assertEqual(self.identity, TechnicianBookingIdentity("tech", "EMP", "Company"))
        with self.assertRaises(FrozenInstanceError):
            frame.document = object()


class TestPersistedProvenanceReader(unittest.TestCase):
    def setUp(self):
        from unittest.mock import Mock, patch
        import types
        self.row = {
            "name": "TS", "custom_telectro_booking_origin": "Phase 2",
            "employee": "EMP", "company": "Company", "user": "tech", "docstatus": 0,
        }
        self.db = Mock()
        self.db.get_value.return_value = self.row
        self.fake = types.ModuleType("frappe")
        self.fake.db = self.db
        patcher = patch.dict("sys.modules", {"frappe": self.fake})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_exact_query_and_defensive_read_only_projection(self):
        before = copy.deepcopy(self.row)
        self.row["private"] = "not exposed"
        result = _load_persisted_provenance("TS")
        self.db.get_value.assert_called_once_with(
            "Timesheet", "TS",
            ["name", "custom_telectro_booking_origin", "employee", "company", "user", "docstatus"],
            as_dict=True, order_by=None, cache=False, for_update=True, skip_locked=False, wait=True,
        )
        self.assertEqual(dict(result), before)
        self.assertEqual([call[0] for call in self.db.method_calls], ["get_value"])
        with self.assertRaises(TypeError):
            result["name"] = "OTHER"
        self.assertEqual(self.row, dict(before, private="not exposed"))
        self.row["employee"] = "CHANGED"
        self.assertEqual(result["employee"], "EMP")

    def test_missing_row_only_none(self):
        self.db.get_value.return_value = None
        self.assertIsNone(_load_persisted_provenance("TS"))
        self.db.get_value.assert_called_once()

    def test_invalid_names_rejected_before_database_read(self):
        class NameString(str):
            pass
        for value in [None, "", " \t", 1, True, [], {}, NameString("TS")]:
            with self.subTest(value=value), self.assertRaises(BookingProvenanceError):
                _load_persisted_provenance(value)
        self.db.get_value.assert_not_called()

    def test_name_not_trimmed_and_record_identifier_must_match(self):
        self.row["name"] = " TS "
        result = _load_persisted_provenance(" TS ")
        self.assertEqual(result["name"], " TS ")
        self.assertEqual(self.db.get_value.call_args.args[1], " TS ")
        self.row["name"] = "TS"
        with self.assertRaisesRegex(BookingProvenanceError, "^Booking provenance is not permitted\\.$"):
            _load_persisted_provenance(" TS ")

    def test_invalid_or_incomplete_records_rejected(self):
        class MarkerString(str):
            pass
        invalid = [False, [], {}, dict(self.row, name="OTHER"),
                   dict(self.row, custom_telectro_booking_origin="forged"),
                   dict(self.row, custom_telectro_booking_origin=MarkerString("Phase 2")),
                   dict(self.row, employee=[]), dict(self.row, user={}),
                   dict(self.row, docstatus=True), dict(self.row, docstatus="0")]
        invalid += [{k: v for k, v in self.row.items() if k != field} for field in self.row]
        for row in invalid:
            with self.subTest(row=row):
                self.db.get_value.return_value = row
                with self.assertRaisesRegex(BookingProvenanceError, "^Booking provenance is not permitted\\.$"):
                    _load_persisted_provenance("TS")

    def test_native_nullable_fields_and_actual_docstatus_supported(self):
        self.row.update(custom_telectro_booking_origin=None, employee=None, user=None,
                        docstatus=DocStatus.SUBMITTED)
        result = _load_persisted_provenance("TS")
        self.assertIsNone(result["custom_telectro_booking_origin"])
        self.assertIsNone(result["employee"])
        self.assertEqual(result["docstatus"], 1)
        self.assertIs(type(result["docstatus"]), int)
        self.assertIs(self.row["docstatus"], DocStatus.SUBMITTED)

    def test_infrastructure_missing_column_and_lock_errors_propagate(self):
        for error in [RuntimeError("database unavailable"), RuntimeError("missing column"),
                      TimeoutError("lock timeout"), RuntimeError("deadlock")]:
            with self.subTest(error=error):
                self.db.get_value.side_effect = error
                with self.assertRaises(type(error)) as caught:
                    _load_persisted_provenance("TS")
                self.assertIs(caught.exception, error)


if __name__ == "__main__":
    unittest.main()
