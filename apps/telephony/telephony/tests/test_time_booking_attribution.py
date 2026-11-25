"""No-site attribution contract, native hook policy and managed API wiring."""

from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from telephony import time_booking_attribution as attribution
from telephony.api import booking_correction, time_booking
from telephony.tests import test_project_booking_authorization as authorization
from telephony.tests.test_time_booking_correction_audit import snapshot
from telephony.time_booking_provenance import BookingProvenanceError
from telephony.time_booking_ticket_interval import ORIGIN_FIELD

FIELD = attribution.FIELD
START = authorization.START
END = authorization.END


class Row(dict):
    def set(self, name, value):
        self[name] = value


def detail(**values):
    return Row(
        dict(name="DETAIL", parent="TS", parenttype="Timesheet", parentfield="time_logs",
             custom_work_context="Helpdesk", custom_hd_ticket="1", from_time=START,
             to_time=END, **{FIELD: -1}) | values
    )


class TestAttribution(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(attribution, "schema_ready", return_value=True)
        self.ready = patcher.start()
        self.addCleanup(patcher.stop)

    def prepare(self, *args, **kwargs):
        with patch.object(attribution, "_require_child_protection"):
            return attribution.prepare_attribution(*args, **kwargs)

    def test_installed_field_requires_the_complete_child_guard_registration(self):
        registered = {event: [attribution.CHILD_HANDLER] for event in attribution.CHILD_EVENTS}
        with patch.object(attribution, "frappe", SimpleNamespace(
            get_doc_hooks=lambda: {attribution.DETAIL: registered},
        )):
            self.assertEqual(attribution.prepare_attribution(detail(), START, END, portion=timedelta()), {FIELD: 0})
            del registered["before_validate"]
            with self.assertRaises(attribution.AttributionUnavailable):
                attribution.prepare_attribution(detail(), START, END, portion=timedelta())

    def test_exact_positive_zero_and_maximum(self):
        row = detail()
        for end, portion, expected in (
            (END, timedelta(microseconds=1000001), 1000001),
            (END, timedelta(), 0),
            (START + timedelta(days=1), timedelta(days=1), 86400000000),
        ):
            with self.subTest(portion=portion):
                values = self.prepare(row, START, end, portion=portion)
                self.assertEqual(values, {FIELD: expected})
                self.assertEqual(attribution.attribution_response(row | values | {"to_time": end}),
                                 {"pre_creation_us": expected})
        self.assertEqual(attribution.attribution_response(row), {"pre_creation_us": None})

    def test_stored_value_must_be_exact_and_within_interval(self):
        row = detail()
        for invalid in (-2, True, "0", 3.0, 3600000001, 86400000001, None):
            previous = row | {FIELD: invalid}
            self.assertEqual(attribution.attribution_response(previous), {"pre_creation_us": None})
            with self.subTest(invalid=invalid), self.assertRaises(attribution.AttributionUnavailable):
                self.prepare(row, START, END, portion=None, previous=previous)
        for invalid in (None, timedelta(microseconds=-1), timedelta(hours=1, microseconds=1)):
            with self.subTest(invalid=invalid), self.assertRaises(attribution.AttributionUnavailable):
                self.prepare(row, START, END, portion=invalid)

    def test_unchanged_legacy_zero_positive_and_transition(self):
        row = detail()
        for value in (-1, 0, 1000001):
            previous = row | {FIELD: value}
            self.assertEqual(self.prepare(row, START, END, portion=None, previous=previous),
                             {FIELD: value})
        previous = row.copy()
        previous.pop(FIELD)
        self.assertEqual(self.prepare(row, START, END, portion=None, previous=previous), {FIELD: -1})
        non_helpdesk = row | {"custom_work_context": "Project"}
        self.assertEqual(self.prepare(non_helpdesk, START, END, portion=None, previous=row), {FIELD: -1})
        self.assertEqual(attribution.attribution_response(non_helpdesk), {})

    def test_missing_schema_blocks_required_persistence_only(self):
        self.ready.return_value = False
        row = detail()
        with self.assertRaises(attribution.AttributionUnavailable):
            self.prepare(row, START, END, portion=timedelta())
        self.assertEqual(self.prepare(row, START, END, portion=None, previous=row), {})
        self.assertEqual(self.prepare(row | {"custom_work_context": "Project"},
                                                          START, END, portion=None), {})

    def test_owned_history_attribution_survives_missing_ticket_reference(self):
        row = detail(custom_hd_ticket=None, **{FIELD: 1000001})
        self.assertEqual(attribution.attribution_response(row), {"pre_creation_us": 1000001})

    def test_snapshot_does_not_project_missing_raw_value_as_zero(self):
        row = detail(**{FIELD: None})
        doc = SimpleNamespace(time_logs=[row], as_dict=lambda: {"time_logs": [{FIELD: 0}]})
        self.assertNotIn(FIELD, attribution.booking_snapshot(doc)["time_logs"][0])
        row[FIELD] = 0
        self.assertEqual(attribution.booking_snapshot(doc)["time_logs"][0][FIELD], 0)


class TestAttributionGuards(unittest.TestCase):
    def setUp(self):
        self.stored = detail(**{FIELD: 1000001})
        self.row = Row(self.stored)
        self.doc = Row(name="TS", time_logs=[self.row])
        self.doc.time_logs = self.doc["time_logs"]
        self.db = SimpleNamespace(get_values=Mock(return_value=[self.stored]))
        for patcher in (
            patch.object(attribution, "frappe", SimpleNamespace(db=self.db)),
            patch.object(attribution, "_native_schema_ready", return_value=True),
            patch.object(attribution, "_stored_row", return_value=self.stored),
            patch.object(attribution, "_is_managed_parent", side_effect=lambda name: name == "TS"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def parent(self, *, inserting=False, managed=True, doc=None):
        attribution.protect_parent(doc if doc is not None else self.doc, inserting=inserting,
                                   managed=managed, method="before_save")

    def test_generic_parent_edits_cannot_change_attribution_interval_reference_or_child_identity(self):
        self.parent()
        for changes in (
            {FIELD: 0}, {FIELD: -1}, {FIELD: None}, {FIELD: 1000002},
            {"from_time": START + timedelta(seconds=1)}, {"to_time": END + timedelta(seconds=1)},
            {"custom_hd_ticket": "2"}, {"custom_work_context": "Project"}, {"name": "SUBSTITUTE"},
        ):
            self.row.clear()
            self.row.update(self.stored | changes)
            with self.subTest(changes=changes), self.assertRaises(BookingProvenanceError):
                self.parent()
        self.doc["time_logs"] = []
        with self.assertRaises(BookingProvenanceError):
            self.parent()

    def test_generic_parent_cannot_establish_confirmed_zero_from_unknown(self):
        self.stored[FIELD] = -1
        self.row[FIELD] = 0
        with self.assertRaises(BookingProvenanceError):
            self.parent()

    def test_unmanaged_parent_rejects_adopting_managed_detail_but_preserves_ordinary_native_row(self):
        outsider = Row(name="OTHER", time_logs=[self.row])
        with self.assertRaises(BookingProvenanceError):
            self.parent(managed=False, doc=outsider)
        attribution._stored_row.return_value = None
        self.row[FIELD] = None
        self.parent(managed=False, doc=outsider)
        self.assertEqual(self.row[FIELD], -1)

    def test_managed_insert_requires_bound_value_and_checks_persisted_row(self):
        attribution._stored_row.return_value = None
        with self.assertRaises(BookingProvenanceError):
            self.parent(inserting=True)
        with attribution.authorized_attribution(self.doc, {FIELD: self.row[FIELD]}):
            self.parent(inserting=True)
            attribution._stored_row.return_value = self.stored
        with self.assertRaises(BookingProvenanceError), attribution.authorized_attribution(self.doc, {FIELD: self.row[FIELD]}):
            attribution._stored_row.return_value = self.stored | {FIELD: 0}

    def test_scope_does_not_allow_a_different_child_or_outlive_the_write(self):
        self.row[FIELD] = 0
        with attribution.authorized_attribution(self.doc, {FIELD: 0}):
            original_rows = self.doc["time_logs"]
            self.doc["time_logs"] = [Row(self.row)]
            with self.assertRaises(BookingProvenanceError):
                self.parent()
            self.doc["time_logs"] = original_rows
            self.parent()
            self.stored[FIELD] = 0
        self.stored[FIELD] = -1
        with self.assertRaises(BookingProvenanceError):
            self.parent()

    def test_direct_child_current_or_proposed_managed_parent_is_protected(self):
        for method in ("before_insert", "before_validate", "before_save", "before_change", "on_trash"):
            with self.subTest(method=method), self.assertRaises(BookingProvenanceError):
                attribution.protect_child(self.row, method)
        self.row["parent"] = "OTHER"
        with self.assertRaises(BookingProvenanceError):
            attribution.protect_child(self.row, "before_save")
        self.row["parent"] = "TS"
        attribution._stored_row.return_value = self.stored | {"parent": "OTHER"}
        with self.assertRaises(BookingProvenanceError):
            attribution.protect_child(self.row, "before_save")

    def test_native_child_allows_unset_but_cannot_establish_attribution(self):
        attribution._stored_row.return_value = None
        self.row.update(parent="OTHER", **{FIELD: None})
        attribution.protect_child(self.row, "before_validate")
        self.assertEqual(self.row[FIELD], -1)
        for value in (0, 1, -2):
            self.row[FIELD] = value
            with self.assertRaises(BookingProvenanceError):
                attribution.protect_child(self.row, "before_validate")

    def test_no_schema_leaves_native_hooks_inert(self):
        attribution._native_schema_ready.return_value = False
        self.parent()
        attribution.protect_child(self.row, "before_save")
        attribution._stored_row.assert_not_called()

    def test_physical_attribution_is_protected_even_if_metadata_is_absent(self):
        fake = SimpleNamespace(db=SimpleNamespace(has_column=lambda *_: True))
        with patch.object(attribution, "frappe", fake), patch.object(
            attribution, "_native_schema_ready", wraps=REAL_NATIVE_READY,
        ):
            self.assertTrue(attribution._native_schema_ready((self.row,)))

    def test_partial_schema_omits_column_only_for_current_native_documents(self):
        meta = SimpleNamespace(has_field=lambda _: True, get_valid_columns=lambda: ["name", FIELD],
                               _valid_columns=["name", FIELD])
        fake = SimpleNamespace(get_meta=lambda _: meta, db=SimpleNamespace(has_column=lambda *_: False))
        with patch.object(attribution, "frappe", fake), patch.object(
            attribution, "_native_schema_ready", wraps=REAL_NATIVE_READY,
        ):
            self.assertFalse(attribution._native_schema_ready([self.row]))
        self.assertEqual(self.row.meta._valid_columns, ["name"])
        self.assertEqual(meta._valid_columns, ["name", FIELD])


REAL_NATIVE_READY = attribution._native_schema_ready


class TestManagedAttributionIntegration(unittest.TestCase):
    def setUp(self):
        self.booking = authorization.TestProjectBookingAuthorization()
        self.booking.setUp()
        self.addCleanup(self.booking.doCleanups)
        for patcher in (
            patch.object(time_booking, "prepare_attribution", attribution.prepare_attribution),
            patch.object(booking_correction, "prepare_attribution", attribution.prepare_attribution),
            patch.object(attribution, "schema_ready", return_value=True),
            patch.object(attribution, "_require_child_protection"),
            patch.object(attribution, "_stored_row", side_effect=self.persisted_child),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def persisted_child(self, name):
        doc = self.booking.inserted[-1] if self.booking.mutations[-1] == "insert" else self.booking.original
        return doc.time_logs[0] | {"parent": doc.name, "parenttype": "Timesheet", "parentfield": "time_logs"}

    def original(self, submitted, value, *, start=START, end=END):
        data = snapshot(status=int(submitted))
        data["modified"] = authorization.REVISION
        data["time_logs"][0].update(
            custom_hd_ticket=self.booking.ticket.name, from_time=start, to_time=end,
            activity_type=authorization.ACTIVITY, **{FIELD: value},
        )
        self.booking.original = self.booking.Timesheet(data)
        return self.booking.original

    def test_create_exact_portion_and_unchanged_total(self):
        self.booking.current_ticket.update(creation=START + timedelta(microseconds=1000001),
                                           **{ORIGIN_FIELD: 1})
        result = self.booking.call_helpdesk("create")
        self.assertEqual(result["pre_creation_us"], 1000001)
        row = self.booking.inserted[0].time_logs[0]
        self.assertEqual(row[FIELD], 1000001)
        self.assertEqual(row["hours"], 1.0)

    def test_draft_unchanged_and_changed_work(self):
        old = self.original(False, 0)
        result = self.booking.call_helpdesk("correct", description="description only")
        self.assertEqual(old.time_logs[0][FIELD], 0)
        self.assertEqual(self.booking.audit["name"], result["audit"])
        self.booking.audit = {}
        self.booking.current_ticket.update(creation=START + timedelta(microseconds=1000001),
                                           **{ORIGIN_FIELD: 1})
        self.booking.call_helpdesk("correct", from_time=(START - timedelta(minutes=1)).isoformat())
        self.assertEqual(old.time_logs[0][FIELD], 61000001)
        self.assertEqual(old.time_logs[0]["hours"], 1.0)

    def test_replacement_exact_carry_forward_and_replay(self):
        for value in (1000001, 0, -1):
            with self.subTest(value=value):
                self.original(True, value)
                self.booking.audit = {}
                self.booking.mutations.clear()
                self.booking.inserted.clear()
                with patch.object(time_booking, "validate_ticket_interval") as validator:
                    result = self.booking.call_helpdesk("replace")
                    self.assertEqual(self.booking.inserted[0].time_logs[0][FIELD], value)
                    self.assertEqual(self.booking.call_helpdesk("replace"), result)
                    validator.assert_not_called()
                self.assertEqual(len(self.booking.inserted), 1)

    def test_changed_replacement_recalculates_and_cannot_consume_client_field(self):
        original = self.original(True, 1000001)
        before = deepcopy(original.as_dict())
        with self.assertRaises(TypeError):
            self.booking.call_helpdesk("replace", **{FIELD: 1})
        self.assertEqual(original.as_dict(), before)
        self.booking.current_ticket.update(creation=START + timedelta(microseconds=42), **{ORIGIN_FIELD: 1})
        self.booking.call_helpdesk("replace", from_time=(START - timedelta(minutes=1)).isoformat())
        self.assertEqual(self.booking.inserted[0].time_logs[0][FIELD], 60000042)
        self.assertEqual(original.time_logs[0][FIELD], 1000001)

    def test_failed_changed_correction_retains_original_and_attribution(self):
        original = self.original(True, 1000001)
        before = deepcopy(original.as_dict())
        attribution.schema_ready.return_value = False
        with self.assertRaises(attribution.AttributionUnavailable):
            self.booking.call_helpdesk("replace", from_time=(START - timedelta(minutes=1)).isoformat())
        self.assertEqual(original.as_dict(), before)
        self.assertEqual(self.booking.mutations, [])
        self.assertEqual(self.booking.inserted, [])
        self.booking.db.rollback.assert_called_once_with()
