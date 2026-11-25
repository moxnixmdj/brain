"""Tests for the two-site instrument. Small fixtures pin the mechanism; real rows are measured separately."""
from __future__ import annotations

import pathlib
import subprocess
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(TOOLS.parents[1]) not in sys.path:
    sys.path.insert(0, str(TOOLS.parents[1]))

import a_relation_over_two_guards_v1 as pair  # noqa: E402
import the_demand_is_learned_from_the_run_v1 as single  # noqa: E402


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def _commit(repo: pathlib.Path, message: str) -> str:
    _git(repo, "add", "-A")
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "commit", "-q", "-m", message], check=True, capture_output=True)
    return _git(repo, "rev-parse", "HEAD").strip()


def _obs(line: int, col: int, node: str, *, is_none: bool) -> dict[str, object]:
    return {"line": line, "col": col, "node": node, "type": "object" if not is_none else "NoneType",
            "repr": "Falsy()" if not is_none else "None", "is_none": is_none,
            "is_bool": False, "truthy": not is_none, "zero": False, "empty_str": False,
            "is_str": False, "is_list": False, "is_dict": False, "is_tuple": False,
            "is_set": False, "is_int": False, "is_float": False, "has_len": False, "length": 0}


SITES = [
    {"line": 2, "col": 7, "text": "v", "test_line": 2},
    {"line": 6, "col": 7, "text": "v", "test_line": 6},
]


def test_root_grouping_keeps_attribute_expressions_together() -> None:
    assert pair.root_of("self.required") == "self"
    assert pair.root_of("args") == "args"


def test_a_shared_rule_requires_two_sites_and_a_passing_observation() -> None:
    observations = [
        _obs(2, 7, "t.py::fail", is_none=False),
        _obs(6, 7, "t.py::fail", is_none=False),
        _obs(6, 7, "t.py::pass", is_none=True),
    ]
    rules = pair.learn_groups(observations, {"t.py::fail"}, {"t.py::pass"}, SITES)
    assert rules and (rules[0]["feature"], rules[0]["polarity"]) in {
        ("is_none", False), ("truthy", True)}, rules[0]
    assert len(rules[0]["sites"]) == 2 and rules[0]["pass_mismatches"] == 0
    alone = pair.learn_groups(observations, {"t.py::fail"}, {"t.py::pass"}, SITES[:1])
    assert alone == [], "a single site cannot enter a two-site test"


def test_replace_many_changes_both_spans_and_refuses_a_stale_one() -> None:
    source = "def f(v):\n    if v:\n        return 1\n    return 0\n"
    edits = [{"line": 2, "col": 7, "text": "v", "expression": "not ((v) is None)"}]
    assert pair.replace_many(source, edits) is not None
    edits.append({"line": 999, "col": 7, "text": "v", "expression": "True"})
    assert pair.replace_many(source, edits) is None


SOURCE = '''from __future__ import annotations


def inner(v):
    if v:
        return 1
    return 0


def outer(v):
    if v:
        return inner(v) + 1
    return 0
'''

TESTS = '''from proj.core import outer


class Falsy:
    def __bool__(self):
        return False


def test_none():
    assert outer(None) == 0


def test_falsy():
    assert outer(Falsy()) == 2
'''


def test_a_two_frame_fix_is_learned_and_verified(tmp_path: pathlib.Path) -> None:
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
    commit = _commit(repo, "accept falsey values in both frames")
    row = pair.explore(repo, {"repo": "proj", "commit": commit, "test": "tests/test_core.py",
                              "sources": ["proj/core.py"]}, seconds=90)
    assert row["stage"] == "VERIFIED", row
    assert row["control"]["accepted"] is True
    assert len(row["edits"]) == 2
    assert row["flipped"] == ["tests/test_core.py::test_falsy"]
