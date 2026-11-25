"""Tests for the run-learned demand instrument, not evidence of capability.

The mechanism must not confuse a feature that merely appears in a failing run with
one that *separates* failing from passing runs, and the judge must still refuse a
partial flip. One small fixture pins the end-to-end path; the 45 real commits are
measured separately in the receipt, not in this test file.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(TOOLS.parents[1]) not in sys.path:
    sys.path.insert(0, str(TOOLS.parents[1]))

import the_demand_is_learned_from_the_run_v1 as learned  # noqa: E402
import the_relation_not_the_value_v1 as prior  # noqa: E402


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def _commit(repo: pathlib.Path, message: str) -> str:
    _git(repo, "add", "-A")
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "commit", "-q", "-m", message], check=True, capture_output=True)
    return _git(repo, "rev-parse", "HEAD").strip()


def _observation(node: str, *, is_none: bool, truthy: bool = False) -> dict[str, object]:
    return {"line": 3, "col": 8, "node": node, "type": "object" if not is_none else "NoneType",
            "repr": "Falsy()" if not is_none else "None", "is_none": is_none,
            "is_bool": False, "truthy": truthy, "zero": False, "empty_str": False,
            "is_str": False, "is_list": False, "is_dict": False, "is_tuple": False,
            "is_set": False, "is_int": False, "is_float": False, "has_len": False,
            "length": 0}


SITE = [{"line": 3, "col": 8, "text": "v", "test_line": 3}]


def test_a_strict_separating_feature_is_learned_and_a_merely_present_one_is_not() -> None:
    observations = [
        _observation("t1.py::fail", is_none=False),
        _observation("t1.py::pass", is_none=True),
    ]
    rules = learned.learn(observations, {"t1.py::fail"}, {"t1.py::pass"}, SITE)
    assert rules, "a strict separator exists and must be found"
    assert rules[0]["feature"] == "is_none" and rules[0]["polarity"] is False
    assert rules[0]["strict"] is True and rules[0]["gain"] == 1
    assert all(rule["feature"] != "is_bool" for rule in rules), \
        "a feature true in neither group is not a demand"


def test_a_rule_needs_a_passing_observation_to_claim_separation() -> None:
    """A guard seen only in the failing run cannot distinguish fail from pass."""
    rules = learned.learn([_observation("t1.py::fail", is_none=False)],
                          {"t1.py::fail"}, {"t1.py::pass"}, SITE)
    assert rules == []


def test_the_learned_rule_compiles_and_is_applied_to_only_one_span() -> None:
    source = "def pick(v):\n    if v:\n        return 1\n    return 2\n"
    candidate = {"line": 2, "col": 7, "text": "v", "feature": "is_none", "polarity": False}
    expression = learned.compile_rule(candidate)
    assert expression == "not (((v) is None))"
    patched = learned.replace(source, candidate, expression)
    assert patched is not None
    assert "if (not (((v) is None))):" in patched
    assert learned.replace(source, {**candidate, "text": "other"}, expression) is None


def test_the_judge_still_refuses_a_partial_witness_and_a_broken_passing_test() -> None:
    baseline = {"a": "FAILED", "b": "FAILED", "c": "PASSED"}
    partial = learned.judge(baseline, {"a": "PASSED", "b": "FAILED", "c": "PASSED"},
                            ["a", "b"])
    assert partial[0] is False and partial[1].startswith("PARTIAL_FLIP")
    broken = learned.judge(baseline, {"a": "PASSED", "b": "PASSED", "c": "FAILED"}, [])
    assert broken[0] is False and "BROKE" in broken[1]


def test_the_receipt_cannot_claim_a_new_repair_on_a_row_the_fixed_engine_solved(tmp_path) -> None:
    """L4 is counted only on rows the earlier fixed-form engine missed."""
    receipt = {"rows": [{"commit": "abc1234567", "stage": "VERIFIED"}]}
    missed = {"def0000000"}
    assert sum(row.get("stage") == "VERIFIED" and str(row.get("commit", ""))[:10] in missed
               for row in receipt["rows"]) == 0


SOURCE = '''from __future__ import annotations


def pick(v):
    if v:
        return 1
    return 2
'''

TESTS = '''from proj.core import pick


class Falsy:
    def __bool__(self):
        return False


def test_none():
    assert pick(None) == 2


def test_falsy():
    assert pick(Falsy()) == 1
'''


def test_an_end_to_end_run_learns_existence_from_the_two_tests(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "proj"
    (repo / "proj").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "proj" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "proj" / "core.py").write_text(SOURCE, encoding="utf-8")
    (repo / "tests" / "test_core.py").write_text(TESTS, encoding="utf-8")
    _git(repo, "init", "-q")
    _commit(repo, "parent")

    (repo / "proj" / "core.py").write_text(
        SOURCE.replace("if v:", "if v is not None:"), encoding="utf-8")
    (repo / "tests" / "test_core.py").write_text(TESTS, encoding="utf-8")
    commit = _commit(repo, "accept a falsey object")
    row = learned.explore(repo, {"repo": "proj", "commit": commit,
                                 "test": "tests/test_core.py", "sources": ["proj/core.py"]},
                          seconds=90)
    assert row["stage"] == "VERIFIED", row
    assert row["control"]["accepted"] is True
    assert row["rule"]["feature"] == "is_none", row.get("learned")
    assert row["rule"]["polarity"] is False
    assert row["flipped"] == ["tests/test_core.py::test_falsy"]
