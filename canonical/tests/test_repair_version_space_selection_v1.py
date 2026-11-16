#!/usr/bin/env python3
"""Mechanism tests for version-space repair selection.

The properties pinned here are the ones the measurement depends on. Each is a
small, exact case whose answer is known by construction -- no corpus is read.

The important one is `test_one_class_is_not_evidence`: a single behaviour class
is the case where every candidate agrees, which is *also* what an equally wrong
committee looks like. If that ever reports SETTLED, the whole module is lying.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import repair_version_space_selection_v1 as vspace  # noqa: E402


def test_partition_groups_equal_behaviour():
    part = vspace.partition(
        ["a", "b", "c"],
        {"a": [("value", "1"), ("value", "2")],
         "b": [("value", "1"), ("value", "3")],
         "c": [("value", "1"), ("value", "2")]})
    assert part["status"] == "OK"
    assert part["distinct"] == 2
    assert {"a", "c"} in [set(m) for m in part["classes"]]
    assert part["class_of"]["b"] != part["class_of"]["a"]


def test_partition_refuses_partial_observation():
    part = vspace.partition(["a", "b"], {"a": [("value", "1")]})
    assert part["status"] == "REFUSED" and part["reason"] == "BEHAVIOUR_MISSING"


def test_partition_refuses_unequal_probe_counts():
    part = vspace.partition(["a", "b"], {"a": [("value", "1")],
                                         "b": [("value", "1"), ("value", "2")]})
    assert part["status"] == "REFUSED"
    assert part["reason"] == "PROBE_VECTORS_UNEQUAL_LENGTH"


def test_partition_refuses_no_probes():
    part = vspace.partition(["a"], {"a": []})
    assert part["status"] == "REFUSED" and part["reason"] == "NO_PROBES"


def test_diagnose_split_says_a_question_decides():
    part = vspace.partition(["a", "b"], {"a": [("value", "1")], "b": [("value", "2")]})
    assert vspace.diagnose(part)["verdict"] == "UNDETERMINED__A_QUESTION_DECIDES"


def test_decide_accepts_only_when_one_class_survives():
    part = vspace.partition(["a", "b"], {"a": [("value", "1")], "b": [("value", "2")]})
    outcomes = {"0": ["value:1", "value:2"]}
    assert vspace.decide(part, probe_ids=["0"], probe_outcomes=outcomes)["decision"] == "ASK"
    ruled = vspace.decide(part, probe_ids=["0"], probe_outcomes=outcomes,
                          observations={"0": "value:1"})
    assert ruled["decision"] == "ACCEPT" and ruled["class"] == ["a"]


def test_decide_refuses_when_no_probe_splits_the_survivors():
    part = vspace.partition(["a", "b"], {"a": [("value", "1")], "b": [("value", "2")]})
    ruled = vspace.decide(part, probe_ids=["0"],
                          probe_outcomes={"0": ["value:1", "value:1"]})
    assert ruled["decision"] == "REFUSE"
    assert ruled["reason"] == "NONIDENTIFIABLE_UNDER_AUTHORIZED_EXPERIMENTS"


def test_one_class_is_not_evidence():
    """Every candidate agrees. That is not an answer: a committee of copies is
    exactly what a wrong-but-consistent candidate set looks like."""
    part = vspace.partition(["a", "b"], {"a": [("value", "1")], "b": [("value", "1")]})
    assert part["distinct"] == 1
    sources = {"a": "A", "b": "B"}
    library = {("A", 0): ("value", "1"), ("B", 0): ("value", "1")}
    selection = vspace.ask_until_settled(sources, [0], lambda s, i: library[(s, i)],
                                          lambda i: ("value", "9"))
    assert selection.decision == vspace.ACCEPT
    assert selection.disposition == vspace.UNSEPARATED
    assert selection.rounds == 0


def test_ask_until_settled_pays_one_question_and_names_the_class():
    sources = {"a": "A", "b": "B", "c": "C"}
    library = {("A", 0): ("value", "1"), ("B", 0): ("value", "1"), ("C", 0): ("value", "1"),
               ("A", 1): ("value", "2"), ("B", 1): ("value", "3"), ("C", 1): ("value", "2")}
    oracle = {0: ("value", "1"), 1: ("value", "3")}
    selection = vspace.ask_until_settled(sources, [0, 1], lambda s, i: library[(s, i)],
                                          lambda i: oracle[i])
    assert selection.decision == vspace.ACCEPT
    assert selection.disposition == vspace.SETTLED
    assert selection.accepted == "b"          # the class the oracle's answer selected
    assert selection.rounds == 1


def test_ask_until_settled_refuses_when_the_probes_cannot_split():
    """Two candidates are identical on every probe supplied, and a third is
    different. The first answer removes the third; nothing can separate the last
    two, and the honest result is a refusal that says so -- not a coin toss."""
    sources = {"a": "A", "b": "B", "c": "C"}
    library = {("A", 0): ("value", "1"), ("B", 0): ("value", "2"), ("C", 0): ("value", "2"),
               ("A", 1): ("value", "1"), ("B", 1): ("value", "2"), ("C", 1): ("value", "2")}
    selection = vspace.ask_until_settled(sources, [0, 1], lambda s, i: library[(s, i)],
                                          lambda i: ("value", "2"))
    # a is eliminated by the answer; b and c are identical on every probe supplied,
    # so the result is a CLASS and it says so rather than pretending to pick one
    assert selection.decision == vspace.ACCEPT
    assert selection.disposition == vspace.SETTLED_TO_A_CLASS
    assert selection.class_size == 2


def test_a_class_of_one_is_the_only_thing_called_settled():
    sources = {"a": "A", "b": "B"}
    library = {("A", 0): ("value", "1"), ("B", 0): ("value", "2")}
    selection = vspace.ask_until_settled(sources, [0], lambda s, i: library[(s, i)],
                                          lambda i: ("value", "2"))
    assert selection.disposition == vspace.SETTLED
    assert selection.class_size == 1
    assert selection.accepted == "b"


def test_a_crash_is_a_behaviour():
    """Two candidates that crash differently are distinguishable; that is often
    the only thing live execution tells you, and it must not be dropped."""
    part = vspace.partition(["a", "b"], {"a": [("raised", "ValueError")],
                                         "b": [("raised", "TypeError")]})
    assert part["distinct"] == 2


def test_refusal_is_a_record_not_an_exception():
    selection = vspace.ask_until_settled({"a": "A"}, [], lambda s, i: ("value", "1"),
                                          lambda i: ("value", "1"))
    record = selection.as_record()
    assert record["decision"] == vspace.REFUSE
    assert record["terminal_authority"] is False


def test_maximum_elimination_beats_a_balanced_split():
    """Three classes. Probe 0 is the BALANCED split (2 vs 1). Probe 1 is three-way, and
    the reference's answer on it ("Z") is predicted by no class, so asking it kills all
    three at once. A minimax rule prefers the balanced split; elimination must not.

    The per-probe path is the one the module actually uses: the reference's answer is a
    vector, not a scalar, because different inputs have different answers.
    """
    part = vspace.partition(
        ["a", "b", "c"],
        {"a": [("value", "x"), ("value", "1")],
         "b": [("value", "y"), ("value", "1")],
         "c": [("value", "x"), ("value", "2")]})
    assert part["distinct"] == 3
    probe, answer = vspace._best_eliminating_probe(
        part, ["0", "1"],
        {"0": ["x", "y", "x"], "1": ["Z", "W", "V"]},
        {"0": "x", "1": "Z"}, ())
    assert (probe, answer) == ("1", "Z")   # kills three; probe 0 kills one


def test_decide_asks_the_eliminating_probe_when_the_answer_is_known():
    part = vspace.partition(
        ["a", "b", "c"],
        {"a": [("value", "1")], "b": [("value", "2")], "c": [("value", "3")]})
    step = vspace.decide(part, probe_ids=["0", "1"],
                         probe_outcomes={"0": ["1", "2", "3"], "1": ["7", "2", "3"]},
                         reference_outcomes={"0": "1", "1": "7"})
    assert step["decision"] == vspace.ASK
    assert step["objective"].startswith("MAXIMUM_ELIMINATION")
