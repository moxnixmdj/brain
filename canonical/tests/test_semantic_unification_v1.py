"""Tests for semantic anti-unification: the organ noticing two programs mean the same thing.

Every test here corresponds to a failure the mechanism actually had on 2026-11-04, or to a trap
that would turn a false positive into a wrong concept in the synthesis grammar. The traps are the
point: agreement on a probe vector is evidence, and the cheap ways to fake agreement are
`p == s` (variable renaming), `True == 1` (bool as number), and `p * q == s * t` inside a pair
whose real relationship is `p * q` versus `s * t + 1`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.semantic_unification_v1 import (  # noqa: E402
    _agreement,
    bridge_sources,
    find_correspondences,
)


def _src(name: str, params: list[str], body: str) -> str:
    return "def %s(%s):\n    return %s" % (name, ", ".join(params), body)


GAP_A = _src("gap", ["p", "q"], "max(p, q) - min(p, q)")
GAP_B = _src("spread", ["s", "t"], "abs(s - t)")
MEAN_A = _src("avg", ["p", "q"], "(p + q) / 2.0")
MEAN_B = _src("mid", ["s", "t"], "s / 2.0 + t / 2.0")
UNRELATED_A = _src("mul", ["p", "q"], "p * q")
UNRELATED_B = _src("add", ["s", "t"], "s + t")
NEAR_MISS = _src("mul_plus", ["s", "t"], "s * t + 1")


def _pairs(doc):
    return {(c["left"], c["right"]) for c in doc["correspondences"]}


def test_notices_distance_written_two_ways():
    """max(p,q)-min(p,q) and abs(s-t) share no syntax -- this is the whole point."""
    doc = find_correspondences([GAP_A, GAP_B])
    assert ("max(p, q) - min(p, q)", "abs(s - t)") in _pairs(doc)
    top = next(c for c in doc["correspondences"]
               if c["left"] == "max(p, q) - min(p, q)" and c["right"] == "abs(s - t)")
    assert top["grade"] == "EXACT"
    assert top["probes_agreed"] == top["probes_exact"] >= 6


def test_notices_mean_written_two_ways():
    doc = find_correspondences([MEAN_A, MEAN_B])
    assert ("(p + q) / 2.0", "s / 2.0 + t / 2.0") in _pairs(doc)


def test_unrelated_programs_produce_no_correspondence():
    doc = find_correspondences([UNRELATED_A, UNRELATED_B])
    assert doc["count"] == 0
    assert doc["correspondences"] == []


def test_bare_variables_are_not_equivalences():
    """Regression: `p` and `s` "agreed on 9 probes" because both got the same probe value.

    That made two unrelated programs report four correspondences. Variable renaming is not a
    shared idea, so a correspondence must involve structure.
    """
    doc = find_correspondences([UNRELATED_A, UNRELATED_B])
    assert all(c["left"] not in ("p", "q", "s", "t") for c in doc["correspondences"])


def test_bool_is_never_treated_as_a_number():
    """`True == 1` in Python; letting it pass would put a comparison result where a number belongs."""
    assert _agreement(True, 1) == "DISAGREE"
    assert _agreement(False, 0) == "DISAGREE"
    assert _agreement(1, 1) == "EXACT"
    assert _agreement(0.0, 0) == "REPRESENTATION"
    assert _agreement(1.0, 1.0 + 1e-15) == "REPRESENTATION"
    assert _agreement(1.0, 2.0) == "DISAGREE"


def test_near_miss_is_not_a_correspondence():
    """`p * q` agrees with `s * t`; it must NOT be reported as agreeing with `s * t + 1`.

    Anchoring the test on the FULL expressions is what makes it a near-miss test: a sub-expression
    matching legitimately is the mechanism working, not a false positive.
    """
    doc = find_correspondences([UNRELATED_A, NEAR_MISS])
    assert ("p * q", "s * t + 1") not in _pairs(doc)


def test_bridge_rewrites_the_second_program_into_the_first_spelling():
    """The direction bug: the first version renamed the wrong side and changed nothing."""
    doc = find_correspondences([GAP_A, GAP_B])
    corr = next(c for c in doc["correspondences"] if c["left"] == "max(p, q) - min(p, q)")
    bridged = bridge_sources(GAP_A, GAP_B, corr)
    assert bridged != GAP_B
    assert "abs(" not in bridged
    assert "max(s, t) - min(s, t)" in bridged     # renamed into the SECOND program's variables


def test_join_is_mechanically_sound_and_keeps_the_corpus_learnable():
    """What the bridge is actually good for, after two gates moved underneath it.

    HISTORY, because the claim has now been wrong twice:

      1. First version asserted `two_spellings < all_one_spelling` at size 4, with the join
         recovering the difference. That ordering INVERTED when the totality gate landed.
      2. Second version asserted `bridged >= mixed` at every size. Measured 2026-11-04: that is
         FALSE at size 5 (mixed 2, bridged 1), because bridging rewrites every program into one
         spelling, which homogenises the corpus and reduces the diversity of learnable subtrees.

    So the honest claim is the mechanical one plus a floor: every correspondence bridges, and the
    bridged corpus is still a corpus the library can learn from. Whether bridging increases
    admission depends on the gates and on the corpus, and asserting a direction would be fitting
    the test to today's numbers -- which is how both previous versions went wrong.
    """
    sys.path.insert(0, str(ROOT / "canonical" / "tools"))
    from semantic_join_benchmark_v1 import (  # type: ignore[import-not-found]
        TRIPLES,
        _measure_arms,
        bridge_corpus,
        spelling_a,
        spelling_b,
    )

    for size in (4, 6, 8):
        first = [spelling_a(i, v) for i, v in enumerate(TRIPLES[:size])]
        second = [spelling_b(i, v) for i, v in enumerate(TRIPLES[:size])]
        bridged, log = bridge_corpus(first, second)
        assert len(bridged) == len(second)
        assert all(b["status"] == "BRIDGED" for b in log), "every pair must bridge"
        assert bridged != second, "the bridge must actually change the text"

        arms = {a["arm"]: a for a in _measure_arms(first, second, bridged)}
        assert arms["all_one_spelling"]["admitted"] >= 1, "concept must be learnable"
        assert arms["bridged"]["admitted"] >= 1, "the bridged corpus must remain learnable"


def test_join_admission_direction_is_not_claimed():
    """Guard against re-adding a directional claim: the data does not support one.

    Measured across the sweep, bridging sometimes raises and sometimes lowers the admitted count.
    Any future assert of a direction must come with a reason, and this test records that the
    direction is genuinely unpinned rather than merely untested.
    """
    sys.path.insert(0, str(ROOT / "canonical" / "tools"))
    from semantic_join_benchmark_v1 import (  # type: ignore[import-not-found]
        TRIPLES,
        _measure_arms,
        bridge_corpus,
        spelling_a,
        spelling_b,
    )

    deltas = []
    for size in (4, 5, 6):
        first = [spelling_a(i, v) for i, v in enumerate(TRIPLES[:size])]
        second = [spelling_b(i, v) for i, v in enumerate(TRIPLES[:size])]
        bridged, _ = bridge_corpus(first, second)
        arms = {a["arm"]: a for a in _measure_arms(first, second, bridged)}
        deltas.append(arms["bridged"]["admitted"] - arms["two_spellings"]["admitted"])
    assert len(set(deltas)) > 1, (
        "if bridging had a consistent direction, that direction could be claimed; it does not, so "
        f"no directional claim is made. deltas={deltas}")


def test_correspondences_carry_no_authority_and_no_proof_claim():
    """An earlier version of this test grepped the prose for the word "proof" and was brittle.

    What must hold structurally: nothing is claimed as authoritative, the non-claims are present,
    and every correspondence is labelled as an OBSERVATION.
    """
    doc = find_correspondences([GAP_A, GAP_B])
    assert doc["authority"] == "NONE"
    assert len(doc["not_claimed"]) >= 2
    assert doc["correspondences"], "test needs at least one correspondence to check"
    assert all(c["evidence"].startswith("OBSERVED_AGREEMENT_ON_") for c in doc["correspondences"])
