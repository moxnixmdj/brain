"""The round's own tests: the probe must not change behaviour, and the judge must accept the answer key.

Three defects from earlier rounds are pinned here as tests, because each one read like a fact about the
world rather than a bug in the instrument:

  * an injected import above `from __future__ import annotations` makes the module unimportable, and the
    run then produces no verdicts at all -- indistinguishable from "the guard was never reached";
  * a probe written to `brain_probe` (no `.py`) is never importable, and the record is silently empty;
  * a criterion that demands every test failing on the parent pass reports "not repaired" for the
    human's own fix wherever the parent carries an unrelated red. The human's edit is therefore run as
    a control on every row, and a row whose control is rejected refuses rather than counts.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(TOOLS.parents[1]) not in sys.path:
    sys.path.insert(0, str(TOOLS.parents[1]))

import the_relation_not_the_value_v1 as relation  # noqa: E402


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def _commit(repo: pathlib.Path, message: str) -> str:
    _git(repo, "add", "-A")
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "commit", "-q", "-m", message], check=True, capture_output=True)
    return _git(repo, "rev-parse", "HEAD").strip()


SOURCE = '''from __future__ import annotations


def pick(v):
    if v:
        return 1
    return 2
'''


def test_the_probe_import_lands_after_the_future_import() -> None:
    """A probe import above `from __future__` is a SyntaxError, and the empty run looks like a fact."""
    source = '"""doc"""\nfrom __future__ import annotations\n\nX = 1\n'
    line = relation._insertion_line(source)
    assert line == 2, line
    instrumented = relation.instrument(source, [])
    assert instrumented is not None
    import ast

    ast.parse(instrumented)  # would raise above `from __future__`
    assert instrumented.splitlines()[2].startswith("from brain_probe import probe")


def test_guards_are_maximal_names_inside_if_tests() -> None:
    source = "def f(a, b):\n    if a.converter and not isinstance(a.converter, int):\n        return b\n"
    sites = relation.guards(source)
    texts = [site["text"] for site in sites]
    assert texts.count("a.converter") == 1, "the isinstance() argument is not a question"
    assert "a" not in texts, "a nested root is not a separate question"
    assert "isinstance" not in texts, "a builtin is never a boolean question worth asking"


def test_a_call_argument_is_not_a_question() -> None:
    """Measured false positive: `hasattr(iterable, '__reversed__')` -- `iterable` is an argument.

    Projecting it gave `hasattr(((iterable) is not None), '__reversed__')`, i.e. `hasattr(True, ...)`,
    which is False, which takes the same branch the human's `getattr(..., None)` takes, which flipped
    the human's own fail-to-pass test. Only the operands a test asks a yes/no question of are sites.
    """
    source = "def f(iterable):\n    if hasattr(iterable, '__reversed__'):\n        return 1\n"
    assert relation.guards(source) == []
    asked = "def f(a, b):\n    if a and not b:\n        return 1\n"
    assert {site["text"] for site in relation.guards(asked)} == {"a", "b"}


def test_instrumentation_wraps_every_probed_span_and_keeps_the_code_parseable() -> None:
    source = "def f(a):\n    if a.converter:\n        return 1\n    return 2\n"
    sites = relation.guards(source)
    instrumented = relation.instrument(source, sites)
    assert instrumented is not None
    assert "__brain_probe__(2, " in instrumented
    compile(instrumented, "<probe>", "exec")


def test_rewrite_projects_one_span_and_refuses_a_stale_span() -> None:
    source = "def f(a):\n    if a.converter and a.converter.x:\n        return 1\n"
    sites = [site for site in relation.guards(source) if site["text"] == "a.converter"]
    rewritten = relation.rewrite(source, sites[0])
    assert rewritten is not None
    assert "((a.converter) is not None)" in rewritten
    stale = {**sites[0], "text": "something.else"}
    assert relation.rewrite(source, stale) is None, "a span that no longer matches is refused"


def test_the_judge_accepts_a_repair_that_leaves_an_unrelated_red_in_place() -> None:
    baseline = {"a": "FAILED", "b": "FAILED", "c": "PASSED"}
    after = {"a": "PASSED", "b": "FAILED", "c": "PASSED"}
    ok, why, flipped = relation.judge(baseline, after)
    assert ok, why
    assert flipped == ["a"]


def test_the_judge_refuses_a_candidate_that_flips_only_part_of_the_witness() -> None:
    """A demand's footprint is the set of tests the human edit turns green; matching part of it is not it."""
    baseline = {"a": "FAILED", "b": "FAILED", "c": "PASSED"}
    human = {"a": "PASSED", "b": "PASSED", "c": "PASSED"}
    _ok, _why, witness = relation.judge(baseline, human)
    ok, why, flipped = relation.judge(baseline, {"a": "PASSED", "b": "FAILED", "c": "PASSED"},
                                      witness=witness)
    assert not ok and why.startswith("PARTIAL_FLIP")
    assert flipped == ["a"]


def test_the_judge_refuses_a_repair_that_breaks_a_passing_test() -> None:
    baseline = {"a": "FAILED", "c": "PASSED"}
    after = {"a": "PASSED", "c": "FAILED"}
    ok, why, _flipped = relation.judge(baseline, after)
    assert not ok and "BROKE" in why


def test_the_judge_refuses_a_candidate_that_flips_nothing() -> None:
    baseline = {"a": "FAILED", "c": "PASSED"}
    ok, why, _flipped = relation.judge(baseline, after={"a": "FAILED", "c": "PASSED"})
    assert not ok and why == "NO_TEST_FLIPPED"


@pytest.fixture()
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "proj").mkdir()
    (root / "tests").mkdir()
    (root / "proj" / "__init__.py").write_text("", encoding="utf-8")
    (root / "proj" / "core.py").write_text(SOURCE, encoding="utf-8")
    (root / "tests" / "test_core.py").write_text(
        "from proj.core import pick\n\n\ndef test_true():\n    assert pick(True) == 1\n",
        encoding="utf-8")
    _commit(root, "first")
    return root


def test_a_falsey_but_valid_object_is_the_site_and_the_edit_verifies(repo: pathlib.Path) -> None:
    """End to end: the guard is found by MEASUREMENT, projected, and verified by the suite."""
    (repo / "proj" / "core.py").write_text(
        'from __future__ import annotations\n\n\ndef pick(v):\n    if v is not None:\n'
        '        return 1\n    return 2\n', encoding="utf-8")
    (repo / "tests" / "test_core.py").write_text(
        "from proj.core import pick\n\n\nclass Falsy:\n    def __bool__(self):\n        return False\n"
        "\n\ndef test_true():\n    assert pick(True) == 1\n\n\ndef test_falsey():\n"
        "    assert pick(Falsy()) == 1\n", encoding="utf-8")
    commit = _commit(repo, "accept a falsey object")
    row = relation.explore(repo, {"repo": "proj", "commit": commit,
                                  "test": "tests/test_core.py", "sources": ["proj/core.py"]},
                           cap=8, seconds=90)
    assert row["stage"] == "VERIFIED", row
    assert row["site_expression"] == "v"
    assert row["replacement"] == "(v) is not None"
    assert row["control"]["accepted"] is True
    assert row["flipped"] == ["tests/test_core.py::test_falsey"]
