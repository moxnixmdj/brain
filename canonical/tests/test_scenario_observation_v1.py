"""Tests for observation by replaying the environment's own scenarios.

The rules that carry the round:

  * the record must be stable across two runs at one revision, or it is refused, not counted;
  * an object's return is observed as its TYPE, never as a repr that would carry addresses and timings in;
  * a literal or JSON-able return is observed exactly, so a value move cannot hide behind a type;
  * a callable is observable only if the environment itself reaches it -- never because we constructed args;
  * a move must carry both sides of the evidence (what only the old run did, what only the new run did);
  * the same outcomes in different proportions is a TEST change, not a behaviour change;
  * the unlock is measured against the round-6 unexercised set, not against a convenient denominator.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import scenario_observation_v1 as S  # noqa: E402

PACKAGE = '''\
def parse_tag(tag):
    return tag.split("-")


def strict(tag):
    raise ValueError(tag)
'''

TESTS = '''\
from pkg.core import parse_tag, strict


def test_tags():
    assert parse_tag("cp311-cp311-manylinux_2_17_x86_64") == ["cp311", "cp311", "manylinux_2_17_x86_64"]


def test_strict():
    try:
        strict("x")
    except ValueError:
        pass
'''


def _tree(tmp_path: pathlib.Path, name: str, package: str, tests: str | None = TESTS) -> pathlib.Path:
    root = tmp_path / name
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "core.py").write_text(package, encoding="utf-8")
    if tests is not None:
        (root / "tests").mkdir()
        (root / "tests" / "test_core.py").write_text(tests, encoding="utf-8")
    return root


def test_schema_zero_model_and_zero_cost(tmp_path):
    report = S.measure(tmp_path / "c", tmp_path / "w", limit=0)
    assert report["schema"] == "BRAIN_SCENARIO_OBSERVATION_V1"
    assert report["model_calls"] == 0 and report["network_calls"] == 0


def test_an_object_return_is_observed_as_a_type_not_a_repr():
    class Thing:
        def __repr__(self) -> str:  # a repr with an address is exactly what must not enter the record
            return "<Thing at 0xdeadbeef>"

    assert S._digest(Thing()) == "Thing"


def test_literals_and_structures_are_observed_exactly():
    assert S._digest(7) == "7"
    assert S._digest("x") == "'x'"
    assert S._digest({"b": 2, "a": 1}) == "dict{'a':1,'b':2}"
    assert S._digest([1, "two"]) == "list[2](1,'two')"


def test_addresses_and_temporary_paths_are_erased_so_one_revision_compares_equal():
    assert "0x?" in S._normalise("at 0x7f3a2b")
    assert S._normalise("/tmp/pytest-abc/item") == "<path>"


def test_only_the_environments_own_tests_produce_observations(tmp_path):
    tree = _tree(tmp_path, "t", PACKAGE)
    run = S.run_suite(tree, {"parse_tag", "strict"})
    assert run["state"] == "RAN"
    names = {record["n"] for record in run["records"]}
    assert names == {"parse_tag", "strict"}
    assert any(record["o"].startswith("RETURNED|list[3]") for record in run["records"])
    assert any(record["o"] == "RAISED|ValueError" for record in run["records"])


def test_a_tree_with_no_tests_is_refused_by_name(tmp_path):
    tree = _tree(tmp_path, "t", PACKAGE, tests=None)
    assert S.run_suite(tree, {"parse_tag"})["state"] == S.REFUSED_NO_SUITE


def test_two_runs_of_one_revision_stable_is_a_precondition(tmp_path):
    old = ["RETURNED|'a'|arity=1"]
    assert S.classify(old, old, old)[0] == S.STABLE
    assert S.classify(old, ["RETURNED|'b'|arity=1"], old)[0] == S.REFUSED_NONDETERMINISTIC


def test_a_later_release_that_raises_is_a_move_with_the_evidence_on_both_sides(tmp_path):
    state, _ = S.classify(["RETURNED|'a'|arity=1"], ["RETURNED|'a'|arity=1"], ["RAISED|ValueError|arity=1"])
    assert state == S.MOVE_NOW_RAISES


def test_the_same_outcomes_in_different_proportions_are_a_test_change_not_a_move():
    old = ["RETURNED|'a'|arity=1", "RETURNED|'a'|arity=1"]
    new = ["RETURNED|'a'|arity=1"]
    assert S.classify(old, old, new)[0] == S.MIX
    assert S.classify(old, old, new)[0] not in (S.MOVE_NOW_RAISES, S.MOVE_NOW_RETURNS, S.MOVE_ARITY, S.MOVE_VALUE)


def test_an_action_its_own_suite_never_reaches_is_refused_by_name(tmp_path):
    tree = _tree(tmp_path, "t", PACKAGE + '\n\ndef unused(anything):\n    return anything\n')
    run = S.run_suite(tree, {"parse_tag", "unused"})
    grouped = S._by_callable(run["records"])
    assert ("pkg/core.py", "unused") not in grouped
    assert S.classify([], [], [])[0] != S.STABLE


def test_headline_uses_the_round6_denominator_and_names_every_refusal():
    report = {"totals": {"callables": 82, "modules_measured": 11, "round6_unexercised": 38,
                         "reached_unexercised": 28, "reached_fraction": 0.7368,
                         "moved_unexercised": 22, "moved_fraction_of_reached": 0.7857,
                         "moves": {S.MOVE_ARITY: 19, S.MOVE_VALUE: 3, S.STABLE: 8,
                                   S.REFUSED_NOT_REACHED: 47, S.REFUSED_GONE: 2}}}
    line = S._headline(report)
    assert "82 real actions" in line
    assert "28 (0.7368)" in line
    assert "moves 22 of those 28" in line
    assert "REFUSED__NOT_REACHED_BY_OWN_SUITE 47" in line
