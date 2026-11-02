"""Red-phase authorization regressions for the real TELECTRO Claim function.

Compile the actual Claim function from telectro_claim.py's AST without importing
Frappe. The database and document operations are simulated. No delivery, DEV
connection, or production access is required.

These tests are INTENTIONALLY RED against the 2026-10-30 Claim implementation.
Do not amend expectations to make that unguarded implementation pass.
"""

import __future__
import ast
import copy
import json
import types
import unittest
from pathlib import Path
from unittest import mock


CLAIM_SOURCE = Path(__file__).resolve().parents[1] / "telectro_claim.py"
TICKET = "100"
TECH = "tech.bravo@local.test"
TECH_ROLE = "TELECTRO-POC Role - Tech"
COORD_ROLE = "TELECTRO-POC Role - Coordinator Ops"


class FakeDocument(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class FakeDatabase:
    def __init__(self, ticket, identity, *, open_todo=False):
        self.ticket = dict(ticket)
        self.identity = dict(identity)
        self.open_todo = open_todo
        self.updates = 0
        self.commits = 0
        self.rowcount = 0


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
            assert values is not None and len(values) == 5
            assign_json, name, group, privileged, claimant = values
            assert str(name) == TICKET
            assert group == self.ticket.get("agent_group")
            assert privileged in (0, 1)
            assert claimant == self.identity["user"]
            assert "`status` = 'Open'" in query
            assert "`custom_fulfilment_party` = 'Telectro'" in query
            assert "`agent_group` = %s" in query
            assert "NOT EXISTS" in query and "`tabToDo`" in query
            assert "`tabHD Team Member`" in query
            assert "claim_member.user = %s" in query
            if (
                self.ticket.get("_assign") in ("", "[]", None)
                and self.ticket.get("status") == "Open"
                and self.ticket.get("custom_fulfilment_party") == "Telectro"
                and self.ticket.get("agent_group") == group
                and not self.open_todo
                and (privileged == 1 or group in self.identity["teams"])
            ):
                self.ticket["_assign"] = assign_json
                self.rowcount = 1
            else:
                self.rowcount = 0
            return []

        if "ROW_COUNT()" in query.upper():
            return [(self.rowcount,)]

        raise AssertionError("Unexpected Claim SQL: " + str(query)[:200])

    def get_value(self, doctype, name, fieldname, **kwargs):
        if doctype == "HD Ticket" and str(name) == TICKET:
            if isinstance(fieldname, (list, tuple)):
                result = {field: self.ticket.get(field) for field in fieldname}
                return result if kwargs.get("as_dict") else tuple(result.values())
            return self.ticket.get(fieldname)
        if doctype == "User" and name == self.identity["user"]:
            if isinstance(fieldname, (list, tuple)):
                result = {field: self.identity.get(field) for field in fieldname}
                return result if kwargs.get("as_dict") else tuple(result.values())
            return self.identity.get(fieldname)
        raise AssertionError("Unexpected get_value: " + repr((doctype, name, fieldname)))

    def exists(self, doctype, filters):
        if doctype == "ToDo":
            return "TODO-EXISTING" if self.open_todo else None
        if doctype == "HD Team":
            return filters if filters in {"Routing", "PABX"} else None
        if doctype == "HD Team Member":
            group = filters.get("parent")
            return "MEMBER" if group in self.identity["teams"] else None
        if doctype == "User":
            return self.identity["user"] if self.identity["enabled"] else None
        raise AssertionError("Unexpected exists: " + repr((doctype, filters)))

    def commit(self):
        self.commits += 1


def build_case(**overrides):
    case = {
        "user": TECH,
        "enabled": 1,
        "user_type": "System User",
        "roles": {"Agent", TECH_ROLE},
        "teams": {"Routing", "SIM", "CCTV", "Internet Connection"},
        "has_permission": True,
        "ticket": {
            "name": TICKET,
            "status": "Open",
            "agent_group": "Routing",
            "custom_fulfilment_party": "Telectro",
            "custom_contextual_assignment_hold": 1,
            "_assign": "",
        },
        "open_todo": False,
    }
    case.update(overrides)
    return case


def compile_claim(case):
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
    # Compile the actual authorization helper rather than mocking it.
    helpers = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_require_claim_authorization"
    ]
    assert len(helpers) == 1
    module = ast.Module(
        body=[copy.deepcopy(helpers[0]), function], type_ignores=[]
    )
    ast.fix_missing_locations(module)

    identity = {
        "user": case["user"],
        "enabled": case["enabled"],
        "user_type": case["user_type"],
        "roles": set(case["roles"]),
        "teams": set(case["teams"]),
    }
    database = FakeDatabase(
        case["ticket"], identity, open_todo=case["open_todo"]
    )
    normalize = mock.Mock(return_value="COMMENT-CLAIM-001")
    capture = mock.Mock(return_value={"ok": True, "created": True})

    def frappe_throw(message, exc=None):
        raise (exc or PermissionError)(message)

    def has_permission(*args, **kwargs):
        return case["has_permission"]

    frappe = types.SimpleNamespace(
        db=database,
        session=types.SimpleNamespace(user=case["user"]),
        get_roles=lambda user=None: list(identity["roles"]),
        has_permission=has_permission,
        get_doc=lambda doctype, name: FakeDocument(case["ticket"]),
        PermissionError=PermissionError,
        throw=frappe_throw,
    )
    namespace = {
        "json": json,
        "frappe": frappe,
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
    return namespace["telectro_claim_ticket"], database, normalize, capture


class TestTaskNotificationClaimAuthorization(unittest.TestCase):
    def assert_denied(self, case):
        claim, database, normalize, capture = compile_claim(case)
        try:
            result = claim(TICKET)
        except PermissionError:
            pass
        else:
            self.assertIsInstance(result, dict)
            self.assertNotEqual(result.get("ok"), 1, "Ineligible Claim succeeded")
        self.assertEqual(database.updates, 0, "Denial attempted an ownership UPDATE")
        self.assertEqual(database.commits, 0, "Denial committed")
        normalize.assert_not_called()
        capture.assert_not_called()

    def assert_allowed(self, case):
        claim, database, normalize, capture = compile_claim(case)
        result = claim(TICKET)
        self.assertEqual(result.get("ok"), 1)
        self.assertEqual(result.get("assigned_to"), case["user"])
        self.assertEqual(database.updates, 1)
        self.assertEqual(database.commits, 1)
        normalize.assert_called_once_with(TICKET, case["user"], note="Claim")
        capture.assert_called_once()

    def test_guest_must_not_claim(self):
        self.assert_denied(build_case(user="Guest", enabled=0, roles=set()))

    def test_empty_session_user_must_not_claim(self):
        self.assert_denied(build_case(user="", enabled=0, roles=set()))

    def test_partner_must_not_claim(self):
        self.assert_denied(build_case(
            user="partner.test@local.test",
            roles={"TELECTRO-POC Role - Partner"},
        ))

    def test_customer_portal_user_must_not_claim(self):
        self.assert_denied(build_case(
            user="customer@local.test", user_type="Website User",
            roles={"Customer"},
        ))

    def test_generic_helpdesk_agent_must_not_claim(self):
        self.assert_denied(build_case(
            user="helpdesk@local.test", roles={"Support Team", "Agent"},
        ))

    def test_disabled_technician_must_not_claim(self):
        self.assert_denied(build_case(enabled=0))

    def test_technician_must_not_claim_outside_team(self):
        self.assert_denied(build_case(ticket={
            **build_case()["ticket"], "agent_group": "PABX",
        }))

    def test_technician_must_not_claim_missing_team(self):
        self.assert_denied(build_case(ticket={
            **build_case()["ticket"], "agent_group": "",
        }))

    def test_archived_ticket_must_not_be_claimed(self):
        self.assert_denied(build_case(ticket={
            **build_case()["ticket"], "status": "Archived",
        }))

    def test_resolved_ticket_must_not_be_claimed(self):
        self.assert_denied(build_case(ticket={
            **build_case()["ticket"], "status": "Resolved",
        }))

    def test_closed_ticket_must_not_be_claimed(self):
        self.assert_denied(build_case(ticket={
            **build_case()["ticket"], "status": "Closed",
        }))

    def test_partner_fulfilment_must_not_be_claimed(self):
        self.assert_denied(build_case(ticket={
            **build_case()["ticket"], "custom_fulfilment_party": "Partner",
        }))

    def test_open_todo_must_block_empty_assign_claim(self):
        self.assert_denied(build_case(open_todo=True))

    def test_missing_ticket_read_permission_must_block_claim(self):
        self.assert_denied(build_case(has_permission=False))

    def test_coordinator_must_not_claim_partner_fulfilment(self):
        self.assert_denied(build_case(
            user="coordinator.test@local.test",
            roles={COORD_ROLE},
            ticket={**build_case()["ticket"],
                    "custom_fulfilment_party": "Partner"},
        ))

    def test_same_team_true_pool_hold_remains_claimable(self):
        self.assert_allowed(build_case())

    def test_same_team_unheld_pool_remains_claimable(self):
        self.assert_allowed(build_case(ticket={
            **build_case()["ticket"], "custom_contextual_assignment_hold": 0,
        }))

    def test_coordinator_cross_team_open_pool_remains_claimable(self):
        self.assert_allowed(build_case(
            user="coordinator.test@local.test", roles={COORD_ROLE},
            teams=set(),
            ticket={**build_case()["ticket"], "agent_group": "PABX"},
        ))


if __name__ == "__main__":
    unittest.main()
