import unittest
from unittest import mock

from telephony.setup import (
    location_customer_durability,
)


class TestLocationCustomerOwnershipVerification(
    unittest.TestCase
):
    def test_blank_campus_owner_is_reconcilable(
        self,
    ):
        relationships = [
            {
                "name": "Customer B",
                "custom_default_campus":
                    "Boschendal",
            }
        ]

        campus = {
            "name": "Boschendal",
            "parent_location": "Pilot Sites",
            "is_group": 1,
            "custom_customer": None,
        }

        with (
            mock.patch.object(
                location_customer_durability,
                "_get_default_campus_relationships",
                return_value=relationships,
            ),
            mock.patch.object(
                location_customer_durability,
                "_get_campus_state",
                return_value=campus,
            ),
            mock.patch.object(
                location_customer_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                location_customer_durability
                .verify_location_customer_ownership()
            )

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["reconcilable_count"],
            1,
        )
        self.assertEqual(
            result["reconcilable"],
            [
                {
                    "campus": "Boschendal",
                    "customer": "Customer B",
                }
            ],
        )
        self.assertEqual(
            result["issue_count"],
            0,
        )

    def test_conflicting_campus_owner_is_reported(
        self,
    ):
        relationships = [
            {
                "name": "Customer B",
                "custom_default_campus":
                    "Boschendal",
            }
        ]

        campus = {
            "name": "Boschendal",
            "parent_location": "Pilot Sites",
            "is_group": 1,
            "custom_customer": "Customer A",
        }

        with (
            mock.patch.object(
                location_customer_durability,
                "_get_default_campus_relationships",
                return_value=relationships,
            ),
            mock.patch.object(
                location_customer_durability,
                "_get_campus_state",
                return_value=campus,
            ),
            mock.patch.object(
                location_customer_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                location_customer_durability
                .verify_location_customer_ownership()
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["reconcilable_count"],
            0,
        )
        self.assertEqual(
            result["issue_count"],
            1,
        )
        self.assertEqual(
            result["issues"],
            [
                {
                    "type":
                        "campus_customer_conflict",
                    "campus": "Boschendal",
                    "expected_customer":
                        "Customer B",
                    "actual_customer":
                        "Customer A",
                }
            ],
        )
    def test_duplicate_default_campus_is_reported_as_ambiguous(
        self,
    ):
        relationships = [
            {
                "name": "Customer A",
                "custom_default_campus":
                    "Boschendal",
            },
            {
                "name": "Customer B",
                "custom_default_campus":
                    "Boschendal",
            },
        ]

        with (
            mock.patch.object(
                location_customer_durability,
                "_get_default_campus_relationships",
                return_value=relationships,
            ),
            mock.patch.object(
                location_customer_durability,
                "_get_campus_state",
            ) as get_campus_state,
            mock.patch.object(
                location_customer_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                location_customer_durability
                .verify_location_customer_ownership()
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["reconcilable_count"],
            0,
        )
        self.assertEqual(
            result["issue_count"],
            1,
        )
        self.assertEqual(
            result["issues"],
            [
                {
                    "type":
                        "ambiguous_default_campus_ownership",
                    "campus": "Boschendal",
                    "customers": (
                        "Customer A",
                        "Customer B",
                    ),
                }
            ],
        )

        get_campus_state.assert_not_called()
    def test_missing_default_campus_location_is_reported(
        self,
    ):
        relationships = [
            {
                "name": "Customer B",
                "custom_default_campus":
                    "Missing Campus",
            }
        ]

        with (
            mock.patch.object(
                location_customer_durability,
                "_get_default_campus_relationships",
                return_value=relationships,
            ),
            mock.patch.object(
                location_customer_durability,
                "_get_campus_state",
                return_value=None,
            ),
            mock.patch.object(
                location_customer_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                location_customer_durability
                .verify_location_customer_ownership()
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["reconcilable_count"],
            0,
        )
        self.assertEqual(
            result["issues"],
            [
                {
                    "type":
                        "missing_default_campus_location",
                    "campus": "Missing Campus",
                    "customer": "Customer B",
                }
            ],
        )
    def test_invalid_default_campus_location_is_reported(
        self,
    ):
        relationships = [
            {
                "name": "Customer B",
                "custom_default_campus":
                    "Boschendal",
            }
        ]

        campus = {
            "name": "Boschendal",
            "parent_location": "Not Pilot Sites",
            "is_group": 0,
            "custom_customer": None,
        }

        with (
            mock.patch.object(
                location_customer_durability,
                "_get_default_campus_relationships",
                return_value=relationships,
            ),
            mock.patch.object(
                location_customer_durability,
                "_get_campus_state",
                return_value=campus,
            ),
            mock.patch.object(
                location_customer_durability,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                location_customer_durability
                .verify_location_customer_ownership()
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["reconcilable_count"],
            0,
        )
        self.assertEqual(
            result["issues"],
            [
                {
                    "type":
                        "invalid_default_campus_location",
                    "campus": "Boschendal",
                    "customer": "Customer B",
                    "parent_location":
                        "Not Pilot Sites",
                    "is_group": 0,
                }
            ],
        )


class TestLocationCustomerOwnershipReconciliation(
    unittest.TestCase
):
    def test_blank_owner_is_established_from_default_campus(
        self,
    ):
        before = {
            "ok": True,
            "site": "frontend",
            "relationship_count": 1,
            "verified_count": 0,
            "reconcilable_count": 1,
            "issue_count": 0,
            "verified": [],
            "reconcilable": [
                {
                    "campus": "Boschendal",
                    "customer": "Customer B",
                }
            ],
            "issues": [],
        }

        after = {
            "ok": True,
            "site": "frontend",
            "relationship_count": 1,
            "verified_count": 1,
            "reconcilable_count": 0,
            "issue_count": 0,
            "verified": [
                {
                    "campus": "Boschendal",
                    "customer": "Customer B",
                }
            ],
            "reconcilable": [],
            "issues": [],
        }

        with (
            mock.patch.object(
                location_customer_durability,
                "verify_location_customer_ownership",
                side_effect=[
                    before,
                    after,
                ],
            ),
            mock.patch.object(
                location_customer_durability.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = (
                location_customer_durability
                .ensure_location_customer_ownership()
            )

        set_value.assert_called_once_with(
            "Location",
            "Boschendal",
            "custom_customer",
            "Customer B",
            update_modified=False,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["changed_count"],
            1,
        )
        self.assertEqual(
            result["changed"],
            [
                {
                    "action":
                        "establish_customer_ownership",
                    "campus": "Boschendal",
                    "customer": "Customer B",
                }
            ],
        )

    def test_conflict_stops_reconciliation_without_writes(
        self,
    ):
        before = {
            "ok": False,
            "site": "frontend",
            "relationship_count": 1,
            "verified_count": 0,
            "reconcilable_count": 0,
            "issue_count": 1,
            "verified": [],
            "reconcilable": [],
            "issues": [
                {
                    "type":
                        "campus_customer_conflict",
                    "campus": "Boschendal",
                    "expected_customer":
                        "Customer B",
                    "actual_customer":
                        "Customer A",
                }
            ],
        }

        with (
            mock.patch.object(
                location_customer_durability,
                "verify_location_customer_ownership",
                return_value=before,
            ),
            mock.patch.object(
                location_customer_durability.frappe,
                "throw",
                side_effect=ValueError(
                    "ownership conflict"
                ),
            ),
            mock.patch.object(
                location_customer_durability.frappe.db,
                "set_value",
            ) as set_value,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "ownership conflict",
            ):
                (
                    location_customer_durability
                    .ensure_location_customer_ownership()
                )

        set_value.assert_not_called()

    def test_existing_correct_owner_is_not_rewritten(
        self,
    ):
        verification = {
            "ok": True,
            "site": "frontend",
            "relationship_count": 1,
            "verified_count": 1,
            "reconcilable_count": 0,
            "issue_count": 0,
            "verified": [
                {
                    "campus": "Boschendal",
                    "customer": "Customer B",
                }
            ],
            "reconcilable": [],
            "issues": [],
        }

        with (
            mock.patch.object(
                location_customer_durability,
                "verify_location_customer_ownership",
                side_effect=[
                    verification,
                    verification,
                ],
            ),
            mock.patch.object(
                location_customer_durability.frappe.db,
                "set_value",
            ) as set_value,
        ):
            result = (
                location_customer_durability
                .ensure_location_customer_ownership()
            )

        set_value.assert_not_called()

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["changed_count"],
            0,
        )
        self.assertEqual(
            result["changed"],
            [],
        )
    @mock.patch.object(
        location_customer_durability,
        "ensure_location_customer_ownership",
    )
    def test_apply_commits_successful_reconciliation(
        self,
        ensure_ownership,
    ):
        expected = {
            "ok": True,
            "site": "frontend",
            "changed_count": 1,
            "changed": [
                {
                    "action":
                        "establish_customer_ownership",
                    "campus": "Boschendal",
                    "customer": "Customer B",
                }
            ],
            "verification": {},
        }

        ensure_ownership.return_value = expected

        with (
            mock.patch.object(
                location_customer_durability.frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                location_customer_durability.frappe.db,
                "rollback",
            ) as rollback,
        ):
            result = (
                location_customer_durability
                .apply_location_customer_ownership()
            )

        ensure_ownership.assert_called_once_with()
        commit.assert_called_once_with()
        rollback.assert_not_called()

        self.assertEqual(
            result,
            expected,
        )

    @mock.patch.object(
        location_customer_durability,
        "ensure_location_customer_ownership",
    )
    def test_apply_rolls_back_failed_reconciliation(
        self,
        ensure_ownership,
    ):
        ensure_ownership.side_effect = ValueError(
            "ownership conflict"
        )

        with (
            mock.patch.object(
                location_customer_durability.frappe.db,
                "commit",
            ) as commit,
            mock.patch.object(
                location_customer_durability.frappe.db,
                "rollback",
            ) as rollback,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "ownership conflict",
            ):
                (
                    location_customer_durability
                    .apply_location_customer_ownership()
                )

        rollback.assert_called_once_with()
        commit.assert_not_called()
    @mock.patch.object(
        location_customer_durability,
        "ensure_location_customer_ownership",
    )
    def test_after_migrate_ensures_and_logs_ownership(
        self,
        ensure_ownership,
    ):
        expected = {
            "ok": True,
            "site": "frontend",
            "changed_count": 1,
            "changed": [
                {
                    "action":
                        "establish_customer_ownership",
                    "campus": "Boschendal",
                    "customer": "Customer B",
                }
            ],
            "verification": {},
        }

        ensure_ownership.return_value = expected

        logger = mock.Mock()

        with mock.patch.object(
            location_customer_durability.frappe,
            "logger",
            return_value=logger,
        ) as frappe_logger:
            result = (
                location_customer_durability
                .after_migrate()
            )

        ensure_ownership.assert_called_once_with()

        frappe_logger.assert_called_once_with(
            "telephony",
        )

        logger.info.assert_called_once_with(
            "Location Customer ownership verified: %s changed",
            1,
        )

        self.assertEqual(
            result,
            expected,
        )
