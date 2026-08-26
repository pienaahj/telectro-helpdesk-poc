import unittest
from unittest import mock

from telephony.setup import helpdesk_folder


class TestHelpdeskFolderVerification(unittest.TestCase):
    def test_correct_helpdesk_folder_is_valid(self):
        folder = {
            "name": "Home/Helpdesk",
            "file_name": "Helpdesk",
            "folder": "Home",
            "is_folder": 1,
            "is_private": 0,
        }

        with (
            mock.patch.object(
                helpdesk_folder,
                "frappe",
            ) as frappe_mock,
            mock.patch.object(
                helpdesk_folder,
                "_get_helpdesk_folder",
                return_value=folder,
            ),
            mock.patch.object(
                helpdesk_folder,
                "_get_same_location_rows",
                return_value=[folder],
            ),
        ):
            frappe_mock.db.exists.return_value = True
            frappe_mock.local.site = "frontend"

            result = helpdesk_folder.verify_helpdesk_folder()

        frappe_mock.db.exists.assert_called_once_with(
            "File",
            "Home",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["site"], "frontend")
        self.assertTrue(result["parent_exists"])
        self.assertTrue(result["exists"])
        self.assertEqual(result["issue_count"], 0)
        self.assertEqual(result["issues"], [])

    def test_missing_helpdesk_folder_is_reported(self):
        with (
            mock.patch.object(
                helpdesk_folder,
                "frappe",
            ) as frappe_mock,
            mock.patch.object(
                helpdesk_folder,
                "_get_helpdesk_folder",
                return_value=None,
            ),
            mock.patch.object(
                helpdesk_folder,
                "_get_same_location_rows",
                return_value=[],
            ),
        ):
            frappe_mock.db.exists.return_value = True
            frappe_mock.local.site = "frontend"

            result = helpdesk_folder.verify_helpdesk_folder()

        frappe_mock.db.exists.assert_called_once_with(
            "File",
            "Home",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["site"], "frontend")
        self.assertTrue(result["parent_exists"])
        self.assertFalse(result["exists"])
        self.assertEqual(result["issue_count"], 1)
        self.assertEqual(
            result["issues"],
            [
                {
                    "type": "missing_helpdesk_folder",
                    "folder": "Home/Helpdesk",
                }
            ],
        )

class TestHelpdeskFolderReconciliation(unittest.TestCase):
    def test_existing_correct_folder_is_noop(self):
        before = {
            "ok": True,
            "site": "frontend",
            "folder": "Home/Helpdesk",
            "parent_exists": True,
            "exists": True,
            "row": {
                "name": "Home/Helpdesk",
            },
            "location_rows": [
                {
                    "name": "Home/Helpdesk",
                }
            ],
            "issue_count": 0,
            "issues": [],
        }

        with (
            mock.patch.object(
                helpdesk_folder,
                "verify_helpdesk_folder",
                return_value=before,
            ),
            mock.patch.object(
                helpdesk_folder,
                "create_helpdesk_folder",
            ) as create_folder,
        ):
            result = helpdesk_folder.ensure_helpdesk_folder()

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_count"], 0)
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["verification"], before)

        create_folder.assert_not_called()

    def test_missing_folder_is_recreated_with_helpdesk_helper(self):
        before = {
            "ok": False,
            "site": "frontend",
            "folder": "Home/Helpdesk",
            "parent_exists": True,
            "exists": False,
            "row": None,
            "location_rows": [],
            "issue_count": 1,
            "issues": [
                {
                    "type": "missing_helpdesk_folder",
                    "folder": "Home/Helpdesk",
                }
            ],
        }

        after = {
            "ok": True,
            "site": "frontend",
            "folder": "Home/Helpdesk",
            "parent_exists": True,
            "exists": True,
            "row": {
                "name": "Home/Helpdesk",
                "file_name": "Helpdesk",
                "folder": "Home",
                "is_folder": 1,
                "is_private": 0,
            },
            "location_rows": [
                {
                    "name": "Home/Helpdesk",
                    "file_name": "Helpdesk",
                    "folder": "Home",
                    "is_folder": 1,
                    "is_private": 0,
                }
            ],
            "issue_count": 0,
            "issues": [],
        }

        with (
            mock.patch.object(
                helpdesk_folder,
                "verify_helpdesk_folder",
                side_effect=[before, after],
            ),
            mock.patch.object(
                helpdesk_folder,
                "create_helpdesk_folder",
            ) as create_folder,
        ):
            result = helpdesk_folder.ensure_helpdesk_folder()

        create_folder.assert_called_once_with()

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_count"], 1)
        self.assertEqual(
            result["changed"],
            [
                {
                    "action": "create",
                    "folder": "Home/Helpdesk",
                }
            ],
        )
        self.assertEqual(result["verification"], after)

    def test_unexpected_state_is_not_silently_repaired(self):
        before = {
            "ok": False,
            "site": "frontend",
            "folder": "Home/Helpdesk",
            "parent_exists": False,
            "exists": False,
            "row": None,
            "location_rows": [],
            "issue_count": 2,
            "issues": [
                {
                    "type": "missing_parent_folder",
                    "folder": "Home",
                },
                {
                    "type": "missing_helpdesk_folder",
                    "folder": "Home/Helpdesk",
                },
            ],
        }

        with (
            mock.patch.object(
                helpdesk_folder,
                "verify_helpdesk_folder",
                return_value=before,
            ),
            mock.patch.object(
                helpdesk_folder,
                "create_helpdesk_folder",
            ) as create_folder,
            mock.patch.object(
                helpdesk_folder.frappe,
                "throw",
                side_effect=RuntimeError(
                    "Helpdesk Folder Conflict"
                ),
            ) as frappe_throw,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Helpdesk Folder Conflict",
            ):
                helpdesk_folder.ensure_helpdesk_folder()

        create_folder.assert_not_called()
        frappe_throw.assert_called_once()


class TestHelpdeskFolderLifecycle(unittest.TestCase):
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
                helpdesk_folder,
                "ensure_helpdesk_folder",
                return_value=result,
            ) as ensure_folder,
            mock.patch.object(
                helpdesk_folder,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.logger.return_value = logger

            actual = helpdesk_folder.after_migrate()

        ensure_folder.assert_called_once_with()
        self.assertEqual(actual, result)

        frappe_mock.logger.assert_called_once_with(
            "telephony",
        )

        logger.info.assert_called_once_with(
            "Helpdesk folder verified: %s, %s changed",
            "Home/Helpdesk",
            0,
        )

    def test_apply_commits_successful_repair(self):
        result = {
            "ok": True,
            "site": "frontend",
            "changed_count": 1,
            "changed": [
                {
                    "action": "create",
                    "folder": "Home/Helpdesk",
                }
            ],
            "verification": {
                "ok": True,
            },
        }

        with (
            mock.patch.object(
                helpdesk_folder,
                "frappe",
            ) as frappe_mock,
            mock.patch.object(
                helpdesk_folder,
                "ensure_helpdesk_folder",
                return_value=result,
            ) as ensure_folder,
        ):
            actual = helpdesk_folder.apply_helpdesk_folder()

        ensure_folder.assert_called_once_with()
        frappe_mock.db.commit.assert_called_once_with()
        frappe_mock.db.rollback.assert_not_called()

        self.assertEqual(actual, result)

    def test_apply_rolls_back_failed_repair(self):
        with (
            mock.patch.object(
                helpdesk_folder,
                "frappe",
            ) as frappe_mock,
            mock.patch.object(
                helpdesk_folder,
                "ensure_helpdesk_folder",
                side_effect=RuntimeError(
                    "D13 repair failure"
                ),
            ) as ensure_folder,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "D13 repair failure",
            ):
                helpdesk_folder.apply_helpdesk_folder()

        ensure_folder.assert_called_once_with()
        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
