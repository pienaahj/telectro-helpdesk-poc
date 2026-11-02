"""Isolated tests for Claim normalization event identity.

The real helper body is compiled without importing Frappe.
All database and document operations are simulated.
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


class FakeDocument:
    def __init__(self, payload):
        self.doctype = payload["doctype"]
        self.name = {
            "ToDo": "TODO-001",
            "Comment": "COMMENT-CLAIM-001",
        }[self.doctype]

        self.insert = mock.Mock(return_value=self)


def load_normalizer(existing_todos):
    source = CLAIM_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_normalize_assignment"
    ]

    assert len(matches) == 1

    function = copy.deepcopy(matches[0])
    function.decorator_list = []

    module = ast.Module(
        body=[function],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)

    database = types.SimpleNamespace(
        sql=mock.Mock(),
        set_value=mock.Mock(),
    )

    get_all = mock.Mock(
        return_value=existing_todos
    )

    def new_document(payload):
        return FakeDocument(payload)

    get_doc = mock.Mock(
        side_effect=new_document
    )

    frappe = types.SimpleNamespace(
        db=database,
        get_all=get_all,
        get_doc=get_doc,
    )

    namespace = {
        "json": json,
        "frappe": frappe,
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

    return (
        namespace["_normalize_assignment"],
        database,
        get_all,
        get_doc,
    )


class TestTaskNotificationClaimEventIdentity(unittest.TestCase):

    USER = "tech@example.invalid"
    TICKET = "100"

    def test_new_todo_returns_inserted_comment_identity(self):
        normalize, db, get_all, get_doc = (
            load_normalizer([])
        )

        event_id = normalize(
            self.TICKET,
            self.USER,
            note="Claim",
        )

        self.assertEqual(
            event_id,
            "COMMENT-CLAIM-001",
        )

        doctypes = [
            call.args[0]["doctype"]
            for call in get_doc.call_args_list
        ]

        self.assertEqual(
            doctypes,
            ["ToDo", "Comment"],
        )

        self.assertEqual(
            get_doc.call_args_list[-1].args[0]["content"],
            "Claim | Assigned via TELECTRO pilot action",
        )

        db.set_value.assert_not_called()

    def test_reused_todo_still_returns_new_comment_identity(self):
        existing_todo = {
            "name": "TODO-EXISTING",
            "allocated_to": self.USER,
            "creation": "2026-10-30 08:00:00",
        }

        normalize, db, get_all, get_doc = (
            load_normalizer([existing_todo])
        )

        event_id = normalize(
            self.TICKET,
            self.USER,
            note="Claim",
        )

        self.assertEqual(
            event_id,
            "COMMENT-CLAIM-001",
        )

        doctypes = [
            call.args[0]["doctype"]
            for call in get_doc.call_args_list
        ]

        # No new ToDo is necessary, but the new Claim
        # still has its own durable Comment identity.
        self.assertEqual(doctypes, ["Comment"])

        db.set_value.assert_not_called()

    def test_normalization_without_note_returns_none(self):
        existing_todo = {
            "name": "TODO-EXISTING",
            "allocated_to": self.USER,
            "creation": "2026-10-30 08:00:00",
        }

        normalize, db, get_all, get_doc = (
            load_normalizer([existing_todo])
        )

        result = normalize(
            self.TICKET,
            self.USER,
            note=None,
        )

        self.assertIsNone(result)
        get_doc.assert_not_called()
        db.set_value.assert_not_called()


if __name__ == "__main__":
    unittest.main()
