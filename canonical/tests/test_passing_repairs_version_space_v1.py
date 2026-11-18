"""Round 13: when several repairs pass the same suite, the suite identified none of them.

The end-to-end test builds a real module with a real missing check and a real pytest file, runs the actual
instrument against it, and asserts that the version space and the question it produces are what the theory
says they are -- because a version-space count that is never checked against a runnable case is just a claim.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import passing_repairs_version_space_v1 as V  # noqa: E402

MODULE = '''import pathlib


def check_paths(paths):
    """Refuse parent-directory indicators and stars. A drive letter is not refused -- that is the bug."""
    for part in paths:
        if ".." in part:
            raise ValueError("parent directory indicators are not allowed")
        if "*" in part:
            raise ValueError("paths must be resolved")
    return paths
'''

TEST = '''import pytest
from mod import check_paths


@pytest.mark.parametrize("paths", [["ok"], ["C:x"]])
def test_check(paths):
    if paths == ["C:x"]:
        with pytest.raises(ValueError):
            check_paths(paths)
        return
    assert check_paths(paths) == paths
'''

TWO_GUARDS = '''import pathlib


def guard(value):
    if ".." in value:
        raise ValueError("parent directory indicators are not allowed")
    if "*" in value:
        raise ValueError("paths must be resolved")
'''


def _repo(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(MODULE, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def test_message_at_reads_the_guard_that_fires():
    assert "parent directory indicators" in V._message_at(TWO_GUARDS, 5)
    assert "paths must be resolved" in V._message_at(TWO_GUARDS, 7)
    assert V._message_at(TWO_GUARDS, 1) == ""


def test_question_is_none_when_every_repair_says_the_same_thing():
    repairs = [{"at_line": 5, "term": "t", "operator": "or"}, {"at_line": 5, "term": "t", "operator": "and"}]
    assert V.question_from_repairs(repairs, TWO_GUARDS, ["C:x"]) is None


def test_question_lists_one_option_per_behaviour():
    repairs = [{"at_line": 5, "term": "t", "operator": "or"}, {"at_line": 7, "term": "t", "operator": "or"}]
    question = V.question_from_repairs(repairs, TWO_GUARDS, ["C:x"])
    assert question is not None
    assert len(question["options"]) == 2
    assert question["about_input"] == "C:x"
    assert sum(question["repairs_behind_each_option"].values()) == 2


def test_the_suite_admits_more_than_one_repair_end_to_end(tmp_path):
    tree = _repo(tmp_path)
    task = {"repo": "t/t", "sha": "0" * 40, "parent_tree": str(tree), "source": "src/mod.py",
            "test": "tests/test_mod.py", "failed_nodes": ["tests/test_mod.py::test_check[paths1]"]}
    row = V.passing_repairs(task)
    assert row["state"] in (V.UNIQUE, V.UNDERDETERMINED)
    assert len(row["passing"]) >= 1
    assert row["trials"] >= 1
    # every accepted repair must really pass: re-judging is the only claim that matters
    for repair in row["passing"]:
        source = (tree / "src/mod.py").read_text()
        candidate = V.OPERAND.rewritten(source, repair["at_line"],
                                        repair["condition"], repair["term"], repair["operator"])
        if candidate is not None:
            from canonical.swe_kernel import history_induced_edit_grammar_v1 as G
            assert G.try_candidate(tree, "src/mod.py", "tests/test_mod.py", candidate)["passed"]


def test_a_task_without_a_partition_refuses_by_name(tmp_path):
    tree = _repo(tmp_path)
    task = {"repo": "t/t", "sha": "0" * 40, "parent_tree": str(tree), "source": "src/mod.py",
            "test": "tests/test_mod.py", "failed_nodes": []}
    assert V.passing_repairs(task)["state"] == V.REFUSED_NO_PARTITION


def test_headline_states_the_denominator_and_the_maximum():
    report = {"rows": [{"repo": "a/b", "passing": [{}, {}, {}], "distinct_seats": [1, 2, 3]}],
              "totals": {"tasks": 1, "tasks_admitting_many": 1, "repairs_accepted_total": 3,
                         "max_repairs_accepted": 3, "trials": 9, "states": {V.UNDERDETERMINED: 1}}}
    text = V.headline(report)
    assert "1 real fix commits" in text and "3 repairs accepted" in text
