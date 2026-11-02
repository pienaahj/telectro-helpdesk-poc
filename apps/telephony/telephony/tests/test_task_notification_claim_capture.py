"""Claim notification capture integration contract.

Executes the real Claim function body against simulated
database operations. No Frappe runtime or delivery required.
"""

import __future__
import ast
import copy
import json
import types
import unittest
from pathlib import Path
from unittest import mock


CLAIM_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "telectro_claim.py"
)


class FakeDatabase:

    def __init__(self, events, current_assign=""):
        self.events = events
        self.current_assign = current_assign
        self.status = "Open"
        self.fulfilment_party = "Telectro"
        self.agent_group = "Routing"
        self.open_todo = False
        self.team_members = {"tech@example.invalid"}
        self.rowcount = 0
        self.commits = 0


    def table_exists(self, doctype, cached=True):
        assert doctype == "TELECTRO Task Notification Intent"
        assert cached is False

        self.schema_checks = getattr(self, "schema_checks", 0) + 1

        error = getattr(self, "schema_check_error", None)
        if error is not None:
            raise error

        return getattr(self, "notification_schema_available", True)

    def sql(self, query, values=None, **kwargs):
        if "UPDATE `tabHD Ticket`" in query:
            self.events.append("update")

            assert values is not None and len(values) == 5, values
            assign_json, ticket, group, privileged, claimant = values
            assert ticket == "100"
            assert group == "Routing"
            assert privileged == 0
            assert claimant == "tech@example.invalid"
            assert "`status` = 'Open'" in query
            assert "`custom_fulfilment_party` = 'Telectro'" in query
            assert "`agent_group` = %s" in query
            assert "NOT EXISTS" in query and "`tabToDo`" in query
            assert "`tabHD Team Member`" in query
            assert "claim_member.user = %s" in query

            if (
                self.current_assign in ("", "[]")
                and self.status == "Open"
                and self.fulfilment_party == "Telectro"
                and self.agent_group == group
                and not self.open_todo
                and (privileged == 1 or claimant in self.team_members)
            ):
                self.current_assign = assign_json
                self.rowcount = 1
            else:
                self.rowcount = 0

            return []

        if "ROW_COUNT()" in query.upper():
            self.events.append("rowcount")
            return [[self.rowcount]]

        raise AssertionError(
            "Unexpected SQL: " + query[:120]
        )

    def get_value(self, doctype, name, field):
        assert (doctype, name, field) == (
            "HD Ticket", "100", "_assign"
        )

        self.events.append("readback")
        return self.current_assign

    def commit(self):
        self.events.append("commit")
        self.commits += 1


def compile_actual_claim(db, user, normalize, capture):
    source = CLAIM_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "telectro_claim_ticket"
    ]

    assert len(matches) == 1

    function = copy.deepcopy(matches[0])
    function.decorator_list = []

    module = ast.Module(
        body=[function],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)

    namespace = {
        "json": json,
        "frappe": types.SimpleNamespace(
            db=db,
            session=types.SimpleNamespace(user=user),
        ),
        # These legacy tests cover Claim/capture ordering, not role authorization.
        # Role authorization is exercised in the dedicated real-helper tests.
        "_require_claim_authorization": lambda ticket, user: {
            "agent_group": "Routing", "privileged": False,
        },
        "_normalize_assignment": normalize,
        "capture_verified_task_ownership_transition": capture,
    }

    exec(
        compile(
            module,
            str(CLAIM_SOURCE),
            "exec",
            flags=__future__.annotations.compiler_flag,
        ),
        namespace,
    )

    return namespace["telectro_claim_ticket"]


class TestTaskNotificationClaimCapture(unittest.TestCase):

    USER = "tech@example.invalid"
    OTHER = "other@example.invalid"
    COMMENT = "COMMENT-CLAIM-001"

    def setUp(self):
        self.events = []
        self.capture_result = {
            "ok": True,
            "created": True,
            "event_key": "a" * 64,
            "error": "",
        }
        self.capture_error = None

    def setup_claim(self, current_assign=""):
        self.db = FakeDatabase(
            self.events,
            current_assign=current_assign,
        )

        def normalize(*args, **kwargs):
            self.events.append("normalize")
            return self.COMMENT

        def capture(*args, **kwargs):
            self.events.append("capture")

            if self.capture_error is not None:
                raise self.capture_error

            return self.capture_result

        self.normalize = mock.Mock(side_effect=normalize)
        self.capture = mock.Mock(side_effect=capture)

        return compile_actual_claim(
            db=self.db,
            user=self.USER,
            normalize=self.normalize,
            capture=self.capture,
        )

    def assert_capture_arguments(self):
        self.capture.assert_called_once_with(
            ticket="100",
            action="claim",
            previous_owner="",
            recipient=self.USER,
            event_id=self.COMMENT,
            transition_confirmed=True,
            actor_user=self.USER,
            note="Claim",
        )

    def test_first_claim_captures_durable_comment_before_commit(self):
        claim = self.setup_claim("")

        result = claim("100")

        self.assertEqual(result["ok"], 1)
        self.assert_capture_arguments()

        self.normalize.assert_called_once_with(
            "100",
            self.USER,
            note="Claim",
        )

        self.assertEqual(
            self.events[-3:],
            ["normalize", "capture", "commit"],
        )

        self.assertEqual(self.db.commits, 1)

    def test_json_empty_pool_captures(self):
        claim = self.setup_claim("[]")

        result = claim("100")

        self.assertEqual(result["ok"], 1)
        self.assert_capture_arguments()
        self.assertEqual(self.db.commits, 1)

    def test_safe_capture_failure_does_not_cancel_claim(self):
        self.capture_result = {
            "ok": False,
            "created": False,
            "event_key": None,
            "error": "capture_failed",
        }

        claim = self.setup_claim("")

        result = claim("100")

        self.assertEqual(result["ok"], 1)
        self.assert_capture_arguments()
        self.assertEqual(self.db.commits, 1)

        self.assertEqual(
            self.events[-3:],
            ["normalize", "capture", "commit"],
        )

    def test_unrecoverable_savepoint_rollback_prevents_commit(self):
        self.capture_error = RuntimeError(
            "Cannot restore savepoint"
        )

        claim = self.setup_claim("")

        with self.assertRaisesRegex(
            RuntimeError,
            "Cannot restore savepoint",
        ):
            claim("100")

        self.assert_capture_arguments()
        self.assertEqual(self.db.commits, 0)
        self.assertNotIn("commit", self.events)

    def test_repeated_owner_does_not_capture(self):
        claim = self.setup_claim(
            json.dumps([self.USER])
        )

        result = claim("100")

        self.assertEqual(result["ok"], 0)
        self.assertEqual(
            result["reason"],
            "already_claimed",
        )

        self.normalize.assert_not_called()
        self.capture.assert_not_called()
        self.assertEqual(self.db.commits, 0)

    def test_other_owner_does_not_capture(self):
        claim = self.setup_claim(
            json.dumps([self.OTHER])
        )

        result = claim("100")

        self.assertEqual(result["ok"], 0)
        self.assertEqual(
            result["reason"],
            "already_claimed",
        )

        self.normalize.assert_not_called()
        self.capture.assert_not_called()
        self.assertEqual(self.db.commits, 0)

    def test_missing_ticket_does_not_capture(self):
        claim = self.setup_claim("")

        result = claim("")

        self.assertEqual(
            result,
            {"ok": 0, "reason": "missing_ticket"},
        )

        self.normalize.assert_not_called()
        self.capture.assert_not_called()
        self.assertEqual(self.db.commits, 0)
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
