"""Regression tests for the Data Request 10-minute escalation policy."""

import runpy
import unittest
from datetime import datetime, timedelta
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / (
    "data_request_escalation_policy.py"
)

evaluate = runpy.run_path(str(POLICY))["evaluate_escalation"]
START = datetime(2026, 11, 4, 10, 0)


def check(minutes, completed=None, area="Data Request", start=START):
    return evaluate(
        service_area=area,
        arrival_at=start,
        first_completed_at=(
            start + timedelta(minutes=completed)
            if completed is not None else None
        ),
        now=start + timedelta(minutes=minutes),
    )


class DataRequestEscalationPolicyTests(unittest.TestCase):

    def test_waiting(self):
        result = check(9)
        self.assertEqual(result["state"], "waiting")
        self.assertFalse(result["notification_due"])

    def test_exact_threshold(self):
        result = check(10)
        self.assertEqual(result["state"], "escalation_due")
        self.assertTrue(result["notification_due"])

    def test_after_threshold(self):
        self.assertTrue(check(11)["notification_due"])

    def test_completed_before_threshold(self):
        result = check(20, completed=9)
        self.assertEqual(result["state"], "completed_on_time")
        self.assertFalse(result["notification_due"])

    def test_completed_at_threshold(self):
        self.assertEqual(
            check(20, completed=10)["state"],
            "completed_on_time",
        )

    def test_completed_late(self):
        result = check(20, completed=11)
        self.assertEqual(result["state"], "completed_late")
        self.assertFalse(result["notification_due"])

    def test_unrelated_service_area(self):
        result = check(30, area="PABX")
        self.assertEqual(result["state"], "not_applicable")
        self.assertFalse(result["notification_due"])

    def test_missing_arrival_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(
                service_area="Data Request",
                arrival_at=None,
                first_completed_at=None,
                now=START,
            )

    def test_invalid_completion_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(
                service_area="Data Request",
                arrival_at=START,
                first_completed_at="invalid",
                now=START,
            )

    def test_cross_midnight(self):
        start = datetime(2026, 11, 4, 23, 55)
        result = check(10, start=start)
        self.assertEqual(
            result["due_at"],
            datetime(2026, 11, 5, 0, 5),
        )
        self.assertTrue(result["notification_due"])


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(
            DataRequestEscalationPolicyTests
        )
    )

    assert result.wasSuccessful()
    assert result.testsRun == 10

    print("ESC_18_REGRESSION_COUNT=10")
    print("ESC_18_PERSISTENT_REGRESSIONS=PASS")
