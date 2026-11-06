"""Permanent regressions for Data Request notification worker policy."""

import unittest

from datetime import datetime, timedelta, timezone

from telephony import data_request_notification_worker_policy as policy


class TestWorkerPolicy(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 11, 5, 12, 0, 0)

    def failure(self, count=0, code="DISPATCH_ERROR"):
        return policy.plan_worker_failure(
            now=self.now,
            attempt_count=count,
            failure_code=code,
        )

    def result(self, state, count=0):
        return policy.plan_worker_result(
            now=self.now,
            attempt_count=count,
            delivery_state=state,
        )

    def assert_retry(self, count, minutes):
        result = self.failure(count)

        self.assertEqual(result["delivery_state"], "Retry")
        self.assertEqual(result["attempt_count"], count + 1)
        self.assertEqual(result["last_attempt_on"], self.now)
        self.assertEqual(
            result["next_attempt_on"],
            self.now + timedelta(minutes=minutes),
        )

    def test_first_failure_one_minute(self):
        self.assert_retry(0, 1)

    def test_second_failure_two_minutes(self):
        self.assert_retry(1, 2)

    def test_third_failure_four_minutes(self):
        self.assert_retry(2, 4)

    def test_fourth_failure_eight_minutes(self):
        self.assert_retry(3, 8)

    def test_fifth_failure_terminal(self):
        result = self.failure(4)

        self.assertEqual(result["delivery_state"], "Failed")
        self.assertEqual(result["attempt_count"], 5)
        self.assertIsNone(result["next_attempt_on"])

    def test_excess_failures_remain_terminal(self):
        result = self.failure(8)

        self.assertEqual(result["delivery_state"], "Failed")
        self.assertEqual(result["attempt_count"], 9)
        self.assertIsNone(result["next_attempt_on"])

    def test_native_email_failure_is_retryable(self):
        result = self.failure(
            0,
            "NATIVE_EMAIL_FAILURE",
        )

        self.assertEqual(result["delivery_state"], "Retry")
        self.assertEqual(
            result["last_error"],
            "NATIVE_EMAIL_FAILURE",
        )

    def test_authorization_revocation_terminal(self):
        result = self.failure(
            0,
            "AUTHORIZATION_REVOKED",
        )

        self.assertEqual(result["delivery_state"], "Failed")
        self.assertEqual(result["attempt_count"], 1)
        self.assertIsNone(result["next_attempt_on"])

    def test_invalid_intent_terminal(self):
        result = self.failure(
            0,
            "INVALID_INTENT",
        )

        self.assertEqual(result["delivery_state"], "Failed")
        self.assertIsNone(result["next_attempt_on"])

    def test_retry_result_counts_native_failure(self):
        result = self.result("Retry", count=2)

        self.assertEqual(result["delivery_state"], "Retry")
        self.assertEqual(result["attempt_count"], 3)
        self.assertEqual(
            result["next_attempt_on"],
            self.now + timedelta(minutes=4),
        )
        self.assertEqual(
            result["last_error"],
            "NATIVE_EMAIL_FAILURE",
        )

    def test_processing_poll_does_not_consume_retry(self):
        result = self.result("Processing", count=3)

        self.assertEqual(result["delivery_state"], "Processing")
        self.assertEqual(result["attempt_count"], 3)
        self.assertEqual(
            result["next_attempt_on"],
            self.now + timedelta(minutes=5),
        )
        self.assertIsNone(result["last_error"])

    def test_complete_is_terminal(self):
        result = self.result("Complete", count=2)

        self.assertEqual(result["delivery_state"], "Complete")
        self.assertEqual(result["attempt_count"], 2)
        self.assertIsNone(result["next_attempt_on"])
        self.assertIsNone(result["last_error"])

    def test_processing_preserves_prior_failure_count(self):
        for count in (0, 1, 4, 5):
            with self.subTest(count=count):
                result = self.result("Processing", count)
                self.assertEqual(
                    result["attempt_count"],
                    count,
                )

    def test_failure_preserves_timestamp_and_code(self):
        result = self.failure(
            1,
            "DISPATCH_ERROR",
        )

        self.assertEqual(result["last_attempt_on"], self.now)
        self.assertEqual(result["last_error"], "DISPATCH_ERROR")

    def test_unknown_failure_codes_rejected(self):
        for code in ("", "UNKNOWN", None, "SMTP_DELIVERED"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    self.failure(code=code)

    def test_unknown_dispatcher_results_rejected(self):
        for state in (
            "",
            "Pending",
            "Failed",
            "Unknown",
            None,
        ):
            with self.subTest(state=state):
                with self.assertRaises(ValueError):
                    self.result(state)

    def test_invalid_timestamps_rejected(self):
        invalid = (
            None,
            "2026-11-05 12:00:00",
            self.now.replace(tzinfo=timezone.utc),
            self.now.replace(
                tzinfo=timezone(timedelta(hours=2))
            ),
        )

        for now in invalid:
            with self.subTest(now=now):
                with self.assertRaises(ValueError):
                    policy.plan_worker_failure(
                        now=now,
                        attempt_count=0,
                        failure_code="DISPATCH_ERROR",
                    )

                with self.assertRaises(ValueError):
                    policy.plan_worker_result(
                        now=now,
                        attempt_count=0,
                        delivery_state="Processing",
                    )

    def test_invalid_attempt_counts_rejected(self):
        for count in (-1, True, False, 1.5, "2", None):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    self.failure(count)

                with self.assertRaises(ValueError):
                    self.result("Processing", count)

    def test_policy_constants_are_consistent(self):
        self.assertEqual(policy.MAX_FAILED_ATTEMPTS, 5)
        self.assertEqual(
            policy.RETRY_DELAYS_MINUTES,
            (1, 2, 4, 8),
        )
        self.assertEqual(policy.PROCESSING_POLL_MINUTES, 5)

        self.assertFalse(
            policy.RETRYABLE_FAILURE_CODES
            & policy.TERMINAL_FAILURE_CODES
        )


if __name__ == "__main__":
    unittest.main()
