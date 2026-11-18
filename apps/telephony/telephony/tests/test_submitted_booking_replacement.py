"""Submitted booking replacement endpoint regression tests."""

import sys
import types
import unittest
from unittest.mock import Mock, patch

from telephony.api import booking_correction as api
from telephony.time_booking_transaction import BookingTransactionDenied


class TestSubmittedBookingReplacement(unittest.TestCase):

    def test_revision_matches_frappe_and_audit_formats(self):
        from telephony.api.booking_correction import _revision_matches

        iso = "2026-11-18T17:59:29.129381"
        http = "2026-11-18 17:59:29.129381"

        self.assertTrue(_revision_matches(iso, http))
        self.assertTrue(_revision_matches(http, iso))

        for stale in (
            "2026-11-18 17:59:29.129380",
            "2026-11-18 17:59:29.129382",
            "2026-11-18 17:59:29",
        ):
            self.assertFalse(_revision_matches(iso, stale))

        for invalid in (
            None,
            "",
            "invalid",
            123,
            "2026-11-18T17:59:29.129381+02:00",
        ):
            self.assertFalse(_revision_matches(iso, invalid))

        self.assertFalse(_revision_matches(None, http))

    def test_get_rejected_without_database_mutation(self):
        command = api.PREFIX + "replace_submitted_booking"

        db = types.SimpleNamespace(
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="GET",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            session=types.SimpleNamespace(
                user="tech@example.com",
            ),
        )

        with patch.dict(sys.modules, {"frappe": fake_frappe}):
            with self.assertRaises(BookingTransactionDenied):
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17 12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=90,
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-1",
                )

        # HTTP rejection must happen before transaction mutation.
        db.rollback.assert_not_called()

    def test_post_fails_closed_before_database_mutation(self):
        command = api.PREFIX + "replace_submitted_booking"

        db = types.SimpleNamespace(
            sql=Mock(),
            commit=Mock(),
            rollback=Mock(),
        )

        fake_frappe = types.SimpleNamespace(
            conf={},
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(cmd=command),
                db=db,
            ),
            session=types.SimpleNamespace(
                user="tech@example.com",
            ),
            get_doc=Mock(),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
        ):
            with self.assertRaises(api.ActivationConfigurationError):
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=90,
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-1",
                )

        # No database reads or writes may occur.
        db.sql.assert_not_called()
        fake_frappe.get_doc.assert_not_called()
        db.commit.assert_not_called()

        # An exception inside the top-level transaction must abort it.
        db.rollback.assert_called_once()

    def test_foreign_technician_cannot_replace_submitted_booking(self):
        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity
        from telephony.time_booking_ownership import BookingOwnershipError

        command = api.PREFIX + "replace_submitted_booking"

        # Persisted booking belongs to tech@example.com.
        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:00:00"

        # A different authenticated Technician attempts replacement.
        identity = TechnicianBookingIdentity(
            "other@example.com", "EMP-2", "Company A"
        )

        class SubmittedDoc:
            def __init__(self):
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )
                self.cancel = Mock()

            def as_dict(self):
                return state

        doc = SubmittedDoc()

        def sql(query, value, **kwargs):
            self.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
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
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-foreign-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=90,
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-1",
                )

        # Foreign ownership must be rejected before lifecycle changes.
        doc.cancel.assert_not_called()
        audit.assert_not_called()

        # No replacement Timesheet may be constructed.
        self.assertLessEqual(fake_frappe.get_doc.call_count, 1)

        db.commit.assert_not_called()
        db.rollback.assert_called_once()

    def test_stale_revision_rejected_without_lifecycle_mutation(self):
        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity
        from telephony.time_booking_ownership import BookingOwnershipError

        command = api.PREFIX + "replace_submitted_booking"

        state = snapshot(status=1)

        # The persisted booking has changed since the caller read it.
        state["modified"] = "2026-11-17T12:01:00"

        identity = TechnicianBookingIdentity(
            "tech@example.com",
            "EMP-1",
            "Company A",
        )

        class SubmittedDoc:
            def __init__(self):
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )
                self.cancel = Mock()

            def as_dict(self):
                return state

        doc = SubmittedDoc()

        def sql(query, value, **kwargs):
            self.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
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
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-stale-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=90,
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-1",
                )

        # Original must not be cancelled.
        doc.cancel.assert_not_called()

        # No audit or replacement creation.
        audit.assert_not_called()

        fake_frappe.get_doc.assert_called_once_with(
            "Timesheet",
            "TS-1",
            for_update=True,
        )

        # No explicit commit; transaction must roll back.
        db.commit.assert_not_called()
        db.rollback.assert_called_once()

        # Persisted status remains Submitted.
        self.assertEqual(state["docstatus"], 1)

    def test_conflicting_replacement_retry_rejected_without_mutation(self):
        import json
        from datetime import datetime

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_correction_audit import _snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity
        from telephony.time_booking_ownership import BookingOwnershipError
        from telephony.api import time_booking as time_booking_api

        command = api.PREFIX + "replace_submitted_booking"

        identity = TechnicianBookingIdentity(
            "tech@example.com",
            "EMP-1",
            "Company A",
        )

        before = snapshot(status=1)
        before["modified"] = "2026-11-17T12:00:00"

        # The first successful operation requested 90 minutes.
        original_request = {
            "work_context": "Helpdesk",
            "from_time": "2026-11-16T09:00:00",
            "to_time": "2026-11-16T10:30:00",
            "duration_minutes": 90,
            "description": "Corrected repair duration",
            "activity_type": "Service",
            "ticket_name": "HD-1",
            "project_name": None,
            "task_name": None,
            "customer_name": None,
        }

        evidence = json.dumps(
            original_request,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

        prior = {
            "name": "AUDIT-1",
            "actor": identity.user,
            "action": "Submitted Replacement",
            "reason": "Incorrect submitted time",
            "original_timesheet": "TS-1",
            "before_snapshot": _snapshot(before),
            "after_snapshot": None,
            "replacement_timesheet": "TS-2",
            "replacement_request_snapshot": evidence,
        }

        def sql(query, value, **kwargs):
            self.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                self.assertIn("replacement_timesheet", query)
                self.assertIn("replacement_request_snapshot", query)
                return [prior]

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
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
            utils=types.SimpleNamespace(
                now_datetime=lambda: datetime(2026, 11, 18, 12),
            ),
            get_doc=Mock(
                side_effect=AssertionError(
                    "Conflicting retry must not load a Timesheet"
                )
            ),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(time_booking_api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "record_correction_event") as audit,
        ):
            with self.assertRaises(BookingOwnershipError):
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-1",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=120,  # Conflicts with original 90.
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-1",
                )

        fake_frappe.get_doc.assert_not_called()
        audit.assert_not_called()
        db.commit.assert_not_called()
        db.rollback.assert_called_once()

    def test_matching_replacement_retry_returns_existing_result(self):
        import json
        from datetime import datetime

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_correction_audit import _snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity
        from telephony.api import time_booking as time_booking_api

        command = api.PREFIX + "replace_submitted_booking"

        identity = TechnicianBookingIdentity(
            "tech@example.com",
            "EMP-1",
            "Company A",
        )

        before = snapshot(status=1)
        before["modified"] = "2026-11-17T12:00:00"

        original_request = {
            "work_context": "Helpdesk",
            "from_time": "2026-11-16T09:00:00",
            "to_time": "2026-11-16T10:30:00",
            "duration_minutes": 90,
            "description": "Corrected repair duration",
            "activity_type": "Service",
            "ticket_name": "HD-1",
            "project_name": None,
            "task_name": None,
            "customer_name": None,
        }

        evidence = json.dumps(
            original_request,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

        prior = {
            "name": "AUDIT-1",
            "actor": identity.user,
            "action": "Submitted Replacement",
            "reason": "Incorrect submitted time",
            "original_timesheet": "TS-1",
            "before_snapshot": _snapshot(before),
            "after_snapshot": None,
            "replacement_timesheet": "TS-2",
            "replacement_request_snapshot": evidence,
        }

        def sql(query, value, **kwargs):
            self.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return [prior]

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
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
            utils=types.SimpleNamespace(
                now_datetime=lambda: datetime(2026, 11, 18, 12),
            ),
            get_doc=Mock(),
        )

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(time_booking_api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "record_correction_event") as audit,
        ):
            result = api.replace_submitted_booking.__wrapped__(
                timesheet_name="TS-1",
                event_id="replacement-1",
                reason="Incorrect submitted time",
                expected_modified="2026-11-17T12:00:00",
                work_context="Helpdesk",
                from_time="2026-11-16 09:00:00",
                duration_minutes="90",
                description="Corrected repair duration",
                activity_type="Service",
                ticket_name="HD-1",
            )

        self.assertEqual(
            result,
            {
                "original_timesheet": "TS-1",
                "replacement_timesheet": "TS-2",
                "audit": "AUDIT-1",
            },
        )

        # No second replacement or lifecycle operation.
        fake_frappe.get_doc.assert_not_called()
        audit.assert_not_called()

        # Existing audit evidence is sufficient.
        self.assertEqual(db.sql.call_count, 2)

        # No explicit transaction commit or rollback on success.
        db.commit.assert_not_called()
        db.rollback.assert_not_called()

    def test_owned_submitted_replacement_cancels_creates_and_audits(self):
        import json
        from contextlib import contextmanager
        from datetime import datetime

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "replace_submitted_booking"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        before = snapshot(status=1)
        before["modified"] = "2026-11-17T12:00:00"

        operations = []
        created = []

        class TimesheetDoc(dict):
            def __init__(self, values):
                super().__init__(values)
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )
                self.time_logs = values["time_logs"]
                self.name = values.get("name")

            def as_dict(self):
                return dict(self)

            def cancel(self):
                if self.flags.ignore_permissions is not True:
                    raise PermissionError(
                        "Native cancellation permission denied"
                    )
                operations.append("cancel")
                self["docstatus"] = 2

            def insert(self):
                if self.flags.ignore_permissions is not True:
                    raise PermissionError(
                        "Native creation permission denied"
                    )
                operations.append("insert")
                self.name = "TS-2"
                self["name"] = self.name
                self["owner"] = self["user"]
                return self

        original = TimesheetDoc(before)

        def get_doc(*args, **kwargs):
            if (
                args == ("Timesheet", "TS-1")
                and kwargs == {"for_update": True}
            ):
                return original

            if (
                len(args) == 1
                and isinstance(args[0], dict)
                and not kwargs
            ):
                replacement = TimesheetDoc(args[0])
                created.append(replacement)
                return replacement

            raise AssertionError(
                f"Unexpected get_doc call: {args}, {kwargs}"
            )

        def sql(query, value, **kwargs):
            self.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
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
            get_doc=Mock(side_effect=get_doc),
        )

        @contextmanager
        def creation_intent(doc, actor):
            self.assertEqual(len(created), 1)
            self.assertIs(doc, created[0])
            self.assertIs(actor, identity)
            operations.append("creation_intent")
            yield

        @contextmanager
        def creation_permission(doc, actor):
            self.assertIs(doc, created[0])
            self.assertIs(actor, identity)
            self.assertIs(doc.flags.ignore_permissions, False)

            doc.flags.ignore_permissions = True
            try:
                yield
            finally:
                doc.flags.ignore_permissions = False

        def record(**kwargs):
            operations.append("audit")

            self.assertEqual(
                kwargs["action"], "Submitted Replacement"
            )
            self.assertEqual(kwargs["event_id"], "replacement-1")
            self.assertEqual(kwargs["before"]["docstatus"], 1)
            self.assertEqual(kwargs["before"]["name"], "TS-1")
            self.assertEqual(kwargs["replacement_timesheet"], "TS-2")

            evidence = json.loads(
                kwargs["replacement_request_snapshot"]
            )

            self.assertEqual(evidence["duration_minutes"], 90)
            self.assertEqual(
                evidence["from_time"],
                "2026-11-16T09:00:00",
            )
            self.assertEqual(evidence["ticket_name"], "HD-1")

            # Both lifecycle operations must precede audit insertion.
            self.assertEqual(original["docstatus"], 2)
            self.assertEqual(len(created), 1)
            self.assertEqual(created[0].name, "TS-2")

            # Permission elevation must not leak into the audit.
            self.assertIs(
                original.flags.ignore_permissions, False
            )
            self.assertIs(
                created[0].flags.ignore_permissions, False
            )

            db.commit.assert_not_called()
            return "AUDIT-1"

        start = datetime(2026, 11, 16, 9)
        end = datetime(2026, 11, 16, 10, 30)

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "TelectroBookingTimesheet", TimesheetDoc),
            patch.object(
                api, "_period", return_value=(start, end, 90)
            ),
            patch.object(api, "_authorize_references") as references,
            patch.object(api, "_visible") as visible,
            patch.object(
                api,
                "_phase2_creation_intent",
                creation_intent,
                create=True,
            ),
            patch.object(
                api,
                "_authorized_native_creation",
                creation_permission,
                create=True,
            ),
            patch.object(
                api, "record_correction_event",
                side_effect=record,
            ) as audit,
        ):
            result = api.replace_submitted_booking.__wrapped__(
                timesheet_name="TS-1",
                event_id="replacement-1",
                reason="Incorrect submitted time",
                expected_modified="2026-11-17 12:00:00",
                work_context="Helpdesk",
                from_time="2026-11-16 09:00:00",
                duration_minutes=90,
                description="Corrected repair duration",
                activity_type="Service",
                ticket_name="HD-1",
            )

        self.assertEqual(
            result,
            {
                "original_timesheet": "TS-1",
                "replacement_timesheet": "TS-2",
                "audit": "AUDIT-1",
            },
        )

        self.assertEqual(
            operations,
            ["cancel", "creation_intent", "insert", "audit"],
        )

        self.assertEqual(original["docstatus"], 2)
        self.assertEqual(len(created), 1)

        replacement = created[0]

        self.assertEqual(replacement["docstatus"], 0)
        self.assertEqual(
            replacement["custom_telectro_booking_origin"],
            "Phase 2",
        )
        self.assertEqual(replacement["employee"], identity.employee)
        self.assertEqual(replacement["company"], identity.company)
        self.assertEqual(replacement["user"], identity.user)
        self.assertEqual(replacement["owner"], identity.user)

        self.assertEqual(len(replacement.time_logs), 1)
        self.assertEqual(replacement.time_logs[0]["hours"], 1.5)

        self.assertIs(
            replacement.flags.ignore_permissions, False
        )

        references.assert_called_once()
        visible.assert_called_once_with("Activity Type", "Service")
        audit.assert_called_once()

        db.commit.assert_not_called()
        db.rollback.assert_not_called()

    def test_audit_failure_rolls_back_cancellation_and_replacement(self):
        import copy
        from contextlib import contextmanager
        from datetime import datetime

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "replace_submitted_booking"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        before = snapshot(status=1)
        before["modified"] = "2026-11-17T12:00:00"

        original_state = copy.deepcopy(before)

        operations = []
        persisted_replacements = []
        constructed_replacements = []

        class TimesheetDoc(dict):
            def __init__(self, values):
                super().__init__(values)
                self.name = values.get("name")
                self.time_logs = values["time_logs"]
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )

            def as_dict(self):
                return dict(self)

            def cancel(self):
                self_test.assertIs(
                    self.flags.ignore_permissions, True
                )
                operations.append("cancel")
                self["docstatus"] = 2

            def insert(self):
                self_test.assertIs(
                    self.flags.ignore_permissions, True
                )
                operations.append("insert")

                self.name = "TS-2"
                self["name"] = self.name
                self["owner"] = self["user"]

                persisted_replacements.append(self)
                return self

        self_test = self

        original = TimesheetDoc(copy.deepcopy(before))

        def get_doc(*args, **kwargs):
            if (
                args == ("Timesheet", "TS-1")
                and kwargs == {"for_update": True}
            ):
                return original

            if (
                len(args) == 1
                and isinstance(args[0], dict)
                and not kwargs
            ):
                replacement = TimesheetDoc(args[0])
                constructed_replacements.append(replacement)
                return replacement

            raise AssertionError(
                f"Unexpected get_doc: {args}, {kwargs}"
            )

        def sql(query, value, **kwargs):
            self.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError("Unexpected SQL query")

        def rollback():
            operations.append("rollback")

            # Simulate restoring transactional database state.
            original.clear()
            original.update(copy.deepcopy(original_state))

            persisted_replacements.clear()

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
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
            session=types.SimpleNamespace(
                user=identity.user
            ),
            get_doc=Mock(side_effect=get_doc),
        )

        @contextmanager
        def creation_intent(doc, actor):
            self.assertIs(actor, identity)
            self.assertIs(doc, constructed_replacements[0])
            yield

        @contextmanager
        def creation_permission(doc, actor):
            self.assertIs(actor, identity)
            self.assertIs(
                doc.flags.ignore_permissions, False
            )

            doc.flags.ignore_permissions = True
            try:
                yield
            finally:
                doc.flags.ignore_permissions = False

        def record(**kwargs):
            operations.append("audit")

            self.assertEqual(
                kwargs["action"], "Submitted Replacement"
            )
            self.assertEqual(
                kwargs["before"]["docstatus"], 1
            )
            self.assertEqual(
                kwargs["replacement_timesheet"], "TS-2"
            )

            # Both lifecycle operations have already executed.
            self.assertEqual(original["docstatus"], 2)
            self.assertEqual(len(persisted_replacements), 1)

            # Neither native permission scope may leak.
            self.assertIs(
                original.flags.ignore_permissions, False
            )
            self.assertIs(
                persisted_replacements[0].flags.ignore_permissions,
                False,
            )

            # No intermediate commit is permitted.
            db.commit.assert_not_called()

            raise RuntimeError("replacement audit failed")

        start = datetime(2026, 11, 16, 9)
        end = datetime(2026, 11, 16, 10, 30)

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(
                api, "TelectroBookingTimesheet", TimesheetDoc
            ),
            patch.object(
                api,
                "_period",
                return_value=(start, end, 90),
            ),
            patch.object(api, "_authorize_references"),
            patch.object(api, "_visible"),
            patch.object(
                api,
                "_phase2_creation_intent",
                creation_intent,
            ),
            patch.object(
                api,
                "_authorized_native_creation",
                creation_permission,
            ),
            patch.object(
                api,
                "record_correction_event",
                side_effect=record,
            ) as audit,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "replacement audit failed",
            ):
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-audit-failure",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17 12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=90,
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-1",
                )

        # Both native lifecycle operations preceded the audit failure.
        # The enclosing transaction then requested rollback.
        self.assertEqual(
            operations,
            ["cancel", "insert", "audit", "rollback"],
        )

        audit.assert_called_once()
        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()

        # Simulated persisted database state is restored.
        self.assertEqual(
            dict(original),
            original_state,
        )
        self.assertEqual(persisted_replacements, [])

        # The replacement was constructed and inserted before rollback.
        self.assertEqual(len(constructed_replacements), 1)

        # Permission elevation must always be restored.
        self.assertIs(
            original.flags.ignore_permissions, False
        )
        self.assertIs(
            constructed_replacements[0].flags.ignore_permissions,
            False,
        )

    def test_native_cancellation_failure_prevents_replacement_creation(self):
        import copy
        from datetime import datetime

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "replace_submitted_booking"

        identity = TechnicianBookingIdentity(
            "tech@example.com",
            "EMP-1",
            "Company A",
        )

        state = snapshot(status=1)
        state["modified"] = "2026-11-17T12:00:00"

        original_state = copy.deepcopy(state)
        operations = []
        self_test = self

        class SubmittedDoc(dict):
            def __init__(self, values):
                super().__init__(values)
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )

            def as_dict(self):
                return dict(self)

            def cancel(self):
                # The existing private cancellation scope must
                # authorize the native operation temporarily.
                self_test.assertIs(
                    self.flags.ignore_permissions,
                    True,
                )

                operations.append("cancel")

                # Simulate a native operation that mutates
                # transactional state before raising.
                self["docstatus"] = 2

                raise RuntimeError(
                    "native replacement cancellation failed"
                )

        original = SubmittedDoc(copy.deepcopy(state))

        def sql(query, value, **kwargs):
            self.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError(
                f"Unexpected SQL query: {query}"
            )

        def rollback():
            operations.append("rollback")

            original.clear()
            original.update(copy.deepcopy(original_state))

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
            rollback=Mock(side_effect=rollback),
        )

        fake_frappe = types.SimpleNamespace(
            local=types.SimpleNamespace(
                request=types.SimpleNamespace(
                    method="POST",
                    path="/api/method/" + command,
                ),
                form_dict=types.SimpleNamespace(
                    cmd=command
                ),
                db=db,
            ),
            db=db,
            session=types.SimpleNamespace(
                user=identity.user
            ),
            get_doc=Mock(return_value=original),
        )

        start = datetime(2026, 11, 16, 9)
        end = datetime(2026, 11, 16, 10, 30)

        with (
            patch.dict(
                sys.modules,
                {"frappe": fake_frappe},
            ),
            patch.object(
                api, "frappe", fake_frappe
            ),
            patch.object(
                api, "_guard", return_value=identity
            ),
            patch.object(
                api, "TelectroBookingTimesheet",
                SubmittedDoc,
            ),
            patch.object(
                api, "_period",
                return_value=(start, end, 90),
            ),
            patch.object(api, "_authorize_references"),
            patch.object(api, "_visible"),
            patch.object(
                api, "record_correction_event"
            ) as audit,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "native replacement cancellation failed",
            ):
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-cancel-failure",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=90,
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-1",
                )

        # Cancellation was attempted, then the enclosing
        # transaction requested rollback.
        self.assertEqual(
            operations,
            ["cancel", "rollback"],
        )

        # No replacement Timesheet was constructed.
        fake_frappe.get_doc.assert_called_once_with(
            "Timesheet",
            "TS-1",
            for_update=True,
        )

        # No correction audit may be recorded.
        audit.assert_not_called()

        # No commit is permitted on failure.
        db.commit.assert_not_called()
        db.rollback.assert_called_once_with()

        # Simulated database state must be restored.
        self.assertEqual(
            dict(original),
            original_state,
        )

        # Temporary permission elevation must not leak.
        self.assertIs(
            original.flags.ignore_permissions,
            False,
        )

    def test_replacement_insert_failure_rolls_back_original_cancellation(self):
        import copy
        from contextlib import contextmanager
        from datetime import datetime

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity

        command = api.PREFIX + "replace_submitted_booking"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        before = snapshot(status=1)
        before["modified"] = "2026-11-17T12:00:00"
        original_state = copy.deepcopy(before)

        operations = []
        constructed = []
        pending_inserts = []
        test_case = self

        class TimesheetDoc(dict):
            def __init__(self, values):
                super().__init__(values)
                self.name = values.get("name")
                self.time_logs = values["time_logs"]
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )

            def as_dict(self):
                return dict(self)

            def cancel(self):
                test_case.assertIs(
                    self.flags.ignore_permissions, True
                )
                operations.append("cancel")
                self["docstatus"] = 2

            def insert(self):
                test_case.assertIs(
                    self.flags.ignore_permissions, True
                )
                operations.append("insert")

                # Simulate partial transactional writes before
                # ERPNext's native insertion raises an exception.
                pending_inserts.append(self)

                raise RuntimeError(
                    "native replacement insertion failed"
                )

        original = TimesheetDoc(copy.deepcopy(before))

        def get_doc(*args, **kwargs):
            if (
                args == ("Timesheet", "TS-1")
                and kwargs == {"for_update": True}
            ):
                return original

            if (
                len(args) == 1
                and isinstance(args[0], dict)
                and not kwargs
            ):
                replacement = TimesheetDoc(args[0])
                constructed.append(replacement)
                return replacement

            raise AssertionError(
                f"Unexpected get_doc: {args}, {kwargs}"
            )

        def sql(query, value, **kwargs):
            test_case.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError(
                f"Unexpected SQL query: {query}"
            )

        def rollback():
            operations.append("rollback")

            original.clear()
            original.update(copy.deepcopy(original_state))
            pending_inserts.clear()

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
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
            get_doc=Mock(side_effect=get_doc),
        )

        @contextmanager
        def creation_intent(doc, actor):
            test_case.assertIs(actor, identity)
            test_case.assertEqual(len(constructed), 1)
            test_case.assertIs(doc, constructed[0])
            yield

        @contextmanager
        def creation_permission(doc, actor):
            test_case.assertIs(actor, identity)
            test_case.assertIs(
                doc.flags.ignore_permissions, False
            )

            doc.flags.ignore_permissions = True
            try:
                yield
            finally:
                doc.flags.ignore_permissions = False

        start = datetime(2026, 11, 16, 9)
        end = datetime(2026, 11, 16, 10, 30)

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(
                api, "TelectroBookingTimesheet", TimesheetDoc
            ),
            patch.object(
                api, "_period",
                return_value=(start, end, 90),
            ),
            patch.object(api, "_authorize_references"),
            patch.object(api, "_visible"),
            patch.object(
                api, "_phase2_creation_intent", creation_intent
            ),
            patch.object(
                api, "_authorized_native_creation",
                creation_permission,
            ),
            patch.object(
                api, "record_correction_event"
            ) as audit,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "native replacement insertion failed",
            ):
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-insert-failure",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=90,
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-1",
                )

        # Cancellation succeeds, insertion fails, then
        # the enclosing transaction requests rollback.
        self.assertEqual(
            operations,
            ["cancel", "insert", "rollback"],
        )

        # No audit may be written for an unsuccessful replacement.
        audit.assert_not_called()

        # No intermediate commit.
        db.commit.assert_not_called()
        db.rollback.assert_called_once_with()

        # Original Submitted state restored by simulated rollback.
        self.assertEqual(dict(original), original_state)
        self.assertEqual(original["docstatus"], 1)

        # Partial replacement writes rolled back.
        self.assertEqual(len(constructed), 1)
        self.assertEqual(pending_inserts, [])

        # Both permission scopes are no longer elevated.
        self.assertIs(
            original.flags.ignore_permissions, False
        )
        self.assertIs(
            constructed[0].flags.ignore_permissions, False
        )

        # Only the original and proposed replacement were loaded.
        self.assertEqual(fake_frappe.get_doc.call_count, 2)

    def test_invalid_replacement_reference_prevents_cancellation(self):
        from datetime import datetime

        from telephony.tests.test_time_booking_correction_audit import snapshot
        from telephony.time_booking_identity import TechnicianBookingIdentity
        from telephony.api.time_booking import BookingReferenceDenied

        command = api.PREFIX + "replace_submitted_booking"

        identity = TechnicianBookingIdentity(
            "tech@example.com", "EMP-1", "Company A"
        )

        before = snapshot(status=1)
        before["modified"] = "2026-11-17T12:00:00"

        class SubmittedDoc:
            def __init__(self):
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )
                self.cancel = Mock()

            def as_dict(self):
                return before

        original = SubmittedDoc()

        def sql(query, value, **kwargs):
            self.assertIn("FOR UPDATE", query)

            if "tabTimesheet" in query:
                return [{"name": "TS-1"}]

            if "tabTELECTRO Booking Correction Audit" in query:
                return []

            raise AssertionError(f"Unexpected SQL: {query}")

        db = types.SimpleNamespace(
            sql=Mock(side_effect=sql),
            commit=Mock(),
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
            get_doc=Mock(return_value=original),
        )

        start = datetime(2026, 11, 16, 9)
        end = datetime(2026, 11, 16, 10, 30)

        with (
            patch.dict(sys.modules, {"frappe": fake_frappe}),
            patch.object(api, "frappe", fake_frappe),
            patch.object(api, "_guard", return_value=identity),
            patch.object(api, "TelectroBookingTimesheet", SubmittedDoc),
            patch.object(
                api, "_period",
                return_value=(start, end, 90),
            ),
            patch.object(
                api, "_authorize_references",
                side_effect=BookingReferenceDenied(),
            ) as references,
            patch.object(api, "_visible") as visible,
            patch.object(api, "record_correction_event") as audit,
        ):
            with self.assertRaises(BookingReferenceDenied):
                api.replace_submitted_booking.__wrapped__(
                    timesheet_name="TS-1",
                    event_id="replacement-hidden-reference",
                    reason="Incorrect submitted time",
                    expected_modified="2026-11-17T12:00:00",
                    work_context="Helpdesk",
                    from_time="2026-11-16 09:00:00",
                    duration_minutes=90,
                    description="Corrected repair duration",
                    activity_type="Service",
                    ticket_name="HD-HIDDEN",
                )

        references.assert_called_once()
        visible.assert_not_called()

        # Original lifecycle must remain untouched.
        original.cancel.assert_not_called()
        self.assertEqual(before["docstatus"], 1)

        # No replacement Draft was constructed.
        fake_frappe.get_doc.assert_called_once_with(
            "Timesheet",
            "TS-1",
            for_update=True,
        )

        # No audit, commit or permission elevation.
        audit.assert_not_called()
        db.commit.assert_not_called()
        db.rollback.assert_called_once_with()

        self.assertIs(
            original.flags.ignore_permissions,
            False,
        )
