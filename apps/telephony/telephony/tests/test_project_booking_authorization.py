"""No-site coverage of Project grant authorization across the booking write paths."""

from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timedelta
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from frappe import QueryDeadlockError, QueryTimeoutError

from telephony import time_booking_project_grant as grants
from telephony.api import booking_correction, time_booking
from telephony.tests.test_time_booking_correction_audit import snapshot
from telephony.tests.test_time_booking_post import Reference, customer_mapping_sql
from telephony.time_booking_correction_audit import DOCTYPE as AUDIT_DOCTYPE, _snapshot
from telephony.time_booking_identity import TechnicianBookingIdentity
from telephony.time_booking_ownership import BookingOwnershipError
from telephony.time_booking_ticket_interval import ORIGIN_FIELD, TicketIntervalError


START = datetime(2026, 11, 16, 9)
END = datetime(2026, 11, 16, 10)
CREATION = datetime(2026, 11, 15, 8)
IDENTITY = TechnicianBookingIdentity("tech@example.com", "EMP-1", "Company A")
PROJECT = "PROJ-1"
TASK = "TASK-1"
ACTIVITY = "Repair & Maintenance"
REVISION = "2026-11-17T12:00:00"


class TestProjectBookingAuthorization(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.project_locks = []
        self.mutations = []
        self.audit = {}
        self.inserted = []
        self.original = None
        self.project = SimpleNamespace(
            name=PROJECT, company=IDENTITY.company, creation=CREATION, customer="ERP-C",
        )
        self.customer = Reference("HD Customer", "C", custom_erp_customer="ERP-C")
        self.current_customer = Reference("HD Customer", "C", **self.customer)
        self.ticket = Reference(
            "HD Ticket", "HD-2", customer="C", custom_customer="ERP-C",
            custom_service_area="Routing", status="Open", status_category="Open",
            creation=CREATION,
        )
        self.current_ticket = Reference("HD Ticket", self.ticket.name, **self.ticket)
        self.task = SimpleNamespace(name=TASK, project=PROJECT, creation=CREATION)
        self.history = [self.grant()]
        self.db = SimpleNamespace(
            get_value=self.get_value, get_values=self.get_values, sql=self.sql, rollback=Mock(),
            db_type="mariadb",
        )
        self.frappe = SimpleNamespace(
            db=self.db, session=SimpleNamespace(user=IDENTITY.user),
            utils=SimpleNamespace(now_datetime=lambda: END + timedelta(days=2)),
            get_doc=self.get_doc, PermissionError=PermissionError, DoesNotExistError=LookupError,
            QueryDeadlockError=QueryDeadlockError, QueryTimeoutError=QueryTimeoutError,
        )
        test = self

        class Timesheet(dict):
            def __init__(self, values):
                super().__init__(values)
                self.flags = SimpleNamespace(ignore_permissions=False)
                self.time_logs = values["time_logs"]
                self.name = values.get("name")

            @property
            def docstatus(self):
                return self["docstatus"]

            def as_dict(self):
                return dict(self)

            def insert(self):
                test.assertIs(self.flags.ignore_permissions, True)
                test.mutations.append("insert")
                self.name = "TS-2"
                self.update(name=self.name, owner=self["user"])
                test.inserted.append(self)
                return self

            def cancel(self):
                test.assertIs(self.flags.ignore_permissions, True)
                test.mutations.append("cancel")
                self["docstatus"] = 2

            def save(self):
                test.assertIs(self.flags.ignore_permissions, True)
                test.mutations.append("save")

        self.Timesheet = Timesheet
        patchers = [
            patch.dict(sys.modules, {"frappe": self.frappe}),
            patch.object(time_booking, "frappe", self.frappe),
            patch.object(booking_correction, "frappe", self.frappe),
            patch.object(time_booking, "_booking_identity", return_value=IDENTITY),
            patch.object(time_booking, "prepare_attribution", return_value={}),
            patch.object(booking_correction, "prepare_attribution", return_value={}),
            patch.object(booking_correction, "_guard", return_value=IDENTITY),
            patch.object(time_booking, "TelectroBookingTimesheet", Timesheet),
            patch.object(booking_correction, "TelectroBookingTimesheet", Timesheet),
            patch.object(time_booking, "_allowed_service_areas", return_value=("Routing",)),
            patch.object(booking_correction, "_allowed_service_areas", return_value=("Routing",)),
            patch.object(time_booking, "_phase2_creation_intent", lambda *args: nullcontext()),
            patch.object(booking_correction, "_phase2_creation_intent", lambda *args: nullcontext()),
            patch.object(booking_correction, "record_correction_event", side_effect=self.record),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def grant(*, start=CREATION, end=None, tasks=()):
        return {
            "technician_user": IDENTITY.user, "employee": IDENTITY.employee,
            "company": IDENTITY.company, "project": PROJECT, "project_created_at": CREATION,
            "effective_start": start, "effective_end": end,
            "permitted_tasks": grants._task_json((task, CREATION) for task in tasks),
            "granted_by": "Administrator", "grant_reason": "Pilot",
            "active_key": grants._active_key(IDENTITY, PROJECT) if end is None else None,
            "ended_by": None if end is None else "Administrator",
            "end_reason": None if end is None else "Stopped",
        }

    def get_value(self, doctype, name, fields, *, as_dict=False, for_update=False, **kwargs):
        if (doctype, name, fields) == ("HD Ticket", self.ticket.name, "*"):
            self.assertTrue(as_dict and for_update)
            self.assertEqual(kwargs, {"order_by": None, "wait": False})
            self.events.append("Ticket lock")
            return self.current_ticket
        if doctype == "Customer":
            self.assertEqual(fields, "name")
            self.assertTrue(for_update and not as_dict)
            self.assertEqual(kwargs, {"order_by": None, "wait": False})
            self.events.append("ERPNext Customer lock")
            return name
        if doctype == "HD Customer":
            self.assertEqual((name, fields), ("C", "*"))
            self.assertTrue(as_dict and for_update)
            self.assertEqual(kwargs, {"order_by": None, "wait": False})
            self.events.append("HD Customer lock")
            return self.current_customer
        self.assertEqual((doctype, fields), ("Project", ["name", "company", "creation", "customer"]))
        self.assertTrue(as_dict and for_update)
        self.events.append("Project")
        self.project_locks.append(name)
        if name == PROJECT:
            return self.project
        if name in ("PROJ-0", "PROJ-2"):
            return SimpleNamespace(name=name, company=IDENTITY.company, creation=CREATION, customer=None)
        return None

    def get_values(self, doctype, filters, fields, *, for_update, **kwargs):
        self.assertTrue(for_update)
        self.assertIn("Project", self.events)
        self.events.append(doctype)
        if doctype == "Task":
            self.assertEqual(fields, ["name", "project", "creation"])
            if self.task.name in filters["name"][1]:
                return [(self.task.name, self.task.project, self.task.creation)]
            return []

        self.assertEqual(doctype, grants.DOCTYPE)
        self.assertTrue(kwargs["as_dict"])
        self.assertEqual(filters, {
            "technician_user": IDENTITY.user, "employee": IDENTITY.employee,
            "company": IDENTITY.company, "project": PROJECT,
            "project_created_at": self.project.creation,
        })
        return [
            {field: record[field] for field in fields}
            for record in self.history
            if all(record.get(field) == value for field, value in filters.items())
        ]

    def sql(self, query, key=None, *, as_dict=False):
        if "tabHD Ticket Status" in query:
            self.assertIn("LOCK IN SHARE MODE NOWAIT", query)
            self.events.append("Ticket status")
            return ((key[0], {"Open": "Open", "Resolved": "Resolved"}[key[0]]),)
        if "FOR UPDATE NOWAIT" in query:
            self.events.append("reverse range lock")
            return customer_mapping_sql(query, key)
        if "FOR UPDATE" not in query:
            return customer_mapping_sql(query, key)
        self.assertTrue(as_dict)
        self.assertIn("FOR UPDATE", query)
        if "tabTimesheet" in query:
            self.events.append("Timesheet")
            return [{"name": key}]
        self.assertIn(AUDIT_DOCTYPE, query)
        return [self.audit] if self.audit else []

    def get_doc(self, doctype, name=None, *, for_update=False):
        if isinstance(doctype, dict):
            if doctype["doctype"] == "HD Ticket":
                return self.current_ticket
            if doctype["doctype"] == "HD Customer":
                return self.current_customer
            self.assertEqual(doctype["doctype"], "Timesheet")
            return self.Timesheet(doctype)
        if doctype == "Timesheet":
            self.assertTrue(for_update)
            return self.original
        if (doctype, name) == ("HD Customer", "C"):
            return self.customer
        if (doctype, name) == ("HD Ticket", self.ticket.name):
            return self.ticket
        self.assertEqual((doctype, name), ("Activity Type", ACTIVITY))
        return SimpleNamespace(doctype=doctype, name=name, check_permission=Mock())

    def record(self, *, action, reason, before, after=None, **evidence):
        self.mutations.append("audit")
        self.audit = dict(
            name="AUDIT-1", actor=IDENTITY.user, action=action, reason=reason,
            original_timesheet=before["name"], before_snapshot=_snapshot(before),
            after_snapshot=_snapshot(after) if after else None, **evidence,
        )
        return self.audit["name"]

    def call(self, operation="create", **updates):
        if operation == "create":
            command = time_booking.COMMAND
            endpoint = time_booking.book_technician_time
        else:
            submitted = operation in ("replace", "cancel")
            endpoint = {
                "replace": booking_correction.replace_submitted_booking,
                "correct": booking_correction.correct_draft_booking,
                "cancel": booking_correction.cancel_submitted_booking,
            }[operation]
            command = booking_correction.PREFIX + endpoint.__name__
            if self.original is None:
                self.original = self.Timesheet({
                    **snapshot(status=int(submitted)), "modified": REVISION,
                })
            updates = dict(
                timesheet_name="TS-1", event_id="EVENT-1", reason="Correction",
                expected_modified=REVISION, **updates,
            )
        self.frappe.local = SimpleNamespace(
            request=SimpleNamespace(method="POST", path="/api/method/" + command),
            form_dict=SimpleNamespace(cmd=command), db=self.db,
        )
        args = dict(
            work_context="Project", project_name=PROJECT, from_time=START.isoformat(),
            duration_minutes=60, description="Project work", activity_type=ACTIVITY,
            service_area="Routing", work_location="Remote", work_origin="Direct / Ad-hoc",
            emergency=0,
        )
        if operation == "cancel":
            return endpoint.__wrapped__(**updates)
        args.update(updates)
        return endpoint.__wrapped__(**args)

    def test_project_only_and_explicit_task_succeed_without_native_read(self):
        self.assertEqual(self.call(), {"timesheet": "TS-2"})
        self.assertEqual(self.events, ["Project", grants.DOCTYPE])
        self.assertIsNone(self.inserted[0].time_logs[0]["task"])

        self.events.clear()
        self.history = [self.grant(tasks=(TASK,))]
        self.assertEqual(self.call(task_name=TASK), {"timesheet": "TS-2"})
        self.assertEqual(self.events, ["Project", "Task", grants.DOCTYPE])
        self.assertEqual(self.inserted[1].time_logs[0]["task"], TASK)

    def test_creation_accepts_consistent_project_customer_after_task_grant(self):
        self.history = [self.grant(tasks=(TASK,))]

        self.assertEqual(self.call(task_name=TASK, customer_name="C"), {"timesheet": "TS-2"})

        self.assertEqual(self.events, [
            "Project", "Task", grants.DOCTYPE, "ERPNext Customer lock", "HD Customer lock", "reverse range lock",
        ])
        self.assertEqual(self.project_locks, [PROJECT])
        self.assertEqual(self.mutations, ["insert"])
        self.assertEqual(self.inserted[0].time_logs[0]["custom_hd_customer"], "C")
        self.assertEqual(self.audit, {})
        self.db.rollback.assert_not_called()

    def test_creation_rejects_inconsistent_project_customer_without_mutation(self):
        self.project.customer = "ERP-OTHER"

        with self.assertRaisesRegex(
            time_booking.BookingReferenceDenied, r"^Booking reference is unavailable\.$",
        ):
            self.call(customer_name="C")

        self.assertEqual(self.events, [
            "Project", grants.DOCTYPE, "ERPNext Customer lock", "HD Customer lock",
        ])
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.inserted, [])
        self.assertEqual(self.audit, {})
        self.db.rollback.assert_called_once_with()

    def test_creation_denied_task_grant_skips_customer_consistency(self):
        with (
            patch.object(time_booking, "_validate_customer_consistency") as consistency,
            self.assertRaises(time_booking.BookingReferenceDenied),
        ):
            self.call(task_name=TASK, customer_name="C")

        consistency.assert_not_called()
        self.assertEqual(self.events, ["Project", "Task", grants.DOCTYPE])
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.inserted, [])
        self.assertEqual(self.audit, {})
        self.db.rollback.assert_called_once_with()

    def test_draft_correction_accepts_consistent_project_customer_after_task_grant(self):
        self.history = [self.grant(tasks=(TASK,))]

        result = self.call("correct", task_name=TASK, customer_name="C")

        self.assertEqual(result, {"timesheet": "TS-1", "audit": "AUDIT-1"})
        self.assertEqual(self.events, [
            "Timesheet", "Project", "Task", grants.DOCTYPE,
            "ERPNext Customer lock", "HD Customer lock", "reverse range lock",
        ])
        self.assertEqual(self.project_locks, [PROJECT])
        self.assertEqual(self.mutations, ["save", "audit"])
        self.assertEqual(self.original.time_logs[0]["custom_hd_customer"], "C")
        self.db.rollback.assert_not_called()

    def test_draft_correction_denied_task_grant_skips_customer_consistency(self):
        with (
            patch.object(booking_correction, "_validate_customer_consistency") as consistency,
            self.assertRaises(time_booking.BookingReferenceDenied),
        ):
            self.call("correct", task_name=TASK, customer_name="C")

        consistency.assert_not_called()
        self.assertEqual(self.events, ["Timesheet", "Project", "Task", grants.DOCTYPE])
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.audit, {})
        self.db.rollback.assert_called_once_with()

    def replace_helpdesk(self, **updates):
        args = dict(work_context="Helpdesk", project_name=None, ticket_name=self.ticket.name)
        args.update(updates)
        return self.call("replace", **args)

    def call_helpdesk(self, operation, **updates):
        return self.call(operation, work_context="Helpdesk", project_name=None,
                         ticket_name=self.ticket.name, **updates)

    def test_create_changed_draft_and_changed_replacement_use_the_same_locked_interval_policy(self):
        self.current_ticket.update(creation=START + timedelta(minutes=30), **{ORIGIN_FIELD: 1})
        from telephony.time_booking_ticket_interval import validate_ticket_interval

        for operation, expected in (("create", ["insert"]), ("correct", ["save", "audit"]),
                                    ("replace", ["cancel", "insert", "audit"])):
            with self.subTest(operation=operation):
                self.original = None
                self.audit = {}
                self.mutations.clear()
                self.events.clear()
                if operation != "create":
                    before = {**snapshot(status=int(operation == "replace")), "modified": REVISION}
                    before["time_logs"][0].update(
                        custom_hd_ticket=self.ticket.name, from_time=START + timedelta(hours=1),
                        to_time=END + timedelta(hours=1),
                    )
                    self.original = self.Timesheet(before)

                def verify_locked(ticket, start, end, **kwargs):
                    self.assertIs(ticket, self.current_ticket)
                    self.assertEqual(self.events[-1], "Ticket lock")
                    self.assertFalse(self.mutations)
                    result = validate_ticket_interval(ticket, start, end, **kwargs)
                    self.assertEqual(result, timedelta(minutes=30))
                    return result

                with patch.object(time_booking, "validate_ticket_interval", side_effect=verify_locked) as check:
                    self.call_helpdesk(operation)
                check.assert_called_once()
                self.assertEqual(self.events[-2:], ["Ticket lock", "Ticket status"])
                self.assertEqual(self.mutations, expected)

    def test_description_only_draft_and_replacement_do_not_validate_stale_lifecycle(self):
        self.current_ticket["creation"] = None
        for operation in ("correct", "replace"):
            with self.subTest(operation=operation):
                before = {**snapshot(status=int(operation == "replace")), "modified": REVISION}
                before["time_logs"][0].update(
                    custom_hd_ticket=self.ticket.name, activity_type=ACTIVITY, custom_service_area="Routing",
                    custom_work_location="Remote", custom_work_origin="Direct / Ad-hoc", custom_emergency=0,
                )
                self.original = self.Timesheet(before)
                self.audit = {}
                self.events.clear()
                with patch.object(time_booking, "validate_ticket_interval") as check:
                    self.call_helpdesk(operation, description="Description only", activity_type="Repair & Maintenance")
                check.assert_not_called()
                self.assertEqual(self.events, ["Timesheet"])

    def test_changed_replacement_reference_rechecks_interval_before_cancellation(self):
        before = {**snapshot(status=1), "modified": REVISION}
        self.original = self.Timesheet(deepcopy(before))
        self.current_ticket["creation"] = START + timedelta(microseconds=1)

        with self.assertRaises(TicketIntervalError):
            self.call_helpdesk("replace")

        self.assertEqual(self.original.as_dict(), before)
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.inserted, [])
        self.assertFalse(self.audit)
        booking_correction.record_correction_event.assert_not_called()
        self.db.rollback.assert_called_once_with()

    def test_lifecycle_is_never_read_for_unauthorized_helpdesk_references(self):
        self.current_ticket["creation"] = None
        self.ticket.visible = False
        for operation in ("create", "correct", "replace"):
            with self.subTest(operation=operation):
                self.original = None
                self.events.clear()
                with patch.object(time_booking, "validate_ticket_interval") as check:
                    with self.assertRaises(time_booking.BookingReferenceDenied):
                        self.call_helpdesk(operation)
                check.assert_not_called()
                self.assertNotIn("Ticket lock", self.events)
        self.assertEqual(self.mutations, [])

    def test_lifecycle_is_never_read_when_locked_ticket_loses_read_permission(self):
        self.current_ticket.visible = False
        with (
            patch.object(time_booking, "validate_ticket_interval") as check,
            self.assertRaises(time_booking.BookingReferenceDenied),
        ):
            self.call_helpdesk("create")
        check.assert_not_called()
        self.assertEqual(self.events, ["Ticket lock"])
        self.assertEqual(self.mutations, [])

    def test_replacement_uses_locked_ticket_customer_over_snapshot(self):
        self.ticket.update(customer="OTHER", custom_customer="ERP-OTHER")
        with patch.object(self.frappe, "get_doc", wraps=self.get_doc) as get_doc:
            result = self.replace_helpdesk(customer_name="C")

        self.assertEqual(result, {
            "original_timesheet": "TS-1", "replacement_timesheet": "TS-2", "audit": "AUDIT-1",
        })
        ticket_reads = [
            call.args for call in get_doc.call_args_list if call.args[0] == "HD Ticket"
        ]
        self.assertEqual(ticket_reads, [("HD Ticket", self.ticket.name)])
        self.assertEqual(self.events, [
            "Timesheet", "Ticket lock", "ERPNext Customer lock", "HD Customer lock", "reverse range lock", "Ticket status",
        ])
        self.assertEqual(self.mutations, ["cancel", "insert", "audit"])
        self.assertEqual(self.original["docstatus"], 2)
        self.assertEqual(self.inserted[0]["docstatus"], 0)
        self.assertEqual(self.inserted[0].time_logs[0]["custom_hd_customer"], "C")
        self.assertNotIn("amended_from", self.inserted[0])
        self.assertEqual(self.audit["replacement_timesheet"], "TS-2")
        self.db.rollback.assert_not_called()

    def test_replacement_accepts_consistent_project_customer_after_task_grant(self):
        self.history = [self.grant(tasks=(TASK,))]

        self.call("replace", task_name=TASK, customer_name="C")

        self.assertEqual(self.events, [
            "Timesheet", "Project", "Task", grants.DOCTYPE,
            "ERPNext Customer lock", "HD Customer lock", "reverse range lock",
        ])
        self.assertEqual(self.project_locks, [PROJECT])
        self.assertEqual(self.mutations, ["cancel", "insert", "audit"])
        self.assertEqual(self.inserted[0].time_logs[0]["custom_hd_customer"], "C")
        self.db.rollback.assert_not_called()

    def test_replacement_rejects_unchanged_customer_when_new_ticket_conflicts(self):
        before = {**snapshot(status=1), "modified": REVISION}
        before["time_logs"][0]["custom_hd_customer"] = "C"
        self.original = self.Timesheet(deepcopy(before))
        self.current_ticket["custom_customer"] = "ERP-OTHER"

        with (
            patch.object(self.frappe, "get_doc", wraps=self.get_doc) as get_doc,
            patch.object(self.original, "cancel") as cancel,
            patch.object(booking_correction, "_phase2_creation_intent") as intent,
            self.assertRaisesRegex(
                time_booking.BookingReferenceDenied, r"^Booking reference is unavailable\.$",
            ),
        ):
            self.replace_helpdesk(customer_name="C")

        self.assertEqual(self.original.as_dict(), before)
        self.assertIs(self.original.flags.ignore_permissions, False)
        self.assertFalse(any(
            isinstance(call.args[0], dict) and call.args[0]["doctype"] == "Timesheet"
            for call in get_doc.call_args_list
        ))
        cancel.assert_not_called()
        intent.assert_not_called()
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.inserted, [])
        self.assertEqual(self.audit, {})
        booking_correction.record_correction_event.assert_not_called()
        self.db.rollback.assert_called_once_with()

    def test_replacement_with_omitted_customer_keeps_existing_behavior(self):
        self.ticket["custom_customer"] = "ERP-OTHER"

        self.replace_helpdesk()

        self.assertEqual(self.events, ["Timesheet", "Ticket lock", "Ticket status"])
        self.assertEqual(self.mutations, ["cancel", "insert", "audit"])
        self.assertIsNone(self.inserted[0].time_logs[0]["custom_hd_customer"])
        self.db.rollback.assert_not_called()

    def test_replacement_ownership_revision_and_reference_denials_precede_consistency(self):
        cases = (
            ({"user": "foreign"}, None, BookingOwnershipError),
            ({"modified": END.isoformat()}, None, BookingOwnershipError),
            ({}, self.ticket, time_booking.BookingReferenceDenied),
            ({}, self.customer, time_booking.BookingReferenceDenied),
        )
        for changes, hidden, error in cases:
            with self.subTest(changes=changes, hidden=getattr(hidden, "doctype", None)):
                before = {**snapshot(status=1), "modified": REVISION, **changes}
                self.original = self.Timesheet(deepcopy(before))
                visibility = (
                    patch.object(hidden, "visible", False) if hidden is not None else nullcontext()
                )
                self.db.rollback.reset_mock()
                with (
                    visibility,
                    patch.object(booking_correction, "_validate_customer_consistency") as check,
                    self.assertRaises(error),
                ):
                    self.replace_helpdesk(customer_name="C")
                check.assert_not_called()
                self.assertEqual(self.original.as_dict(), before)
                self.db.rollback.assert_called_once_with()
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.audit, {})

    def test_replacement_denied_task_grant_skips_customer_consistency(self):
        with (
            patch.object(booking_correction, "_validate_customer_consistency") as check,
            self.assertRaises(time_booking.BookingReferenceDenied),
        ):
            self.call("replace", task_name=TASK, customer_name="C")

        check.assert_not_called()
        self.assertEqual(self.events, ["Timesheet", "Project", "Task", grants.DOCTYPE])
        self.assertEqual(self.original["docstatus"], 1)
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.inserted, [])
        self.assertEqual(self.audit, {})
        self.db.rollback.assert_called_once_with()

    def test_replacement_range_contention_rolls_back_before_cancellation(self):
        before = {**snapshot(status=1), "modified": REVISION}
        self.original = self.Timesheet(deepcopy(before))

        def sql(query, *args, **kwargs):
            if "FORCE INDEX" in query:
                raise QueryTimeoutError()
            return self.sql(query, *args, **kwargs)

        with (
            patch.object(self.db, "sql", side_effect=sql),
            self.assertRaisesRegex(
                time_booking.BookingReferenceDenied, r"^Booking reference is unavailable\.$",
            ),
        ):
            self.replace_helpdesk(customer_name="C")

        self.assertEqual(self.original.as_dict(), before)
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.inserted, [])
        self.assertEqual(self.audit, {})
        self.db.rollback.assert_called_once_with()

    def test_committed_replacement_replay_succeeds_after_customer_mapping_changes(self):
        result = self.replace_helpdesk(customer_name="C")

        stored_original = deepcopy(self.original.as_dict())
        stored_replacement = deepcopy(self.inserted[0].as_dict())
        stored_audit = deepcopy(self.audit)
        self.customer["custom_erp_customer"] = "ERP-OTHER"
        self.current_customer["custom_erp_customer"] = "ERP-OTHER"
        self.events.clear()
        self.mutations.clear()

        with (
            patch.object(self.frappe, "get_doc", wraps=self.get_doc) as get_doc,
            patch.object(booking_correction, "_validate_customer_consistency") as check,
        ):
            self.assertEqual(self.replace_helpdesk(customer_name="C"), result)

        get_doc.assert_not_called()
        check.assert_not_called()
        self.assertEqual(self.events, ["Timesheet"])
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.original.as_dict(), stored_original)
        self.assertEqual([doc.as_dict() for doc in self.inserted], [stored_replacement])
        self.assertEqual(self.audit, stored_audit)
        booking_correction.record_correction_event.assert_called_once()
        self.db.rollback.assert_not_called()

    def test_historical_work_before_or_at_revocation_remains_eligible(self):
        for revoke_at in (END, END + timedelta(hours=1)):
            with self.subTest(revoked_at=revoke_at):
                self.history = [self.grant(end=revoke_at, tasks=(TASK,))]
                self.assertEqual(self.call(task_name=TASK), {"timesheet": "TS-2"})

    def test_missing_partial_revoked_and_malformed_grants_are_denied_before_insert(self):
        for history in (
            [], [self.grant(end=END - timedelta(microseconds=1))],
            [self.grant(end=START)], [self.grant(end=START - timedelta(minutes=1))],
            [self.grant(start=START + timedelta(minutes=1))],
            [{**self.grant(), "permitted_tasks": "invalid"}],
            [{**self.grant(), "employee": "EMP-2"}],
        ):
            with self.subTest(history=history), self.assertRaisesRegex(
                time_booking.BookingReferenceDenied, "^Booking reference is unavailable[.]$",
            ):
                self.history = history
                self.call()
        self.assertEqual(self.mutations, [])

    def test_wrong_parent_missing_reused_and_cross_company_references_fail_closed(self):
        cases = (
            (dict(project_name="UNKNOWN"), None, None),
            (dict(task_name="UNKNOWN"), None, None),
            (dict(task_name=TASK), None, {"project": "OTHER"}),
            (dict(task_name=TASK), None, {"creation": START}),
            ({}, {"creation": START}, None),
            ({}, {"company": "Other"}, None),
        )
        for args, project_changes, task_changes in cases:
            with self.subTest(args=args, project=project_changes, task=task_changes):
                self.project = SimpleNamespace(
                    **{**vars(self.project), "creation": CREATION, "company": IDENTITY.company,
                       **(project_changes or {})}
                )
                self.task = SimpleNamespace(
                    name=TASK, **{"project": PROJECT, "creation": CREATION, **(task_changes or {})}
                )
                self.history = [self.grant(tasks=(TASK,))]
                with self.assertRaises(time_booking.BookingReferenceDenied):
                    self.call(**args)
        self.assertEqual(self.mutations, [])

    def test_unlisted_task_is_denied(self):
        with self.assertRaises(time_booking.BookingReferenceDenied):
            self.call(task_name=TASK)
        self.assertEqual(self.mutations, [])

    def test_authorization_order_and_denied_mutations_match_across_entry_points(self):
        for operation in ("create", "correct", "replace"):
            with self.subTest(operation=operation):
                self.original = None
                self.audit.clear()
                self.events.clear()
                self.mutations.clear()
                self.db.rollback.reset_mock()
                self.history = [self.grant(end=END - timedelta(microseconds=1), tasks=(TASK,))]
                with self.assertRaises(time_booking.BookingReferenceDenied):
                    self.call(operation, task_name=TASK)
                expected = ["Project", "Task", grants.DOCTYPE]
                if operation != "create":
                    expected.insert(0, "Timesheet")
                    self.assertEqual(self.original.time_logs[0]["custom_work_context"], "Helpdesk")
                    self.assertEqual(self.original["docstatus"], int(operation == "replace"))
                self.assertEqual(self.events, expected)
                self.assertEqual(self.mutations, [])
                self.assertEqual(self.audit, {})
                self.db.rollback.assert_called_once_with()

                self.history = [self.grant(end=END, tasks=(TASK,))]
                self.call(operation, task_name=TASK)
                self.assertEqual(self.mutations, {
                    "create": ["insert"], "correct": ["save", "audit"],
                    "replace": ["cancel", "insert", "audit"],
                }[operation])

    def test_cross_project_replace_locks_both_projects_before_authorizing_the_task(self):
        for original_project in ("PROJ-0", "PROJ-2"):
            with self.subTest(original_project=original_project):
                before = {**snapshot(status=1), "modified": REVISION}
                before["time_logs"][0].update(
                    custom_work_context="Project", custom_hd_ticket=None, project=original_project,
                )
                self.original = self.Timesheet(before)
                self.audit.clear()
                self.events.clear()
                self.project_locks.clear()
                self.history = [self.grant(tasks=(TASK,))]
                self.call("replace", task_name=TASK)
                self.assertEqual(self.project_locks, [*sorted((original_project, PROJECT)), PROJECT])
                self.assertEqual(
                    self.events, ["Timesheet", "Project", "Project", "Project", "Task", grants.DOCTYPE],
                )

    def test_submitted_cancellation_locks_original_project_without_requiring_a_grant(self):
        before = {**snapshot(status=1), "modified": REVISION}
        before["time_logs"][0].update(
            custom_work_context="Project", custom_hd_ticket=None, project=PROJECT, task=TASK,
        )
        self.original = self.Timesheet(before)
        self.history = []
        self.assertEqual(self.call("cancel"), {"timesheet": "TS-1", "audit": "AUDIT-1"})
        self.assertEqual(self.events, ["Timesheet", "Project"])
        self.assertEqual(self.mutations, ["audit", "cancel"])

    def test_committed_replacement_retry_does_not_consult_current_grants(self):
        self.history = [self.grant(tasks=(TASK,))]
        result = self.call("replace", task_name=TASK)
        stored_audit = deepcopy(self.audit)
        self.history = [self.grant(end=END + timedelta(hours=1), tasks=(TASK,))]
        self.events.clear()
        self.mutations.clear()
        self.assertEqual(self.call("replace", task_name=TASK), result)
        self.assertEqual(self.events, ["Timesheet"])
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.audit, stored_audit)
