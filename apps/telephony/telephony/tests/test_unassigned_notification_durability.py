import unittest
from unittest import mock

import frappe

from telephony.setup import unassigned_notification_durability as durability


class TestUnassignedNotificationCondition(unittest.TestCase):

    def test_condition_is_scoped_to_unassigned_routing_and_pabx(self):
        cases = [
            ("Routing", None, True),
            ("Routing", "", True),
            ("Routing", "[]", True),
            ("PABX", "[]", True),
            ("CCTV", "[]", False),
            ("Internet Connection", "[]", False),
            ("Routing", '["tech.bravo@local.test"]', False),
            ("PABX", '["tech.charlie@local.test"]', False),
            (None, "[]", False),
        ]

        for service_area, assigned, expected in cases:
            with self.subTest(
                service_area=service_area,
                assigned=assigned,
            ):
                doc = frappe._dict({
                    "custom_service_area": service_area,
                    "_assign": assigned,
                })

                result = frappe.safe_eval(
                    durability.SCOPED_CONDITION,
                    eval_locals={"doc": doc},
                )

                self.assertEqual(bool(result), expected)


class TestUnassignedNotificationReconciliation(unittest.TestCase):

    def test_missing_notification_is_not_created(self):
        with (
            mock.patch.object(
                durability.frappe.db,
                "exists",
                return_value=False,
            ),
            mock.patch.object(
                durability.frappe.db,
                "get_value",
            ) as get_value,
            mock.patch.object(
                durability.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = durability.ensure_unassigned_notification_scope()

        self.assertEqual(
            result,
            {
                "ok": True,
                "present": False,
                "changed_count": 0,
            },
        )

        get_value.assert_not_called()
        set_value.assert_not_called()

    def test_legacy_condition_is_corrected(self):
        with (
            mock.patch.object(
                durability.frappe.db,
                "exists",
                return_value=True,
            ),
            mock.patch.object(
                durability.frappe.db,
                "get_value",
                side_effect=[
                    durability.LEGACY_CONDITION + "\n\n",
                    durability.SCOPED_CONDITION,
                ],
            ),
            mock.patch.object(
                durability.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = durability.ensure_unassigned_notification_scope()

        set_value.assert_called_once_with(
            "Notification",
            durability.NOTIFICATION_NAME,
            "condition",
            durability.SCOPED_CONDITION,
            update_modified=False,
        )

        self.assertEqual(result["changed_count"], 1)
        self.assertTrue(result["ok"])
        self.assertTrue(result["present"])

    def test_already_scoped_condition_is_idempotent(self):
        with (
            mock.patch.object(
                durability.frappe.db,
                "exists",
                return_value=True,
            ),
            mock.patch.object(
                durability.frappe.db,
                "get_value",
                return_value=durability.SCOPED_CONDITION,
            ),
            mock.patch.object(
                durability.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = durability.ensure_unassigned_notification_scope()

        self.assertEqual(result["changed_count"], 0)
        self.assertTrue(result["ok"])
        self.assertTrue(result["present"])

        set_value.assert_not_called()

    def test_unexpected_condition_is_not_overwritten(self):
        with (
            mock.patch.object(
                durability.frappe.db,
                "exists",
                return_value=True,
            ),
            mock.patch.object(
                durability.frappe.db,
                "get_value",
                return_value='doc.status == "Open"',
            ),
            mock.patch.object(
                durability.frappe.db,
                "set_value",
            ) as set_value,
            mock.patch.object(
                durability.frappe,
                "throw",
                side_effect=RuntimeError(
                    "Notification Scope Conflict"
                ),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Notification Scope Conflict",
            ):
                durability.ensure_unassigned_notification_scope()

        set_value.assert_not_called()

    def test_failed_post_write_verification_raises(self):
        with (
            mock.patch.object(
                durability.frappe.db,
                "exists",
                return_value=True,
            ),
            mock.patch.object(
                durability.frappe.db,
                "get_value",
                side_effect=[
                    durability.LEGACY_CONDITION,
                    durability.LEGACY_CONDITION,
                ],
            ),
            mock.patch.object(
                durability.frappe.db,
                "set_value",
            ) as set_value,
            mock.patch.object(
                durability.frappe,
                "throw",
                side_effect=RuntimeError(
                    "Notification Scope Verification Failed"
                ),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Notification Scope Verification Failed",
            ):
                durability.ensure_unassigned_notification_scope()

        set_value.assert_called_once()


class TestUnassignedNotificationMigration(unittest.TestCase):

    def test_after_migrate_delegates_without_committing(self):
        expected = {
            "ok": True,
            "present": True,
            "changed_count": 0,
        }

        with (
            mock.patch.object(
                durability,
                "ensure_unassigned_notification_scope",
                return_value=expected,
            ) as ensure,
            mock.patch.object(
                durability.frappe.db,
                "commit",
            ) as commit,
        ):
            result = durability.after_migrate()

        self.assertEqual(result, expected)
        ensure.assert_called_once_with()
        commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
