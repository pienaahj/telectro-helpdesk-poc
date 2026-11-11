import importlib.util
import json
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "data_request_completion.py"
FIXTURE_PATH = ROOT / "fixtures/custom_field.json"
FIELD = "custom_data_request_first_completed_on"
STAMP = datetime(2026, 10, 29, 19, 30)


class FakeTicket:
    def __init__(
        self, status="Resolved", area="Data Request",
        stamp=None, previous=None, new=False,
        doctype="HD Ticket",
    ):
        self.doctype = doctype
        self.name = "TEST-DATA-REQUEST"
        self._new = new
        self._previous = previous
        self._values = {
            "status": status,
            "custom_service_area": area,
            FIELD: stamp,
        }

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value

    def is_new(self):
        return self._new

    def get_doc_before_save(self):
        return self._previous


class TestDataRequestCompletion(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType("frappe")
        utils = types.ModuleType("frappe.utils")

        self.frappe.PermissionError = type(
            "FrappePermissionError", (Exception,), {}
        )
        self.frappe.ValidationError = type(
            "FrappeValidationError", (Exception,), {}
        )

        def throw(message, error_type):
            raise error_type(message)

        self.frappe.throw = throw
        self.frappe.db = types.SimpleNamespace(
            get_value=mock.Mock(return_value=None)
        )

        self.clock = mock.Mock(return_value=STAMP)
        utils.now_datetime = self.clock
        self.frappe.utils = utils

        with mock.patch.dict(
            sys.modules,
            {"frappe": self.frappe, "frappe.utils": utils},
        ):
            spec = importlib.util.spec_from_file_location(
                "_data_request_completion_under_test",
                MODULE_PATH,
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        self.subject = module.capture_first_completion

    def ticket(
        self, old="Open", current="Resolved",
        old_stamp=None, stamp=None,
        area="Data Request", created=False,
    ):
        previous = None
        if old is not None:
            previous = {
                "status": old,
                FIELD: old_stamp,
            }
        return FakeTicket(
            status=current,
            area=area,
            stamp=stamp,
            previous=previous,
            new=created,
        )

    def test_first_completion_from_open_or_replied(self):
        for old in ("Open", "Replied"):
            with self.subTest(old=old):
                self.clock.reset_mock()
                doc = self.ticket(old=old)
                self.subject(doc)
                self.assertEqual(doc.get(FIELD), STAMP)
                self.clock.assert_called_once_with()

    def test_non_completion_statuses_remain_unstamped(self):
        for current in ("Open", "Replied", "Closed", "Archived"):
            with self.subTest(current=current):
                doc = self.ticket(current=current)
                self.subject(doc)
                self.assertIsNone(doc.get(FIELD))
        self.clock.assert_not_called()

    def test_unrelated_service_area_is_silent(self):
        doc = self.ticket(area="Routing")
        self.subject(doc)
        self.assertIsNone(doc.get(FIELD))
        self.clock.assert_not_called()

    def test_new_ticket_rejects_prepopulated_audit(self):
        clean = self.ticket(old=None, created=True)
        self.subject(clean)
        self.assertIsNone(clean.get(FIELD))

        spoofed = self.ticket(
            old=None, created=True, stamp=STAMP
        )
        with self.assertRaises(self.frappe.PermissionError):
            self.subject(spoofed)

        self.clock.assert_not_called()

    def test_existing_stamp_survives_later_transitions(self):
        transitions = (
            ("Resolved", "Open"),
            ("Resolved", "Closed"),
            ("Open", "Resolved"),
        )
        for old, current in transitions:
            with self.subTest(old=old, current=current):
                doc = self.ticket(
                    old=old,
                    current=current,
                    old_stamp=STAMP,
                    stamp=STAMP,
                )
                self.subject(doc)
                self.assertEqual(doc.get(FIELD), STAMP)
        self.clock.assert_not_called()

    def test_manual_timestamp_modification_is_rejected(self):
        for replacement in (
            None,
            datetime(2026, 10, 29, 19, 31),
        ):
            with self.subTest(replacement=replacement):
                doc = self.ticket(
                    old_stamp=STAMP,
                    stamp=replacement,
                )
                with self.assertRaises(
                    self.frappe.PermissionError
                ):
                    self.subject(doc)
        self.clock.assert_not_called()

    def test_database_fallback_for_previous_state(self):
        self.frappe.db.get_value.return_value = {
            "status": "Open",
            FIELD: None,
        }
        doc = self.ticket(old=None)
        self.subject(doc)
        self.assertEqual(doc.get(FIELD), STAMP)
        self.frappe.db.get_value.assert_called_once()

    def test_missing_previous_state_fails_closed(self):
        doc = self.ticket(old=None)
        with self.assertRaises(
            self.frappe.ValidationError
        ):
            self.subject(doc)
        self.clock.assert_not_called()

    def test_non_ticket_document_is_ignored(self):
        doc = FakeTicket(doctype="ToDo")
        self.subject(doc)
        self.clock.assert_not_called()
        self.frappe.db.get_value.assert_not_called()

    def test_fixture_field_contract(self):
        rows = json.loads(FIXTURE_PATH.read_text())
        matching = [
            row for row in rows
            if row.get("name") == "HD Ticket-" + FIELD
        ]
        self.assertEqual(len(matching), 1)
        field = matching[0]
        self.assertEqual(field["fieldtype"], "Datetime")
        self.assertEqual(field["hidden"], 1)
        self.assertEqual(field["read_only"], 1)
        self.assertEqual(field["no_copy"], 1)


if __name__ == "__main__":
    unittest.main()
