from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from telephony.time_booking_identity import TechnicianBookingIdentity, TechnicianIdentityError
from telephony import time_booking_project_grant as grants


START = datetime(2026, 11, 23, 8)
MIDDLE = START + timedelta(hours=1)
END = MIDDLE + timedelta(hours=1)
LATER = END + timedelta(days=1)
IDENTITY = TechnicianBookingIdentity("tech", "EMP-1", "Company")
PROJECT = "PROJ-1"
TASK = "TASK-1"
CREATED = START - timedelta(days=1)
MODEL = (
    Path(__file__).resolve().parents[1]
    / "ftelephony/doctype/telectro_project_booking_grant/telectro_project_booking_grant"
)


def period(start=START, end=MIDDLE, tasks=(TASK,)):
    references = frozenset((task, CREATED) for task in tasks)
    return grants.ProjectBookingGrantPeriod(IDENTITY, PROJECT, CREATED, references, start, end)


class CoverageTests(unittest.TestCase):
    def covers(self, periods, **kwargs):
        args = dict(
            identity=IDENTITY, project=PROJECT, project_company=IDENTITY.company,
            project_created_at=CREATED, start=START, end=END, evaluated_at=LATER,
        )
        if kwargs.get("task"):
            args["task_created_at"] = CREATED
        args.update(kwargs)
        return grants.covers_project_booking(periods=periods, **args)

    def test_adjacent_periods_cover_project_and_explicit_task(self):
        periods = [period(MIDDLE, END), period()]
        self.assertTrue(self.covers(periods))
        self.assertTrue(self.covers(periods, task=TASK, task_project=PROJECT))

    def test_task_removal_does_not_remove_project_or_historical_task_authority(self):
        periods = [period(), period(MIDDLE, None, tasks=())]
        self.assertTrue(self.covers(periods))
        self.assertTrue(self.covers(periods, end=MIDDLE, task=TASK, task_project=PROJECT))
        self.assertFalse(self.covers(periods, task=TASK, task_project=PROJECT))

    def test_revocation_preserves_work_ending_at_cutoff(self):
        self.assertTrue(self.covers([period()], end=MIDDLE, task=TASK, task_project=PROJECT))
        self.assertFalse(self.covers([period()], end=MIDDLE + timedelta(microseconds=1)))
        self.assertFalse(self.covers([period()], start=MIDDLE))
        self.assertFalse(self.covers([]))

    def test_gap_and_pregrant_work_are_denied(self):
        self.assertFalse(self.covers([period(), period(MIDDLE + timedelta(microseconds=1), END)]))
        self.assertFalse(self.covers([period(MIDDLE, END)]))

    def test_wrong_identity_project_company_or_task_parent_fails_closed(self):
        for authority in (
            replace(period(), identity=replace(IDENTITY, user="other")),
            replace(period(), identity=replace(IDENTITY, employee="EMP-2")),
            replace(period(), identity=replace(IDENTITY, company="Other")),
            replace(period(), project="PROJ-2"),
        ):
            with self.subTest(authority=authority), self.assertRaises(grants.ProjectBookingGrantError):
                self.covers([period(), authority])
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.covers([period()], project_company="Other")
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.covers([period()], task=TASK, task_project="PROJ-2")

    def test_reused_references_do_not_inherit_prior_grants(self):
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.covers([period()], project_created_at=START, end=MIDDLE)
        self.assertFalse(self.covers(
            [period()], end=MIDDLE, task=TASK, task_project=PROJECT, task_created_at=START,
        ))

    def test_malformed_or_future_work_fails_closed(self):
        for args in ({"end": START}, {"end": LATER + timedelta(seconds=1)}, {"start": START.replace(tzinfo=timezone.utc)}):
            with self.subTest(args=args), self.assertRaises(grants.ProjectBookingGrantError):
                self.covers([period()], **args)
        for invalid_periods in (
            [period(), {}], [period(), period(START, END)],
            [period(START, None), period(LATER, None)], [period(LATER, LATER + timedelta(hours=1))],
        ):
            with self.subTest(periods=invalid_periods), self.assertRaises(grants.ProjectBookingGrantError):
                self.covers(invalid_periods)
        with self.assertRaises(grants.ProjectBookingGrantError):
            period(START, START)


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.rows = {}
        self.projects = {PROJECT: IDENTITY.company, "PROJ-2": "Other"}
        self.project_creation = CREATED
        self.tasks = {TASK: PROJECT, "TASK-2": PROJECT, "TASK-3": "PROJ-2"}
        self.savepoints = {}
        self.now = START
        self.events = []
        self.fail_insert = False

        frappe = ModuleType("frappe")
        frappe.session = SimpleNamespace(user="Administrator")
        frappe.db = SimpleNamespace(
            get_value=self.get_value, get_values=self.get_values, savepoint=self.savepoint,
            rollback=self.rollback, release_savepoint=self.release_savepoint,
        )
        frappe.get_doc = self.get_doc
        utils = ModuleType("frappe.utils")
        utils.now_datetime = self.clock
        document = ModuleType("frappe.model.document")
        document.Document = object
        modules = patch.dict(sys.modules, {
            "frappe": frappe, "frappe.utils": utils,
            "frappe.model.document": document,
        })
        modules.start()
        self.addCleanup(modules.stop)
        self.frappe = frappe
        identity = patch.object(grants, "_resolve_technician_identity", return_value=IDENTITY)
        self.identity = identity.start()
        self.addCleanup(identity.stop)

        spec = importlib.util.spec_from_file_location("grant_controller", MODEL.with_suffix(".py"))
        controller = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(controller)
        test = self

        class Grant(controller.TELECTROProjectBookingGrant):
            def __init__(self, values, previous=None):
                self.values = dict(values)
                self.previous = previous
                self.name = values.get("name")

            def get(self, key):
                return self.values.get(key)

            def update(self, values):
                self.values.update(values)

            def get_doc_before_save(self):
                return self.previous

            def insert(self, *, ignore_permissions):
                self.validate()
                if test.fail_insert:
                    raise RuntimeError("insert failed")
                self.name = f"grant-{len(test.rows) + 1}"
                self.values["name"] = self.name
                test.rows[self.name] = dict(self.values)

            def save(self, *, ignore_permissions):
                self.validate()
                test.rows[self.name] = dict(self.values)

        self.Grant = Grant

    def savepoint(self, name):
        self.savepoints[name] = deepcopy(self.rows)

    def rollback(self, *, save_point):
        self.rows = deepcopy(self.savepoints[save_point])

    def release_savepoint(self, name):
        del self.savepoints[name]

    def clock(self):
        self.events.append("clock")
        return self.now

    def get_value(self, doctype, filters, fields, *, for_update=False, **kwargs):
        if doctype == "Project":
            self.assertTrue(for_update)
            self.events.append("project lock")
            if filters in self.projects:
                return SimpleNamespace(
                    name=filters, company=self.projects[filters], creation=self.project_creation,
                )
            return None
        self.assertEqual(doctype, grants.DOCTYPE)
        if type(filters) is str:
            row = self.rows.get(filters)
            return SimpleNamespace(name=row["name"], project=row["project"]) if row else None
        self.assertTrue(for_update)
        self.events.append("grant read")
        if "active_key" in filters:
            return next((row["name"] for row in self.rows.values()
                         if row.get("active_key") == filters["active_key"]), None)
        closed = [
            row["effective_end"] for row in self.rows.values()
            if row.get("effective_end") and all(
                row.get(key) == value for key, value in filters.items() if key != "effective_end"
            )
        ]
        return max(closed, default=None)

    def get_values(self, doctype, filters, fields, *, for_update=False, **kwargs):
        self.assertEqual(doctype, "Task")
        self.assertTrue(for_update)
        self.events.append("task lock")
        return [(name, self.tasks[name], CREATED) for name in filters["name"][1] if name in self.tasks]

    def get_doc(self, doctype, name=None, *, for_update=False):
        if isinstance(doctype, dict):
            return self.Grant(doctype)
        self.assertTrue(for_update)
        self.events.append("grant lock")
        return self.Grant(self.rows[name], previous=self.rows[name])

    def grant(self, tasks=(TASK,), expected_grant=None, project=PROJECT):
        return grants.set_project_booking_grant(
            technician_user=IDENTITY.user, project=project, permitted_tasks=tasks,
            reason="Pilot", expected_grant=expected_grant,
        )

    def test_server_resolves_scope_and_uses_clock_after_project_lock(self):
        name = self.grant(tasks=("TASK-2", TASK, TASK))
        row = self.rows[name]
        self.identity.assert_called_once_with(IDENTITY.user)
        self.assertEqual(row["employee"], IDENTITY.employee)
        self.assertEqual(row["company"], IDENTITY.company)
        self.assertEqual(row["effective_start"], START)
        self.assertEqual(row["project_created_at"], CREATED)
        self.assertEqual(json.loads(row["permitted_tasks"]), {
            TASK: CREATED.isoformat(), "TASK-2": CREATED.isoformat(),
        })
        self.assertEqual(self.events, ["project lock", "task lock", "grant read", "clock", "grant read"])
        self.assertEqual(self.grant(tasks=(TASK, "TASK-2"), expected_grant=name), name)
        self.assertEqual(len(self.rows), 1)

    def test_replacement_and_revocation_keep_adjacent_immutable_history(self):
        old = self.grant()
        self.now = MIDDLE
        new = self.grant(tasks=(), expected_grant=old)
        self.now = END
        grants.revoke_project_booking_grant(grant_name=new, reason="Stop")
        old_row, new_row = self.rows[old], self.rows[new]
        self.assertEqual(old_row["effective_end"], new_row["effective_start"])
        self.assertEqual(json.loads(old_row["permitted_tasks"]), {TASK: CREATED.isoformat()})
        self.assertEqual(new_row["permitted_tasks"], "{}")
        self.assertEqual(new_row["effective_end"], END)
        self.assertIsNone(old_row["active_key"])
        self.assertIsNone(new_row["active_key"])
        self.assertEqual(new_row["ended_by"], "Administrator")
        self.assertEqual(new_row["end_reason"], "Stop")
        periods = [grants.project_booking_grant_period(row) for row in (old_row, new_row)]
        self.assertTrue(grants.covers_project_booking(
            identity=IDENTITY, project=PROJECT, project_company=IDENTITY.company,
            project_created_at=CREATED, periods=periods, task=TASK, task_project=PROJECT,
            task_created_at=CREATED, start=START, end=MIDDLE, evaluated_at=LATER,
        ))

    def test_failed_replacement_rolls_back_closing_the_active_grant(self):
        old = self.grant()
        before = deepcopy(self.rows)
        self.now = MIDDLE
        self.fail_insert = True
        with self.assertRaisesRegex(RuntimeError, "insert failed"):
            self.grant(tasks=(), expected_grant=old)
        self.assertEqual(self.rows, before)
        self.assertFalse(self.savepoints)

    def test_reused_project_id_requires_revoking_old_grant_and_opening_a_fresh_one(self):
        first = self.grant()
        self.now = MIDDLE
        self.project_creation = START
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.grant(tasks=(), expected_grant=first)
        grants.revoke_project_booking_grant(grant_name=first, reason="Old Project")
        second = self.grant(tasks=())
        self.assertEqual(self.rows[first]["project_created_at"], CREATED)
        self.assertEqual(self.rows[second]["project_created_at"], START)

    def test_stale_create_replace_and_revoke_cannot_change_a_newer_grant(self):
        old = self.grant()
        self.now = MIDDLE
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.grant(tasks=())
        new = self.grant(tasks=(), expected_grant=old)
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.grant(expected_grant=old)
        with self.assertRaises(grants.ProjectBookingGrantError):
            grants.revoke_project_booking_grant(grant_name=old, reason="Stale")
        self.assertEqual(self.rows[new]["effective_start"], MIDDLE)
        self.assertIsNone(self.rows[new].get("effective_end"))

    def test_no_non_admin_mutations_or_client_scope_and_time_assertions(self):
        current = self.grant()
        for user in ("tech", "system-manager", "Guest"):
            self.frappe.session.user = user
            with self.subTest(user=user), self.assertRaises(grants.ProjectBookingGrantError):
                self.grant(expected_grant=current)
            with self.assertRaises(grants.ProjectBookingGrantError):
                grants.revoke_project_booking_grant(grant_name=current, reason="Stop")
        self.frappe.session.user = "Administrator"
        for supplied in ({"company": "Other"}, {"employee": "EMP-2"}, {"effective_start": START}):
            with self.subTest(supplied=supplied), self.assertRaises(TypeError):
                grants.set_project_booking_grant(
                    technician_user=IDENTITY.user, project=PROJECT, permitted_tasks=[],
                    reason="Pilot", **supplied,
                )
        self.assertIsNone(self.rows[current].get("effective_end"))

    def test_cross_company_wrong_parent_and_unknown_recipient_fail_before_open(self):
        for args in ({"project": "PROJ-2"}, {"tasks": ("TASK-3",)}, {"tasks": ("nonexistent",)}):
            with self.subTest(args=args), self.assertRaises(grants.ProjectBookingGrantError):
                self.grant(**args)
        self.identity.side_effect = TechnicianIdentityError()
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.grant()
        self.assertFalse(self.rows)

    def test_revoke_ineligible_recipient_and_reject_clock_regression(self):
        current = self.grant()
        self.now = END
        self.identity.side_effect = TechnicianIdentityError()
        grants.revoke_project_booking_grant(grant_name=current, reason="Departed")
        self.identity.side_effect = None
        self.now = MIDDLE
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.grant()
        self.assertEqual(len(self.rows), 1)

    def test_controller_blocks_direct_edits_deletes_renames_and_historical_rewrites(self):
        name = self.grant()
        self.now = MIDDLE
        grants.revoke_project_booking_grant(grant_name=name, reason="Stop")
        row = self.rows[name]
        doc = self.Grant({**row, "grant_reason": "Changed"}, previous=row)
        for action in (doc.validate, doc.on_trash, lambda: doc.before_rename(name, "other")):
            with self.assertRaises(grants.ProjectBookingGrantError):
                action()
        with self.assertRaises(grants.ProjectBookingGrantError):
            grants._save_transition(doc)
        with self.assertRaises(grants.ProjectBookingGrantError):
            self.Grant(row).validate()
        self.assertEqual(self.rows[name]["grant_reason"], "Pilot")

    def test_schema_is_private_and_active_key_has_a_unique_index(self):
        schema = json.loads(MODEL.with_suffix(".json").read_text())
        fields = {f["fieldname"]: f for f in schema["fields"]}
        self.assertEqual(schema["permissions"], [])
        self.assertEqual(schema["allow_rename"], 0)
        self.assertEqual(schema["engine"], "InnoDB")
        self.assertEqual(fields["active_key"]["unique"], 1)
        self.assertTrue(all(field["read_only"] for field in fields.values()))
        for key in ("technician_user", "employee", "company", "project"):
            self.assertEqual(fields[key]["fieldtype"], "Data")
