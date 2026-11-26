"""Focused Supervisor report checks against the real ledger query and Frappe rules."""

import csv
from datetime import date, datetime
from io import BytesIO, StringIO
import os
from pathlib import Path
import re
import runpy
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import frappe
from frappe.core.doctype.report import report as native_report

from telephony.ftelephony.report.supervisor_booked_hours import supervisor_booked_hours as report
from telephony.supervisor_report_runtime import REPORT_NAME, TelectroReport
from telephony.supervisor_reporting_grant import SupervisorReportingGrantError
from telephony.time_booking_identity import TechnicianBookingIdentity

TECH = TechnicianBookingIdentity("tech", "EMP-1", "Company")
OTHER = TechnicianBookingIdentity("other", "EMP-2", "Other Company")
DATES = {"from_date": "2026-11-23", "to_date": "2026-11-23"}


class TestSupervisorBookedHours(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript("""
            CREATE TABLE `tabTimesheet` (
                name TEXT PRIMARY KEY, user TEXT, employee TEXT, company TEXT,
                custom_telectro_booking_origin TEXT, docstatus INTEGER
            );
            CREATE TABLE `tabTimesheet Detail` (
                name TEXT PRIMARY KEY, parent TEXT, parenttype TEXT, parentfield TEXT,
                from_time TIMESTAMP, to_time TIMESTAMP, activity_type TEXT,
                custom_work_context TEXT, custom_service_area TEXT, custom_work_origin TEXT,
                custom_emergency INTEGER, custom_hd_customer TEXT, custom_unlisted_customer_name TEXT,
                project TEXT, task TEXT, custom_hd_ticket TEXT, custom_external_reference TEXT, description TEXT
            );
        """)
        self.scope = Mock(return_value={TECH})
        self.sql = Mock(side_effect=self.query)
        self.documents = {}
        self.permissions = {}
        self.erp_customers = set()
        for item in (
            patch.object(report, "resolve_supervisor_reporting_scope", self.scope),
            patch.object(report, "get_user_permissions", lambda user: self.permissions),
            patch.object(report, "_hd_customers_for", self.hd_customers_for),
            patch.object(report, "_", lambda label: label),
            patch.object(report, "frappe", SimpleNamespace(
                db=SimpleNamespace(sql=self.sql, get_value=self.get_value),
                session=SimpleNamespace(user="supervisor"), local=SimpleNamespace(message_log=[]),
                get_doc=self.get_doc, PermissionError=frappe.PermissionError,
                DoesNotExistError=frappe.DoesNotExistError, ValidationError=frappe.ValidationError,
            )),
        ):
            item.start()
            self.addCleanup(item.stop)

    def query(self, query, values, *, as_dict):
        self.assertTrue(as_dict)
        params = {
            key: value.isoformat(" ") for key, value in values.items() if isinstance(value, datetime)
        }
        tuples = []
        for number, identity in enumerate(values["roster"]):
            keys = [f"roster_{number}_{field}" for field in range(3)]
            params.update(zip(keys, identity))
            tuples.append("(" + ", ".join(":" + key for key in keys) + ")")
        query = query.replace("%(roster)s", "(" + ", ".join(tuples) + ")")
        query = re.sub(r"%\((\w+)\)s", r":\1", query)
        return [frappe._dict(dict(row)) for row in self.db.execute(query, params)]

    def get_value(self, doctype, name, fieldname):
        self.assertEqual((doctype, fieldname), ("Customer", "name"))
        return name if name in self.erp_customers else None

    def hd_customers_for(self, erp_name):
        return [
            name for (doctype, name), doc in self.documents.items()
            if doctype == "HD Customer" and doc.get("custom_erp_customer") == erp_name
        ]

    def get_doc(self, doctype, name):
        try:
            return self.documents[doctype, name]
        except KeyError as exc:
            raise frappe.DoesNotExistError from exc

    def reference(self, doctype, name, *, readable=True, **fields):
        self.documents[doctype, name] = frappe._dict(
            fields, name=name, has_permission=lambda operation: readable and operation == "read",
        )
        if fields.get("custom_erp_customer") and doctype == "HD Customer":
            self.erp_customers.add(fields["custom_erp_customer"])

    def add(self, name, *, identity=TECH, status=0, marker="Phase 2", context="Internal",
            start="2026-11-23 10:00:00", end="2026-11-23 11:00:00", emergency=0,
            customer=None, unlisted=None, project=None, task=None, ticket=None,
            origin="Direct / Ad-hoc", reference=None, description=None):
        self.db.execute("INSERT INTO `tabTimesheet` VALUES (?, ?, ?, ?, ?, ?)",
                        (name, identity.user, identity.employee, identity.company, marker, status))
        self.db.execute(
            "INSERT INTO `tabTimesheet Detail` VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name + "-line", name, "Timesheet", "time_logs", start, end, "Travel", context,
             "PABX", origin, emergency, customer, unlisted, project, task, ticket, reference, description),
        )

    def rows(self, detail=False, **filters):
        options = dict(DATES, **filters)
        if detail:
            options["view"] = "Booking Detail"
        return report.execute(options)[1]

    def test_role_denial_stops_before_ledger_query(self):
        self.scope.side_effect = SupervisorReportingGrantError
        with self.assertRaises(SupervisorReportingGrantError):
            self.rows()
        self.sql.assert_not_called()

    def test_revocation_and_empty_scope_return_no_data_without_query(self):
        self.add("own")
        self.assertEqual(self.rows()[0]["booked_hours"], 1)
        self.scope.return_value = frozenset()
        self.sql.reset_mock()
        self.assertEqual(self.rows(detail=True, employee=TECH.employee), [])
        self.sql.assert_not_called()

    def test_roster_matches_user_employee_and_company_and_filters_only_narrow(self):
        self.add("granted")
        self.add("other", identity=OTHER)
        self.add("wrong-user", identity=TechnicianBookingIdentity(OTHER.user, TECH.employee, TECH.company))
        self.add("wrong-company", identity=TechnicianBookingIdentity(TECH.user, TECH.employee, OTHER.company))
        self.assertEqual([row["booking"] for row in self.rows(detail=True, user=OTHER.user)], ["granted"])
        self.assertEqual(self.rows(company=OTHER.company), [])
        self.scope.return_value = {TECH, OTHER}
        self.assertEqual([row["booking"] for row in self.rows(detail=True, company=OTHER.company)], ["other"])
        self.assertEqual(self.rows(company=OTHER.company, employee=TECH.employee), [])

    def test_employee_daily_grouping_lifecycle_and_midnight_clipping(self):
        self.scope.return_value = {TECH, OTHER}
        self.add("original", status=2)
        self.add("replacement", start="2026-11-22 23:30:00", end="2026-11-23 00:30:00", emergency=1)
        self.add("submitted", status=1, start="2026-11-23 23:45:00", end="2026-11-24 00:45:00")
        self.add("other", identity=OTHER)
        self.add("legacy", marker="")
        self.add("withdrawn")
        self.db.execute("DELETE FROM `tabTimesheet` WHERE name = 'withdrawn'")
        summary = {row["employee"]: row for row in self.rows()}
        row = summary[TECH.employee]
        self.assertEqual(tuple(row[x] for x in ("booked_hours", "draft_hours", "submitted_hours", "emergency_hours")),
                         (0.75, 0.5, 0.25, 0.5))
        self.assertEqual(summary[OTHER.employee]["booked_hours"], 1)
        rows = self.rows(from_date="2026-11-22", to_date="2026-11-24", employee=TECH.employee)
        self.assertEqual([(r["day"], r["booked_hours"]) for r in rows],
                         [(date(2026, 11, 22), 0.5), (date(2026, 11, 23), 0.75), (date(2026, 11, 24), 0.75)])
        detail = self.rows(detail=True, employee=TECH.employee)
        self.assertEqual([r["booking"] for r in detail], ["replacement", "submitted"])
        self.assertEqual(detail[0]["from_time"], "2026-11-23 00:00:00")

    def test_customer_restrictions_intersect_and_filter_only_authorized_rows(self):
        self.reference("HD Customer", "Boschendal", custom_erp_customer="ERP-A")
        self.reference("HD Customer", "Another", custom_erp_customer="ERP-B")
        self.add("snapfix", context="Customer Support", customer="Boschendal", origin="Snapfix", reference="SF-123")
        self.add("other", context="Customer Support", customer="Another")
        self.add("unlisted", context="Customer Support", unlisted="Boschendal")
        self.add("internal")
        self.permissions = {
            "HD Customer": [{"doc": "Boschendal", "applicable_for": "Timesheet Detail"}],
            "Customer": [{"doc": "ERP-A", "applicable_for": "Timesheet"}],
        }
        row, = self.rows(detail=True, customer="Boschendal")
        self.assertEqual((row["booking"], row["snapfix_reference"]), ("snapfix", "SF-123"))
        self.assertEqual(self.rows()[0]["booked_hours"], 1)
        self.assertEqual(self.rows(customer="Another"), [])
        self.permissions["Customer"][0]["doc"] = "ERP-B"
        self.assertEqual(self.rows(), [])

    def test_conflicting_missing_and_unreadable_customer_attribution_excludes_entire_row(self):
        self.reference("HD Customer", "A", custom_erp_customer="ERP-A")
        self.reference("HD Customer", "B", custom_erp_customer="ERP-B", readable=False)
        self.reference("HD Ticket", "42", customer="B", custom_customer="ERP-B")
        self.reference("Project", "P", company=TECH.company, customer="ERP-B")
        self.add("conflict", context="Helpdesk", customer="A", ticket=42)
        self.add("project-conflict", context="Project", customer="A", project="P")
        self.add("not-readable", context="Customer Support", customer="B")
        self.add("missing", context="Customer Support", customer="Missing")
        self.add("canonical", context="Customer Support", customer="A")
        self.assertEqual([r["booking"] for r in self.rows(detail=True)], ["canonical"])
        self.reference("HD Customer", "Duplicate", custom_erp_customer="ERP-A")
        self.assertEqual(self.rows(), [])

    def test_legacy_blank_counts_in_overall_hours_without_inheriting_mutable_customer(self):
        self.reference("HD Customer", "A", custom_erp_customer="ERP-A", readable=False)
        self.reference("HD Ticket", "42", customer="A", custom_customer="ERP-A", readable=False)
        self.add("legacy-blank", context="Helpdesk", ticket=42)
        row, = self.rows(detail=True)
        self.assertEqual(row["booked_hours"], 1)
        self.assertIsNone(row["customer"])
        self.assertIsNone(row["ticket"])
        self.assertEqual(self.rows(customer="A"), [])
        self.permissions = {"HD Customer": [{"doc": "A", "applicable_for": "Timesheet"}]}
        self.assertEqual(self.rows(), [])

    def test_unrelated_customer_rule_and_independent_linked_read_checks(self):
        self.reference("HD Customer", "A", custom_erp_customer="ERP-A")
        self.reference("Project", "P", company=TECH.company, customer="ERP-A", readable=False)
        self.reference("Task", "T", project="P")
        self.add("project", context="Project", customer="A", project="P", task="T",
                 origin="Snapfix", reference="hidden")
        self.permissions = {"Customer": [{"doc": "Elsewhere", "applicable_for": "Sales Invoice"}]}
        row, = self.rows(detail=True)
        self.assertEqual(row["booked_hours"], 1)
        self.assertEqual((row["project"], row["task"], row["snapfix_reference"]), (None, None, None))
        self.assertNotIn("user", row)
        self.assertIsNone(row["description"])
        self.permissions = {"Customer": [{"doc": "Elsewhere", "applicable_for": "Project"}]}
        self.assertEqual(self.rows(), [])


    def test_all_breakdowns_reconcile_with_clipped_detail_and_saved_customers(self):
        self.scope.return_value = {TECH, OTHER}
        self.reference("HD Customer", "Standalone")
        self.reference("Project", "P", company=TECH.company)
        self.reference("Task", "T", project="P")
        self.add("project", context="Project", project="P", task="T",
                 start="2026-11-22 23:45:00", end="2026-11-23 00:30:00", emergency=1)
        self.add("unlisted", context="Customer Support", unlisted="Standalone", identity=OTHER, status=1)
        self.add("snapfix", context="Customer Support", customer="Standalone",
                 origin="Snapfix", reference="SF-42")
        self.add("internal")
        totals = ("booked_hours", "draft_hours", "submitted_hours", "emergency_hours")
        for view in ("Daily Summary", "Booking Detail", *report._BREAKDOWNS):
            columns, rows = report.execute(dict(DATES, view=view))
            self.assertEqual(tuple(sum(row[k] for row in rows) for k in totals), (3.5, 2.5, 1, 0.5))
            self.assertTrue(all(set(row) == {col["fieldname"] for col in columns} for row in rows))
        customers = self.rows(view="Customer Breakdown")
        self.assertEqual({row["customer_type"] for row in customers},
                         {"Listed Customer", "Unlisted Customer", "Unattributed", "Not applicable"})
        project, = self.rows(detail=True, project="P", task="T", activity_type="Travel")
        self.assertEqual(project["recorded_start"], "2026-11-22 23:45:00")
        self.assertEqual(project["from_time"], "2026-11-23 00:00:00")
        self.assertEqual(self.rows(detail=True, snapfix_reference="SF-42")[0]["booking"], "snapfix")
        self.assertEqual(self.rows(detail=True, customer="Standalone", customer_type="Unlisted Customer")[0]["booking"],
                         "unlisted")

    def test_redacted_dimensions_cannot_be_selected_and_description_is_spreadsheet_safe(self):
        self.reference("HD Ticket", "hidden", readable=False)
        self.reference("HD Ticket", "visible")
        self.add("restricted", context="Helpdesk", ticket="hidden", description="private text",
                 origin="Snapfix", reference="hidden external")
        self.add("missing", context="Helpdesk", ticket="missing-ticket", description="missing private text")
        self.add("visible", context="Helpdesk", ticket="visible", description='=HYPERLINK("example")')
        for view in ("Daily Summary", "Booking Detail", *report._BREAKDOWNS):
            for field, value in (("ticket", "hidden"), ("ticket", "missing-ticket"),
                                 ("snapfix_reference", "hidden external")):
                self.assertEqual(self.rows(view=view, **{field: value}), [])
            self.assertNotIn("hidden", repr(self.rows(view=view)))
        restricted, = self.rows(detail=True, reference_state="Restricted reference")
        missing, = self.rows(detail=True, reference_state="Missing historical reference")
        authorized, = self.rows(detail=True, ticket="visible")
        self.assertIsNone(restricted["description"])
        self.assertIsNone(missing["description"])
        self.assertTrue(authorized["description"].startswith("'="))
        self.assertEqual(restricted["booked_hours"] + missing["booked_hours"], 2)


class TestSupervisorReportDelegation(unittest.TestCase):
    @staticmethod
    def controller(name, *, standard="Yes", prepared=0):
        doc = TelectroReport.__new__(TelectroReport)
        doc.name, doc.is_standard, doc.prepared_report = name, standard, prepared
        return doc

    def test_native_standard_execution_has_timing_and_no_preparation_timer(self):
        doc = self.controller(REPORT_NAME)
        filters = {"from_date": "2026-11-23"}

        def standard_execute(received):
            self.assertIs(received, filters)
            self.assertEqual(doc.prepared_report, 1)
            return "result"

        with patch.object(doc, "execute_module", side_effect=standard_execute) as execute, patch.object(
            native_report.threading, "Timer",
        ) as timer, patch.object(frappe, "cache", Mock()) as cache:
            self.assertEqual(doc.execute_script_report(filters), "result")

        execute.assert_called_once_with(filters)
        timer.assert_not_called()
        key, name, duration = cache.hset.call_args.args
        self.assertEqual((key, name), ("report_execution_time", REPORT_NAME))
        self.assertGreaterEqual(duration, 0)
        self.assertEqual(doc.prepared_report, 0)

    def test_native_exception_propagates_and_restores_either_original_flag(self):
        for original in (0, 1):
            doc = self.controller(REPORT_NAME, prepared=original)
            error = RuntimeError("native execution failed")
            with self.subTest(original=original), patch.object(
                doc, "execute_module", side_effect=error,
            ), patch.object(native_report.threading, "Timer") as timer:
                with self.assertRaises(RuntimeError) as raised:
                    doc.execute_script_report({})
            self.assertIs(raised.exception, error)
            self.assertEqual(doc.prepared_report, original)
            timer.assert_not_called()

    def test_unrelated_report_keeps_native_script_dispatch_and_timer(self):
        doc = self.controller("Other Script Report", standard="No")
        filters = {}
        with patch.object(doc, "execute_script", return_value="result") as execute, patch.object(
            native_report.threading, "Timer",
        ) as timer, patch.object(frappe, "local", SimpleNamespace(site="frontend")), patch.object(
            frappe, "cache", Mock(),
        ):
            self.assertEqual(doc.execute_script_report(filters), "result")

        execute.assert_called_once_with(filters)
        timer.assert_called_once_with(
            interval=15, function=native_report.enable_prepared_report,
            kwargs={"report": doc.name, "site": "frontend"},
        )
        timer.return_value.start.assert_called_once_with()
        timer.return_value.cancel.assert_called_once_with()
        self.assertEqual(doc.prepared_report, 0)

    def test_conflicting_local_report_override_is_rejected(self):
        hooks = Path(__file__).resolve().parents[1] / "hooks.py"
        with self.assertRaisesRegex(RuntimeError, "Conflicting Telephony Report override"):
            runpy.run_path(str(hooks), init_globals={"override_doctype_class": {"Report": "another.Report"}})


@unittest.skipUnless(os.environ.get("TELECTRO_SUPERVISOR_REPORT_TEST_DEV") == "1", "Run explicitly on DEV")
class TestSupervisorBookedHoursNative(unittest.TestCase):
    def test_native_report_and_export_parity(self):
        from frappe.desk import query_report
        from frappe.model.base_document import get_controller
        from frappe.permissions import can_export
        from openpyxl import load_workbook
        from telephony import supervisor_reporting_grant as grants
        from telephony.time_booking_identity import TechnicianIdentityError, _resolve_technician_identity

        frappe.init(site="frontend", sites_path=".")
        frappe.connect()
        try:
            self.assertIs(
                get_controller("Report"), TelectroReport,
                f"Effective Report controller must be TelectroReport. "
                f"Registered overrides: {frappe.get_hooks('override_doctype_class').get('Report')}",
            )
            supervisors = frappe.get_all(
                "Has Role", filters={"role": grants.SUPERVISOR_ROLE, "parenttype": "User"}, pluck="parent",
            )
            supervisor = next(
                (user for user in supervisors if not frappe.has_permission("Timesheet", "read", user=user)),
                None,
            )
            self.assertIsNotNone(supervisor)
            technicians = frappe.get_all(
                "Has Role", filters={"role": "TELECTRO-POC Role - Tech", "parenttype": "User"}, pluck="parent",
            )
            for user in technicians:
                try:
                    identity = _resolve_technician_identity(user)
                except TechnicianIdentityError:
                    continue
                break
            else:
                self.fail("A DEV Technician identity is required")

            self.assertEqual(frappe.db.get_value("HD Customer", "Boschendal", "name"), "Boschendal")
            existing = frappe.db.get_value(grants.DOCTYPE, {
                "supervisor_user": supervisor, "employee": identity.employee, "company": identity.company,
                "revoked_at": ["is", "not set"],
            })
            temporary_grant = None
            if not existing:
                temporary_grant = grants.create_supervisor_reporting_grant(
                    supervisor_user=supervisor, employee=identity.employee, reason="DEV report verification",
                )
            prefix = "test-sbh-" + uuid4().hex
            for suffix, status, customer, company in (
                ("visible", 0, "Boschendal", identity.company),
                ("denied", 0, None, identity.company),
                ("cancelled", 2, "Boschendal", identity.company),
                ("other-company", 0, "Boschendal", "Different Company"),
            ):
                booking = f"{prefix}-{suffix}"
                frappe.db.sql("""
                    INSERT INTO `tabTimesheet`
                        (name, user, employee, company, docstatus, custom_telectro_booking_origin)
                    VALUES (%s, %s, %s, %s, %s, 'Phase 2')
                """, (booking, identity.user, identity.employee, company, status))
                frappe.db.sql("""
                    INSERT INTO `tabTimesheet Detail`
                        (name, parent, parenttype, parentfield, from_time, to_time,
                         activity_type, custom_work_context, custom_work_origin, custom_emergency,
                         custom_hd_customer, custom_external_reference, description)
                    VALUES (%s, %s, 'Timesheet', 'time_logs', '2097-01-15 23:30:00',
                            '2097-01-16 00:30:00', 'Travel', 'Customer Support', 'Snapfix', 1, %s, %s, %s)
                """, (booking, booking, customer, f"SF-{suffix}", f"=1+1 REP {suffix}"))

            frappe.set_user(supervisor)
            self.assertFalse(frappe.has_permission("Timesheet", "read"))
            self.assertTrue(frappe.has_permission("HD Ticket Priority", "report"))
            self.assertTrue(can_export("HD Ticket Priority"))
            self.assertIsInstance(query_report.get_report_doc(REPORT_NAME), TelectroReport)
            self.assertIn('label: __("Customer")', query_report.get_script(REPORT_NAME)["script"])
            frappe.set_user("Administrator")
            variant = frappe.get_doc({
                "doctype": "Report", "report_name": prefix, "is_standard": "No",
                "report_type": "Custom Report", "ref_doctype": "HD Ticket Priority",
                "module": "FTelephony", "reference_report": REPORT_NAME, "prepared_report": 1,
            }).insert(ignore_permissions=True)
            # Verify that the native route stays live even with either flag set in the database.
            frappe.db.set_value("Report", REPORT_NAME, "prepared_report", 1)
            frappe.set_user(supervisor)
            for name in (REPORT_NAME, variant.name):
                self.assertEqual(query_report.get_report_doc(name).prepared_report, 0)
                with self.assertRaises(frappe.PermissionError):
                    frappe.get_doc({
                        "doctype": "Prepared Report", "report_name": name, "filters": "{}",
                    }).insert(ignore_permissions=True)
            filters = {"from_date": "2097-01-15", "to_date": "2097-01-16", "view": "Booking Detail"}
            permissions = {"HD Customer": [{"doc": "Boschendal", "applicable_for": "Timesheet Detail"}]}
            with patch.object(report, "get_user_permissions", return_value=permissions):
                result = query_report.run(REPORT_NAME, filters=filters)
                visible = f"{prefix}-visible"
                self.assertEqual([row["booking"] for row in result["result"][:-1]], [visible, visible])
                self.assertEqual([row["snapfix_reference"] for row in result["result"][:-1]], ["SF-visible"] * 2)
                self.assertEqual(result["result"][-1][3:7], [1.0, 1.0, "", 1.0])
                self.assertFalse(result.get("prepared_report"))
                for view in report._BREAKDOWNS:
                    grouped = query_report.run(REPORT_NAME, filters=dict(filters, view=view))
                    data, total = grouped["result"]
                    self.assertEqual(data["booked_hours"], 1.0)
                    hours_column = next(i for i, column in enumerate(grouped["columns"])
                                        if column["fieldname"] == "booked_hours")
                    self.assertEqual(total[hours_column], 1.0)
                variant_result = query_report.run(variant.name, filters=filters)
                self.assertFalse(variant_result.get("prepared_report"))
                self.assertEqual(variant_result["result"], result["result"])
                for kind in ("CSV", "Excel"):
                    frappe.local.response = frappe._dict()
                    frappe.local.form_dict = frappe._dict(
                        report_name=REPORT_NAME, file_format_type=kind, filters=filters,
                        custom_columns="[]", applied_filters={}, include_indentation=0,
                        include_filters=0, include_hidden_columns=0, visible_idx="[]",
                    )
                    query_report.export_query()
                    content = frappe.response.filecontent
                    if kind == "CSV":
                        rows = list(csv.reader(StringIO(content.decode("utf-8-sig"))))
                    else:
                        workbook = load_workbook(BytesIO(content), read_only=True)
                        rows = list(workbook.active.values)
                        workbook.close()
                    self.assertEqual(rows[0][3], "Booked Hours")
                    self.assertEqual([row[7] for row in rows[1:-1]], [visible, visible])
                    self.assertEqual(float(rows[-1][3]), 1.0)
                    self.assertEqual(float(rows[-1][6]), 1.0)
                    description_column = rows[0].index("Booking Description")
                    self.assertTrue(all(str(row[description_column]).startswith("'=") for row in rows[1:-1]))

            if temporary_grant:
                frappe.set_user("Administrator")
                grants.revoke_supervisor_reporting_grant(
                    grant_name=temporary_grant, reason="DEV report revocation verification",
                )
                frappe.set_user(supervisor)
                self.assertEqual(query_report.run(REPORT_NAME, filters=filters)["result"], [])

            if grants.SUPERVISOR_ROLE not in frappe.get_roles(identity.user):
                frappe.set_user(identity.user)
                with self.assertRaises(frappe.PermissionError):
                    query_report.run(REPORT_NAME, filters=filters)
        finally:
            frappe.db.rollback()
            frappe.destroy()
