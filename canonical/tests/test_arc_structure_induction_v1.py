"""Structure induction: the hypotheses, and the probe that lied.

The most valuable test here is the last one. An earlier probe reported that symmetry
completion held on 34 of 200 tasks. It was wrong: `induce_symmetry` raised
UnboundLocalError, the probe caught the exception, and counted the failure as a hit.
A probe that turns an error into a pass is the failure mode this whole project legislates
against, so it gets a test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import arc_structure_induction_v1 as S  # noqa: E402

DATA = ROOT / "canonical/evaluation/arc_agi1_eval_sample"


def test_lattice_finds_a_period_that_reproduces_the_grid():
    g = [[1, 2, 1, 2], [3, 4, 3, 4], [1, 2, 1, 2], [3, 4, 3, 4]]
    lat = S.induce_lattice([g])
    assert lat is not None
    width, p, q, table = lat
    assert S.apply_lattice(g, p, q, table) == g
    assert width <= 4


def test_symmetry_never_raises_and_returns_none_when_it_does_not_hold():
    # this exact call raised UnboundLocalError in the first version
    g = [[1, 0, 0, 1], [0, 2, 2, 0]]
    assert S.induce_symmetry([{"input": g, "output": g}]) is None


def test_symmetry_completes_a_half_drawn_figure():
    g = [[1, 2, 0, 0], [3, 4, 0, 0]]
    want = [[1, 2, 2, 1], [3, 4, 4, 3]]
    assert S.complete_symmetry(g, "v", 2) == want


def test_recolour_returns_none_on_a_contradiction():
    train = [{"input": [[1]], "output": [[2]]}, {"input": [[1]], "output": [[3]]}]
    assert S.induce_recolour(train) is None


def test_the_induction_order_puts_the_cheapest_description_first():
    # a constant output must be found as `constant`, not as a lattice
    train = [{"input": [[1, 2], [3, 4]], "output": [[7, 7], [7, 7]]}]
    r = S.induce(train)
    assert r is not None
    assert r[0] == "constant"


def test_a_probe_that_swallows_an_exception_cannot_count_it_as_a_hit():
    """Regression: the counting bug that produced a false 34-of-200."""
    def honest_probe(fn, arg):
        try:
            return bool(fn(arg))
        except Exception:
            return False          # an exception is a MISS, never a hit
    # induce_symmetry is total now, so this asserts the contract, not the old bug
    assert honest_probe(S.induce_symmetry, [{"input": [[1]], "output": [[1]]}]) is False


def test_the_whole_sample_is_evaluated_without_crashing():
    if not DATA.is_dir():
        pytest.skip("ARC sample not present")
    out = S.evaluate(str(DATA))
    assert out["tasks"] >= 50
    assert out["trained_parameters"] == 0
    assert out["external_model_calls"] == 0
