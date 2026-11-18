"""Hypotheses must be *counted*, and the count must collapse as the world speaks.

The claim "experience it once and it is learned" is a claim about how many programs remain consistent
with one observation. These tests pin the instrument that counts them, and pin the two self-deceptions
it was built through: probes drawn from the corpus (the corpus grading itself), and passing rows in an
angelic table (where the identity expression satisfies the table trivially).
"""

import pathlib
import random
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import how_many_hypotheses_survive_an_observation_v1 as hypotheses  # noqa: E402

QUIXBUGS = pathlib.Path("/tmp/QuixBugs")
needs_corpus = pytest.mark.skipif(not (QUIXBUGS / "python_programs" / "lis.py").exists(),
                                  reason="the published corpus is not checked out")


def test_a_perturbed_numeric_input_is_never_the_corpus_input():
    """A probe that equals the corpus input is not a probe -- it is the corpus grading itself."""
    rng = random.Random(0)
    for args in ([1, 2, 3], [[4, 1, 5, 3], 2]):
        for _ in range(20):
            now = hypotheses.perturbed(args, rng)
            assert now is not None
            assert list(now) != list(args)


def test_perturbation_keeps_the_shape_of_the_arguments():
    rng = random.Random(1)
    got = hypotheses.perturbed([[3, 6, 7, 1], 2], rng)
    assert isinstance(got[0], list) and all(isinstance(x, int) for x in got[0])
    assert isinstance(got[1], int)


@needs_corpus
def test_one_observation_identifies_lis_and_the_survivor_is_correct():
    """The single bug in six where a single observation is enough. If this ever stops being one, the
    count moved and the document that quotes it is stale."""
    row = hypotheses.measure(QUIXBUGS, "lis")
    first = row["steps"][0]
    assert first["survivors"] == 1, first
    assert first["smallest"] == "max(length + 1, longest)", first
    agree, checked = first["smallest_correct_on_unseen"].split("/")
    assert agree == checked, first


@needs_corpus
def test_survivors_never_grow_as_observations_accumulate():
    row = hypotheses.measure(QUIXBUGS, "mergesort")
    counts = [step["survivors"] for step in row["steps"]]
    assert counts == sorted(counts, reverse=True), counts


@needs_corpus
def test_a_single_observation_does_not_identify_kth():
    """If this ever becomes 1, "once and permanent" got easier and the document must say so."""
    row = hypotheses.measure(QUIXBUGS, "kth")
    assert row["steps"][0]["survivors"] > 1, row["steps"][0]
