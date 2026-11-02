import unittest
from unittest.mock import Mock

from telephony.tests.test_task_notification_claim_capture import (
    FakeDatabase,
    compile_actual_claim,
)


class TestTaskNotificationClaimSchemaGuard(unittest.TestCase):

    def make_claim(self):
        events = []
        database = FakeDatabase(events)

        normalize = Mock(return_value="COMMENT-SCHEMA-001")
        capture = Mock(
            return_value={
                "ok": True,
                "created": True,
                "event_key": "SCHEMA-TEST-001",
            }
        )

        claim = compile_actual_claim(
            database,
            "tech@example.invalid",
            normalize,
            capture,
        )

        return claim, database, events, normalize, capture

    def assert_no_mutation(
        self,
        database,
        events,
        normalize,
        capture,
    ):
        self.assertEqual(database.current_assign, "")
        self.assertEqual(database.rowcount, 0)
        self.assertEqual(database.commits, 0)
        self.assertEqual(events, [])

        normalize.assert_not_called()
        capture.assert_not_called()

    def test_missing_schema_rejects_before_mutation(self):
        claim, db, events, normalize, capture = self.make_claim()

        db.notification_schema_available = False

        result = claim("100")

        self.assertEqual(
            result,
            {
                "ok": 0,
                "ticket": "100",
                "reason": "notification_schema_unavailable",
            },
        )

        self.assertEqual(db.schema_checks, 1)
        self.assert_no_mutation(db, events, normalize, capture)

    def test_schema_check_exception_propagates_without_mutation(self):
        claim, db, events, normalize, capture = self.make_claim()

        db.schema_check_error = RuntimeError(
            "Simulated schema inspection failure"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Simulated schema inspection failure",
        ):
            claim("100")

        self.assertEqual(db.schema_checks, 1)
        self.assert_no_mutation(db, events, normalize, capture)

    def test_claim_can_proceed_after_schema_becomes_available(self):
        claim, db, events, normalize, capture = self.make_claim()

        db.notification_schema_available = False

        rejected = claim("100")

        self.assertEqual(
            rejected["reason"],
            "notification_schema_unavailable",
        )
        self.assert_no_mutation(db, events, normalize, capture)

        # Simulate migration completing while the backend remains alive.
        db.notification_schema_available = True

        accepted = claim("100")

        self.assertEqual(accepted["ok"], 1)
        self.assertEqual(accepted["assigned_to"], "tech@example.invalid")

        self.assertEqual(db.schema_checks, 2)
        self.assertEqual(db.commits, 1)

        self.assertEqual(
            events,
            ["update", "rowcount", "readback", "commit"],
        )

        normalize.assert_called_once()
        capture.assert_called_once()

    def test_unauthorized_actor_does_not_inspect_schema(self):
        claim, db, events, normalize, capture = self.make_claim()

        # Replace only authorization in the isolated test namespace.
        # The actual Claim function body remains unchanged.
        claim.__globals__["_require_claim_authorization"] = (
            lambda ticket, user: None
        )

        db.notification_schema_available = False

        result = claim("100")

        self.assertEqual(
            result,
            {"ok": 0, "reason": "not_authorized"},
        )

        self.assertEqual(getattr(db, "schema_checks", 0), 0)
        self.assert_no_mutation(db, events, normalize, capture)

    def test_missing_ticket_does_not_inspect_schema(self):
        claim, db, events, normalize, capture = self.make_claim()

        db.notification_schema_available = False

        result = claim("  ")

        self.assertEqual(
            result,
            {"ok": 0, "reason": "missing_ticket"},
        )

        self.assertEqual(getattr(db, "schema_checks", 0), 0)
        self.assert_no_mutation(db, events, normalize, capture)


if __name__ == "__main__":
    unittest.main()
