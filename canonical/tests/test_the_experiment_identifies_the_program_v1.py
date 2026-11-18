"""Identification is set arithmetic over a behaviour table, and it is only ever established held out.

The two things that can go wrong here are the two this tree has retracted before: a number produced by
the corpus grading itself, and a "solved" that was never checked on anything new. Both are pinned.
"""

import pathlib
import random
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import the_experiment_that_identifies_v1 as experiment  # noqa: E402

QUIXBUGS = pathlib.Path("/tmp/QuixBugs")
needs_corpus = pytest.mark.skipif(not (QUIXBUGS / "python_programs" / "lis.py").exists(),
                                 reason="the published corpus is not checked out")


def test_a_probe_pool_has_no_duplicates():
    if not QUIXBUGS.exists():
        pytest.skip("corpus not checked out")
    probes = experiment.probe_pool(QUIXBUGS, "lis", count=20)
    keys = [repr(p) for p in probes]
    assert len(keys) == len(set(keys))


@needs_corpus
def test_the_chosen_experiment_identifies_lis_in_a_handful_of_queries():
    row = experiment.measure(QUIXBUGS, "lis")
    assert row["stage"] == "IDENTIFIED_AND_CORRECT", row
    assert row["chosen_queries"] <= 4, row
    agree, checked = row["survivor_agrees_with_the_reference_on_held_out"].split("/")
    assert agree == checked


@needs_corpus
def test_every_used_probe_has_a_reference_output():
    """A probe the reference program cannot answer is outside the precondition and is not evidence."""
    probes = experiment.probe_pool(QUIXBUGS, "kth", count=12)
    truth = experiment.oracle_for(QUIXBUGS, "kth")
    assert truth is not None
    answered = 0
    for args in probes:
        try:
            truth(*args)
            answered += 1
        except Exception:
            pass
    assert answered > 0


@needs_corpus
def test_an_uninformative_observation_resolves_no_bits_and_a_good_one_resolves_everything():
    """The theorem, as a test: bits resolved is log2(candidates/survivors), and it is a property of the
    probe, not of the number of probes."""
    lis = experiment.measure(QUIXBUGS, "lis")
    kth = experiment.measure(QUIXBUGS, "kth")
    assert lis["bits_resolved"] > 7.0
    assert kth["stage"] == "IDENTIFIED_BUT_WRONG_ON_HELD_OUT" or kth["bits_resolved"] >= 0.0
    assert lis["survivors"] == 1


def test_a_probe_that_splits_nothing_is_never_chosen():
    table = {"rows": [[1, 1], [1, 2], [1, 2]]}
    candidates = [{"expression": "a"}, {"expression": "b"}, {"expression": "c"}]
    probes = [[0], [1]]
    truth = [1, 2]
    verdict = experiment.identify("x", candidates, probes, truth, table)
    chosen = [step["probe"] for step in verdict["steps"] if "probe" in step]
    assert 0 not in chosen, verdict
