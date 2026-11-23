"""No-site coverage of Project grant authorization across the booking write paths."""

from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timedelta
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from telephony import time_booking_project_grant as grants
from telephony.api import booking_correction, time_booking
from telephony.tests.test_time_booking_correction_audit import snapshot
from telephony.time_booking_correction_audit import DOCTYPE as AUDIT_DOCTYPE, _snapshot
from telephony.time_booking_identity import TechnicianBookingIdentity


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
        self.project = SimpleNamespace(name=PROJECT, company=IDENTITY.company, creation=CREATION)
        self.task = SimpleNamespace(name=TASK, project=PROJECT, creation=CREATION)
        self.history = [self.grant()]
        self.db = SimpleNamespace(
            get_value=self.get_value, get_values=self.get_values, sql=self.sql, rollback=Mock(),
        )
        self.frappe = SimpleNamespace(
            db=self.db, session=SimpleNamespace(user=IDENTITY.user),
            utils=SimpleNamespace(now_datetime=lambda: END + timedelta(days=2)),
            get_doc=self.get_doc,
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

    def get_value(self, doctype, name, fields, *, as_dict, for_update):
        self.assertEqual((doctype, fields), ("Project", ["name", "company", "creation"]))
        self.assertTrue(as_dict and for_update)
        self.events.append("Project")
        self.project_locks.append(name)
        if name == PROJECT:
            return self.project
        if name in ("PROJ-0", "PROJ-2"):
            return SimpleNamespace(name=name, company=IDENTITY.company, creation=CREATION)
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

    def sql(self, query, key, *, as_dict):
        self.assertTrue(as_dict)
        self.assertIn("FOR UPDATE", query)
        if "tabTimesheet" in query:
            self.events.append("Timesheet")
            return [{"name": key}]
        self.assertIn(AUDIT_DOCTYPE, query)
        return [self.audit] if self.audit else []

    def get_doc(self, doctype, name=None, *, for_update=False):
        if isinstance(doctype, dict):
            self.assertEqual(doctype["doctype"], "Timesheet")
            return self.Timesheet(doctype)
        if doctype == "Timesheet":
            self.assertTrue(for_update)
            return self.original
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
