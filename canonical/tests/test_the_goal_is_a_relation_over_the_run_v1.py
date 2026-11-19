"""The hardest material this round has: real runs, the two vocabularies, and the failure it kept.

These tests do not re-check what the previous round proved. They run the machines, build the two
grammars, and assert the asymmetries this round claims -- plus the one it declared and did NOT meet,
so that a future edit cannot quietly turn it green.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
sys.path.insert(0, str(TOOLS))

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as tool  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_GOAL_IS_A_RELATION_OVER_THE_RUN_20261127_V1.json"


def _machine(name: str) -> env.Machine:
    machine = vocab.MACHINES[name](pathlib.Path(tempfile.mkdtemp(prefix=f"test-{name.lower()}-")))
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    return machine


def _filesystem_goal() -> tuple[env.Machine, tool.RunGoal, list[tool.Trace], list[bool]]:
    machine = _machine("FILESYSTEM")
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "backup"}
    goal = tool.RunGoal("FILESYSTEM", "copy before you move", args,
                        lambda t: any(tool._count(state, env.PROBE_OLD) >= 2 for state in t))
    traces = tool.traces_for(machine, args, depth=2)
    return machine, goal, traces, [goal.judge(trace) for trace in traces]


def test_the_machine_is_read_after_every_step_and_a_trace_is_a_run() -> None:
    machine, _goal, traces, _labels = _filesystem_goal()
    two_step = [trace for trace in traces if len(trace) == 3 and trace[1] != trace[2]]
    assert two_step, "no two-step run changed the machine; the trace is not reading the run"
    assert all(len(trace) == 3 for trace in two_step)
    # the first state of every trace is the machine before any action: the reset state
    assert len({trace[0] for trace in traces}) == 1


def test_the_final_state_vocabulary_has_no_hypothesis_when_a_group_is_present() -> None:
    _machine_, _goal, traces, labels = _filesystem_goal()
    groups: dict[tool.State, list[int]] = {}
    for index, trace in enumerate(traces):
        groups.setdefault(trace[-1], []).append(index)
    split = [indices for indices in groups.values() if len({labels[i] for i in indices}) > 1]
    assert split, "this pool no longer contains two runs with one final state and two judgments"

    whole_terms, end_terms = tool.run_terms(traces)
    whole, end_only = tool.Space(whole_terms, traces), tool.Space(end_terms, traces)
    accepted = sum(1 << i for i, label in enumerate(labels) if label)
    rejected = sum(1 << i for i, label in enumerate(labels) if not label)

    assert end_only.version_space(accepted, rejected) == []
    assert whole.version_space(accepted, rejected) != []
    # and the reason is structural, not bad luck: no final-state term moves inside a group
    assert tool.separation_is_structural(end_only, whole, split)[
        "final_state_terms_that_disagree_inside_a_group"] == 0


def test_a_goal_outside_the_grammar_is_refused_not_rejected() -> None:
    """The trace grammar has no notion of how many steps a run took. That is a real gap.

    A goal about it must come back as `undecided` (no hypothesis at all), never as a rejection --
    otherwise the agent would be silently asserting the opposite of a goal it cannot express.
    """
    _machine_, _goal, traces, _labels = _filesystem_goal()
    labels = [len(trace) == 2 for trace in traces]          # one step only: not in the grammar
    whole_terms, _end_terms = tool.run_terms(traces)
    space = tool.Space(whole_terms, traces)
    accepted = sum(1 << i for i, label in enumerate(labels) if label)
    rejected = sum(1 << i for i, label in enumerate(labels) if not label)
    survivors = space.version_space(accepted, rejected)
    assert survivors == []
    assert tool.predict(space, 0, survivors) is None


def test_the_committed_receipt_is_not_stale() -> None:
    """Re-run the round and demand the same verdicts. A green flip is a failure here."""
    committed = json.loads(RECEIPT.read_text())
    with tempfile.TemporaryDirectory() as where:
        fresh_path = pathlib.Path(where) / "receipt.json"
        tool.main(["--receipt", str(fresh_path)])
        fresh = json.loads(fresh_path.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert [row["runs"] for row in fresh["rows"]] == [row["runs"] for row in committed["rows"]]


def test_the_declared_failure_is_kept_and_its_cause_is_reproducible() -> None:
    """B3 said 'zero false rejects'. It is not met: one held-out run is lost. Keep it that way.

    The mechanism is named rather than excused: dropping that run lets a conjunctive hypothesis
    survive that rejects it, so the intersection -- which is sound -- is not complete.
    """
    receipt = json.loads(RECEIPT.read_text())
    b3 = receipt["verdict"]["B3_the_run_goal_is_not_empty_and_sound"]
    assert b3["MET"] is False
    assert b3["leave_one_out_false_accepts"] == 0
    assert b3["leave_one_out_false_rejects"] == 1

    machine = _machine("FILESYSTEM")
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "backup"}
    traces = tool.traces_for(machine, args, depth=3)
    labels = [any(tool._count(state, env.PROBE_OLD) >= 2 for state in trace) for trace in traces]
    whole_terms, _end_terms = tool.run_terms(traces)
    space = tool.Space(whole_terms, traces)
    true_term = next(term for term in whole_terms if term.text == "two_copies[probe_seed_content]")
    assert [true_term.holds(trace) for trace in traces] == labels

    held_out = []
    for index in range(len(traces)):
        accepted = sum(1 << i for i, label in enumerate(labels) if label and i != index)
        rejected = sum(1 << i for i, label in enumerate(labels) if not label and i != index)
        prediction = tool.predict(space, index, space.version_space(accepted, rejected))
        if prediction is False and labels[index]:      # a rejection of a run the user accepted
            held_out.append(index)
    assert len(held_out) == 1, f"the loss is no longer singular: {held_out}"
    lost = held_out[0]
    survivors = space.version_space(
        sum(1 << i for i, label in enumerate(labels) if label and i != lost),
        sum(1 << i for i, label in enumerate(labels) if not label and i != lost))
    assert tool.predict(space, lost, survivors) is False, "the declared failure no longer reproduces"
    true_mask = space.masks_of[(whole_terms.index(true_term),)]
    assert true_mask in survivors, "the true goal was eliminated; this is a different failure"
    blockers = [combo for combo in space.combos
                if space.masks_of[combo] in survivors and not space.judge(space.masks_of[combo], lost)]
    assert blockers, "nothing in the version space rejects the lost run"
    assert any("monotone[probe_new_content]" in [whole_terms[i].text for i in combo]
               for combo in blockers)


def test_every_hypothesis_literal_is_one_the_grammar_produced() -> None:
    _machine_, _goal, traces, labels = _filesystem_goal()
    whole_terms, end_terms = tool.run_terms(traces)
    texts = {term.text for term in whole_terms} | {term.text for term in end_terms}
    space = tool.Space(whole_terms, traces)
    accepted = [1 << i for i, label in enumerate(labels) if label]
    rejected = [1 << i for i, label in enumerate(labels) if not label]
    smallest = space.smallest(accepted, rejected)
    assert smallest and set(smallest) <= texts
    for combo in space.combos:
        assert all(space.terms[index].text in texts for index in combo)
