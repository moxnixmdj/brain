"""The weightless ARC solver, on real public tasks.

WHY THESE TESTS EXIST
---------------------
Everything else this project reports is a self-report: a corpus we wrote, scored by a
scorer we wrote. ARC-AGI is a public benchmark whose tasks nobody here authored. The
tests below pin the properties that make the number honest:

  * it induces from the demonstrations and VERIFIES against every one of them
  * it moves no learned bytes: no weights, no gradients, no model calls
  * a rule that fails one demonstration is discarded, never patched
  * it is fast enough to run the whole set inside a test

The accuracy itself is deliberately NOT asserted to a high bar. A test that demanded a
score would be a test that pressures the solver toward fitting. It is asserted that the
solver runs, refuses honestly on what it cannot do, and solves the class it claims.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import arc_weightless_solver_v1 as A  # noqa: E402

DATA = ROOT / "canonical/evaluation/arc_agi1_eval_sample"


# ---- a known task, built inline, so the test does not depend on a download ---------
MIRROR_TASK = {
    "train": [
        {"input": [[8, 6], [6, 4]],
         "output": [[8, 6, 8, 6, 8, 6], [6, 4, 6, 4, 6, 4],
                    [6, 8, 6, 8, 6, 8], [4, 6, 4, 6, 4, 6],
                    [8, 6, 8, 6, 8, 6], [6, 4, 6, 4, 6, 4]]},
        {"input": [[7, 9], [4, 3]],
         "output": [[7, 9, 7, 9, 7, 9], [4, 3, 4, 3, 4, 3],
                    [9, 7, 9, 7, 9, 7], [3, 4, 3, 4, 3, 4],
                    [7, 9, 7, 9, 7, 9], [4, 3, 4, 3, 4, 3]]},
    ],
    "test": [
        {"input": [[3, 2], [7, 8]],
         "output": [[3, 2, 3, 2, 3, 2], [7, 8, 7, 8, 7, 8],
                    [2, 3, 2, 3, 2, 3], [8, 7, 8, 7, 8, 7],
                    [3, 2, 3, 2, 3, 2], [7, 8, 7, 8, 7, 8]]},
    ],
}


def test_the_mirror_tile_rule_is_induced_and_verified_on_every_demonstration():
    r = A.solve_task(MIRROR_TASK)
    assert r["rule"] == "mirror_tile"
    assert r["solved"] is True


def test_a_rule_is_never_applied_unless_it_reproduces_all_demonstrations():
    """A task whose rule is outside the hypothesis space must be REFUSED, not guessed.

    The first version of this test was wrong and the solver was right: it used
    `[[1,2],[3,4]] -> [[9,9],[9,9]]` and `[[5,6],[7,8]] -> [[9,9],[9,8]]`, and a colour map
    really does reproduce both (1->9, 2->9, 3->9, 4->9, 8->8, 7->9, 6->9, 5->9). The
    solver induced a verified rule; the test was the thing that was mistaken.

    This version is genuinely unrepresentable: the same two inputs appear with different
    outputs, and no cell-wise or geometric rule can do that.
    """
    task = {"train": [{"input": [[1, 2]], "output": [[3]]},
                      {"input": [[1, 2]], "output": [[4]]}],
            "test": [{"input": [[1, 2]], "output": [[5]]}]}
    r = A.solve_task(task)
    assert r["solved"] is False
    assert r["rule"] is None


def test_a_rule_that_raises_does_not_crash_the_solver():
    # ragged grids appear in real data; a hypothesis that raises must be discarded
    task = {"train": [{"input": [[1, 2], [3]], "output": [[1]]}],
            "test": [{"input": [[1]], "output": [[1]]}]}
    r = A.solve_task(task)
    assert "solved" in r


def test_the_solver_learns_nothing():
    out = A.evaluate(str(DATA)) if DATA.is_dir() else None
    if out is None:
        pytest.skip("ARC data not downloaded")
    assert out["trained_parameters"] == 0
    assert out["gradient_steps"] == 0
    assert out["external_model_calls"] == 0


def test_it_solves_at_least_the_class_it_claims():
    if not DATA.is_dir():
        pytest.skip("ARC data not downloaded")
    out = A.evaluate(str(DATA))
    assert out["tasks"] >= 50, "the denominator must be a real sample"
    assert out["solved"] >= 1, "a solver that solves nothing cannot claim a number"


def test_the_whole_public_sample_runs_fast():
    if not DATA.is_dir():
        pytest.skip("ARC data not downloaded")
    import time
    t = time.perf_counter()
    out = A.evaluate(str(DATA))
    elapsed = (time.perf_counter() - t) * 1000
    assert elapsed < 10_000, f"{elapsed:.0f} ms for {out['tasks']} tasks is too slow"
