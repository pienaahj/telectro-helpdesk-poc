"""Focused report tests using the production query against an isolated ledger."""

from datetime import date, datetime
import re
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import frappe

from telephony.ftelephony.report.technician_own_booked_hours import technician_own_booked_hours as report
from telephony.time_booking_identity import TechnicianBookingIdentity, TechnicianIdentityError


class TestTechnicianOwnBookedHours(unittest.TestCase):
    def setUp(self):
        db = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
        self.addCleanup(db.close)
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE `tabTimesheet` (
                name TEXT PRIMARY KEY, user TEXT, employee TEXT, company TEXT,
                custom_telectro_booking_origin TEXT, docstatus INTEGER
            );
            CREATE TABLE `tabTimesheet Detail` (
                name TEXT PRIMARY KEY, parent TEXT, parenttype TEXT, parentfield TEXT,
                from_time TIMESTAMP, to_time TIMESTAMP, activity_type TEXT,
                custom_work_context TEXT, custom_service_area TEXT, custom_work_origin TEXT,
                custom_emergency INTEGER, custom_hd_customer TEXT, custom_unlisted_customer_name TEXT,
                project TEXT, task TEXT, custom_hd_ticket TEXT, custom_external_reference TEXT,
                description TEXT
            );
        """)
        self.db = db
        self.readable = set()
        self.identity = TechnicianBookingIdentity("tech", "EMP-1", "Company")
        self.filters = {"from_date": "2026-11-22", "to_date": "2026-11-22"}
        self.sql = Mock(side_effect=self._query)
        self.resolve = Mock(return_value=self.identity)
        self.get_doc = Mock(side_effect=self._get_doc)
        for patcher in (
            patch.object(report, "resolve_current_technician_identity", self.resolve),
            patch.object(
                report, "frappe",
                SimpleNamespace(
                    db=SimpleNamespace(sql=self.sql),
                    get_doc=self.get_doc,
                    throw=self._throw,
                    DoesNotExistError=frappe.DoesNotExistError,
                    PermissionError=frappe.PermissionError,
                    ValidationError=frappe.ValidationError,
                ),
            ),
            patch.object(report, "_", lambda label: label),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _query(self, query, values, *, as_dict):
        self.assertTrue(as_dict)
        query = re.sub(r"%\((\w+)\)s", r":\1", query)
        params = {
            key: value.isoformat(" ") if isinstance(value, datetime) else value
            for key, value in values.items()
        }
        return [dict(row) for row in self.db.execute(query, params)]

    @staticmethod
    def _throw(message, error):
        raise error(message)

    def _get_doc(self, doctype, name):
        if name == "missing":
            raise frappe.DoesNotExistError
        return SimpleNamespace(name=name, has_permission=lambda operation: (
            operation == "read" and (doctype, name) in self.readable
        ))

    def _booking(
        self, name, *, status=0, user="tech", employee="EMP-1", company="Company",
        marker="Phase 2", start="2026-11-22 10:00:00", end="2026-11-22 11:00:00",
        emergency=0, context="Internal", origin="Direct / Ad-hoc", customer=None,
        unlisted=None, project=None, task=None, ticket=None, reference=None,
        parenttype="Timesheet", parentfield="time_logs",
    ):
        self.db.execute("INSERT INTO `tabTimesheet` VALUES (?, ?, ?, ?, ?, ?)",
                        (name, user, employee, company, marker, status))
        self.db.execute(
            "INSERT INTO `tabTimesheet Detail` VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name + "-line", name, parenttype, parentfield, start, end, "Travel", context,
             "PABX", origin, emergency, customer, unlisted, project, task, ticket, reference,
             "Unrestricted description must never be returned"),
        )

    def _rows(self, *, detail=False, **filters):
        options = self.filters | filters
        if detail:
            options["view"] = "Booking Detail"
        _, rows = report.execute(options)
        return rows

    def test_scopes_query_to_resolved_identity_even_with_spoofed_filters(self):
        self._booking("own")
        self._booking("other-user", user="other")
        self._booking("other-employee", employee="EMP-2")
        self._booking("other-company", company="Other")
        rows = self._rows(detail=True, user="other", employee="EMP-2", company="Other")
        self.assertEqual([row["booking"] for row in rows], ["own"])
        self.assertEqual(self._rows()[0]["booked_hours"], 1)

    def test_rejects_failed_identity_before_reading_data(self):
        self.resolve.side_effect = TechnicianIdentityError
        with self.assertRaises(frappe.PermissionError):
            self._rows()
        self.sql.assert_not_called()
        self.get_doc.assert_not_called()

    def test_lifecycle_totals_count_current_rows_and_break_down_status(self):
        self._booking("draft")
        self._booking("submitted", status=1)
        self._booking("replaced-original", status=2)
        self._booking("replacement")
        self._booking("withdrawn")
        self.db.execute("DELETE FROM `tabTimesheet Detail` WHERE parent='withdrawn'")
        self.db.execute("DELETE FROM `tabTimesheet` WHERE name='withdrawn'")
        self._booking("legacy", marker="")
        self._booking("unrelated-child", parentfield="other")
        self._booking("unrelated-parent", parenttype="Other")
        row, = self._rows()
        self.assertEqual((row["booked_hours"], row["draft_hours"], row["submitted_hours"]), (3, 2, 1))
        self.assertEqual({row["booking"] for row in self._rows(detail=True)}, {"draft", "submitted", "replacement"})

    def test_midnight_splits_both_daily_totals_and_detail(self):
        self._booking("overnight", start="2026-11-22 23:30:00", end="2026-11-23 00:30:00")
        rows = self._rows(to_date="2026-11-23")
        self.assertEqual([(row["day"], row["booked_hours"]) for row in rows],
                         [(date(2026, 11, 22), 0.5), (date(2026, 11, 23), 0.5)])
        before, after = self._rows(detail=True, to_date="2026-11-23")
        self.assertEqual(before["to_time"], "2026-11-23 00:00:00")
        self.assertEqual(after["from_time"], "2026-11-23 00:00:00")

    def test_date_window_clips_both_ends_and_excludes_boundary_touches(self):
        self._booking("over-left", start="2026-11-21 23:00:00", end="2026-11-22 00:15:00")
        self._booking("over-right", start="2026-11-22 23:30:00", end="2026-11-23 01:00:00")
        self._booking("ends-at-start", start="2026-11-21 23:00:00", end="2026-11-22 00:00:00")
        self._booking("starts-at-end", start="2026-11-23 00:00:00", end="2026-11-23 01:00:00")
        row, = self._rows()
        self.assertEqual(row["booked_hours"], 0.75)

    def test_dates_are_required_and_ordered(self):
        for filters in ({}, {"to_date": "2026-11-21"}, {"from_date": "20261122"}, {"to_date": "9999-12-31"}):
            with self.subTest(filters=filters), self.assertRaises(frappe.ValidationError):
                report.execute(self.filters | filters if filters else {})
        self.sql.assert_not_called()

    def test_emergency_is_a_filterable_subset_of_total_hours(self):
        self._booking("emergency", emergency=1, status=1)
        self._booking("routine")
        row, = self._rows()
        self.assertEqual((row["booked_hours"], row["emergency_hours"]), (2, 1))
        self.assertEqual(self._rows(emergency="Yes")[0]["booked_hours"], 1)
        self.assertEqual(self._rows(emergency="No")[0]["emergency_hours"], 0)

    def test_missing_references_do_not_drop_hours(self):
        self._booking("internal")
        self._booking("unlisted", context="Customer Support", unlisted="External")
        self._booking("archived-reference", context="Helpdesk", ticket="missing")
        self.assertEqual(self._rows()[0]["booked_hours"], 3)
        row, = self._rows(detail=True, customer="External", work_context="Customer Support")
        self.assertEqual(row["unlisted_customer"], "External")
        self.assertIsNone(row["ticket"])
        self.assertIsNone(row["project"])

    def test_denied_reference_is_hidden_from_details_filters_and_totals(self):
        self._booking("private", context="Project", project="Private-P", task="Private-T",
                      customer="Restricted", origin="Snapfix", reference="Private-S")
        self.readable.update({("HD Customer", "Restricted"), ("Project", "Private-P")})
        row, = self._rows(detail=True)
        self.assertEqual(row["booked_hours"], 1)
        self.assertNotIn("description", row)
        for field in ("customer", "project", "task", "snapfix_reference"):
            self.assertIsNone(row[field])
            self.assertEqual(self._rows(**{field: "Restricted" if field == "customer" else {
                "project": "Private-P", "task": "Private-T", "snapfix_reference": "Private-S",
            }[field]}), [])

    def test_readable_references_are_filterable_and_export_unsafe_text_is_neutralized(self):
        self._booking("readable", context="Customer Support", customer="Visible",
                      origin="Snapfix", reference="=External")
        self.readable.add(("HD Customer", "Visible"))
        row, = self._rows(detail=True, customer="visible", snapfix_reference="=External")
        self.assertEqual((row["customer"], row["snapfix_reference"]), ("Visible", "'=External"))
        self.assertEqual(self._rows(work_origin="Snapfix", service_area="PABX")[0]["booked_hours"], 1)
        self.get_doc.assert_called_with("HD Customer", "Visible")
