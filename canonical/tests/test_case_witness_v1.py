"""Round 12: the discriminating pair from the running case, and the census that sizes its shape.

The end-to-end test builds a real module and a real pytest file in a temporary directory and runs the real
capture against them, because the failure this module had to survive was exactly the kind that a mock hides:
its first version built its own subprocess environment, dropped `tree/src`, and the tests silently exercised
an installed copy of the library instead of the tree.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import case_witness_v1 as W  # noqa: E402
from canonical.swe_kernel import change_shape_census_v1 as C  # noqa: E402

MODULE = '''def check(value):
    """Reject a list whose entries contain a drive letter."""
    for part in value:
        if ".." in part:
            raise ValueError(part)
    return value
'''

TEST = '''import pytest
from mod import check


@pytest.mark.parametrize("value", [["ok"], ["../x"]])
def test_check(value):
    if value == ["../x"]:
        with pytest.raises(ValueError):
            check(value)
        return
    assert check(value) == value
'''


def _repo(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(MODULE, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def test_sibling_cases_prefers_the_same_test_function():
    cases = ["t.py::test_a[0]", "t.py::test_a[1]", "t.py::test_b[0]"]
    assert W.sibling_cases(cases, ["t.py::test_a[0]"]) == ["t.py::test_a[1]"]


def test_partition_reports_the_argument_that_differs_and_only_that():
    rows = {
        "t::f[0]": [{"function": "check", "args": {"value": {"value": ["C:x"]},
                                                  "other": {"value": 1}}}],
        "t::f[1]": [{"function": "check", "args": {"value": {"value": ["ok"]},
                                                  "other": {"value": 1}}}],
    }
    parts = W.partition(rows, ["t::f[0]"], ["t::f[1]"])
    assert [(p["function"], p["argument"]) for p in parts] == [("check", "value")]
    assert parts[0]["failing"] == [["C:x"]] and parts[0]["passing"] == [["ok"]]


def test_partition_ignores_repr_only_values():
    rows = {"a": [{"function": "f", "args": {"x": {"repr": "<obj>"}}}],
            "b": [{"function": "f", "args": {"x": {"repr": "<obj2>"}}}]}
    assert W.partition(rows, ["a"], ["b"]) == []


def test_sites_in_returns_only_that_functions_guards():
    seats = W.sites_in(MODULE, "check")
    assert [text for _, text in seats] == ["'..' in part"]


def test_sites_in_is_empty_for_a_function_that_does_not_exist():
    assert W.sites_in(MODULE, "absent") == []


def test_capture_records_real_argument_values_end_to_end(tmp_path):
    tree = _repo(tmp_path)
    cases = W.collect_cases(tree, "tests/test_mod.py")
    assert len(cases) == 2
    failing = [case for case in cases if case.endswith("[1]")]
    passing = [case for case in cases if case not in failing]
    rows = W.capture(tree, "tests/test_mod.py", failing + passing, "src/mod.py", tmp_path / "work"
                     if (tmp_path / "work").mkdir() or True else tmp_path)
    assert rows, "the witness plugin recorded nothing"
    values = [call["args"]["value"]["value"] for node in rows for call in rows[node]
              if call["function"] == "check" and "value" in call["args"]]
    assert ["../x"] in values and ["ok"] in values


def test_shape_of_separates_the_five_shapes():
    assert C.shape_of("def f(x):\n    return x\n",
                      "def f(x):\n    if not x:\n        raise ValueError(x)\n    return x\n") == C.GUARD
    assert C.shape_of("def f(x):\n    return x\n",
                      "def f(x):\n    return x\n\ndef g(y):\n    return y\n") == C.FEATURE
    assert C.shape_of("def f(x):\n    return x + 1\n",
                      "def f(x):\n    return x - 1\n") == C.SUBSTITUTION
    assert C.shape_of("def f(x):\n    return x\n",
                      "def f(x):\n    return x or 'default'\n") == C.VALUE_ADDED
    assert C.shape_of("def f(x):\n    return x\n", "not python at all (") == C.UNREADABLE


def test_census_reports_shares_that_add_up():
    grammar = [{"name": "r", "defective": "def f(x):\n    return x\n",
                "repaired": "def f(x):\n    if x:\n        raise ValueError(x)\n    return x\n"},
               {"name": "r", "defective": "def f(x):\n    return x\n",
                "repaired": "def f(x):\n    return x\n\ndef g(y):\n    return y\n"}]
    report = C.census(grammar)
    assert report["totals"]["sites"] == 2
    assert report["totals"]["predicate_addressable_share"] == 0.5
    assert report["totals"]["new_code_required_share"] == 0.5
    assert report["model_calls"] == 0 and W.MODEL_CALLS == 0


def test_headline_names_the_share_and_the_demand():
    report = C.census([{"name": "r", "defective": "def f(x):\n    return x\n",
                        "repaired": "def f(x):\n    return x\n\ndef g(y):\n    return y\n"}])
    text = C.headline(report)
    assert "1 real changed sites" in text and "new code is required" in text
