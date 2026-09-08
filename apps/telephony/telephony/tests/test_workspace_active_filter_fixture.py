import json
import unittest
from pathlib import Path


ACTIVE_STATUSES = ["Open", "Replied"]

WORKSPACE_ACTIVE_SHORTCUTS = {
    "TELECTRO-POC Coordinator": "All Tickets",
    "TELECTRO-POC Ops": "All Active Tickets",
}


def _telephony_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_workspaces():
    path = _telephony_root() / "fixtures" / "workspace.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _find_workspace(workspaces, name):
    for workspace in workspaces:
        if workspace.get("name") == name:
            return workspace

    raise AssertionError(f"Workspace not found: {name}")


def _find_row(rows, label):
    for row in rows:
        if row.get("label") == label:
            return row

    raise AssertionError(f"Workspace row not found: {label}")


class TestWorkspaceActiveFilterFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspaces = _load_workspaces()

    def test_unclaimed_active_ticket_filters_use_active_status_contract(self):
        expected_filters = [
            [
                "HD Ticket",
                "_assign",
                "in",
                [None, "[]"],
                False,
            ],
            [
                "HD Ticket",
                "status",
                "in",
                ACTIVE_STATUSES,
                False,
            ],
        ]

        for workspace_name in WORKSPACE_ACTIVE_SHORTCUTS:
            workspace = _find_workspace(
                self.workspaces,
                workspace_name,
            )

            row = _find_row(
                workspace.get("quick_lists", []),
                "Unclaimed Active Tickets",
            )

            actual_filters = json.loads(
                row["quick_list_filter"]
            )

            with self.subTest(workspace=workspace_name):
                self.assertEqual(
                    actual_filters,
                    expected_filters,
                )

    def test_active_ticket_shortcuts_use_active_status_contract(self):
        expected_status_filter = [
            "HD Ticket",
            "status",
            "in",
            ACTIVE_STATUSES,
            False,
        ]

        for (
            workspace_name,
            shortcut_label,
        ) in WORKSPACE_ACTIVE_SHORTCUTS.items():
            workspace = _find_workspace(
                self.workspaces,
                workspace_name,
            )

            shortcut = _find_row(
                workspace.get("shortcuts", []),
                shortcut_label,
            )

            actual_filters = json.loads(
                shortcut["stats_filter"]
            )

            with self.subTest(
                workspace=workspace_name,
                shortcut=shortcut_label,
            ):
                self.assertIn(
                    expected_status_filter,
                    actual_filters,
                )

    def test_ops_all_active_ticket_filter_is_status_only(self):
        workspace = _find_workspace(
            self.workspaces,
            "TELECTRO-POC Ops",
        )

        shortcut = _find_row(
            workspace.get("shortcuts", []),
            "All Active Tickets",
        )

        actual_filters = json.loads(
            shortcut["stats_filter"]
        )

        self.assertEqual(
            actual_filters,
            [
                [
                    "HD Ticket",
                    "status",
                    "in",
                    ACTIVE_STATUSES,
                    False,
                ]
            ],
        )


if __name__ == "__main__":
    unittest.main()
