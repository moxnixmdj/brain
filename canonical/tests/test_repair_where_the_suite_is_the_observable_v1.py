"""The suite-as-observable path must select exactly the tasks that have no JSON, and nothing else.

What is pinned here is the *selection*, which is the only part of this tool that is a decision. The
corpus numbers live in the receipt. The screen is deliberately not unit-tested: it is the tree's
existing machinery, and the receipt records the case where it disagrees with pytest.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import repair_where_the_suite_is_the_observable_v1 as tool  # noqa: E402


def corpus(root: pathlib.Path, json_names: list[str], test_names: list[str]) -> pathlib.Path:
    (root / "json_testcases").mkdir(parents=True, exist_ok=True)
    (root / "python_testcases").mkdir(parents=True, exist_ok=True)
    for name in json_names:
        (root / "json_testcases" / f"{name}.json").write_text("{}\n")
    for name in test_names:
        (root / "python_testcases" / f"test_{name}.py").write_text("def test1():\n    assert True\n")
    return root


class TestSelection:
    def test_only_tasks_without_json_are_selected(self, tmp_path: pathlib.Path) -> None:
        root = corpus(tmp_path, ["has_json"], ["has_json", "no_json"])
        assert tool.searchable_only_by_the_suite(root, ["has_json", "no_json"]) == ["no_json"]

    def test_a_task_with_no_test_file_is_not_selected(self, tmp_path: pathlib.Path) -> None:
        root = corpus(tmp_path, [], ["with_test"])
        assert tool.searchable_only_by_the_suite(root, ["with_test", "without_test"]) == ["with_test"]

    def test_a_json_task_is_never_sent_to_the_screen(self, tmp_path: pathlib.Path) -> None:
        root = corpus(tmp_path, ["a", "b"], ["a", "b"])
        assert tool.searchable_only_by_the_suite(root, ["a", "b"]) == []
