"""Registration contract for the Data Request arrival-intent hook."""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

HOOKS = ROOT / "hooks.py"
OUTBOX = ROOT / "data_request_arrival_outbox.py"

FIRST = (
    '_append_hook(doc_events["HD Ticket"], "after_insert", '
    '"telephony.telectro_round_robin.assign_after_insert")'
)

SECOND = (
    '_append_hook(doc_events["HD Ticket"], "after_insert", '
    '"telephony.docshare_guard.hd_ticket_after_insert")'
)

ARRIVAL = (
    '_append_hook(doc_events["HD Ticket"], "after_insert", '
    '"telephony.data_request_arrival_outbox.capture_arrival_intents")'
)


class TestArrivalHookRegistration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = HOOKS.read_text(encoding="utf-8")

    def test_registration_occurs_exactly_once(self):
        self.assertEqual(self.source.count(ARRIVAL), 1)

    def test_existing_handler_order_is_preserved(self):
        self.assertEqual(self.source.count(FIRST), 1)
        self.assertEqual(self.source.count(SECOND), 1)

        self.assertLess(
            self.source.index(FIRST),
            self.source.index(SECOND),
        )

        self.assertLess(
            self.source.index(SECOND),
            self.source.index(ARRIVAL),
        )

    def test_arrival_is_an_after_insert_handler(self):
        self.assertIn(
            '"after_insert", '
            '"telephony.data_request_arrival_outbox.'
            'capture_arrival_intents"',
            self.source,
        )

        self.assertNotIn(
            '"validate", '
            '"telephony.data_request_arrival_outbox.'
            'capture_arrival_intents"',
            self.source,
        )

        self.assertNotIn(
            '"on_update", '
            '"telephony.data_request_arrival_outbox.'
            'capture_arrival_intents"',
            self.source,
        )

    def test_handler_is_defined_in_source(self):
        tree = ast.parse(
            OUTBOX.read_text(encoding="utf-8")
        )

        functions = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }

        self.assertIn(
            "capture_arrival_intents",
            functions,
        )

    def test_hooks_remain_valid_python(self):
        ast.parse(self.source)


if __name__ == "__main__":
    unittest.main()
