"""Permanent regressions for Data Request escalation capture."""

import runpy
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
START = datetime(2026, 11, 3, 22, 41, 15)
TICKET = "956"
USERS = [
    "coordinator.test@local.test",
    "ops.test@local.test",
]

policy = runpy.run_path(
    str(ROOT / "data_request_escalation_policy.py")
)
planner = runpy.run_path(
    str(ROOT / "data_request_escalation_intent.py")
)

fake_frappe = ModuleType("frappe")
sql = Mock()
get_doc = Mock()
resolve = Mock()
insert = Mock()

fake_frappe.db = SimpleNamespace(sql=sql)
fake_frappe.get_doc = get_doc
fake_frappe.utils = SimpleNamespace(
    get_datetime=lambda value: (
        datetime.fromisoformat(value)
        if isinstance(value, str)
        else value
    ),
    now_datetime=lambda: START + timedelta(minutes=11),
)

package = ModuleType("telephony")
package.__path__ = []

arrival = ModuleType("telephony.data_request_arrival_outbox")
arrival._insert_if_missing = insert

intents = ModuleType("telephony.data_request_escalation_intent")
intents.plan_escalation_intents = planner[
    "plan_escalation_intents"
]

escalation_policy = ModuleType(
    "telephony.data_request_escalation_policy"
)
escalation_policy.evaluate_escalation = policy[
    "evaluate_escalation"
]

recipients = ModuleType(
    "telephony.data_request_escalation_recipients"
)
recipients.resolve_coordinator_recipients = resolve

modules = {
    "frappe": fake_frappe,
    "telephony": package,
    arrival.__name__: arrival,
    intents.__name__: intents,
    escalation_policy.__name__: escalation_policy,
    recipients.__name__: recipients,
}

with patch.dict(sys.modules, modules):
    capture = runpy.run_path(
        str(ROOT / "data_request_escalation_outbox.py")
    )["capture_escalation_intents"]


class Ticket:
    def __init__(self):
        self.fields = {
            "custom_service_area": "Data Request",
            "creation": START,
            "custom_data_request_first_completed_on": None,
        }

    def get(self, field):
        return self.fields.get(field)


class EscalationOutboxTests(unittest.TestCase):

    def setUp(self):
        self.ticket = Ticket()

        sql.reset_mock(return_value=True, side_effect=True)
        get_doc.reset_mock(return_value=True, side_effect=True)
        resolve.reset_mock(return_value=True, side_effect=True)
        insert.reset_mock(return_value=True, side_effect=True)

        sql.return_value = [{"name": TICKET}]
        get_doc.return_value = self.ticket
        resolve.return_value = list(USERS)
        insert.return_value = True

    def run_at(self, minutes):
        return capture(
            TICKET,
            now=START + timedelta(minutes=minutes),
        )

    def test_not_due_before_ten_minutes(self):
        self.assertEqual(self.run_at(9), [])
        resolve.assert_not_called()
        insert.assert_not_called()

    def test_due_at_exact_boundary(self):
        created = self.run_at(10)

        self.assertEqual(len(created), 2)
        self.assertEqual(len(set(created)), 2)

        items = [
            call.args[0]
            for call in insert.call_args_list
        ]

        self.assertEqual(
            {item["event"] for item in items},
            {"escalation"},
        )

        self.assertEqual(
            {item["recipient"] for item in items},
            set(USERS),
        )

        self.assertEqual(
            set(created),
            {item["name"] for item in items},
        )

    def test_due_after_ten_minutes(self):
        self.assertEqual(len(self.run_at(11)), 2)

    def test_row_lock_parameters(self):
        self.run_at(10)

        sql.assert_called_once()

        query, parameters = sql.call_args.args

        self.assertIn("FOR UPDATE", query.upper())
        self.assertEqual(parameters, (TICKET,))
        self.assertEqual(
            sql.call_args.kwargs,
            {"as_dict": True},
        )

    def test_completed_on_time_not_notified(self):
        self.ticket.fields[
            "custom_data_request_first_completed_on"
        ] = START + timedelta(minutes=9)

        self.assertEqual(self.run_at(15), [])
        insert.assert_not_called()

    def test_completed_late_not_notified_after_completion(self):
        self.ticket.fields[
            "custom_data_request_first_completed_on"
        ] = START + timedelta(minutes=11)

        self.assertEqual(self.run_at(15), [])
        insert.assert_not_called()

    def test_unrelated_service_area_not_notified(self):
        self.ticket.fields[
            "custom_service_area"
        ] = "PABX"

        self.assertEqual(self.run_at(15), [])
        resolve.assert_not_called()

    def test_no_coordinator_available(self):
        resolve.return_value = []

        self.assertEqual(self.run_at(15), [])
        insert.assert_not_called()

    def test_repeated_capture_reuses_intent_identity(self):
        persisted = set()

        def save_once(item):
            name = item["name"]

            if name in persisted:
                return False

            persisted.add(name)
            return True

        insert.side_effect = save_once

        first = self.run_at(10)
        second = self.run_at(11)

        self.assertEqual(len(first), 2)
        self.assertEqual(second, [])
        self.assertEqual(set(first), persisted)

    def test_missing_ticket_name_rejected(self):
        with self.assertRaises(ValueError):
            capture("")

        sql.assert_not_called()

    def test_missing_ticket_row_rejected(self):
        sql.return_value = []

        with self.assertRaises(ValueError):
            self.run_at(15)

        get_doc.assert_not_called()

    def test_missing_creation_rejected(self):
        self.ticket.fields["creation"] = None

        with self.assertRaises(ValueError):
            self.run_at(15)

        insert.assert_not_called()

    def test_persistence_failure_propagates(self):
        insert.side_effect = RuntimeError(
            "Simulated persistence failure"
        )

        with self.assertRaises(RuntimeError):
            self.run_at(15)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        EscalationOutboxTests
    )

    result = unittest.TextTestRunner(verbosity=2).run(suite)

    assert result.wasSuccessful()
    assert result.testsRun == 13

    print("ESC_33_REGRESSION_COUNT=13")
    print("ESC_33_OUTBOX_ORCHESTRATION=PASS")
