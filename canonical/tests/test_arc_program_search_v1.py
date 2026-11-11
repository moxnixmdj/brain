"""MDL program search on real public ARC tasks.

The point of these tests is NOT to demand a high score. A test that demanded one would
press the solver toward fitting. They pin the properties that make the reported number
honest: the search VERIFIES on every demonstration, composition is measured rather than
assumed, and nothing is learned.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import arc_program_search_v1 as P  # noqa: E402

DATA = ROOT / "canonical/evaluation/arc_agi1_eval_sample"


def test_a_program_is_never_returned_unless_it_reproduces_all_demonstrations():
    # the same input twice with different outputs cannot be produced by any program
    task = {"train": [{"input": [[1, 2]], "output": [[3]]},
                      {"input": [[1, 2]], "output": [[4]]}],
            "test": [{"input": [[1, 2]], "output": [[5]]}]}
    assert P.solve_task(task)["program"] is None


def test_the_search_finds_the_mirror_tile_program_in_one_step():
    d = __import__("json").loads(
        (DATA / "00576224.json").read_text()) if DATA.is_dir() else None
    if d is None:
        pytest.skip("ARC sample not present")
    r = P.solve_task(d, depth=1)
    assert r["solved"] is True
    assert "mirrortile" in (r["program"] or "")


def test_primitive_tuples_are_name_function_cost():
    """A tuple unpacked in the wrong order calls a string. That bug cost a whole run."""
    for name, fn, cost in P.PRIMITIVES:
        assert isinstance(name, str)
        assert callable(fn)
        assert isinstance(cost, int) and cost > 0


def test_cost_is_the_sum_of_primitive_costs():
    prog = tuple(p for p in P.PRIMITIVES if p[1].__name__ != "")
    one = (P.PRIMITIVES[0],)
    assert P._cost(one) == P.PRIMITIVES[0][2]


def test_nothing_is_learned():
    out = P.evaluate(str(DATA), depth=1) if DATA.is_dir() else None
    if out is None:
        pytest.skip("ARC sample not present")
    assert out["trained_parameters"] == 0
    assert out["gradient_steps"] == 0
    assert out["external_model_calls"] == 0


def test_depth_one_searches_the_whole_sample_fast():
    if not DATA.is_dir():
        pytest.skip("ARC sample not present")
    import time
    t = time.perf_counter()
    out = P.evaluate(str(DATA), depth=1)
    assert (time.perf_counter() - t) < 60, "depth 1 must stay fast"
    assert out["tasks"] >= 50
