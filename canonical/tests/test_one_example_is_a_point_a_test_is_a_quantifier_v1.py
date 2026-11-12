"""One demonstration prunes one program; three assertions prune twenty-eight.

The space being counted is the space the repair loop searches: `_candidate_specs` and
`_CandidateRenderer` from `python_test_guided_patch_search_v1.py`, the same pair
`python.patch.search.test_guided.ast.v1` is built on. So the counts below are about a candidate the
project actually generates, not about a toy grammar.

The numbers are pinned. If the generator changes, they change, and that is exactly when somebody
should look at them again — the claim is the ratio, and the ratio is the finding.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from one_example_is_a_point_a_test_is_a_quantifier_probe_20261112 import (  # noqa: E402
    DEMONSTRATION,
    SOURCE,
    SUITE,
    run,
)

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = run()
    return _CACHE["r"]


def test_the_fixture_really_is_wrong_under_the_suite():
    """Otherwise the probe would be counting candidates for a program that was already correct."""
    namespace: dict = {}
    exec(compile(SOURCE, "<fixture>", "exec"), namespace)
    grade = namespace["grade"]
    assert not all(grade(*args) == expected for args, expected in SUITE)
    assert grade(*DEMONSTRATION[0]) == DEMONSTRATION[1], "the demonstration must be satisfied"


def test_a_demonstration_eliminates_almost_nothing():
    s = _report()["summary"]
    assert s["candidates"] == 34
    assert s["consistent_with_one_demonstration"] == 33
    assert s["pruned_by_the_demonstration"] == 1


def test_the_suite_eliminates_almost_everything():
    s = _report()["summary"]
    assert s["consistent_with_the_suite"] == 6
    assert s["pruned_by_the_suite"] == 28


def test_the_programs_a_single_experience_would_keep_are_wrong():
    s = _report()["summary"]
    assert s["demonstration_only_that_is_wrong"] == 27
    assert s["both"] == s["consistent_with_the_suite"]


def test_the_real_fix_is_admitted_by_the_suite_and_by_the_demonstration():
    fixes = [
        row for row in _report()["records"]
        if row["consistent_with_the_suite"] and "score >= 90" in row["source"]
    ]
    assert fixes, "the boundary fix must survive the suite"
    assert all(row["consistent_with_one_demonstration"] for row in fixes)


def test_a_one_point_off_constant_is_admitted_by_the_demonstration_and_rejected_by_the_suite():
    """`90 -> 91` is the canonical false success: it agrees with grade(95) and fails grade(90)."""
    rows = {
        row["detail"]: row for row in _report()["records"]
        if row["kind"] == "CONSTANT_REPLACE"
    }
    assert "90->91" in rows, sorted(rows)
    assert rows["90->91"]["consistent_with_one_demonstration"] is True
    assert rows["90->91"]["consistent_with_the_suite"] is False


def test_the_probe_ran_nothing_from_the_tree():
    report = _report()
    assert report["model_dependency_count"] == 0
    assert report["incremental_spend_usd"] == 0
    assert all("source" in row for row in report["records"])
