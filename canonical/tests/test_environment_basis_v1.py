"""Round 14: the environment-as-knowledge-base claim, and the instrument that must be able to fire.

A negative result from an instrument never shown to fire is worthless, so the end-to-end test here builds a
real module whose missing check requires a term the narrow supply CANNOT produce (a method on the live value,
with no import in the file) and asserts that the widened supply finds it, separates on it, and solves with
one execution. Only then does the zero on the 17-commit corpus mean anything.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import environment_basis_v1 as B  # noqa: E402

MODULE = '''def check_paths(paths):
    """Refuse parent-directory indicators. An all-caps name is not refused -- that is the bug."""
    for part in paths:
        if ".." in part:
            raise ValueError("parent directory indicators are not allowed")
    return paths
'''

TEST = '''import pytest
from mod import check_paths


@pytest.mark.parametrize("paths", [["ok"], ["BAD"]])
def test_check(paths):
    if paths == ["BAD"]:
        with pytest.raises(ValueError):
            check_paths(paths)
        return
    assert check_paths(paths) == paths
'''


def _repo(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(MODULE, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def test_templates_are_legal_and_side_effect_free():
    shapes = B._shape("BAD")
    assert "(x).isupper()" in shapes
    assert all("._" not in part for part in shapes)
    assert all("write" not in part and "open" not in part for part in shapes)


def test_separation_is_decided_by_evaluation_not_by_reading():
    found = B.environment_terms(["BAD"], ["ok", "fine"], MODULE)
    assert "(x).isupper()" in found["terms"]
    assert found["evaluations"] > 0


def test_a_term_true_on_a_passing_value_is_rejected():
    found = B.environment_terms(["BAD"], ["ALSOBAD"], MODULE)
    assert "(x).isupper()" not in found["terms"]


def test_the_widened_supply_solves_what_the_narrow_supply_cannot(tmp_path):
    tree = _repo(tmp_path)
    task = {"repo": "t/t", "sha": "0" * 40, "parent_tree": str(tree), "source": "src/mod.py",
            "test": "tests/test_mod.py", "failed_nodes": ["tests/test_mod.py::test_check[paths1]"]}
    row = B.repair_with_basis(task)
    # the file imports nothing, so round 11's supply is empty and this solve can only come from the widening
    assert row["narrow_terms"] == 0
    assert row["solved"] is True
    assert row["state"] == B.SOLVED
    assert row["term"].endswith(".isupper()") and "(" in row["term"]
    assert row["trials"] == 1


def test_the_union_keeps_the_narrow_supply_it_is_measured_against(tmp_path):
    tree = _repo(tmp_path)
    task = {"repo": "t/t", "sha": "0" * 40, "parent_tree": str(tree), "source": "src/mod.py",
            "test": "tests/test_mod.py", "failed_nodes": ["tests/test_mod.py::test_check[paths1]"]}
    row = B.repair_with_basis(task)
    assert row["narrow_terms"] == 0 and row["basis_terms"]
    assert all(isinstance(term, str) and term for term in row["basis_terms"])


def test_a_task_without_a_differential_refuses_by_name(tmp_path):
    tree = _repo(tmp_path)
    task = {"repo": "t/t", "sha": "0" * 40, "parent_tree": str(tree), "source": "src/mod.py",
            "test": "tests/test_mod.py", "failed_nodes": []}
    row = B.repair_with_basis(task)
    assert row["state"] == B.REFUSED_NO_PARTITION
    assert row["solved"] is False


def test_headline_carries_the_denominator_and_the_cost():
    report = {"rows": [{"repo": "a/b", "sha": "0" * 8, "solved": True, "term": "x.isupper()",
                        "at_line": 3, "trials": 1}],
              "totals": {"tasks": 1, "solved": 1, "basis_terms_total": 1, "templates_considered": 87,
                         "evaluations": 91, "test_executions": 1, "states": {B.SOLVED: 1}}}
    text = B.headline(report)
    assert "1 real fix commits" in text and "87 templates" in text and "1 execution" in text
