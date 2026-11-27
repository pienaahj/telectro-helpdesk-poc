"""Focused tests for the booking-only Project and Task selectors."""

from datetime import datetime, timedelta
import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from telephony import time_booking_project_grant as grants
from telephony.api import time_booking as api
from telephony.time_booking_identity import TechnicianBookingIdentity, TechnicianIdentityError


START = datetime(2026, 11, 20, 9)
END = START + timedelta(hours=1)
CREATED = START - timedelta(days=1)
IDENTITY = TechnicianBookingIdentity("tech@example.com", "EMP-1", "Company A")
PROJECT = "PROJ-1"
TASK = "TASK-1"


class ProjectLookupTests(unittest.TestCase):
    def setUp(self):
        self.projects = {
            PROJECT: SimpleNamespace(name=PROJECT, label="Pilot Project", company=IDENTITY.company, creation=CREATED),
        }
        self.tasks = {
            TASK: SimpleNamespace(name=TASK, label="Pilot Task", project=PROJECT, creation=CREATED),
        }
        self.records = [self.period(tasks=(TASK,))]
        self.reads = []
        self.frappe = SimpleNamespace(
            db=SimpleNamespace(sql=self.sql, get_value=self.get_value, get_values=self.get_values),
            utils=SimpleNamespace(now_datetime=lambda: END + timedelta(days=1)),
        )
        patchers = [
            patch.dict(sys.modules, {"frappe": self.frappe}),
            patch.object(api, "frappe", self.frappe),
            patch.object(api, "_booking_identity", return_value=IDENTITY),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def period(self, *, project=PROJECT, start=CREATED, end=None, tasks=()):
        return {
            "technician_user": IDENTITY.user, "employee": IDENTITY.employee,
            "company": IDENTITY.company, "project": project, "project_created_at": CREATED,
            "effective_start": start, "effective_end": end,
            "permitted_tasks": grants._task_json((task, CREATED) for task in tasks),
            "granted_by": "Administrator", "grant_reason": "Pilot",
            "active_key": grants._active_key(IDENTITY, project) if end is None else None,
            "ended_by": None if end is None else "Administrator",
            "end_reason": None if end is None else "Stopped",
        }

    def get_value(self, doctype, name, fields, *, as_dict):
        self.assertEqual(doctype, "Project")
        self.assertEqual(fields, ["name", "company", "creation"])
        self.assertTrue(as_dict)
        self.reads.append(("parent", name))
        return self.projects.get(name)

    def get_values(self, doctype, filters, fields, *, for_update, as_dict, limit):
        self.assertEqual(doctype, grants.DOCTYPE)
        self.assertFalse(for_update)
        self.assertTrue(as_dict)
        self.assertEqual(limit, 257)
        self.assertEqual(filters["technician_user"], IDENTITY.user)
        self.assertEqual(filters["employee"], IDENTITY.employee)
        self.assertEqual(filters["company"], IDENTITY.company)
        self.reads.append(("history", filters["project"]))
        return [
            {field: record[field] for field in fields}
            for record in self.records
            if all(record.get(field) == value for field, value in filters.items())
        ][:limit]

    def sql(self, statement, params, *, as_dict):
        self.assertTrue(as_dict)
        self.assertNotIn("FOR UPDATE", statement)
        self.assertLessEqual(params["limit"], 100)
        name, term = params["name"], params["term"].casefold()
        if "FROM `tabProject`" in statement:
            self.assertIn("g.project_created_at = p.creation", statement)
            self.assertIn("g.technician_user = %(user)s AND g.employee = %(employee)s", statement)
            self.assertEqual(params["user"], IDENTITY.user)
            self.assertEqual(params["employee"], IDENTITY.employee)
            self.assertEqual(params["company"], IDENTITY.company)
            self.reads.append(("project_search", name))
            # Include candidates that a production query would discard to also
            # exercise the independent Python coverage and metadata checks.
            rows = self.projects.values()
        else:
            self.assertIn("FROM `tabTask`", statement)
            self.assertIn("t.project = %(project)s", statement)
            self.assertEqual(params["project"], PROJECT)
            self.reads.append(("task_search", name))
            rows = [self.tasks[key] for key in json.loads(params["ids"]) if key in self.tasks]
        return sorted(
            (row for row in rows
             if (name is None or row.name.casefold() == name.casefold())
             and (term in row.name.casefold() or term in row.label.casefold())),
            key=lambda row: (row.name != params["term"], row.name),
        )[:params["limit"]]

    def call(self, *, task_lookup=False, **updates):
        args = dict(from_time=START.isoformat(), duration_minutes="60")
        if task_lookup:
            args["project_name"] = PROJECT
        args.update(updates)
        endpoint = api.get_booking_tasks if task_lookup else api.get_booking_projects
        return endpoint.__wrapped__(**args)

    def test_project_only_has_minimal_label_and_no_tasks(self):
        self.records = [self.period()]
        self.assertEqual(self.call(query="pilot"), [{"id": PROJECT, "label": "Pilot Project"}])
        self.assertEqual(self.call(name=PROJECT), [{"id": PROJECT, "label": "Pilot Project"}])
        self.assertEqual(self.call(task_lookup=True), [])
        self.assertNotIn(("task_search", None), self.reads)

    def test_task_requires_explicit_coverage_across_adjacent_periods(self):
        middle = START + timedelta(minutes=30)
        self.records = [self.period(end=middle, tasks=(TASK,)), self.period(start=middle, tasks=(TASK,))]
        self.assertEqual(self.call(task_lookup=True, query="Pilot"), [{"id": TASK, "label": "Pilot Task"}])
        self.assertEqual(self.call(task_lookup=True, name=TASK), [{"id": TASK, "label": "Pilot Task"}])
        self.records[1] = self.period(start=middle)
        self.assertEqual(self.call(task_lookup=True, name=TASK), [])
        self.assertEqual(self.call(name=PROJECT), [{"id": PROJECT, "label": "Pilot Project"}])

    def test_historical_revocation_boundary_and_incomplete_work(self):
        for revoke_at in (END, END + timedelta(minutes=1)):
            with self.subTest(revoke_at=revoke_at):
                self.records = [self.period(end=revoke_at, tasks=(TASK,))]
                self.assertEqual(self.call(name=PROJECT), [{"id": PROJECT, "label": "Pilot Project"}])
                self.assertEqual(self.call(task_lookup=True, name=TASK), [{"id": TASK, "label": "Pilot Task"}])
        for revoke_at in (START - timedelta(minutes=1), END - timedelta(microseconds=1)):
            with self.subTest(revoke_at=revoke_at):
                self.records = [self.period(end=revoke_at, tasks=(TASK,))]
                self.assertEqual(self.call(name=PROJECT), [])
                self.assertEqual(self.call(task_lookup=True, name=TASK), [])
        self.frappe.utils.now_datetime = lambda: END - timedelta(minutes=1)
        self.reads.clear()
        self.assertEqual(self.call(), [])
        self.assertEqual(self.reads, [])

    def test_cross_company_and_reused_project_ids_are_not_disclosed(self):
        self.projects[PROJECT].company = "Other"
        self.assertEqual(self.call(name=PROJECT), [])
        self.assertEqual(self.call(task_lookup=True, name=TASK), [])
        self.projects[PROJECT].company = IDENTITY.company
        self.projects[PROJECT].creation = START
        self.assertEqual(self.call(name=PROJECT), [])
        self.assertEqual(self.call(task_lookup=True, name=TASK), [])

    def test_wrong_parent_reused_and_unentitled_task_ids_are_not_disclosed(self):
        self.tasks[TASK].project = "Other"
        self.assertEqual(self.call(task_lookup=True, name=TASK), [])
        self.tasks[TASK].project = PROJECT
        self.tasks[TASK].creation = START
        self.assertEqual(self.call(task_lookup=True, name=TASK), [])
        self.tasks[TASK].creation = CREATED
        for name in ("UNENTITLED", "MISSING", TASK.lower()):
            self.assertEqual(self.call(task_lookup=True, name=name), [])
        self.assertEqual(self.call(name=PROJECT.lower()), [])

    def test_invalid_or_unauthorized_lookup_has_no_project_reads(self):
        for parameters in (
            {"from_time": "bad"}, {"duration_minutes": "0"}, {"query": "a" * 81},
            {"page": 5}, {"page": True}, {"name": PROJECT, "query": "pilot"},
            {"name": PROJECT, "page": 1},
        ):
            with self.subTest(parameters=parameters):
                self.assertEqual(self.call(**parameters), [])
        for error in (TechnicianIdentityError(), api.ActivationConfigurationError()):
            with patch.object(api, "_booking_identity", side_effect=error):
                self.assertEqual(self.call(), [])
                self.assertEqual(self.call(task_lookup=True, name=TASK), [])
        self.assertEqual(self.reads, [])

    def test_fixed_page_size_and_eligible_result_pagination(self):
        for index in range(25):
            name = f"PROJ-NEW-{index:02}"
            self.projects[name] = SimpleNamespace(
                name=name, label="Other option", company=IDENTITY.company, creation=CREATED,
            )
            self.records.append(self.period(project=name))
        self.records = [record for record in self.records if record["project"] != "PROJ-NEW-00"]
        first = self.call()
        second = self.call(page="1")
        self.assertEqual(len(first), 20)
        self.assertEqual(len(second), 5)
        self.assertFalse({item["id"] for item in first} & {item["id"] for item in second})
        self.assertNotIn("PROJ-NEW-00", {item["id"] for item in first + second})
