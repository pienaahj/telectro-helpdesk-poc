import unittest
from unittest import mock

from telephony.setup import contextual_assignment_durability


class TestContextualAssignmentCondition(unittest.TestCase):
    def test_expected_condition_includes_contextual_hold_guard(self):
        self.assertEqual(
            contextual_assignment_durability.expected_assignment_condition(
                "PABX"
            ),
            (
                "status == 'Open' and "
                "agent_group == 'PABX' and "
                "not custom_contextual_assignment_hold"
            ),
        )


class TestContextualAssignmentVerification(unittest.TestCase):
    def test_linked_rule_with_legacy_condition_is_reported(self):
        with (
            mock.patch.object(
                contextual_assignment_durability,
                "_linked_team_rules",
                return_value=[
                    {
                        "team": "PABX",
                        "assignment_rule": "PABX - Support Rotation-17",
                    }
                ],
            ),
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "get_value",
                return_value={
                    "name": "PABX - Support Rotation-17",
                    "disabled": 0,
                    "assign_condition": (
                        "status == 'Open' and "
                        "agent_group == 'PABX'"
                    ),
                },
            ),
        ):
            result = (
                contextual_assignment_durability
                .verify_contextual_assignment_rules()
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["issues"],
            [
                {
                    "type": "contextual_hold_condition_missing",
                    "team": "PABX",
                    "assignment_rule": "PABX - Support Rotation-17",
                }
            ],
        )

    def test_linked_rule_with_contextual_condition_is_valid(self):
        condition = (
            contextual_assignment_durability
            .expected_assignment_condition("PABX")
        )

        with (
            mock.patch.object(
                contextual_assignment_durability,
                "_linked_team_rules",
                return_value=[
                    {
                        "team": "PABX",
                        "assignment_rule": "PABX - Support Rotation-17",
                    }
                ],
            ),
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "get_value",
                return_value={
                    "name": "PABX - Support Rotation-17",
                    "disabled": 0,
                    "assign_condition": condition,
                },
            ),
        ):
            result = (
                contextual_assignment_durability
                .verify_contextual_assignment_rules()
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["issues"], [])


class TestContextualAssignmentReconciliation(unittest.TestCase):
    def test_legacy_linked_rule_updates_only_assign_condition(self):
        rule_name = "PABX - Support Rotation-17"

        legacy_condition = (
            "status == 'Open' and "
            "agent_group == 'PABX'"
        )

        expected_condition = (
            contextual_assignment_durability
            .expected_assignment_condition("PABX")
        )

        legacy_state = {
            "name": rule_name,
            "disabled": 0,
            "assign_condition": legacy_condition,
            "last_user": "tech.charlie@local.test",
        }

        canonical_state = {
            "name": rule_name,
            "disabled": 0,
            "assign_condition": expected_condition,
            "last_user": "tech.charlie@local.test",
        }

        with (
            mock.patch.object(
                contextual_assignment_durability,
                "_linked_team_rules",
                return_value=[
                    {
                        "team": "PABX",
                        "assignment_rule": rule_name,
                    }
                ],
            ),
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "get_value",
                side_effect=[
                    legacy_state,
                    canonical_state,
                ],
            ),
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = (
                contextual_assignment_durability
                .ensure_contextual_assignment_rules()
            )

        set_value.assert_called_once_with(
            "Assignment Rule",
            rule_name,
            "assign_condition",
            expected_condition,
            update_modified=False,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_count"], 1)
        self.assertEqual(
            result["changed"],
            [
                {
                    "action": "update_assign_condition",
                    "team": "PABX",
                    "assignment_rule": rule_name,
                }
            ],
        )

        self.assertTrue(result["verification"]["ok"])

    def test_canonical_linked_rule_is_idempotent(self):
        rule_name = "PABX - Support Rotation-17"

        expected_condition = (
            contextual_assignment_durability
            .expected_assignment_condition("PABX")
        )

        canonical_state = {
            "name": rule_name,
            "disabled": 0,
            "assign_condition": expected_condition,
            "last_user": "tech.charlie@local.test",
        }

        with (
            mock.patch.object(
                contextual_assignment_durability,
                "_linked_team_rules",
                return_value=[
                    {
                        "team": "PABX",
                        "assignment_rule": rule_name,
                    }
                ],
            ),
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "get_value",
                side_effect=[
                    canonical_state,
                    canonical_state,
                ],
            ),
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = (
                contextual_assignment_durability
                .ensure_contextual_assignment_rules()
            )

        set_value.assert_not_called()

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_count"], 0)
        self.assertEqual(result["changed"], [])
        self.assertTrue(result["verification"]["ok"])

    def test_reconciliation_fails_if_post_write_verification_is_not_clean(self):
        rule_name = "PABX - Support Rotation-17"

        legacy_condition = (
            "status == 'Open' and "
            "agent_group == 'PABX'"
        )

        legacy_state = {
            "name": rule_name,
            "disabled": 0,
            "assign_condition": legacy_condition,
        }

        with (
            mock.patch.object(
                contextual_assignment_durability,
                "_linked_team_rules",
                return_value=[
                    {
                        "team": "PABX",
                        "assignment_rule": rule_name,
                    }
                ],
            ),
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "get_value",
                side_effect=[
                    legacy_state,
                    legacy_state,
                ],
            ),
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "set_value",
            ) as set_value,
            mock.patch.object(
                contextual_assignment_durability.frappe,
                "throw",
                side_effect=RuntimeError(
                    "contextual assignment verification failed"
                ),
            ) as throw,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "contextual assignment verification failed",
            ):
                (
                    contextual_assignment_durability
                    .ensure_contextual_assignment_rules()
                )

        set_value.assert_called_once()
        throw.assert_called_once()

class TestContextualAssignmentEntryPoints(unittest.TestCase):
    def test_apply_commits_successful_reconciliation(self):
        expected = {
            "ok": True,
            "changed_count": 1,
            "changed": [
                {
                    "action": "update_assign_condition",
                    "team": "PABX",
                    "assignment_rule": "PABX - Support Rotation-17",
                }
            ],
            "verification": {
                "ok": True,
                "issues": [],
            },
        }

        with (
            mock.patch.object(
                contextual_assignment_durability,
                "ensure_contextual_assignment_rules",
                return_value=expected,
            ) as ensure,
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "rollback",
            ) as rollback,
        ):
            result = (
                contextual_assignment_durability
                .apply_contextual_assignment_rules()
            )

        self.assertEqual(result, expected)
        ensure.assert_called_once_with()
        commit.assert_called_once_with()
        rollback.assert_not_called()

    def test_apply_rolls_back_failed_reconciliation(self):
        with (
            mock.patch.object(
                contextual_assignment_durability,
                "ensure_contextual_assignment_rules",
                side_effect=RuntimeError(
                    "contextual reconciliation failed"
                ),
            ) as ensure,
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                contextual_assignment_durability.frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "contextual reconciliation failed",
            ):
                (
                    contextual_assignment_durability
                    .apply_contextual_assignment_rules()
                )

        ensure.assert_called_once_with()
        commit.assert_not_called()
        rollback.assert_called_once_with()

    def test_after_migrate_runs_non_committing_reconciliation(self):
        expected = {
            "ok": True,
            "changed_count": 0,
            "changed": [],
            "verification": {
                "ok": True,
                "issues": [],
            },
        }

        with mock.patch.object(
            contextual_assignment_durability,
            "ensure_contextual_assignment_rules",
            return_value=expected,
        ) as ensure:
            result = (
                contextual_assignment_durability
                .after_migrate()
            )

        self.assertEqual(result, expected)
        ensure.assert_called_once_with()

if __name__ == "__main__":
    unittest.main()
