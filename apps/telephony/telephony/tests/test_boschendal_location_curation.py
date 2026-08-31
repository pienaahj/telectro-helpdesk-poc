import unittest
from unittest import mock

from telephony.scripts import curate_boschendal_locations


EXPECTED_DELETE_IDS = [
    "kmzf0dc9b2317a2344d07e677e9",
    "kmz7740022d51c8b7519f005146",
    "kmza2fe6e4dcc77a94cac57db1d",
    "kmza6da13bad8aed33fb1ba5c1a",
    "kmz7d51c710dbfc0d26d9f8ba9f",
    "kmz53a0c0f660fdb87d0ee69f6b",
    "kmzaa1e41f9a6cd6b374f427556",
    "kmz3b44eb1480ddc4d6bb2145bd",
    "kmz19cc4be06e3ba12da6050428",
    "kmz29d8e0d37232a3617e47aa11",
    "kmz35ebc1f4f15ada414500008e",
    "kmza4206e9f13103e0aaee732f5",
    "kmzb2f75ffaab603e30b22bf630",
    "kmz3f848aa55bb24fb989e7245c",
    "kmz8b98dad2a414486f863f65d9",
    "kmz80fa5ff625f358e92dc23039",
    "kmz51559d992f9553bd0c141dfc",
    "kmz254a498fb7e21887080de43e",
    "kmz5d8928b1d4c24dff8331ade0",
    "kmz8ee2c1edc43029685c5cc9ce",
    "kmz09b376d1fd25c899929d7080",
    "kmz3440cc062308997c1ca22b73",
    "kmzb0d5a916d02abb12f4871437",
    "kmz6e84e0ea47d565f351105b86",
    "kmzc51d871585b5af5aa1f07c15",
    "kmz357196828b1aeab0b37579f7",
    "kmzcb3fa91f58c18a38fe4ba7f9",
    "kmzff2de50e0d0e7e8bd5ff76a0",
    "kmz3cd4d52b3498c69eced9718d",
]

EXPECTED_RENAME_UPDATES = [
    (
        "kmz583f46e72afe62354d5672f2",
        "Buildings: Untitled Path",
    ),
    (
        "kmzdec023e575cbcd31aedd0b5a",
        "Network Nodes: Untitled Path",
    ),
    (
        "kmzacd983cd88c586b844e1c73a",
        "Other: Untitled Path",
    ),
]


class TestBoschendalLocationCurationManifest(unittest.TestCase):
    def test_manifest_contract_is_exact(self):
        delete_manifest = (
            curate_boschendal_locations._delete_manifest()
        )

        delete_names = [
            row[0]
            for row in delete_manifest
        ]

        self.assertEqual(
            delete_names,
            EXPECTED_DELETE_IDS,
        )

        self.assertEqual(
            len(delete_manifest),
            29,
        )
        self.assertEqual(
            len(set(delete_names)),
            29,
        )

        self.assertEqual(
            len(
                curate_boschendal_locations.RENAME_PLAN
            ),
            3,
        )

        rename_targets = {
            row[0]: row[2]
            for row in (
                curate_boschendal_locations.RENAME_PLAN
            )
        }

        self.assertEqual(
            rename_targets,
            dict(EXPECTED_RENAME_UPDATES),
        )

        self.assertEqual(
            curate_boschendal_locations
            .EXPECTED_NUMBERED_AFTER,
            {
                "kmzd143a045e261af78e9a3fc96":
                    "Other: Splicebox (2)",
            },
        )

    def test_apply_uses_exact_destructive_contract(self):
        with mock.patch.object(
            curate_boschendal_locations,
            "frappe",
        ) as frappe_mock:
            curate_boschendal_locations._apply()

        self.assertEqual(
            frappe_mock.delete_doc.call_args_list,
            [
                mock.call(
                    "Location",
                    name,
                    ignore_permissions=True,
                )
                for name in EXPECTED_DELETE_IDS
            ],
        )

        self.assertEqual(
            frappe_mock.db.set_value.call_args_list,
            [
                mock.call(
                    "Location",
                    name,
                    "location_name",
                    target_label,
                    update_modified=False,
                )
                for (
                    name,
                    target_label,
                ) in EXPECTED_RENAME_UPDATES
            ],
        )


class TestBoschendalLocationCurationLifecycle(
    unittest.TestCase
):
    def test_dry_run_validates_without_writes(self):
        with (
            mock.patch.object(
                curate_boschendal_locations,
                "_preflight",
            ) as preflight,
            mock.patch.object(
                curate_boschendal_locations,
                "_apply",
            ) as apply_manifest,
            mock.patch.object(
                curate_boschendal_locations,
                "_postflight",
            ) as postflight,
            mock.patch.object(
                curate_boschendal_locations,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                curate_boschendal_locations.run(
                    dry_run=1,
                    commit=0,
                )
            )

        preflight.assert_called_once_with()
        apply_manifest.assert_not_called()
        postflight.assert_not_called()

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_not_called()

        self.assertEqual(
            result,
            {
                "ok": True,
                "dry_run": True,
                "delete_count": 29,
                "rename_count": 3,
            },
        )

    def test_uncommitted_write_mode_is_refused(self):
        with (
            mock.patch.object(
                curate_boschendal_locations,
                "_preflight",
            ) as preflight,
            mock.patch.object(
                curate_boschendal_locations,
                "_apply",
            ) as apply_manifest,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Refusing uncommitted write mode",
            ):
                curate_boschendal_locations.run(
                    dry_run=0,
                    commit=0,
                )

        preflight.assert_not_called()
        apply_manifest.assert_not_called()

    def test_commit_runs_complete_lifecycle(self):
        with (
            mock.patch.object(
                curate_boschendal_locations,
                "_preflight",
            ) as preflight,
            mock.patch.object(
                curate_boschendal_locations,
                "_apply",
            ) as apply_manifest,
            mock.patch.object(
                curate_boschendal_locations,
                "_postflight",
            ) as postflight,
            mock.patch.object(
                curate_boschendal_locations,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            result = (
                curate_boschendal_locations.run(
                    dry_run=1,
                    commit=1,
                )
            )

        preflight.assert_called_once_with()
        apply_manifest.assert_called_once_with()
        postflight.assert_called_once_with()

        frappe_mock.db.commit.assert_called_once_with()
        frappe_mock.db.rollback.assert_not_called()

        self.assertEqual(
            result,
            {
                "ok": True,
                "committed": True,
                "final_total": 269,
            },
        )

    def test_failed_postflight_rolls_back(self):
        with (
            mock.patch.object(
                curate_boschendal_locations,
                "_preflight",
            ) as preflight,
            mock.patch.object(
                curate_boschendal_locations,
                "_apply",
            ) as apply_manifest,
            mock.patch.object(
                curate_boschendal_locations,
                "_postflight",
                side_effect=RuntimeError(
                    "Boschendal postflight failure"
                ),
            ) as postflight,
            mock.patch.object(
                curate_boschendal_locations,
                "frappe",
            ) as frappe_mock,
        ):
            frappe_mock.local.site = "frontend"

            with self.assertRaisesRegex(
                RuntimeError,
                "Boschendal postflight failure",
            ):
                curate_boschendal_locations.run(
                    commit=1,
                )

        preflight.assert_called_once_with()
        apply_manifest.assert_called_once_with()
        postflight.assert_called_once_with()

        frappe_mock.db.commit.assert_not_called()
        frappe_mock.db.rollback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
