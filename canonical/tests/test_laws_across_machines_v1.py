#!/usr/bin/env python3
"""Laws do not cross machines, and the reason is measured: the keys are not lifted.

Four source:target pairs, alignment derived from behaviour (never hand-written):

    A  target only              58 predictions,  6 wrong, accuracy 0.906, coverage 0.136
    B  transferred               5 predictions,  2 wrong, accuracy 0.714, coverage 0.023
    B' shuffled alignment        3 predictions,  0 wrong, accuracy 1.000, coverage 0.014  <- its own null
    C  transferred + refined    42 predictions,  6 wrong, accuracy 0.875

10 of 16 source laws have no counterpart KEY anywhere in the target, because a law's key is a
projection value over ground names (`GIT_A1`, `probe_seed_content`) and ground names differ per machine.
A law that says "in every state with these row identities" cannot apply to a machine whose rows have
other identities, however similar its behaviour.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import laws_across_machines_v1 as xm  # noqa: E402

ARTIFACT = (REPO / "canonical" / "verification" / "LAWS_ACROSS_MACHINES_20261124_V1.json")


def test_the_alignment_is_derived_from_behaviour_not_written_down():
    """`align` must produce a bijection from fingerprints alone. If it ever needed a table of pairs, the
    transfer claim would be a hand-written world fact."""
    source = xm.Prints([("A1", (("r1", "c1"),), (("r1", "c1"), ("r2", "c1")))])
    target = xm.Prints([("Z9", (("q1", "c9"),), (("q1", "c9"), ("q2", "c9")))])
    mapping = xm.align(source, target)
    assert mapping == {"A1": "Z9"}, "different names, same behaviour, must align"
    # and it must not invent a partner it has no evidence for
    assert len(set(mapping.values())) == len(mapping)


def test_a_law_only_crosses_if_its_key_exists_in_the_target():
    """The mechanism, as a unit test rather than a paragraph: translation is a rename, and a rename does
    not turn `IDENT` keys into a relation the target shares."""
    law = xm.width.Law("GIT_A1", "IDENT", ("GIT_A1", "GIT_A2"), ((), ()), support=2,
                       witness=(("GIT_A1", "x"),))
    translated = xm.translate([law], {"GIT_A1": "LS_A1"})
    assert translated[0].atom == "LS_A1"
    assert translated[0].key == ("GIT_A1", "GIT_A2"), "the KEY is untouched by translation"
    assert not translated[0].admits((("LS_A1", "x"), ("LS_A2", "y"))), (
        "so it refuses every target state -- which is the finding")


def test_transfer_does_not_beat_the_target_learning_alone():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    a, b = summary["A_target_only"], summary["B_transferred"]
    assert b["predictions"] < a["predictions"] / 5
    assert b["accuracy"] < a["accuracy"]
    assert summary["verdicts"]["transferred_laws_are_more_accurate_than_target_only"] is False


def test_the_transferred_arm_is_indistinguishable_from_its_own_null():
    """The test that stops 'transfer helped a little' from being claimed on noise: shuffling the
    alignment produces the same reach, and a BETTER accuracy on seven transitions."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    b, null = summary["B_transferred"], summary["B_shuffled_alignment"]
    assert abs(b["predictions"] - null["predictions"]) <= 3
    assert summary["verdicts"]["the_derived_alignment_beats_a_shuffled_one"] is False


def test_the_block_is_naming_and_that_is_recorded():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["key_misses"] > summary["source_laws"] / 2
    assert summary["verdicts"]["the_blocks_is_naming_not_evidence"] is True
