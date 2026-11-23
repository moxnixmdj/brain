"""The probe test: a tie is resolved by behaviour, not by more text.

Every fixture here is real behaviour measured in this session:
  np.prod([1,2,3,4]) -> 24.0 (scalar)   vs  np.nancumprod -> array of 4
  librosa.util.localmin -> a boolean mask marking minima
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import the_shape_of_the_answer_is_the_probe_v1 as P


def test_the_goal_names_its_output_shape():
    assert P.named_shape("computes the product of an array") == "scalar"
    assert P.named_shape("locate the local minimas of an array") == "mask"
    # AND IT MUST DECLINE WHEN THE GOAL DOES NOT STATE A SHAPE. "an array of time values"
    # names `array` (an input or a container noun that appears in both vocabularies) and
    # `values` -- neither says what comes BACK, so the honest answer is no verdict rather than a
    # guess. `None` here is the mechanism working, not failing.
    assert P.named_shape("return an array of time values") is None
    assert P.named_shape("do something unspecified") is None


def test_shape_of_reads_a_scalar_and_a_sequence():
    assert P.shape_of(24.0) == "scalar"
    assert P.shape_of([1, 2, 3]) == "sequence"
    assert P.shape_of(True) == "scalar"


def test_the_probe_separates_prod_from_cumprod():
    """The tie the ranker cannot break: same words, different shapes."""
    std = P.probe("/tmp/instv/bin/python", "numpy", "prod", "[1.0, 2.0, 3.0, 4.0]")
    cum = P.probe("/tmp/instv/bin/python", "numpy", "nancumprod", "[1.0, 2.0, 3.0, 4.0]")
    assert std["kind"] == "scalar", std
    assert cum["kind"] == "sequence", cum


def test_resolve_keeps_only_the_matching_shape():
    res = P.resolve("/tmp/instv/bin/python", "computes the product of an array",
                    [("numpy", "prod"), ("numpy", "nancumprod"),
                     ("numpy", "nanprod"), ("numpy", "cumprod")],
                    "[1.0, 2.0, 3.0, 4.0]")
    assert res["goal_shape"] == "scalar"
    assert "prod" in res["survivors"]
    assert "nancumprod" not in res["survivors"]
    assert "cumprod" not in res["survivors"]


def test_a_candidate_that_raises_is_eliminated_not_blamed():
    """The sample may not be the data it takes; that is not evidence against the goal."""
    res = P.resolve("/tmp/instv/bin/python", "computes the product of an array",
                    [("numpy", "prod"), ("numpy", "nonexistent_name")],
                    "[1.0, 2.0]")
    assert "prod" in res["survivors"]
    assert any(p["kind"] == "error" for p in res["probes"])


def test_an_unshaped_goal_is_not_forced_into_a_verdict():
    res = P.resolve("/tmp/instv/bin/python", "do the needful", [("numpy", "prod")], "[1.0]")
    assert res["resolved"] is False and res["goal_shape"] is None
