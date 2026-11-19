"""Tests for agreement-is-not-equivalence.

The tests do not trust the receipt. They drive the statements, the envelope and the machines themselves,
and they pin the two things the round rests on: that `created_once` is not `at_least_once`, and that the
witness separating the two survivors is a transition no machine in the tree can perform.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parents[1]))

import agreement_is_not_equivalence_v1 as aq  # noqa: E402
import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

RECEIPT = (pathlib.Path(__file__).resolve().parents[1] / "verification"
           / "AGREEMENT_IS_NOT_EQUIVALENCE_20261119_V1.json")

CREATED_ONCE = "created_once[" + env.PROBE_NEW + "]"
SURVIVOR = "monotone[" + env.PROBE_NEW + "] ∧ final:count[" + env.PROBE_NEW + "]==1"


def terms() -> dict:
    """The union grammar's terms, built from one real run of the fitted machines -- not hand-written."""
    machine = vocab.MACHINES["FILESYSTEM"](pathlib.Path("/tmp/agreement-terms"))
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    traces = runs.traces_for(machine, aq.ARGS, depth=2)
    whole, end_only = runs.run_terms(traces)
    return {term.text: term for term in list(whole) + list(end_only)}


def trace_of(counts) -> tuple:
    return tuple(aq.state_with(count) for count in counts)


# ------------------------------------------------------------------------------------------------------
# what the two statements actually say
# ------------------------------------------------------------------------------------------------------

def test_the_grammar_contains_both_survivors_and_the_conjuncts():
    """A statement is a term or a PAIR of terms; the survivor is a pair, and its conjuncts must be terms
    in their own right -- that is what makes it a conjunction rather than one hand-written predicate."""
    index = terms()
    for text in (CREATED_ONCE, "monotone[" + env.PROBE_NEW + "]",
                 "final:count[" + env.PROBE_NEW + "]==1", "at_least_once[" + env.PROBE_NEW + "]"):
        assert text in index, text
    assert SURVIVOR not in index
    assert [part.strip() for part in SURVIVOR.split("∧")] == [
        "monotone[" + env.PROBE_NEW + "]", "final:count[" + env.PROBE_NEW + "]==1"]


def test_created_once_is_not_at_least_once():
    index = terms()
    gone = trace_of([0, 1, 0])
    assert index["at_least_once[" + env.PROBE_NEW + "]"].holds(gone) is True
    assert index[CREATED_ONCE].holds(gone) is False


def test_created_once_holds_on_a_single_jump_of_two():
    index = terms()
    two_at_once = trace_of([0, 2])
    assert index[CREATED_ONCE].holds(two_at_once) is True
    assert quotient.portable_judge(two_at_once) is False


def test_the_conjunction_is_evaluated_as_every_conjunct():
    index = terms()
    # monotone holds (1 stays 1) but the final count is 2, so the conjunction must be false
    assert aq.holds(SURVIVOR, trace_of([0, 1, 2]), index) is False
    assert aq.holds(SURVIVOR, trace_of([0, 1, 1]), index) is True


# ------------------------------------------------------------------------------------------------------
# the envelope is a quotient, not a sample
# ------------------------------------------------------------------------------------------------------

def test_the_envelope_starts_at_zero_and_never_goes_negative():
    histories = aq.envelope(max_length=4, max_jump=3)
    assert histories
    assert all(len(trace[0]) == 0 for trace in histories)
    assert all(len(state) >= 0 for trace in histories for state in trace)


def test_the_statements_read_only_the_count():
    """Two histories with the same counts are the same input: that is why an envelope check is a proof."""
    index = terms()
    counts = [0, 1, 1, 2]
    plain = trace_of(counts)
    renamed = tuple(tuple(("other_holder", content) for _ident, content in state) for state in plain)
    for text in (CREATED_ONCE, SURVIVOR):
        assert aq.holds(text, plain, index) == aq.holds(text, renamed, index)
    assert quotient.portable_judge(plain) == quotient.portable_judge(renamed)


def test_exactly_one_statement_is_equivalent_over_the_envelope():
    index = terms()
    histories = aq.envelope(max_length=5, max_jump=3)
    judge = [quotient.portable_judge(trace) for trace in histories]
    created = [aq.holds(CREATED_ONCE, trace, index) for trace in histories]
    survivor = [aq.holds(SURVIVOR, trace, index) for trace in histories]
    assert survivor == judge
    assert created != judge


def test_the_witness_is_the_step_no_run_shows():
    index = terms()
    two_at_once = trace_of([0, 2])
    assert aq.holds(CREATED_ONCE, two_at_once, index) is True
    assert aq.holds(SURVIVOR, two_at_once, index) is False
    assert quotient.portable_judge(two_at_once) is False


# ------------------------------------------------------------------------------------------------------
# the machines: the precondition, and the alphabet that cannot exhibit the witness
# ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["TARBALL", "FILESYSTEM", "SQLITE", "GIT", "SORT"])
def test_the_precondition_holds_on_every_machine(name, tmp_path):
    machine = vocab.MACHINES[name](tmp_path / name.lower())
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    assert runs._count(tuple(machine.read()), env.PROBE_NEW) == 0


@pytest.mark.parametrize("name", ["TARBALL", "FILESYSTEM", "SQLITE", "GIT", "SORT"])
def test_no_atom_adds_two_copies_in_one_step(name, tmp_path):
    machine = vocab.MACHINES[name](tmp_path / name.lower())
    machine.root.mkdir(parents=True, exist_ok=True)
    for atom in machine.atoms:
        machine.reset()
        before = runs._count(tuple(machine.read()), env.PROBE_NEW)
        env.execute(atom, machine, aq.ARGS)
        after = runs._count(tuple(machine.read()), env.PROBE_NEW)
        assert after - before < 2, (name, atom.ident, before, after)


# ------------------------------------------------------------------------------------------------------
# the measurement, and the receipt it produced
# ------------------------------------------------------------------------------------------------------

def test_the_measurement_meets_every_claim(tmp_path):
    receipt = aq.measure(tmp_path / "receipt.json", quick=True)
    assert [key for key, value in receipt["verdict"].items() if not value["MET"]] == []
    k3 = receipt["verdict"]["K3_the_proof_finds_the_difference_that_no_run_shows"]
    assert k3["witness"]["counts"] == [0, 2]
    assert k3["witness"]["statement_says"] is True
    assert k3["witness"]["judge_says"] is False
    k2 = receipt["verdict"]["K2_agreement_is_total_and_still_not_identity"]
    assert all(row["ALL_FIVE"]["differs_from_the_judge"] == 0 for row in k2["per_statement"].values())
    assert receipt["verdict"]["K5_the_price_is_zero_questions_corrected"]["questions_needed_here"] == 0


def test_the_committed_receipt_meets_every_claim():
    receipt = json.loads(RECEIPT.read_text())
    assert [key for key, value in receipt["verdict"].items() if not value["MET"]] == []
    assert sum(receipt["pools"].values()) == 983
    assert receipt["pools"]["TARBALL"] == 231
    assert receipt["verdict"]["K6_permanence_is_a_checkable_precondition"]["survivor"] == SURVIVOR
    assert receipt["correction_to_the_previous_round"]["what_it_said"].endswith(
        "closed by language, not by experience")
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0
    assert receipt["limits"]


def test_the_producer_has_no_model_no_parameters_no_network():
    source = pathlib.Path(aq.__file__).read_text(encoding="utf-8")
    for forbidden in ("import requests", "import urllib", "import socket", "import torch",
                      "import openai", "from openai", "http://", "https://"):
        assert forbidden not in source, forbidden
