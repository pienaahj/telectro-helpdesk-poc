"""Submitted booking cancellation endpoint regression tests."""

import sys
import types
import unittest
from unittest.mock import Mock, patch

from telephony.api import booking_correction as api
from telephony.time_booking_transaction import BookingTransactionDenied

class TestSubmittedBookingCancellation(unittest.TestCase):

    def test_get_rejected_without_database_mutation(self):
        command = api.PREFIX + "cancel_submitted_booking"

        db = types.SimpleNamespace(rollback=Mock())

        local = types.SimpleNamespace(
            request=types.SimpleNamespace(
                method="GET",
                path="/api/method/" + command,
            ),
            form_dict=types.SimpleNamespace(cmd=command),
            db=db,
        )

        fake_frappe = types.SimpleNamespace(
            local=local,
            session=types.SimpleNamespace(user="tech@example.com"),
        )

        with patch.dict(sys.modules, {"frappe": fake_frappe}):
            with self.assertRaises(BookingTransactionDenied):
                api.cancel_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="event-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                )

        db.rollback.assert_not_called()

    def test_owned_submitted_post_cancels_and_audits(self):
        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "cancel_submitted_booking"

        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:00:00"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        class SubmittedDoc:
            def __init__(self):
                self.flags = types.SimpleNamespace(ignore_permissions=False)

            def as_dict(self):
                return state

            def check_permission(self, permission):
                assert permission == "cancel"

            def cancel(self):
                state["docstatus"] = 2

        doc = SubmittedDoc()

        def sql(query, value, **kwargs):
            assert "FOR UPDATE" in query
            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]
            if "tabTELECTRO Booking Correction Audit" in query:
                return []
            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(user=identity.user),
            get_doc=Mock(return_value=doc),
        )

        def record(**kwargs):
            self.assertEqual(kwargs["action"], "Submitted Cancellation")
            self.assertEqual(kwargs["before"]["docstatus"], 1)
            self.assertEqual(state["docstatus"], 1)
            return "AUDIT-1"

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "TelectroBookingTimesheet", SubmittedDoc),
            patch.object(api, "record_correction_event", side_effect=record) as audit,
        ):
            result = api.cancel_submitted_booking.__wrapped__(
                timesheet_name="TS-1",
                event_id="event-1",
                reason="Incorrect submitted time",
                expected_modified="2026-11-17T12:00:00",
            )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )
        self.assertEqual(state["docstatus"], 2)
        audit.assert_called_once()
        db.rollback.assert_not_called()

    def test_stale_revision_rejected_without_cancellation_or_audit(self):
        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity
        from telephony.time_booking_ownership import BookingOwnershipError

        command = api.PREFIX + "cancel_submitted_booking"

        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:01:00"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        class SubmittedDoc:
            def __init__(self):
                self.check_permission = Mock()
                self.cancel = Mock()

            def as_dict(self):
                return state

        doc = SubmittedDoc()

        def sql(query, value, **kwargs):
            assert "FOR UPDATE" in query
            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]
            if "tabTELECTRO Booking Correction Audit" in query:
                return []
            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(user=identity.user),
            get_doc=Mock(return_value=doc),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "TelectroBookingTimesheet", SubmittedDoc),
            patch.object(api, "record_correction_event") as audit,
        ):
            with self.assertRaises(BookingOwnershipError):
                api.cancel_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="event-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                )

        fake_frappe.get_doc.assert_called_once_with(
            "Timesheet", "TS-1", for_update=True
        )
        doc.check_permission.assert_not_called()
        doc.cancel.assert_not_called()
        audit.assert_not_called()
        db.rollback.assert_called_once()
        self.assertEqual(state["docstatus"], 1)

    def test_audit_failure_prevents_cancellation_and_rolls_back(self):
        import copy

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "cancel_submitted_booking"

        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:00:00"
        original = copy.deepcopy(state)

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        class SubmittedDoc:
            def __init__(self):
                self.check_permission = Mock()
                self.cancel = Mock()
                self.flags = types.SimpleNamespace(ignore_permissions=False)

            def as_dict(self):
                return state

        doc = SubmittedDoc()

        def sql(query, value, **kwargs):
            assert "FOR UPDATE" in query

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(user=identity.user),
            get_doc=Mock(return_value=doc),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "TelectroBookingTimesheet", SubmittedDoc),
            patch.object(
                api,
                "record_correction_event",
                side_effect=RuntimeError("audit unavailable"),
            ) as audit,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "audit unavailable"
            ):
                api.cancel_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="event-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                )

        audit.assert_called_once()
        self.assertEqual(
            audit.call_args.kwargs["action"],
            "Submitted Cancellation",
        )
        self.assertEqual(
            audit.call_args.kwargs["before"]["docstatus"],
            1,
        )

        doc.check_permission.assert_not_called()
        self.assertIs(doc.flags.ignore_permissions, False)
        doc.cancel.assert_not_called()
        db.rollback.assert_called_once_with()

        self.assertEqual(state, original)

    def test_native_cancellation_failure_rolls_back_audit_and_booking(self):
        import copy

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "cancel_submitted_booking"

        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:00:00"
        original = copy.deepcopy(state)

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        pending_audits = []

        def record(**kwargs):
            assert kwargs["action"] == "Submitted Cancellation"
            assert kwargs["before"]["docstatus"] == 1
            pending_audits.append("AUDIT-1")
            return "AUDIT-1"

        def cancel():
            self.assertIs(doc.flags.ignore_permissions, True)
            state["docstatus"] = 2
            raise RuntimeError("native cancellation failed")

        def rollback():
            state.clear()
            state.update(copy.deepcopy(original))
            pending_audits.clear()

        class SubmittedDoc:
            def __init__(self):
                self.check_permission = Mock()
                self.cancel = Mock(side_effect=cancel)
                self.flags = types.SimpleNamespace(ignore_permissions=False)

            def as_dict(self):
                return state

        doc = SubmittedDoc()

        def sql(query, value, **kwargs):
            assert "FOR UPDATE" in query

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            rollback=Mock(side_effect=rollback),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(user=identity.user),
            get_doc=Mock(return_value=doc),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "TelectroBookingTimesheet", SubmittedDoc),
            patch.object(
                api, "record_correction_event", side_effect=record
            ) as audit,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "native cancellation failed"
            ):
                api.cancel_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="event-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                )

        audit.assert_called_once()
        doc.cancel.assert_called_once_with()
        db.rollback.assert_called_once_with()

        self.assertEqual(state, original)
        self.assertEqual(pending_audits, [])
        self.assertIs(doc.flags.ignore_permissions, False)

    def test_successful_cancellation_retry_is_idempotent(self):
        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_correction_audit import _snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "cancel_submitted_booking"

        before = snapshot(status=1)
        before["modified"] = "2026-11-17T12:00:00"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        prior = {
            "name": "AUDIT-1",
            "actor": identity.user,
            "action": "Submitted Cancellation",
            "reason": "Incorrect submitted time",
            "original_timesheet": "TS-1",
            "before_snapshot": _snapshot(before),
            "after_snapshot": None,
        }

        def sql(query, value, **kwargs):
            assert "FOR UPDATE" in query

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return [prior]

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(user=identity.user),
            get_doc=Mock(),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "record_correction_event") as audit,
        ):
            result = api.cancel_submitted_booking.__wrapped__(
                timesheet_name="TS-1",
                event_id="event-1",
                reason="Incorrect submitted time",
                expected_modified="2026-11-17T12:00:00",
            )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )

        fake_frappe.get_doc.assert_not_called()
        audit.assert_not_called()
        db.rollback.assert_not_called()
        # Reusing the same event with conflicting audit evidence
        # must fail without touching the Timesheet.
        prior["reason"] = "Conflicting cancellation reason"

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "record_correction_event") as second_audit,
        ):
            with self.assertRaises(api.BookingOwnershipError):
                api.cancel_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="event-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                )

        fake_frappe.get_doc.assert_not_called()
        second_audit.assert_not_called()
        db.rollback.assert_called_once_with()

    def test_foreign_technician_cannot_cancel_submitted_booking(self):
        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity
        from telephony.time_booking_ownership import BookingOwnershipError

        command = api.PREFIX + "cancel_submitted_booking"

        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:00:00"
        state["employee"] = "FOREIGN-EMP"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        class SubmittedDoc:
            def __init__(self):
                self.check_permission = Mock()
                self.cancel = Mock()

            def as_dict(self):
                return state

        doc = SubmittedDoc()

        def sql(query, value, **kwargs):
            assert "FOR UPDATE" in query

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(user=identity.user),
            get_doc=Mock(return_value=doc),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "TelectroBookingTimesheet", SubmittedDoc),
            patch.object(api, "record_correction_event") as audit,
        ):
            with self.assertRaises(BookingOwnershipError):
                api.cancel_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="event-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                )

        doc.check_permission.assert_not_called()
        doc.cancel.assert_not_called()
        audit.assert_not_called()
        db.rollback.assert_called_once_with()
        self.assertEqual(state["docstatus"], 1)

    def test_missing_revision_rejected_before_database_access(self):
        command = api.PREFIX + "cancel_submitted_booking"

        db = types.SimpleNamespace(
            sql=Mock(),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(
                user="tech@example.com"
            ),
            get_doc=Mock(),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=Mock()),
            patch.object(api, "record_correction_event") as audit,
        ):
            for revision in (None, ""):
                with self.subTest(expected_modified=revision):
                    with self.assertRaises(api.BookingInputError):
                        api.cancel_submitted_booking.__wrapped__(
                            timesheet_name="TS-1",
                            event_id="event-1",
                            reason="Incorrect submitted time",
                            expected_modified=revision,
                        )

        db.sql.assert_not_called()
        fake_frappe.get_doc.assert_not_called()
        audit.assert_not_called()

        # Each rejected POST enters the transaction boundary
        # and rolls back without making database changes.
        self.assertEqual(db.rollback.call_count, 2)

    def test_native_cancellation_failure_preserves_audit_permission_boundary(self):
        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:00:00"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )
        command = api.PREFIX + "cancel_submitted_booking"

        doc = types.SimpleNamespace(
            check_permission=Mock(),
            as_dict=Mock(return_value=state),
            cancel=Mock(),
            flags=types.SimpleNamespace(ignore_permissions=False),
        )

        def record(**kwargs):
            # Audit must run before temporary permission elevation.
            self.assertIs(doc.flags.ignore_permissions, False)
            self.assertEqual(
                kwargs["action"],
                "Submitted Cancellation",
            )
            return "AUDIT-1"

        def cancel():
            # Simulate a native failure inside the elevated scope.
            self.assertIs(doc.flags.ignore_permissions, True)
            raise PermissionError("native cancellation failed")

        doc.cancel.side_effect = cancel

        def sql(query, value, **kwargs):
            assert "FOR UPDATE" in query

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(
                user="tech@example.com"
            ),
            get_doc=Mock(return_value=doc),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(
                api,
                "_guard",
                return_value=identity,
            ),
            patch.object(
                api, "TelectroBookingTimesheet",
                types.SimpleNamespace,
            ),
            patch.object(
                api, "record_correction_event"
            ) as audit,
        ):
            with self.assertRaisesRegex(
                PermissionError, "native cancellation failed"
            ):
                api.cancel_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="event-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                )

        doc.check_permission.assert_not_called()
        doc.as_dict.assert_called_once_with()
        doc.cancel.assert_called_once_with()
        audit.assert_called_once()
        db.rollback.assert_called_once_with()

        # The permission override must not survive the failure.
        self.assertIs(doc.flags.ignore_permissions, False)
        self.assertEqual(state["docstatus"], 1)

    def test_owned_cancellation_uses_temporary_native_permission_scope(self):
        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "cancel_submitted_booking"

        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:00:00"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        class SubmittedDoc:
            def __init__(self):
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )
                self.permission_checks = []
                self.scope_active_during_cancel = False

            def as_dict(self):
                return state

            def check_permission(self, permission):
                self.permission_checks.append(permission)

                if not self.flags.ignore_permissions:
                    raise PermissionError(
                        f"Native {permission} permission denied"
                    )

            def cancel(self):
                self.scope_active_during_cancel = (
                    self.flags.ignore_permissions is True
                )

                # Simulate native write and cancellation checks.
                self.check_permission("write")
                self.check_permission("cancel")

                state["docstatus"] = 2

        doc = SubmittedDoc()

        def sql(query, value, **kwargs):
            assert "FOR UPDATE" in query

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(user=identity.user),
            get_doc=Mock(return_value=doc),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "TelectroBookingTimesheet", SubmittedDoc),
            patch.object(
                api,
                "record_correction_event",
                return_value="AUDIT-1",
            ) as audit,
        ):
            result = api.cancel_submitted_booking.__wrapped__(
                timesheet_name="TS-1",
                event_id="event-1",
                reason="Incorrect submitted time",
                expected_modified="2026-11-17T12:00:00",
            )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )

        self.assertTrue(doc.scope_active_during_cancel)
        self.assertIs(doc.flags.ignore_permissions, False)
        self.assertEqual(state["docstatus"], 2)

        audit.assert_called_once()
        db.rollback.assert_not_called()

    def test_pre_elevated_document_rejected(self):
        from telephony.time_booking_ownership import BookingOwnershipError

        class SubmittedDoc:
            def __init__(self):
                self.flags = types.SimpleNamespace(
                    ignore_permissions=True
                )
                self.cancel = Mock()

        doc = SubmittedDoc()

        token = api._active_booking.set(True)

        try:
            with patch.object(
                api, "TelectroBookingTimesheet", SubmittedDoc
            ):
                with self.assertRaises(BookingOwnershipError):
                    with api._authorized_native_cancellation(doc):
                        self.fail("Permission scope admitted")

        finally:
            api._active_booking.reset(token)

        # The helper must reject the document without changing
        # its pre-existing permission state.
        self.assertIs(doc.flags.ignore_permissions, True)
        doc.cancel.assert_not_called()

    def test_permission_scope_rejected_outside_booking_transaction(self):
        from telephony.time_booking_ownership import BookingOwnershipError

        class SubmittedDoc:
            def __init__(self):
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )
                self.cancel = Mock()

        doc = SubmittedDoc()

        # Simulate an ordinary Frappe execution context rather
        # than entry through the dedicated booking endpoint.
        self.assertFalse(api._active_booking.get())

        with patch.object(
            api, "TelectroBookingTimesheet", SubmittedDoc
        ):
            with self.assertRaises(BookingOwnershipError):
                with api._authorized_native_cancellation(doc):
                    self.fail("Permission scope admitted outside booking")

        # No privilege elevation may survive or occur.
        self.assertIs(doc.flags.ignore_permissions, False)
        doc.cancel.assert_not_called()
        self.assertFalse(api._active_booking.get())
