"""Permanent regressions for the Data Request escalation scheduler."""

import runpy
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "jobs/data_request_escalation.py"

NOW = datetime(2026, 11, 5, 9, 0, 0)
SETTING = "telectro_data_request_escalation_start_at"

fake = ModuleType("frappe")
fake.conf = {}
fake.db = SimpleNamespace(sql=Mock())
fake.utils = SimpleNamespace(
    get_datetime=lambda value: (
        datetime.fromisoformat(value)
        if isinstance(value, str)
        else value
    ),
    now_datetime=Mock(),
)

capture = Mock()

package = ModuleType("telephony")
package.__path__ = []

outbox = ModuleType("telephony.data_request_escalation_outbox")
outbox.capture_escalation_intents = capture

with patch.dict(
    sys.modules,
    {
        "frappe": fake,
        "telephony": package,
        outbox.__name__: outbox,
    },
):
    run = runpy.run_path(str(SOURCE))["run"]


class SchedulerTests(unittest.TestCase):

    def setUp(self):
        self.rows = []

        fake.conf.clear()
        fake.conf[SETTING] = NOW - timedelta(minutes=30)

        fake.db.sql.reset_mock(
            return_value=True,
            side_effect=True,
        )

        fake.utils.now_datetime.reset_mock(
            return_value=True,
            side_effect=True,
        )
        fake.utils.now_datetime.return_value = NOW

        capture.reset_mock(
            return_value=True,
            side_effect=True,
        )
        capture.return_value = ["new-intent"]

        run.__globals__["PAGE_SIZE"] = 100

        def select(query, params, as_dict=False):
            self.assertTrue(as_dict)

            for required in (
                "custom_service_area = %s",
                "creation >= %s",
                "creation <= %s",
                "custom_data_request_first_completed_on IS NULL",
                "ORDER BY creation ASC, name ASC",
                "LIMIT %s OFFSET %s",
            ):
                self.assertIn(required, query)

            area, activation, cutoff, limit, offset = params

            selected = [
                row
                for row in self.rows
                if row["area"] == area
                and activation <= row["creation"] <= cutoff
                and row["completed"] is None
            ]

            selected.sort(
                key=lambda row: (
                    row["creation"],
                    str(row["name"]),
                )
            )

            return [
                {"name": row["name"]}
                for row in selected[offset:offset + limit]
            ]

        fake.db.sql.side_effect = select

    def add_ticket(
        self,
        name,
        age_minutes,
        *,
        area="Data Request",
        completed=None,
    ):
        self.rows.append({
            "name": name,
            "creation": NOW - timedelta(minutes=age_minutes),
            "area": area,
            "completed": completed,
        })

    def test_disabled_configuration_fails_closed(self):
        fake.conf.clear()

        result = run()

        self.assertEqual(
            result,
            {"state": "disabled", "scanned": 0, "inserted": 0},
        )
        fake.db.sql.assert_not_called()
        capture.assert_not_called()

    def test_activation_not_yet_due(self):
        fake.conf[SETTING] = NOW - timedelta(minutes=5)

        result = run()

        self.assertEqual(result["state"], "not_due")
        self.assertEqual(result["scanned"], 0)
        fake.db.sql.assert_not_called()

    def test_historical_ticket_excluded(self):
        self.add_ticket("old", 40)
        self.add_ticket("new", 20)

        result = run()

        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(
            capture.call_args.args[0],
            "new",
        )

    def test_exact_ten_minute_boundary(self):
        self.add_ticket(956, 10)

        result = run()

        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["inserted"], 1)

        capture.assert_called_once_with(
            "956",
            now=NOW,
        )

    def test_before_ten_minutes_excluded(self):
        self.rows.append({
            "name": "early",
            "creation": NOW - timedelta(
                minutes=9,
                seconds=59,
            ),
            "area": "Data Request",
            "completed": None,
        })

        result = run()

        self.assertEqual(result["scanned"], 0)
        capture.assert_not_called()

    def test_first_completion_excluded(self):
        self.add_ticket(
            "completed",
            20,
            completed=NOW - timedelta(minutes=1),
        )

        result = run()

        self.assertEqual(result["scanned"], 0)
        capture.assert_not_called()

    def test_other_service_area_excluded(self):
        self.add_ticket("pabx", 20, area="PABX")

        result = run()

        self.assertEqual(result["scanned"], 0)
        capture.assert_not_called()

    def test_dry_run_never_captures(self):
        self.add_ticket("A", 20)
        self.add_ticket("B", 15)

        result = run(dry_run=True)

        self.assertEqual(
            result,
            {"state": "dry_run", "scanned": 2, "inserted": 0},
        )
        capture.assert_not_called()

    def test_pagination_without_skipping(self):
        run.__globals__["PAGE_SIZE"] = 2

        for index in range(5):
            self.add_ticket(
                f"T{index}",
                15 - index,
            )

        result = run()

        self.assertEqual(result["scanned"], 5)
        self.assertEqual(result["inserted"], 5)

        captured = [
            call.args[0]
            for call in capture.call_args_list
        ]

        self.assertEqual(
            captured,
            ["T0", "T1", "T2", "T3", "T4"],
        )

        offsets = [
            call.args[1][-1]
            for call in fake.db.sql.call_args_list
        ]

        self.assertEqual(offsets, [0, 2, 4])

    def test_repeated_execution_is_idempotent(self):
        self.add_ticket("A", 20)

        capture.side_effect = [
            ["new-intent"],
            [],
        ]

        first = run()
        second = run()

        self.assertEqual(first["inserted"], 1)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(second["scanned"], 1)

    def test_capture_failure_propagates(self):
        self.add_ticket("A", 20)

        capture.side_effect = RuntimeError(
            "Simulated persistence failure"
        )

        with self.assertRaises(RuntimeError):
            run()

    def test_timezone_aware_clock_rejected(self):
        fake.utils.now_datetime.return_value = (
            NOW.replace(tzinfo=timezone.utc)
        )

        with self.assertRaises(ValueError):
            run()

        fake.db.sql.assert_not_called()
        capture.assert_not_called()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        SchedulerTests
    )

    result = unittest.TextTestRunner(
        verbosity=2
    ).run(suite)

    assert result.wasSuccessful()
    assert result.testsRun == 12

    print("ESC_42_REGRESSION_COUNT=12")
    print("ESC_42_SCHEDULER_REGRESSIONS=PASS")
