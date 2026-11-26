from datetime import datetime
import unittest
from unittest.mock import Mock, patch

import frappe

from telephony.ftelephony.page.technician_work_overview import technician_work_overview as page


class TestTechnicianWorkOverview(unittest.TestCase):
    def setUp(self):
        local_flags = patch.object(frappe.local, "flags", frappe._dict(in_test=True), create=True)
        local_flags.start()
        self.addCleanup(local_flags.stop)
        self.addCleanup(patch.stopall)
        patch.object(page, "_", lambda message: message).start()
        patch.object(page, "nowdate", return_value="2026-11-26").start()
        patch.object(page, "_authorized_scope", return_value=frozenset({"supervisor scope"})).start()
        patch.object(page, "_employee_labels", return_value={"EMP-A": "Alex", "EMP-Z": "Zee"}).start()
        patch.object(page.frappe, "throw", side_effect=lambda message, exc=frappe.ValidationError: self._raise(exc, message)).start()
        self.rows = [
            self.booking("a", "EMP-A", "Helpdesk", "Boschendal", "2026-11-22 23:55:00",
                         "2026-11-23 00:17:00", reference_state="Restricted reference", description=None),
            self.booking("b", "EMP-Z", "Customer Support", "Boschendal", "2026-11-25 10:00:00",
                         "2026-11-25 10:15:00", snapfix_reference="SF-42", reference_kind="Snapfix"),
            self.booking("c", "EMP-Z", "Project", None, "2026-11-26 10:00:00",
                         "2026-11-26 10:01:00.000001", project="P-1", project_name="Installation",
                         reference_kind="Project"),
        ]
        self.authorized = patch.object(page, "authorized_bookings", side_effect=lambda *args: self.rows).start()

    @staticmethod
    def _raise(exc, message):
        raise exc(message)

    @staticmethod
    def booking(name, employee, context, customer, start, end, **fields):
        return {
            "booking": name, "employee": employee, "company": "Demo", "docstatus": 0,
            "from_time": datetime.fromisoformat(start), "to_time": datetime.fromisoformat(end), "emergency": 0,
            "work_context": context, "customer": customer, "unlisted_customer": None,
            "customer_type": "Listed Customer" if customer else "Unattributed",
            "project": None, "project_name": None, "task": None, "ticket": None, "snapfix_reference": None,
            "reference_kind": "No visible reference", "reference_state": "Available",
            "service_area": "PABX", "activity_type": "Repair", "status": "Draft",
            "description": "Authorized note", **fields,
        }

    def test_site_calendar_presets(self):
        expected = {
            "today": ("2026-11-26", "2026-11-27"),
            "this_week": ("2026-11-23", "2026-11-27"),
            "last_week": ("2026-11-16", "2026-11-23"),
            "this_month": ("2026-11-01", "2026-11-27"),
        }
        for preset, dates in expected.items():
            start, end, _ = page._period(preset, None, None)
            self.assertEqual((start.date().isoformat(), end.date().isoformat()), dates)
        with self.assertRaises(frappe.ValidationError):
            page._period("custom", "2026-01-01", "2026-11-26")

    def test_summary_groups_and_detail_reconcile_in_integer_microseconds(self):
        data = page.get_overview()
        self.assertEqual(data["booked_us"], 33 * 60_000_000 + 1)
        self.assertEqual(sum(row["booked_us"] for row in data["contexts"]), data["booked_us"])
        self.assertEqual(sum(row["booked_us"] for row in data["groups"]), data["booked_us"])
        self.assertEqual(sum(row["booked_us"] for row in data["detail"]), data["booked_us"])
        self.assertEqual((data["technician_count"], data["customer_count"]), (2, 1))
        self.assertEqual([row["label"] for row in data["groups"]], ["Alex", "Zee"])

    def test_selected_customer_and_reference_handover(self):
        groups = page.get_overview(dimension="customer")["groups"]
        customer = next(row for row in groups if row["label"] == "Boschendal")
        data = page.get_overview(dimension="customer", group=customer["key"])
        self.assertEqual({row["booking"] for row in data["detail"]}, {"a", "b"})
        self.assertEqual(data["report_filters"], {
            "from_date": "2026-11-23", "to_date": "2026-11-26", "view": "Booking Detail",
            "customer": "Boschendal", "customer_type": "Listed Customer",
        })
        groups = page.get_overview(dimension="reference")["groups"]
        snapfix = next(row for row in groups if row["label"] == "SF-42")
        data = page.get_overview(dimension="reference", group=snapfix["key"])
        self.assertEqual(data["report_filters"]["snapfix_reference"], "SF-42")
        self.assertEqual(data["report_filters"]["reference_kind"], "Snapfix")

    def test_restricted_projection_and_unrecognized_groups(self):
        data = page.get_overview()
        restricted = next(row for row in data["detail"] if row["booking"] == "a")
        self.assertIsNone(restricted["ticket"])
        self.assertIsNone(restricted["description"])
        self.assertNotIn("employee", restricted)
        with self.assertRaises(frappe.PermissionError):
            page.get_overview(group="0" * 64)

    def test_pagination_and_project_default_filter(self):
        self.rows *= 5
        first = page.get_overview()
        self.assertEqual(len(first["detail"]), 12)
        self.assertEqual(first["next_offset"], 12)
        second = page.get_overview(offset=12)
        self.assertEqual(len(second["detail"]), 3)
        self.assertEqual(second["previous_offset"], 0)
        self.assertIsNone(second["next_offset"])
        projects = page.get_overview(dimension="project")
        self.assertEqual(projects["report_filters"]["work_context"], "Project")
        self.assertTrue(all(row["work_context"] == "Project" for row in projects["detail"]))

    def test_rechecks_scope_before_each_request(self):
        page.get_overview()
        page._authorized_scope.side_effect = frappe.PermissionError
        with self.assertRaises(frappe.PermissionError):
            page.get_overview(offset=12)
        self.assertEqual(self.authorized.call_count, 1)


class TestOverviewFeatureGate(unittest.TestCase):
    def test_disabled_feature_fails_before_report_or_grant_access(self):
        fake = Mock(conf={})
        fake.PermissionError = frappe.PermissionError
        fake.throw.side_effect = frappe.PermissionError
        with (
            patch.object(page, "frappe", fake),
            patch.object(page, "_", lambda text: text),
            patch.object(page, "get_report_doc") as report,
            patch.object(page, "resolve_supervisor_reporting_scope") as scope,
            self.assertRaises(frappe.PermissionError),
        ):
            page._authorized_scope()
        report.assert_not_called()
        scope.assert_not_called()
