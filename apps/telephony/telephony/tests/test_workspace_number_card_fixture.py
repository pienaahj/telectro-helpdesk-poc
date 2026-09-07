import ast
import json
import unittest
from pathlib import Path


TELECTRO_WORKSPACES = (
    "TELECTRO-POC Ops",
    "TELECTRO-POC Coordinator",
)


def _telephony_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _number_card_names_from_hooks(hooks_path: Path) -> set[str]:
    tree = ast.parse(
        hooks_path.read_text(encoding="utf-8"),
        filename=str(hooks_path),
    )

    fixtures = None

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        if not any(
            isinstance(target, ast.Name)
            and target.id == "fixtures"
            for target in node.targets
        ):
            continue

        fixtures = ast.literal_eval(node.value)
        break

    if fixtures is None:
        raise AssertionError(
            "Could not find literal fixtures assignment in hooks.py"
        )

    for fixture in fixtures:
        if fixture.get("dt") != "Number Card":
            continue

        for fixture_filter in fixture.get("filters", []):
            if (
                len(fixture_filter) == 3
                and fixture_filter[0] == "name"
                and fixture_filter[1] == "in"
            ):
                return set(fixture_filter[2])

    raise AssertionError(
        "Could not find Number Card fixture boundary in hooks.py"
    )


class TestWorkspaceNumberCardFixtureClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = _telephony_root()

        workspaces = _load_json(
            root / "fixtures" / "workspace.json"
        )

        number_cards = _load_json(
            root / "fixtures" / "number_card.json"
        )

        cls.workspaces = {
            workspace["name"]: workspace
            for workspace in workspaces
        }

        cls.number_card_fixture_names = {
            card["name"]
            for card in number_cards
        }

        cls.number_card_hook_names = (
            _number_card_names_from_hooks(
                root / "hooks.py"
            )
        )

    def test_expected_workspaces_exist(self):
        for workspace_name in TELECTRO_WORKSPACES:
            with self.subTest(
                workspace=workspace_name
            ):
                self.assertIn(
                    workspace_name,
                    self.workspaces,
                )

    def test_workspace_number_card_targets_are_fixture_closed(self):
        for workspace_name in TELECTRO_WORKSPACES:
            workspace = self.workspaces[
                workspace_name
            ]

            targets = {
                row["number_card_name"]
                for row in workspace.get(
                    "number_cards",
                    [],
                )
            }

            with self.subTest(
                workspace=workspace_name
            ):
                self.assertTrue(
                    targets,
                    f"{workspace_name} has no Number Card references",
                )

                self.assertEqual(
                    targets
                    - self.number_card_fixture_names,
                    set(),
                    (
                        f"{workspace_name} references Number Cards "
                        "missing from number_card.json"
                    ),
                )

                self.assertEqual(
                    targets
                    - self.number_card_hook_names,
                    set(),
                    (
                        f"{workspace_name} references Number Cards "
                        "missing from the hooks.py export boundary"
                    ),
                )

    def test_workspace_content_number_card_labels_resolve(self):
        for workspace_name in TELECTRO_WORKSPACES:
            workspace = self.workspaces[
                workspace_name
            ]

            content = json.loads(
                workspace["content"]
            )

            content_labels = {
                item["data"]["number_card_name"]
                for item in content
                if item.get("type") == "number_card"
            }

            child_labels = {
                row["label"]
                for row in workspace.get(
                    "number_cards",
                    [],
                )
            }

            with self.subTest(
                workspace=workspace_name
            ):
                self.assertEqual(
                    content_labels - child_labels,
                    set(),
                    (
                        f"{workspace_name} Workspace content "
                        "contains unresolved Number Card labels"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
