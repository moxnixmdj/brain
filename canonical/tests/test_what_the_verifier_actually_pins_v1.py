"""Round 15: a passing suite pins only the part of a change its assertions can observe.

The end-to-end fixture is built so that one fix contains three kinds of part at once -- a behavioural part
the test requires, a behavioural part no test observes, and a cosmetic part -- and asserts the instrument
separates them. Without that, the corpus number would be a number produced by an instrument nobody saw fire.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as P  # noqa: E402

DEFECTIVE = '''def check(paths):
    for part in paths:
        if ".." in part:
            return False
    return True
'''

REPAIRED = '''def check(paths):
    """Refuse parent-directory indicators and drive letters."""
    for part in paths:
        if ".." in part:
            return False
        if part[1:2] == ":":
            return False
    return True


def scratch(paths):
    for part in paths:
        if len(part) > 100:
            return False
    return True
'''

TEST = '''import pytest
from mod import check


@pytest.mark.parametrize("paths", [["ok"], ["..x"], ["C:x"]])
def test_check(paths):
    if paths == ["ok"]:
        assert check(paths) is True
        return
    assert check(paths) is False
'''

TYPING = '''from __future__ import annotations
from typing_extensions import Self


class Thing:
    def copy(self) -> Self:
        return Thing()
'''

USED = '''from pathlib import Path


def drive(path: str) -> str:
    return Path(path).drive
'''


def _repo(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(DEFECTIVE, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def test_hunks_split_the_change_into_its_parts():
    parts = P.hunks(DEFECTIVE, REPAIRED)
    assert len(parts) >= 2
    assert all({"tag", "old", "new", "added", "removed"} <= set(part) for part in parts)


def test_reverting_every_part_restores_the_defective_text():
    parts = P.hunks(DEFECTIVE, REPAIRED)
    text = REPAIRED
    for part in reversed(parts):
        text = P.revert(text, DEFECTIVE, part)
    assert text.splitlines() == DEFECTIVE.splitlines()


def test_a_docstring_only_part_is_not_behavioural():
    parts = P.hunks(DEFECTIVE, REPAIRED)
    docstring_parts = [part for part in parts if "docstring" in part["added"] or '"""' in part["added"]]
    assert docstring_parts, "the fixture must contain the docstring part"
    assert not any(P.is_behavioural(REPAIRED, part) for part in docstring_parts)


def test_an_annotation_only_import_is_not_runtime_behaviour():
    parts = P.hunks("from typing import Any\n", TYPING)
    typing_parts = [part for part in parts if "typing_extensions" in part["added"]]
    assert typing_parts and P.typing_only(TYPING, typing_parts[0])
    used = P.hunks("import os\n", USED)
    assert not any(P.typing_only(USED, part) for part in used)


def test_the_instrument_separates_pinned_observed_and_cosmetic_parts(tmp_path):
    tree = _repo(tmp_path)
    grammar = [{"sha": "a" * 40, "source": "src/mod.py", "defective": DEFECTIVE, "repaired": REPAIRED}]
    task = {"repo": "t/t", "sha": "a" * 40, "parent_tree": str(tree), "source": "src/mod.py",
            "test": "tests/test_mod.py", "failed_nodes": ["tests/test_mod.py::test_check[paths2]"]}
    row = P.pin_task(task, grammar)
    assert row["state"] == P.PARTIALLY_PINNED
    assert row["behavioural_pinned"] >= 1                 # the drive-letter guard is required by the test
    assert row["unpinned_behavioural"] >= 1               # the >100 guard is observed by nothing
    # the tree must be restored exactly, or every later measurement is a lie
    assert (tree / "src" / "mod.py").read_text(encoding="utf-8") == DEFECTIVE


def test_a_task_whose_controls_do_not_hold_is_refused_by_name(tmp_path):
    tree = _repo(tmp_path)
    # a "fix" identical to the defect: the parent cannot fail, so nothing can be attributed
    grammar = [{"sha": "b" * 40, "source": "src/mod.py", "defective": DEFECTIVE, "repaired": DEFECTIVE}]
    task = {"repo": "t/t", "sha": "b" * 40, "parent_tree": str(tree), "source": "src/mod.py",
            "test": "tests/test_mod.py", "failed_nodes": []}
    assert P.pin_task(task, grammar)["state"] == P.REFUSED_CONTROL


def test_headline_carries_the_denominator_and_the_share():
    report = {"rows": [], "totals": {"tasks_with_controls": 16, "suite_executions": 77, "parts": 45,
                                     "parts_pinned": 30, "behavioural_parts": 42, "behavioural_pinned": 30,
                                     "pinned_share_of_behavioural": 0.714, "states": {P.FULLY_PINNED: 10}}}
    text = P.headline(report)
    assert "16 real fixes" in text and "0.714" in text and "77 executions" in text
