"""Tests for the filing-key bottleneck.

The mistake this file exists to prevent is the one it made in its own first draft: the benchmark
calls `make(1)` everywhere, and instance 1 is the hardest of the three for several kinds. Reading
"no policy solves it" off instance 1 alone is an instrument artifact that looks exactly like a
capability finding. The sweep over instances is the fix, and these tests pin it.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/user/brain")
from canonical.tools import the_index_is_the_bottleneck_v1 as IDX  # noqa: E402


def test_solving_policies_sweeps_instances_not_only_the_benchmarks_default():
    """`letter_shift` is unsolvable at instance 1 and solvable at instance 2.

    If this test ever passes with a single-instance reading, the instrument has regressed to the
    artifact it was written to correct.
    """
    bench = IDX.load_benchmark()
    l2l = IDX._load("_l2l", IDX.ROOT / "canonical" / "runtime" / "learn_to_learn_v1.py")
    makers = dict(IDX.kinds_and_makers(bench))
    assert "letter_shift" in makers
    detail = IDX.solving_policies(bench, l2l, "letter_shift", makers["letter_shift"])
    assert detail["per_instance"]["1"] == []
    assert detail["per_instance"]["2"], "instance 2 must be solvable, or the sweep is not running"
    assert detail["solved_on_any_instance"] is True


def test_a_kind_unsolvable_everywhere_is_reported_separately_from_an_unswept_one():
    bench = IDX.load_benchmark()
    l2l = IDX._load("_l2l", IDX.ROOT / "canonical" / "runtime" / "learn_to_learn_v1.py")
    makers = dict(IDX.kinds_and_makers(bench))
    detail = IDX.solving_policies(bench, l2l, "ring_rotate", makers["ring_rotate"])
    assert detail["solved_on_any_instance"] is False
    assert all(v == [] for v in detail["per_instance"].values())


def test_instance_sensitivity_is_its_own_finding():
    """A kind needing different policies on different instances cannot be indexed by kind features."""
    result = IDX.run()
    sensitive = result["instance_sensitivity"]["kinds_whose_policy_set_changes_with_instance"]
    assert len(sensitive) >= 4
    assert "adjacent_sort" in sensitive


def test_no_key_family_separates_what_the_policy_depends_on():
    """The sweep's conclusion, and the shape that makes it a conclusion rather than a preference."""
    result = IDX.run()
    assert result["usable_key_families"] == []
    assert result["verdict"] == "NO_GRANULARITY_OF_THESE_FEATURES_SEPARATES_WHAT_THE_POLICY_DEPENDS_ON"


def test_coarser_collides_more_and_the_trivial_key_answers_nothing_new():
    """Both ends of the trade, measured: coarse collides, one-key-per-kind does not transfer."""
    result = IDX.run()
    rows = {r["name"]: r for r in result["sweep"]}
    coarse = rows["coarser_still"]
    tree = rows["tree_coarse__b(2,4,6)_m(.45,.8)_r(1.5,3)_d(0,3,10)"]
    trivial = rows["trivial_one_key_per_kind"]
    assert coarse["collisions"] >= tree["collisions"]
    assert trivial["collisions"] == 0
    # one key per kind is the degenerate end: it separates everything and transfers nothing
    assert trivial["keys"] == trivial["kinds"]


def test_every_family_is_scored_on_the_same_kinds():
    result = IDX.run()
    counts = {r["kinds"] for r in result["sweep"]}
    assert len(counts) == 1, "families must be comparable; a differing kind count is a bug"
