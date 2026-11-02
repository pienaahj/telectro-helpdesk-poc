"""Isolated regression tests for the real Claim function body.

The Claim source is compiled from its AST with only the
whitelist decorator removed. No Frappe connection is made.
"""

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
    """Simulate the conditional SQL UPDATE accurately."""

    def __init__(self, current_assign=""):
        self.current_assign = current_assign
        self.status = "Open"
        self.fulfilment_party = "Telectro"
        self.agent_group = "Routing"
        self.open_todo = False
        self.team_members = {"tech@example.invalid"}
        self.rowcount = 0
        self._cursor = types.SimpleNamespace(rowcount=0)
        self.commits = 0
        self.updates = 0


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
            self.updates += 1

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

            self._cursor.rowcount = self.rowcount
            return []

        if "ROW_COUNT()" in query.upper():
            return [(self.rowcount,)]

        raise AssertionError(
            "Unexpected SQL in Claim: " + query[:100]
        )

    def get_value(self, doctype, name, field):
        assert (doctype, name, field) == (
            "HD Ticket", "100", "_assign"
        )

        return self.current_assign

    def affected_rows(self):
        return self.rowcount

    def commit(self):
        self.commits += 1


def load_actual_claim(db, user, normalize):
    source = CLAIM_SOURCE.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    functions = [
        node for node in parsed.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "telectro_claim_ticket"
    ]

    assert len(functions) == 1

    function = copy.deepcopy(functions[0])

    # Do not execute the Frappe whitelist decorator.
    # Everything inside the function body is unchanged.
    function.decorator_list = []

    isolated = ast.Module(
        body=[function],
        type_ignores=[],
    )

    ast.fix_missing_locations(isolated)

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
        "capture_verified_task_ownership_transition": mock.Mock(),
    }

    exec(
        compile(isolated, str(CLAIM_SOURCE), "exec"),
        namespace,
    )

    return namespace["telectro_claim_ticket"]


class TestTaskNotificationClaimBoundary(unittest.TestCase):

    USER = "tech@example.invalid"
    OTHER = "other@example.invalid"

    def setup_claim(self, current_assign=""):
        db = FakeDatabase(current_assign=current_assign)
        normalize = mock.Mock()

        claim = load_actual_claim(
            db=db,
            user=self.USER,
            normalize=normalize,
        )

        return claim, db, normalize

    def test_first_claim_from_empty_pool_succeeds(self):
        claim, db, normalize = self.setup_claim("")

        result = claim("100")

        self.assertEqual(result["ok"], 1)
        self.assertEqual(
            result["assigned_to"],
            self.USER,
        )
        self.assertEqual(
            db.current_assign,
            json.dumps([self.USER]),
        )

        normalize.assert_called_once_with(
            "100", self.USER, note="Claim"
        )
        self.assertEqual(db.updates, 1)
        self.assertEqual(db.commits, 1)

    def test_first_claim_from_json_empty_pool_succeeds(self):
        claim, db, normalize = self.setup_claim("[]")

        result = claim("100")

        self.assertEqual(result["ok"], 1)
        normalize.assert_called_once()
        self.assertEqual(db.commits, 1)

    def test_other_owner_cannot_be_claimed(self):
        existing = json.dumps([self.OTHER])

        claim, db, normalize = self.setup_claim(existing)

        result = claim("100")

        self.assertEqual(result["ok"], 0)
        self.assertEqual(
            result["reason"],
            "already_claimed",
        )
        self.assertEqual(db.current_assign, existing)

        normalize.assert_not_called()
        self.assertEqual(db.commits, 0)

    def test_repeated_claim_by_same_owner_is_not_new_claim(self):
        existing = json.dumps([self.USER])

        claim, db, normalize = self.setup_claim(existing)

        result = claim("100")

        # The existing implementation incorrectly returns
        # ok=1 because it checks the value after UPDATE,
        # not whether the UPDATE affected a row.
        self.assertEqual(result["ok"], 0)
        self.assertEqual(
            result["reason"],
            "already_claimed",
        )
        self.assertEqual(db.current_assign, existing)

        normalize.assert_not_called()
        self.assertEqual(db.commits, 0)


if __name__ == "__main__":
    unittest.main()
