from datetime import datetime
from io import BytesIO
from unittest import TestCase
from unittest.mock import Mock, patch
from zipfile import ZipFile

import frappe
from openpyxl import load_workbook

from telephony.booked_hours import date_window
from telephony.customer_labour_workbook import make_workbook, RATES, BREAKDOWN, SUMMARY
from telephony.ftelephony.page.customer_labour_cost_analysis import customer_labour_cost_analysis as page


def fixture_bookings():
    def row(employee, company, begin, end, customer=None, unlisted=None, context="Helpdesk"):
        return {
            "employee": employee, "company": company, "docstatus": 0, "emergency": 0,
            "from_time": datetime.fromisoformat(begin), "to_time": datetime.fromisoformat(end),
            "customer": customer, "unlisted_customer": unlisted, "work_context": context,
            "description": "PRIVATE DESCRIPTION", "ticket": "PRIVATE REFERENCE",
        }
    return [
        row("EMP-01", "Company A", "2026-11-19 23:45:00", "2026-11-20 01:00:00", "Boschendal"),
        row("EMP-02", "Company B", "2026-11-20 09:00:00", "2026-11-20 09:30:00", "Boschendal"),
        row("EMP-01", "Company A", "2026-11-20 10:00:00", "2026-11-20 10:15:00",
            unlisted="Boschendal", context="Customer Support"),
        row("EMP-02", "Company B", "2026-11-20 11:00:00", "2026-11-20 11:45:00", "=Literal customer",
            context="Customer Support"),
        row("EMP-01", "Company A", "2026-11-20 12:00:00", "2026-11-20 12:15:00", context="Internal"),
        row("EMP-02", "Company B", "2026-11-20 12:00:00", "2026-11-20 12:10:00", context="Project"),
    ]


def sample_workbook(bookings=None):
    start, end = date_window("2026-11-20", "2026-11-26")
    return make_workbook(fixture_bookings() if bookings is None else bookings, start, end,
                         {"EMP-01": "+Same name", "EMP-02": "+Same name"}, {"Company A", "Company B"})


class TestCustomerLabourWorkbook(TestCase):
    def setUp(self):
        self.binary = sample_workbook()
        self.book = load_workbook(BytesIO(self.binary))
        self.addCleanup(self.book.close)

    def test_layout_and_blank_inputs(self):
        self.assertEqual(self.book.sheetnames, [RATES, BREAKDOWN, SUMMARY])
        self.assertEqual(self.book.active.title, SUMMARY)
        self.assertTrue(all(sheet.freeze_panes == "A9" for sheet in self.book))
        rates, summary = self.book[RATES], self.book[SUMMARY]
        self.assertTrue(all(rates[f"E{i}"].value is None for i in (9, 10)))
        self.assertTrue(all(summary[f"F{i}"].value is None for i in (9, 10, 11)))
        self.assertTrue(all(rates[f"D{i}"].data_type == "n" for i in (9, 10)))
        self.assertTrue(all(summary[f"G{i}"].data_type == "f" for i in (9, 10, 11)))
        self.assertIn("AccountComparison", summary.tables)
        self.assertEqual(summary["A1"].value, SUMMARY)

    def test_exact_clipping_and_scoped_identities(self):
        rates, summary = self.book[RATES], self.book[SUMMARY]
        self.assertEqual({(rates[f"B{i}"].value, rates[f"C{i}"].value, rates[f"F{i}"].value)
                          for i in (9, 10)}, {("EMP-01", "Company A", 1), ("EMP-02", "Company B", 2)})
        self.assertEqual(summary["A10"].value, "Boschendal")
        self.assertEqual(summary["D10"].value, 1.5)
        self.assertEqual(summary["A11"].value, "Boschendal")
        self.assertEqual(summary["D11"].value, 0.25)
        self.assertEqual(summary["D12"].value, 2.5)
        self.assertAlmostEqual(summary["B19"].value, 10 / 60)
        self.assertAlmostEqual(summary["B20"].value, 175 / 60)
        self.assertIn("Customer hours and labour cost by Company", [cell.value for cell in summary["A"]])

    def test_literal_text_no_private_metadata_or_external_links(self):
        self.assertEqual(self.book[SUMMARY]["A9"].value, "=Literal customer")
        self.assertEqual(self.book[SUMMARY]["A9"].data_type, "s")
        self.assertEqual(self.book[RATES]["A9"].value, "+Same name")
        self.assertEqual(self.book[RATES]["A9"].data_type, "s")
        self.assertFalse(any("PRIVATE" in str(cell.value) for sheet in self.book
                             for row in sheet.iter_rows() for cell in row))
        with ZipFile(BytesIO(self.binary)) as archive:
            self.assertFalse(any("externalLink" in name or "vbaProject" in name for name in archive.namelist()))

    def test_empty_scope_has_clear_message_and_no_inputs(self):
        book = load_workbook(BytesIO(sample_workbook([])))
        self.addCleanup(book.close)
        self.assertIn("No Customer-attributed", book[SUMMARY]["A9"].value)
        self.assertEqual(book[SUMMARY]["F9"].value, None)


class TestCostExportGate(TestCase):
    def test_scope_is_resolved_before_validation_or_export(self):
        with patch.object(page, "_authorized_scope", side_effect=frappe.PermissionError), \
                patch.object(page, "_period") as period, self.assertRaises(frappe.PermissionError):
            page._selection("this_month", None, None)
        period.assert_not_called()

    def test_financial_payload_is_outside_the_request_contract(self):
        def deny(message):
            raise frappe.ValidationError(message)

        fake = Mock(form_dict={"cmd": "download_workbook", "revenue": "1000"})
        fake.throw.side_effect = deny
        with patch.object(page, "_authorized_scope", return_value=frozenset()), \
                patch.object(page, "frappe", fake), patch.object(page, "_", lambda message: message), \
                patch.object(page, "_period") as period, self.assertRaises(frappe.ValidationError):
            page._selection("this_month", None, None)
        period.assert_not_called()
