import unittest
from unittest import mock

from telephony.setup import ticket_status_durability


class TestArchivedStatusVerification(unittest.TestCase):
    def test_valid_archived_status_is_accepted(self):
        status = {
            "name": "Archived",
            "label_agent": "Archived",
            "enabled": 1,
            "category": "Resolved",
            "order": 5,
            "color": "Gray",
            "different_view": 0,
            "label_customer": None,
        }

        with (
            mock.patch.object(
                ticket_status_durability,
                "_get_archived_status_state",
                return_value=status,
            ),
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                ticket_status_durability
                .verify_archived_status()
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["site"], "frontend")
        self.assertEqual(result["issue_count"], 0)
        self.assertEqual(result["issues"], [])
        self.assertEqual(
            result["expected"],
            ticket_status_durability.ARCHIVED_STATUS_SPEC,
        )

    def test_missing_archived_status_is_reported(self):
        with (
            mock.patch.object(
                ticket_status_durability,
                "_get_archived_status_state",
                return_value=None,
            ),
            mock.patch.object(
                ticket_status_durability,
                "_get_archived_label_conflict",
                return_value=None,
            ),
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                ticket_status_durability
                .verify_archived_status()
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["issue_count"], 1)
        self.assertEqual(
            result["issues"],
            [
                {
                    "type": "missing_archived_status",
                    "status": "Archived",
                }
            ],
        )

    def test_archived_status_name_conflict_is_reported(self):
        conflict = {
            "name": "Archived Legacy",
            "label_agent": "Archived",
        }

        with (
            mock.patch.object(
                ticket_status_durability,
                "_get_archived_status_state",
                return_value=None,
            ),
            mock.patch.object(
                ticket_status_durability,
                "_get_archived_label_conflict",
                return_value=conflict,
            ),
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                ticket_status_durability
                .verify_archived_status()
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["issue_count"], 1)
        self.assertEqual(
            result["issues"],
            [
                {
                    "type": "archived_status_name_conflict",
                    "expected_name": "Archived",
                    "actual_name": "Archived Legacy",
                }
            ],
        )

    def test_archived_status_field_mismatch_is_reported(self):
        status = {
            "name": "Archived",
            "label_agent": "Archived",
            "enabled": 0,
            "category": "Resolved",
            "order": 5,
            "color": "Gray",
            "different_view": 0,
            "label_customer": "",
        }

        with (
            mock.patch.object(
                ticket_status_durability,
                "_get_archived_status_state",
                return_value=status,
            ),
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                ticket_status_durability
                .verify_archived_status()
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["issue_count"], 1)
        self.assertEqual(
            result["issues"],
            [
                {
                    "type": "archived_status_field_mismatch",
                    "field": "enabled",
                    "expected": 1,
                    "actual": 0,
                }
            ],
        )


class TestArchivedStatusReconciliation(unittest.TestCase):
    def test_existing_valid_status_is_not_rewritten(self):
        verification = {
            "ok": True,
            "site": "frontend",
            "status": {},
            "expected": dict(
                ticket_status_durability
                .ARCHIVED_STATUS_SPEC
            ),
            "issue_count": 0,
            "issues": [],
        }

        with (
            mock.patch.object(
                ticket_status_durability,
                "verify_archived_status",
                side_effect=[
                    verification,
                    verification,
                ],
            ),
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.db.exists.return_value = True

            result = (
                ticket_status_durability
                .ensure_archived_status()
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_count"], 0)
        self.assertEqual(result["changed"], [])

        frappe_mock.new_doc.assert_not_called()

    def test_missing_status_is_created_with_canonical_values(self):
        before = {
            "ok": False,
            "site": "frontend",
            "status": None,
            "expected": dict(
                ticket_status_durability
                .ARCHIVED_STATUS_SPEC
            ),
            "issue_count": 1,
            "issues": [
                {
                    "type": "missing_archived_status",
                    "status": "Archived",
                }
            ],
        }

        after = {
            "ok": True,
            "site": "frontend",
            "status": {},
            "expected": dict(
                ticket_status_durability
                .ARCHIVED_STATUS_SPEC
            ),
            "issue_count": 0,
            "issues": [],
        }

        status_doc = mock.Mock()

        with (
            mock.patch.object(
                ticket_status_durability,
                "verify_archived_status",
                side_effect=[
                    before,
                    after,
                ],
            ),
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.db.exists.return_value = False
            frappe_mock.new_doc.return_value = status_doc

            result = (
                ticket_status_durability
                .ensure_archived_status()
            )

        frappe_mock.new_doc.assert_called_once_with(
            "HD Ticket Status",
        )

        self.assertEqual(
            status_doc.label_agent,
            "Archived",
        )
        self.assertEqual(status_doc.enabled, 1)
        self.assertEqual(
            status_doc.category,
            "Resolved",
        )
        self.assertEqual(status_doc.order, 5)
        self.assertEqual(status_doc.color, "Gray")
        self.assertEqual(
            status_doc.different_view,
            0,
        )
        self.assertEqual(
            status_doc.label_customer,
            "",
        )

        status_doc.insert.assert_called_once_with()

        self.assertEqual(result["changed_count"], 1)
        self.assertEqual(
            result["changed"],
            [
                {
                    "action": "create",
                    "status": "Archived",
                }
            ],
        )

    def test_conflicting_existing_status_is_not_rewritten(self):
        before = {
            "ok": False,
            "site": "frontend",
            "status": {},
            "expected": dict(
                ticket_status_durability
                .ARCHIVED_STATUS_SPEC
            ),
            "issue_count": 1,
            "issues": [
                {
                    "type": "archived_status_field_mismatch",
                    "field": "category",
                    "expected": "Resolved",
                    "actual": "Open",
                }
            ],
        }

        with (
            mock.patch.object(
                ticket_status_durability,
                "verify_archived_status",
                return_value=before,
            ),
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.throw.side_effect = RuntimeError(
                "Archived Status Conflict"
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "Archived Status Conflict",
            ):
                (
                    ticket_status_durability
                    .ensure_archived_status()
                )

        frappe_mock.new_doc.assert_not_called()


class TestArchivedStatusLifecycle(unittest.TestCase):
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
                ticket_status_durability,
                "ensure_archived_status",
                return_value=result,
            ) as ensure_status,
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.logger.return_value = logger

            actual = (
                ticket_status_durability
                .after_migrate()
            )

        ensure_status.assert_called_once_with()

        frappe_mock.logger.assert_called_once_with(
            "telephony",
        )

        logger.info.assert_called_once_with(
            "Archived HD Ticket Status verified: %s changed",
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
                    "status": "Archived",
                }
            ],
            "verification": {
                "ok": True,
            },
        }

        with (
            mock.patch.object(
                ticket_status_durability,
                "ensure_archived_status",
                return_value=result,
            ) as ensure_status,
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            actual = (
                ticket_status_durability
                .apply_archived_status()
            )

        ensure_status.assert_called_once_with()
        frappe_mock.db.commit.assert_called_once_with()
        frappe_mock.db.rollback.assert_not_called()

        self.assertEqual(actual, result)

    def test_apply_rolls_back_failed_reconciliation(self):
        with (
            mock.patch.object(
                ticket_status_durability,
                "ensure_archived_status",
                side_effect=RuntimeError(
                    "Archived status reconciliation failure"
                ),
            ) as ensure_status,
            mock.patch.object(
                ticket_status_durability,
                "frappe",
            ) as frappe_mock,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Archived status reconciliation failure",
            ):
                (
                    ticket_status_durability
                    .apply_archived_status()
                )

        ensure_status.assert_called_once_with()
        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
