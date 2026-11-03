"""Tests for the generalisation check -- the instrument that reversed a null result.

The three bugs this file guards against all made a REAL reach gain look like nothing:
  1. a multi-`def` body (concept helper + final `return`) was wrapped in a single function;
  2. `exec` used separate globals/locals, so a helper `def` was invisible to the body;
  3. the benchmark's expected values were transcribed by hand and two were wrong.
Plus the thing being measured: counting a non-None body as a solve.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.generalization_check_v1 import (  # noqa: E402
    OVERFIT,
    SOLVED,
    UNREACHED,
    _split_body,
    classify,
)

# A real body from `synthesize_python_function_body` with a materialised concept helper.
HELPER_BODY = (
    "def concept_640d4492(_v0, _v1, _v2):\n"
    "    return (min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1) if _v2 > _v1 else 0.0\n"
    "return (concept_640d4492(v, l, h) + 0.5)"
)

WITHHELD = [
    ((9, 8, 10), (min(max(9, 8), 10) - 8) / (10 - 8) + 0.5),
    ((1, 0, 4), (min(max(1, 0), 4) - 0) / (4 - 0) + 0.5),
    ((12, 10, 11), (min(max(12, 10), 11) - 10) / (11 - 10) + 0.5),
]


def test_splits_helpers_from_the_final_body():
    helpers, outer = _split_body(HELPER_BODY)
    assert len(helpers) == 2 and helpers[0].startswith("def concept_")
    assert len(outer) == 1 and outer[0].startswith("return (concept_")


def test_multi_def_body_compiles_and_is_solved():
    """Bug 1 and bug 2 together: this body is CORRECT and must not be scored OVERFIT."""
    verdict, observed = classify(HELPER_BODY, ["v", "l", "h"], WITHHELD)
    assert verdict == SOLVED
    assert len(observed) == len(WITHHELD)


def test_interpolation_is_overfit_not_solved():
    """`(v / h) + 0.5` fits some examples and is not the clamped normalisation."""
    body = "return ((v / h) + 0.5)"
    verdict, observed = classify(body, ["v", "l", "h"], WITHHELD)
    assert verdict == OVERFIT
    assert observed, "a verdict of OVERFIT must carry what was actually observed"


def test_conditional_interpolation_is_overfit():
    """The body the first benchmark counted as a solve."""
    body = "if not (min(v, l)):\n    return ((v / h) + 0.5)\nreturn abs((l - 0.5))"
    verdict, _ = classify(body, ["v", "l", "h"], WITHHELD)
    assert verdict == OVERFIT


def test_none_body_is_unreached_not_overfit():
    assert classify(None, ["v", "l", "h"], WITHHELD) == (UNREACHED, [])


def test_uncompilable_body_is_not_a_solve():
    verdict, _ = classify("return (((", ["v", "l", "h"], WITHHELD)
    assert verdict in (OVERFIT, UNREACHED)


def test_agreement_tolerates_float_representation():
    """0.1 + 0.2 style drift must not be scored as a generalisation failure."""
    body = "return (v * 0.1 + 0.2)"
    withheld = [((1,), 0.1 + 0.2), ((2,), 0.2 + 0.2)]
    verdict, _ = classify(body, ["v"], withheld)
    assert verdict == SOLVED


# --------------------------------------------------------------------------- #
# The reversed result: concept invention turns interpolation into generalisation.
# This is the test that must fail if the reach gain ever becomes imaginary.
# --------------------------------------------------------------------------- #
def _norm(v, l, h):
    return (min(max(v, l), h) - l) / (h - l) if h > l else 0.0


def test_invented_concept_enables_generalising_reach():
    """G0 solves nothing; after invention the composed function generalises to unseen points.

    Measured 2026-11-04: 0/3 -> 2/3. Before the compiler bugs were fixed this read 0/3 vs 0/3 and
    was written up as "the concept buys compactness, not reach". The gain was real; the
    instrument was blind.
    """
    import pathlib
    import tempfile

    from canonical.runtime.generalization_check_v1 import measure
    from canonical.runtime.swe_observational_program_synthesizer_v1 import (
        synthesize_python_function_body as synth,
    )
    from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary

    train_inputs = [(5, 2, 4), (7, 0, 10), (-3, 0, 10)]
    withheld_inputs = [(9, 8, 10), (1, 0, 4), (12, 10, 11), (6, 1, 9)]
    problems = [
        {"name": "norm_plus_half", "params": ["v", "l", "h"],
         "train": [(p, _norm(*p) + 0.5) for p in train_inputs],
         "withheld": [(p, _norm(*p) + 0.5) for p in withheld_inputs]},
        {"name": "norm_times_2", "params": ["v", "l", "h"],
         "train": [(p, _norm(*p) * 2.0) for p in train_inputs],
         "withheld": [(p, _norm(*p) * 2.0) for p in withheld_inputs]},
    ]

    triples = [("val", "lo", "hi"), ("u", "a", "b"), ("x", "mn", "mx"), ("t", "low", "high"),
               ("q", "pp", "qq"), ("zz", "k0", "k1"), ("mm", "n0", "n1"), ("hh", "g0", "g1")]

    def src(name, v):
        val, lo, hi = v
        return (
            f"def {name}({val}, {lo}, {hi}):\n"
            f"    return (min(max({val}, {lo}), {hi}) - {lo}) / ({hi} - {lo})"
            f" if {hi} > {lo} else 0.0"
        )

    teaching = [src(f"na{i}", v) for i, v in enumerate(triples)]

    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "library.json"
        library = CompoundingConceptLibrary(path)
        admitted = library.sleep_abstract(teaching + teaching)["admitted_count"]
        assert admitted >= 1, "concept must be invented, or the test measures nothing"

        grown = CompoundingConceptLibrary(path)
        before = measure(problems, synth, max_weight=4, extra_constants=(0.5, 2.0),
                         concept_library=None)
        after = measure(problems, synth, max_weight=4, extra_constants=(0.5, 2.0),
                        concept_library=grown)

    assert before["solved"] == 0, "an empty library must not generalise these"
    assert after["solved"] > before["solved"], "the invented concept must add generalising reach"
