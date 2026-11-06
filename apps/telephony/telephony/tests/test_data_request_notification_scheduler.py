"""Permanent regressions for scheduled Data Request delivery.

No live notification delivery, SMTP, or DB writes.
"""

import ast
import unittest

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from telephony import data_request_notification_batch as batch
from telephony import data_request_notification_selection as selection
from telephony.jobs import data_request_notification_delivery as job


INBOX = "telephony.jobs.pull_pilot_inboxes.run"
ESCALATION = "telephony.jobs.data_request_escalation.run"
DELIVERY = "telephony.jobs.data_request_notification_delivery.run"


class TestNotificationScheduler(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 11, 5, 15, 0, 0)

    def simulate_hooks(self, existing=()):
        """Execute only the isolated cron registration statements."""

        hooks = (
            Path(__file__).resolve().parents[1]
            / "hooks.py"
        )

        tree = ast.parse(
            hooks.read_text(),
            filename=str(hooks),
        )

        starts = [
            index
            for index, node in enumerate(tree.body)
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id == "scheduler_events"
                    for target in node.targets
                )
            )
        ]

        ends = [
            index
            for index, node in enumerate(tree.body)
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "scheduler_events"
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value == "cron"
                    for target in node.targets
                )
            )
        ]

        self.assertEqual(len(starts), 1)
        self.assertEqual(len(ends), 1)

        start = starts[0]
        end = ends[0]

        self.assertLess(start, end)
        self.assertLessEqual(end - start, 20)

        namespace = {
            "scheduler_events": {
                "cron": {
                    "*/1 * * * *": list(existing),
                    "0 2 * * *": ["keep.nightly"],
                },
            },
        }

        isolated = ast.Module(
            body=tree.body[start:end + 1],
            type_ignores=[],
        )

        exec(
            compile(isolated, str(hooks), "exec"),
            namespace,
        )

        return namespace["scheduler_events"]["cron"]

    def test_wrapper_delegates_once(self):
        expected = {"state": "processed"}

        with patch.object(
            job,
            "run_notification_delivery_batch",
            return_value=expected,
        ) as runner:
            result = job.run()

        self.assertIs(result, expected)
        runner.assert_called_once_with(dry_run=False)

    def test_wrapper_passes_dry_run(self):
        with patch.object(
            job,
            "run_notification_delivery_batch",
            return_value={"state": "dry_run"},
        ) as runner:
            result = job.run(dry_run=True)

        self.assertEqual(result["state"], "dry_run")
        runner.assert_called_once_with(dry_run=True)

    def test_wrapper_propagates_failure(self):
        with patch.object(
            job,
            "run_notification_delivery_batch",
            side_effect=RuntimeError("Simulated batch failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Simulated batch failure",
            ):
                job.run()

    def test_invalid_dry_run_type_rejected(self):
        with self.assertRaises(ValueError):
            job.run(dry_run="yes")

    def test_disabled_without_activation(self):
        db = Mock()

        with (
            patch.object(batch.frappe, "conf", {}),
            patch.object(batch.frappe, "db", db),
            patch.object(
                batch.frappe.utils,
                "now_datetime",
                return_value=self.now,
            ),
            patch.object(
                batch,
                "process_due_notification_intent",
            ) as worker,
            patch.object(
                batch,
                "persist_unhandled_batch_error",
            ) as reporter,
            patch.object(
                batch,
                "record_unhandled_notification_failure",
            ) as backoff,
        ):
            result = job.run()

        self.assertEqual(result["state"], "disabled")
        self.assertEqual(result["selected"], 0)
        self.assertEqual(result["attempted"], 0)

        db.sql.assert_not_called()
        db.commit.assert_not_called()
        worker.assert_not_called()
        reporter.assert_not_called()
        backoff.assert_not_called()

    def test_future_activation_not_due(self):
        db = Mock()

        future = self.now + timedelta(minutes=5)

        with (
            patch.object(
                selection.frappe,
                "conf",
                {
                    selection.ACTIVATION_KEY:
                        future.strftime("%Y-%m-%d %H:%M:%S"),
                },
            ),
            patch.object(batch.frappe, "db", db),
            patch.object(
                batch.frappe.utils,
                "now_datetime",
                return_value=self.now,
            ),
            patch.object(
                batch,
                "process_due_notification_intent",
            ) as worker,
        ):
            result = job.run()

        self.assertEqual(result["state"], "not_due")
        self.assertEqual(result["attempted"], 0)

        db.sql.assert_not_called()
        db.commit.assert_not_called()
        worker.assert_not_called()

    def test_activated_selector_empty_read_only(self):
        db = Mock()
        db.sql.return_value = []

        with (
            patch.object(
                selection.frappe,
                "conf",
                {
                    selection.ACTIVATION_KEY:
                        "2026-11-05 14:00:00",
                },
            ),
            patch.object(batch.frappe, "db", db),
            patch.object(
                batch.frappe.utils,
                "now_datetime",
                return_value=self.now,
            ),
            patch.object(
                batch,
                "process_due_notification_intent",
            ) as worker,
        ):
            result = job.run()

        self.assertEqual(result["state"], "processed")
        self.assertEqual(result["selected"], 0)
        self.assertEqual(result["attempted"], 0)

        db.sql.assert_called_once()
        db.commit.assert_not_called()
        db.rollback.assert_not_called()
        worker.assert_not_called()

    def test_dry_run_never_dispatches(self):
        with (
            patch.object(
                batch,
                "select_due_notification_intents",
                return_value={
                    "state": "ready",
                    "intents": ["ESC132-TEST"],
                    "selected": 1,
                },
            ),
            patch.object(
                batch.frappe.utils,
                "now_datetime",
                return_value=self.now,
            ),
            patch.object(
                batch,
                "process_due_notification_intent",
            ) as worker,
            patch.object(
                batch,
                "persist_unhandled_batch_error",
            ) as reporter,
            patch.object(
                batch,
                "record_unhandled_notification_failure",
            ) as backoff,
        ):
            result = job.run(dry_run=True)

        self.assertEqual(result["state"], "dry_run")
        self.assertEqual(result["selected"], 1)
        self.assertEqual(result["attempted"], 0)

        worker.assert_not_called()
        reporter.assert_not_called()
        backoff.assert_not_called()

    def test_wrapper_has_no_direct_side_effects(self):
        path = Path(job.__file__)
        tree = ast.parse(path.read_text())

        functions = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        ]

        self.assertEqual(
            [node.name for node in functions],
            ["run"],
        )

        calls = [
            ast.unparse(node.func)
            for node in ast.walk(functions[0])
            if isinstance(node, ast.Call)
        ]

        self.assertEqual(
            calls,
            ["run_notification_delivery_batch"],
        )

    def test_hooks_register_expected_minute_jobs(self):
        cron = self.simulate_hooks()

        self.assertEqual(
            cron["*/1 * * * *"],
            [INBOX, ESCALATION, DELIVERY],
        )

    def test_hooks_do_not_duplicate_existing_jobs(self):
        existing = [INBOX, ESCALATION, DELIVERY]

        cron = self.simulate_hooks(existing)

        self.assertEqual(
            cron["*/1 * * * *"],
            existing,
        )

        self.assertEqual(
            cron["*/1 * * * *"].count(DELIVERY),
            1,
        )

    def test_hooks_preserve_unrelated_cron_jobs(self):
        cron = self.simulate_hooks(["keep.other"])

        self.assertEqual(
            cron["*/1 * * * *"],
            ["keep.other", INBOX, ESCALATION, DELIVERY],
        )

        self.assertEqual(
            cron["0 2 * * *"],
            ["keep.nightly"],
        )


if __name__ == "__main__":
    unittest.main()
