"""Behavioural regressions for Data Request notification selection.

The production SELECT runs against an isolated in-memory SQLite
fixture. No Frappe database or email transport is modified.
"""

import sqlite3
import unittest

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from telephony import data_request_notification_selection as selection


class TestNotificationSelection(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 11, 5, 12, 0)
        self.activation = datetime(2026, 11, 5, 9, 0)

        self.conf = {
            selection.ACTIVATION_KEY: self.activation
        }

        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

        self.conn.execute(
            """
            CREATE TABLE
              `tabTELECTRO Data Request Notification Intent`
            (
                name TEXT,
                creation TEXT,
                delivery_state TEXT,
                next_attempt_on TEXT,
                last_attempt_on TEXT
            )
            """
        )

        self.addCleanup(self.conn.close)

        self.queries = []
        self.db = Mock()
        self.db.sql.side_effect = self.execute_select

        patches = [
            patch.object(selection.frappe, "conf", self.conf),
            patch.object(selection.frappe, "db", self.db),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def timestamp(self, value):
        if value is None:
            return None

        return value.strftime("%Y-%m-%d %H:%M:%S")

    def add_intent(
        self,
        name,
        *,
        state="Pending",
        creation=None,
        next_attempt=None,
        last_attempt=None,
    ):
        if creation is None:
            creation = self.now - timedelta(minutes=10)

        self.conn.execute(
            """
            INSERT INTO
              `tabTELECTRO Data Request Notification Intent`
            (
                name,
                creation,
                delivery_state,
                next_attempt_on,
                last_attempt_on
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                self.timestamp(creation),
                state,
                self.timestamp(next_attempt),
                self.timestamp(last_attempt),
            ),
        )

    def execute_select(self, query, params, *, as_dict=False):
        self.assertTrue(as_dict)

        # Prevent accidental writes through this test adapter.
        self.assertTrue(
            query.lstrip().upper().startswith("SELECT")
        )

        self.queries.append((query, params))

        translated = query.replace("%s", "?")

        rows = self.conn.execute(
            translated,
            params,
        ).fetchall()

        return [dict(row) for row in rows]

    def select(self, **kwargs):
        kwargs.setdefault("now", self.now)

        return selection.select_due_notification_intents(
            **kwargs
        )

    def assert_names(self, expected, **kwargs):
        result = self.select(**kwargs)

        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["intents"], expected)
        self.assertEqual(result["selected"], len(expected))

    def test_disabled_fails_closed_without_query(self):
        self.conf.clear()

        result = self.select()

        self.assertEqual(
            result,
            {
                "state": "disabled",
                "intents": [],
                "selected": 0,
            },
        )

        self.db.sql.assert_not_called()

    def test_before_activation_returns_not_due(self):
        self.conf[selection.ACTIVATION_KEY] = (
            self.now + timedelta(minutes=1)
        )

        result = self.select()

        self.assertEqual(result["state"], "not_due")
        self.assertEqual(result["selected"], 0)

        self.db.sql.assert_not_called()

    def test_invalid_batch_limits_rejected(self):
        invalid = (
            0,
            -1,
            101,
            True,
            False,
            1.5,
            "10",
            None,
        )

        for limit in invalid:
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    self.select(limit=limit)

        self.db.sql.assert_not_called()

    def test_timezone_aware_activation_rejected(self):
        self.conf[selection.ACTIVATION_KEY] = (
            self.activation.replace(
                tzinfo=timezone(timedelta(hours=2))
            )
        )

        with self.assertRaises(ValueError):
            self.select()

        self.db.sql.assert_not_called()

    def test_timezone_aware_now_rejected(self):
        aware = self.now.replace(
            tzinfo=timezone.utc
        )

        with self.assertRaises(ValueError):
            self.select(now=aware)

        self.db.sql.assert_not_called()

    def test_pending_intent_selected(self):
        self.add_intent("PENDING")

        self.assert_names(["PENDING"])

    def test_historical_intents_excluded(self):
        self.add_intent(
            "OLD",
            creation=self.activation - timedelta(seconds=1),
        )

        self.add_intent(
            "BOUNDARY",
            creation=self.activation,
        )

        self.assert_names(["BOUNDARY"])

    def test_pending_retry_deadline(self):
        self.add_intent(
            "DUE",
            next_attempt=self.now,
        )

        self.add_intent(
            "FUTURE",
            next_attempt=self.now + timedelta(seconds=1),
        )

        self.assert_names(["DUE"])

    def test_retry_requires_due_deadline(self):
        self.add_intent(
            "NO-DEADLINE",
            state="Retry",
        )

        self.add_intent(
            "DUE",
            state="Retry",
            next_attempt=self.now,
        )

        self.add_intent(
            "FUTURE",
            state="Retry",
            next_attempt=self.now + timedelta(seconds=1),
        )

        self.assert_names(["DUE"])

    def test_processing_with_deadline(self):
        self.add_intent(
            "DUE",
            state="Processing",
            next_attempt=self.now,
        )

        self.add_intent(
            "FUTURE",
            state="Processing",
            next_attempt=self.now + timedelta(seconds=1),
        )

        self.assert_names(["DUE"])

    def test_processing_recovers_stale_last_attempt(self):
        cutoff = self.now - timedelta(minutes=5)

        self.add_intent(
            "STALE",
            state="Processing",
            last_attempt=cutoff,
        )

        self.add_intent(
            "RECENT",
            state="Processing",
            last_attempt=cutoff + timedelta(seconds=1),
        )

        self.assert_names(["STALE"])

    def test_processing_falls_back_to_creation(self):
        self.add_intent(
            "STALE",
            state="Processing",
            creation=self.now - timedelta(minutes=6),
        )

        self.add_intent(
            "RECENT",
            state="Processing",
            creation=self.now - timedelta(minutes=4),
        )

        self.assert_names(["STALE"])

    def test_terminal_and_future_intents_excluded(self):
        self.add_intent("COMPLETE", state="Complete")
        self.add_intent("FAILED", state="Failed")

        self.add_intent(
            "FUTURE-CREATION",
            creation=self.now + timedelta(seconds=1),
        )

        self.assert_names([])

    def test_bounded_deterministic_ordering(self):
        created = self.now - timedelta(minutes=10)

        self.add_intent(
            "B",
            creation=created,
        )

        self.add_intent(
            "A",
            creation=created,
        )

        self.add_intent(
            "C",
            state="Retry",
            creation=self.activation + timedelta(minutes=15),
            next_attempt=self.activation + timedelta(minutes=30),
        )

        self.assert_names(["C", "A"], limit=2)

        self.assertEqual(len(self.queries), 1)
        self.assertEqual(self.queries[0][1][-1], 2)

    def test_duplicate_names_detected(self):
        self.add_intent("DUPLICATE")
        self.add_intent("DUPLICATE")

        with self.assertRaises(ValueError):
            self.select()

    def test_default_now_uses_site_clock(self):
        self.add_intent("CLOCK")

        with patch.object(
            selection.frappe.utils,
            "now_datetime",
            return_value=self.now,
        ) as clock:
            result = (
                selection.select_due_notification_intents()
            )

        clock.assert_called_once_with()

        self.assertEqual(result["intents"], ["CLOCK"])


if __name__ == "__main__":
    unittest.main()
