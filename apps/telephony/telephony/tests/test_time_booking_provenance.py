"""Deterministic provenance and context isolation tests; no Frappe imports."""

import asyncio
import copy
import unittest
from contextvars import Context, copy_context
from types import MappingProxyType

from telephony.time_booking_identity import TechnicianBookingIdentity
from telephony.time_booking_provenance import (
    BookingProvenanceError,
    _complete_creation,
    _creation_authorization,
    validate_provenance_transition,
)


MARKER = "custom_telectro_booking_origin"


class TestBookingProvenance(unittest.TestCase):
    def setUp(self):
        self.identity = TechnicianBookingIdentity("tech", "EMP-1", "Company")
        self.doc = {
            "doctype": "Timesheet", "name": "TS-1", "docstatus": 0,
            "employee": "EMP-1", "company": "Company", "user": "tech",
            MARKER: "Phase 2",
        }

    def check(self, doc=None, *, persisted=None, identity=None):
        return validate_provenance_transition(
            self.doc if doc is None else doc, persisted=persisted,
            identity=self.identity if identity is None else identity,
        )

    def denied(self, *args, **kwargs):
        with self.assertRaises(BookingProvenanceError) as caught:
            self.check(*args, **kwargs)
        self.assertEqual(str(caught.exception), "Booking provenance is not permitted.")

    def test_native_creation_blank_forms(self):
        for doc in [{}, {MARKER: None}, {MARKER: ""}]:
            with self.subTest(doc=doc):
                self.assertIsNone(self.check(doc))

    def test_existing_native_blank_equivalence_and_identity_freedom(self):
        for old in [None, ""]:
            for new in [None, ""]:
                with self.subTest(old=old, new=new):
                    self.assertIsNone(self.check(
                        {MARKER: new, "employee": "OTHER", "user": "OTHER"},
                        persisted={MARKER: old, "employee": "LEGACY"},
                    ))

    def test_all_managed_to_blank_transitions_rejected(self):
        for doc in [{}, {MARKER: None}, {MARKER: ""}]:
            with self.subTest(doc=doc):
                self.denied(doc, persisted=self.doc)

    def test_legacy_adoption_rejected_even_with_grant(self):
        with _creation_authorization(self.doc, self.identity):
            for previous in [{}, {MARKER: None}, {MARKER: ""}]:
                with self.subTest(previous=previous):
                    self.denied(persisted=previous)

    def test_managed_marker_and_identities_preserved_without_grant(self):
        for status in [0, 1, 2]:
            with self.subTest(status=status):
                self.assertIsNone(self.check(
                    {**self.doc, "docstatus": status}, persisted=self.doc,
                ))

    def test_unknown_markers_rejected_in_each_position(self):
        for value in [" ", "Unknown", "phase 2", False, True, 1, [], {}]:
            with self.subTest(value=value):
                self.denied({**self.doc, MARKER: value})
                self.denied({**self.doc, MARKER: value}, persisted=self.doc)
                for proposed in [None, "", "Phase 2", "Unknown"]:
                    self.denied(
                        {**self.doc, MARKER: proposed},
                        persisted={**self.doc, MARKER: value},
                    )

    def test_marked_creation_without_grant(self):
        self.denied()

    def test_authorized_creation_and_repeated_events(self):
        with _creation_authorization(self.doc, self.identity):
            for _ in range(3):
                self.assertIsNone(self.check())
            _complete_creation(self.doc, self.identity)
            self.denied()

    def test_different_document_same_values_rejected(self):
        with _creation_authorization(self.doc, self.identity):
            self.denied(copy.deepcopy(self.doc))
            self.assertIsNone(self.check())

    def test_mismatched_identity_rejected(self):
        with _creation_authorization(self.doc, self.identity):
            for identity in [
                TechnicianBookingIdentity("OTHER", "EMP-1", "Company"),
                TechnicianBookingIdentity("tech", "OTHER", "Company"),
                TechnicianBookingIdentity("tech", "EMP-1", "OTHER"),
            ]:
                with self.subTest(identity=identity):
                    self.denied(identity=identity)

    def test_forged_creation_identifiers_rejected(self):
        for field in ["employee", "company", "user"]:
            with self.subTest(field=field):
                with _creation_authorization(self.doc, self.identity):
                    self.doc[field] = "SECRET-FOREIGN"
                    self.denied()
                self.setUp()

    def test_invalid_creation_grants_rejected(self):
        for changes in [
            {"docstatus": 1}, {"docstatus": 2}, {"docstatus": True},
            {"docstatus": "0"}, {"doctype": "Other"},
            {"employee": "FOREIGN"}, {MARKER: ""},
        ]:
            with self.subTest(changes=changes):
                with self.assertRaises(BookingProvenanceError):
                    with _creation_authorization({**self.doc, **changes}, self.identity):
                        self.fail("Invalid grant entered")

    def test_existing_managed_identity_reassignment_rejected(self):
        for field in ["employee", "company", "user"]:
            for value in [None, "", "OTHER"]:
                with self.subTest(field=field, value=value):
                    self.denied({**self.doc, field: value}, persisted=self.doc)

    def test_invalid_persisted_managed_identity_rejected(self):
        for field in ["employee", "company", "user"]:
            with self.subTest(field=field):
                previous = {**self.doc, field: ""}
                self.denied(previous, persisted=previous)

    def test_nested_grants_rejected_without_revoking_outer(self):
        with _creation_authorization(self.doc, self.identity):
            with self.assertRaises(BookingProvenanceError):
                with _creation_authorization(self.doc, self.identity):
                    self.fail("Nested grant entered")
            self.assertIsNone(self.check())

    def test_completion_cannot_be_reused(self):
        with _creation_authorization(self.doc, self.identity):
            self.assertIsNone(self.check())
            _complete_creation(self.doc, self.identity)
            self.denied()
            with self.assertRaises(BookingProvenanceError):
                _complete_creation(self.doc, self.identity)
        self.denied()

    def test_exception_cleanup_and_propagation(self):
        error = RuntimeError("insertion failed")
        with self.assertRaises(RuntimeError) as caught:
            with _creation_authorization(self.doc, self.identity):
                self.assertIsNone(self.check())
                raise error
        self.assertIs(caught.exception, error)
        self.denied()
        with _creation_authorization(self.doc, self.identity):
            self.assertIsNone(self.check())

    def test_scope_exit_revokes_without_completion(self):
        with _creation_authorization(self.doc, self.identity):
            self.assertIsNone(self.check())
            inherited = copy_context()
        self.denied()
        with self.assertRaises(BookingProvenanceError):
            inherited.run(self.check)

    def test_independent_contexts_do_not_share_authorization(self):
        one, two = Context(), Context()
        def attempt():
            with _creation_authorization(self.doc, self.identity):
                self.assertIsNone(self.check())
                with self.assertRaises(BookingProvenanceError):
                    two.run(self.check)
                two.run(independent_attempt)
                self.assertIsNone(self.check())
        def independent_attempt():
            other = copy.deepcopy(self.doc)
            with _creation_authorization(other, self.identity):
                self.assertIsNone(self.check(other))
                _complete_creation(other, self.identity)
        one.run(attempt)
        self.denied()

    def test_async_child_task_cannot_inherit_permission(self):
        async def child():
            with self.assertRaises(BookingProvenanceError):
                self.check()
        async def parent():
            with _creation_authorization(self.doc, self.identity):
                await asyncio.create_task(child())
                self.assertIsNone(self.check())
        asyncio.run(parent())

    def test_completion_wrong_document_or_identity_rejected(self):
        with _creation_authorization(self.doc, self.identity):
            for doc, identity in [
                (copy.deepcopy(self.doc), self.identity),
                (self.doc, TechnicianBookingIdentity("OTHER", "EMP-1", "Company")),
            ]:
                with self.subTest(identity=identity):
                    with self.assertRaises(BookingProvenanceError):
                        _complete_creation(doc, identity)
            self.assertIsNone(self.check())

    def test_input_immutability_on_success_and_failure(self):
        before = copy.deepcopy(self.doc)
        view = MappingProxyType(self.doc)
        with _creation_authorization(view, self.identity):
            self.assertIsNone(self.check(view))
        self.assertEqual(self.doc, before)
        previous = copy.deepcopy(self.doc)
        invalid = {**self.doc, "employee": "OTHER"}
        invalid_before = copy.deepcopy(invalid)
        self.denied(MappingProxyType(invalid), persisted=MappingProxyType(previous))
        self.assertEqual(previous, before)
        self.assertEqual(invalid, invalid_before)

    def test_generic_denial_no_foreign_identifiers(self):
        self.denied({**self.doc, "name": "SECRET", "employee": "SECRET",
                     "company": "SECRET", "user": "SECRET"})

    def test_non_mapping_snapshots_fail_closed(self):
        for doc in [[], 42, "Phase 2"]:
            with self.subTest(doc=doc):
                self.denied(doc)
                self.denied(persisted=doc)


    def test_custom_equality_and_string_subclasses_rejected(self):
        class EqualToMarker:
            def __init__(self, target):
                self.target = target

            def __eq__(self, other):
                return other == self.target

        class MarkerString(str):
            pass

        for value in [EqualToMarker(""), EqualToMarker("Phase 2"),
                      MarkerString("Phase 2")]:
            with self.subTest(marker_type=type(value).__name__):
                # Ordinary creation and existing-document transitions.
                self.denied({**self.doc, MARKER: value})
                self.denied({**self.doc, MARKER: value}, persisted=self.doc)
                for proposed in [None, "", "Phase 2"]:
                    self.denied(
                        {**self.doc, MARKER: proposed},
                        persisted={**self.doc, MARKER: value},
                    )
                # Reject mutation of the exact object in a valid grant.
                document = copy.deepcopy(self.doc)
                with _creation_authorization(document, self.identity):
                    self.assertIsNone(self.check(document))
                    document[MARKER] = value
                    self.denied(document)
                # Reject forged markers before a grant can be issued.
                with self.assertRaises(BookingProvenanceError):
                    with _creation_authorization(
                        {**self.doc, MARKER: value}, self.identity
                    ):
                        self.fail("Forged marker obtained a grant")

if __name__ == "__main__":
    unittest.main()
