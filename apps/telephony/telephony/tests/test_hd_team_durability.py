import unittest
from pathlib import Path
from unittest import mock

from telephony.setup import hd_team_durability


class TestHDTeamVerification(unittest.TestCase):
    def test_required_hd_teams_are_valid(self):
        def get_team(team_name):
            return {
                "name": team_name,
                "team_name": team_name,
                "assignment_rule": f"{team_name} - Support Rotation",
            }

        with (
            mock.patch.object(
                hd_team_durability,
                "_get_team_state",
                side_effect=get_team,
            ),
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"
            frappe_mock.db.exists.return_value = True

            result = hd_team_durability.verify_hd_teams()

        self.assertTrue(result["ok"])
        self.assertEqual(result["site"], "frontend")
        self.assertEqual(result["issue_count"], 0)
        self.assertEqual(result["issues"], [])
        self.assertEqual(
            result["required_teams"],
            list(hd_team_durability.REQUIRED_HD_TEAMS),
        )
        self.assertEqual(
            len(result["teams"]),
            len(hd_team_durability.REQUIRED_HD_TEAMS),
        )

    def test_missing_hd_team_is_reported(self):
        missing_team = "PABX"

        def get_team(team_name):
            if team_name == missing_team:
                return None

            return {
                "name": team_name,
                "team_name": team_name,
                "assignment_rule": f"{team_name} - Support Rotation",
            }

        with (
            mock.patch.object(
                hd_team_durability,
                "_get_team_state",
                side_effect=get_team,
            ),
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"
            frappe_mock.db.exists.return_value = True

            result = hd_team_durability.verify_hd_teams()

        self.assertFalse(result["ok"])
        self.assertEqual(result["issue_count"], 1)
        self.assertEqual(
            result["issues"],
            [
                {
                    "type": "missing_hd_team",
                    "team": "PABX",
                }
            ],
        )

    def test_missing_assignment_rule_link_is_reported(self):
        def get_team(team_name):
            return {
                "name": team_name,
                "team_name": team_name,
                "assignment_rule": (
                    None
                    if team_name == "PABX"
                    else f"{team_name} - Support Rotation"
                ),
            }

        with (
            mock.patch.object(
                hd_team_durability,
                "_get_team_state",
                side_effect=get_team,
            ),
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"
            frappe_mock.db.exists.return_value = True

            result = hd_team_durability.verify_hd_teams()

        self.assertFalse(result["ok"])
        self.assertEqual(result["issue_count"], 1)
        self.assertIn(
            {
                "type": "missing_hd_team_assignment_rule",
                "team": "PABX",
            },
            result["issues"],
        )

    def test_missing_linked_assignment_rule_is_reported(self):
        def get_team(team_name):
            return {
                "name": team_name,
                "team_name": team_name,
                "assignment_rule": f"{team_name} - Support Rotation",
            }

        with (
            mock.patch.object(
                hd_team_durability,
                "_get_team_state",
                side_effect=get_team,
            ),
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            frappe_mock.db.exists.side_effect = (
                lambda doctype, name:
                not (
                    doctype == "Assignment Rule"
                    and name == "PABX - Support Rotation"
                )
            )

            result = hd_team_durability.verify_hd_teams()

        self.assertFalse(result["ok"])
        self.assertEqual(result["issue_count"], 1)
        self.assertIn(
            {
                "type": "missing_assignment_rule",
                "team": "PABX",
                "assignment_rule": "PABX - Support Rotation",
            },
            result["issues"],
        )

class TestHDTeamReconciliation(unittest.TestCase):
    def test_existing_teams_are_not_rewritten(self):
        verification = {
            "ok": True,
            "site": "frontend",
            "required_teams": list(
                hd_team_durability.REQUIRED_HD_TEAMS
            ),
            "teams": [],
            "issue_count": 0,
            "issues": [],
        }

        with (
            mock.patch.object(
                hd_team_durability,
                "verify_hd_teams",
                side_effect=[
                    verification,
                    verification,
                ],
            ),
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.db.exists.return_value = True

            result = hd_team_durability.ensure_hd_teams()

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_count"], 0)
        self.assertEqual(result["changed"], [])

        frappe_mock.new_doc.assert_not_called()

    def test_missing_team_is_created_without_members(self):
        before = {
            "ok": False,
            "site": "frontend",
            "required_teams": list(
                hd_team_durability.REQUIRED_HD_TEAMS
            ),
            "teams": [],
            "issue_count": 1,
            "issues": [
                {
                    "type": "missing_hd_team",
                    "team": "PABX",
                }
            ],
        }

        after = {
            "ok": True,
            "site": "frontend",
            "required_teams": list(
                hd_team_durability.REQUIRED_HD_TEAMS
            ),
            "teams": [],
            "issue_count": 0,
            "issues": [],
        }

        team_doc = mock.Mock()

        with (
            mock.patch.object(
                hd_team_durability,
                "verify_hd_teams",
                side_effect=[
                    before,
                    after,
                ],
            ),
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.db.exists.side_effect = (
                lambda doctype, name: name != "PABX"
            )
            frappe_mock.new_doc.return_value = team_doc

            result = hd_team_durability.ensure_hd_teams()

        frappe_mock.new_doc.assert_called_once_with(
            "HD Team",
        )

        self.assertEqual(
            team_doc.team_name,
            "PABX",
        )
        team_doc.insert.assert_called_once_with()

        self.assertEqual(result["changed_count"], 1)
        self.assertEqual(
            result["changed"],
            [
                {
                    "action": "create",
                    "team": "PABX",
                }
            ],
        )

    def test_unexpected_team_state_is_not_rewritten(self):
        before = {
            "ok": False,
            "site": "frontend",
            "required_teams": list(
                hd_team_durability.REQUIRED_HD_TEAMS
            ),
            "teams": [],
            "issue_count": 1,
            "issues": [
                {
                    "type": "hd_team_team_name_mismatch",
                    "team": "PABX",
                    "actual": "Unexpected",
                }
            ],
        }

        with (
            mock.patch.object(
                hd_team_durability,
                "verify_hd_teams",
                return_value=before,
            ),
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.throw.side_effect = RuntimeError(
                "HD Team Conflict"
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "HD Team Conflict",
            ):
                hd_team_durability.ensure_hd_teams()

        frappe_mock.new_doc.assert_not_called()


class TestHDTeamLifecycle(unittest.TestCase):
    def test_after_migrate_uses_idempotent_ensure(self):
        result = {
            "ok": True,
            "site": "frontend",
            "changed_count": 0,
            "changed": [],
            "verification": {
                "ok": True,
            },
        }

        logger = mock.Mock()

        with (
            mock.patch.object(
                hd_team_durability,
                "ensure_hd_teams",
                return_value=result,
            ) as ensure_teams,
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.logger.return_value = logger

            actual = hd_team_durability.after_migrate()

        ensure_teams.assert_called_once_with()

        frappe_mock.logger.assert_called_once_with(
            "telephony",
        )

        logger.info.assert_called_once_with(
            "Required HD Teams verified: %s, %s changed",
            len(hd_team_durability.REQUIRED_HD_TEAMS),
            0,
        )

        self.assertEqual(actual, result)

    def test_apply_commits_successful_reconciliation(self):
        result = {
            "ok": True,
            "site": "frontend",
            "changed_count": 1,
            "changed": [
                {
                    "action": "create",
                    "team": "PABX",
                }
            ],
            "verification": {
                "ok": True,
            },
        }

        with (
            mock.patch.object(
                hd_team_durability,
                "ensure_hd_teams",
                return_value=result,
            ) as ensure_teams,
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            actual = hd_team_durability.apply_hd_teams()

        ensure_teams.assert_called_once_with()
        frappe_mock.db.commit.assert_called_once_with()
        frappe_mock.db.rollback.assert_not_called()

        self.assertEqual(actual, result)

    def test_apply_rolls_back_failed_reconciliation(self):
        with (
            mock.patch.object(
                hd_team_durability,
                "ensure_hd_teams",
                side_effect=RuntimeError(
                    "D1-D3 reconciliation failure"
                ),
            ) as ensure_teams,
            mock.patch.object(
                hd_team_durability,
                "frappe",
            ) as frappe_mock,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "D1-D3 reconciliation failure",
            ):
                hd_team_durability.apply_hd_teams()

        ensure_teams.assert_called_once_with()
        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_called_once_with()


class TestHDTeamOwnershipContract(unittest.TestCase):
    def test_hd_team_fixture_ownership_is_removed(self):
        telephony_root = (
            Path(hd_team_durability.__file__)
            .resolve()
            .parents[1]
        )

        fixture_path = (
            telephony_root
            / "fixtures/hd_team.json"
        )

        hooks_path = (
            telephony_root
            / "hooks.py"
        )

        self.assertFalse(
            fixture_path.exists(),
            "hd_team.json must not return as a runtime fixture",
        )

        hooks_source = hooks_path.read_text()

        self.assertNotIn(
            '"dt": "HD Team"',
            hooks_source,
        )

        hook_path = (
            "telephony.setup."
            "hd_team_durability.after_migrate"
        )

        self.assertEqual(
            hooks_source.count(hook_path),
            1,
        )


if __name__ == "__main__":
    unittest.main()
