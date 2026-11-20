"""Isolated admission and cleanup proof for the private booking boundary."""

import sys
import types
import unittest
from unittest.mock import patch

from telephony.time_booking_transaction import (
    BookingTransactionCleanupError,
    BookingTransactionDenied,
    _active_booking,
    _top_level_booking_transaction,
)


COMMAND = "telephony.booking.create"


class Database:
    def __init__(self):
        self.transaction_writes = 0
        self.pending = []
        self.rollbacks = 0
        self.failure = None

    def rollback(self):
        self.rollbacks += 1
        if self.failure:
            raise self.failure
        self.pending.clear()


class TestTopLevelBookingTransaction(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.request = types.SimpleNamespace(method="POST", path="/api/method/" + COMMAND)
        self.form_dict = types.SimpleNamespace(cmd=COMMAND)
        self.frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(request=self.request, form_dict=self.form_dict, db=self.db),
            session=types.SimpleNamespace(user="tech@example.com"),
        )
        self.module_patch = patch.dict(sys.modules, {"frappe": self.frappe})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def denied(self):
        with self.assertRaisesRegex(BookingTransactionDenied, r"^Technician booking is not available\.$"):
            with _top_level_booking_transaction(expected_command=COMMAND):
                self.fail("body entered")
        self.assertEqual(self.db.rollbacks, 0)
        self.assertFalse(_active_booking.get())

    def test_success_leaves_commit_to_frappe(self):
        with _top_level_booking_transaction(expected_command=COMMAND):
            self.assertTrue(_active_booking.get())
        self.assertEqual(self.db.rollbacks, 0)
        self.assertFalse(_active_booking.get())

    def test_rejects_non_post_and_wrong_routes(self):
        for method, path in (("GET", "/api/method/" + COMMAND), ("POST", "/api/resource/Timesheet"), ("POST", "/api/method/other")):
            self.request.method, self.request.path = method, path
            self.denied()

    def test_rejects_wrong_command_and_invalid_expected_command(self):
        self.form_dict.cmd = "other"
        self.denied()
        self.form_dict.cmd = COMMAND
        for value in (None, "", 1, "other"):
            with self.assertRaises(BookingTransactionDenied):
                with _top_level_booking_transaction(expected_command=value):
                    self.fail("body entered")

    def test_rejects_unauthenticated_or_unavailable_context(self):
        for user in (None, "", "Guest", "Administrator"):
            self.frappe.session.user = user
            self.denied()
        self.frappe.session.user = "tech@example.com"
        del self.frappe.local.request
        self.denied()

    def test_admits_preceding_counted_writes(self):
        self.db.transaction_writes = 1
        self.db.pending.append("earlier request write")
        with _top_level_booking_transaction(expected_command=COMMAND):
            self.db.pending.append("booking write")
        self.assertEqual(self.db.pending, ["earlier request write", "booking write"])
        self.assertEqual(self.db.rollbacks, 0)

    def test_failure_rolls_back_entire_request_including_uncounted_write(self):
        self.db.transaction_writes = 0
        self.db.pending.append("uncounted earlier write")
        with self.assertRaises(ValueError):
            with _top_level_booking_transaction(expected_command=COMMAND):
                self.db.pending.append("booking write")
                raise ValueError("booking failed")
        self.assertEqual(self.db.pending, [])
        self.assertEqual(self.db.rollbacks, 1)

    def test_rejects_nested_and_reentrant_calls(self):
        with _top_level_booking_transaction(expected_command=COMMAND):
            with self.assertRaises(BookingTransactionDenied):
                with _top_level_booking_transaction(expected_command=COMMAND):
                    self.fail("nested body entered")
            self.assertTrue(_active_booking.get())
        self.assertFalse(_active_booking.get())

    def test_failure_rolls_back_once_and_propagates(self):
        failure = ValueError("body failed")
        with self.assertRaises(ValueError) as caught:
            with _top_level_booking_transaction(expected_command=COMMAND):
                raise failure
        self.assertIs(caught.exception, failure)
        self.assertEqual(self.db.rollbacks, 1)
        self.assertFalse(_active_booking.get())

    def test_rollback_failure_is_fatal_and_chained(self):
        self.db.failure = OSError("rollback failed")
        original = ValueError("body failed")
        with self.assertRaises(BookingTransactionCleanupError) as caught:
            with _top_level_booking_transaction(expected_command=COMMAND):
                raise original
        self.assertIs(caught.exception.__cause__, self.db.failure)
        self.assertIs(self.db.failure.__context__, original)
        self.assertEqual(self.db.rollbacks, 1)
        self.assertFalse(_active_booking.get())

    def test_scope_revoked_after_failure_allows_new_entry(self):
        with self.assertRaises(ValueError):
            with _top_level_booking_transaction(expected_command=COMMAND):
                raise ValueError("failed")
        with _top_level_booking_transaction(expected_command=COMMAND):
            self.assertTrue(_active_booking.get())
        self.assertEqual(self.db.rollbacks, 1)
