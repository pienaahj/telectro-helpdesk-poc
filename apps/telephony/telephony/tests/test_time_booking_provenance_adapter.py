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

if __name__ == "__main__":
    unittest.main()
