"""A remembered plan learns WHERE it applies, and a failure stops being a global ban.

The defect this pins: `macro_v1` counted successes and failures against a plan keyed by goal
shape. A count cannot say "works here, not there", so two failures in one context erased a plan
that worked in every other context -- the error `macro_v1.note_failure`'s own docstring records
four sightings of.

Both directions are executed, because either alone is satisfiable by a broken store:

  * a store that never withholds anything passes "keeps the plan";
  * a store that always withholds passes "withholds where it fails".

The controls are the load-bearing part. A success-only store must report UNDETERMINED and its
default must admit the state where the plan fails; a failure in the SAME context as the success
must not manufacture a boundary; and a caller passing no context must see historical behaviour.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import macro_v1  # noqa: E402

from a_failure_is_a_context_not_a_ban_probe_20261112 import (  # noqa: E402
    CLAUSES,
    HAS_SIDECAR,
    NO_SIDECAR,
    STEPS,
    run,
)


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Redirect the macro store; the repository's own state is never touched."""
    monkeypatch.setattr(macro_v1, "STATE", tmp_path / "chain_macros_v1.json")
    return macro_v1


# --------------------------------------------------------------------------- the learner

def test_a_success_alone_cannot_produce_a_requirement():
    boundary = APP.learn([(HAS_SIDECAR, True), (HAS_SIDECAR, True)])
    assert boundary.status == APP.UNDETERMINED
    assert boundary.required is None
    assert boundary.survivor_count == 0
    # Nothing is licensed, so nothing may be withheld.
    assert APP.explains_failure(boundary, NO_SIDECAR) is False


def test_no_success_means_nothing_to_scope():
    assert APP.learn([(NO_SIDECAR, False)]).status == APP.UNDETERMINED


def test_empty_evidence_is_undetermined():
    assert APP.learn([]).status == APP.UNDETERMINED


def test_one_success_one_failure_leaves_two_requirements_not_one():
    """The honest size of the version space, and the reason one exposure is not enough."""
    boundary = APP.learn([(HAS_SIDECAR, True), (NO_SIDECAR, False)])
    assert boundary.status == APP.AMBIGUOUS
    assert boundary.survivor_count == 2
    assert boundary.most_general == ("docx_intent_sidecar_present",)
    assert boundary.most_specific == ("docx_intent_sidecar_present", "python_source_present")


def test_a_contrasting_success_identifies_the_requirement_exactly():
    boundary = APP.learn([
        (HAS_SIDECAR, True),
        (NO_SIDECAR, False),
        (frozenset({"docx_intent_sidecar_present"}), True),
    ])
    assert boundary.status == APP.IDENTIFIED
    assert boundary.required == ("docx_intent_sidecar_present",)


def test_withholding_uses_the_least_demanding_survivor_not_the_strictest():
    """If G refuses a state, every survivor refuses it. Using S would manufacture a ban.

    `{sidecar}` and `{sidecar, python}` both survive. A state with the sidecar but no python is
    admitted by G and refused by S. It must NOT be withheld: the evidence does not support that.
    """
    boundary = APP.learn([(HAS_SIDECAR, True), (NO_SIDECAR, False)])
    sidecar_only = frozenset({"docx_intent_sidecar_present"})
    assert APP.admits(boundary.most_general, sidecar_only) is True
    assert APP.admits(boundary.most_specific, sidecar_only) is False
    assert APP.explains_failure(boundary, sidecar_only) is False
    assert APP.explains_failure(boundary, NO_SIDECAR) is True


def test_a_failure_in_the_same_state_as_the_success_explains_nothing():
    boundary = APP.learn([(HAS_SIDECAR, True), (HAS_SIDECAR, False)])
    assert boundary.status == APP.INCONSISTENT
    assert boundary.survivor_count == 0
    assert APP.explains_failure(boundary, HAS_SIDECAR) is False
    assert APP.explains_failure(boundary, NO_SIDECAR) is False


def test_the_enumeration_is_bounded_and_says_so():
    facts = frozenset(f"f{i}" for i in range(6))
    boundary = APP.learn([(facts, True), (frozenset(), False)], max_candidate_facts=3)
    assert boundary.status == APP.BOUNDED
    assert APP.explains_failure(boundary, frozenset()) is False


def test_order_of_evidence_does_not_change_the_answer():
    rows = [(HAS_SIDECAR, True), (NO_SIDECAR, False), (frozenset({"docx_intent_sidecar_present"}), True)]
    answers = {tuple(APP.learn(list(p)).as_row()["required"] or ()) for p in itertools.permutations(rows)}
    assert answers == {("docx_intent_sidecar_present",)}


def test_mapping_context_counts_only_facts_observed_true():
    assert APP.normalise_state({"a": True, "b": False, "c": "true"}) == frozenset({"a"})


def test_the_production_learner_agrees_with_the_measurement_that_motivated_it():
    """One notion of consistency in the tree, not two.

    `what_a_success_teaches_20261112.py` measured 0/200 identification from one success using its
    own version space. The production learner must return the same survivors on the same evidence,
    otherwise the measurement no longer describes the code that runs.
    """
    import what_a_success_teaches_20261112 as probe

    facts = ("f1", "f2", "f3")
    hidden = frozenset({"f1", "f3"})
    states = [frozenset(s) for r in range(len(facts) + 1)
              for s in itertools.combinations(facts, r)]
    rows = [(s, hidden <= s) for s in states]

    space = probe.full_space(facts)
    for state, ok in rows:
        probe.observe(space, state, succeeded=ok)
    expected = {probe.as_set(h) for h in probe.survivors(space)}

    produced = APP.learn(rows)
    assert produced.status == APP.IDENTIFIED
    assert {frozenset(produced.required or ())} == expected


# --------------------------------------------------------------------------- the store

def test_the_counter_only_path_really_does_lose_a_plan_that_works(store):
    """Reproduces the historical defect, so the fix is measured against something real."""
    assert store.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = store.signature(CLAUSES)
    store.note_failure(key)
    store.note_failure(key)
    assert store.lookup(CLAUSES) is None


def test_the_same_outcomes_with_context_keep_the_plan_and_scope_the_refusal(store):
    assert store.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = store.signature(CLAUSES)
    assert store.note_failure(key, context=NO_SIDECAR) is False
    assert store.note_failure(key, context=NO_SIDECAR) is False
    assert store.lookup(CLAUSES) is not None
    assert store.applicable(key, HAS_SIDECAR) is True
    assert store.applicable(key, NO_SIDECAR) is False
    entry = (store._load()["macros"])[key]
    assert int(entry.get("failures") or 0) == 0
    assert int(entry.get("scoped_failures") or 0) == 2


def test_a_scoped_failure_does_not_count_against_the_plan_elsewhere(store):
    """The e-process rule still runs when the evidence cannot separate the contexts."""
    assert store.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = store.signature(CLAUSES)
    store.note_failure(key, context=HAS_SIDECAR)
    entry = (store._load()["macros"])[key]
    assert int(entry.get("failures") or 0) == 1
    assert int(entry.get("scoped_failures") or 0) == 0
    assert store.applicable(key, NO_SIDECAR) is True


def test_callers_passing_no_context_are_unchanged(store):
    assert store.record(CLAUSES, STEPS)
    key = store.signature(CLAUSES)
    entry = (store._load()["macros"])[key]
    assert "evidence" not in entry
    assert store.note_failure(key) is False
    assert store.note_failure(key) is True
    assert store.lookup(CLAUSES) is None


def test_the_evidence_log_is_bounded(store):
    assert store.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = store.signature(CLAUSES)
    for _ in range(APP.MAX_CANDIDATE_FACTS * 2 + macro_v1.MAX_EVIDENCE + 5):
        store.note_failure(key, context=NO_SIDECAR)
    entry = (store._load()["macros"])[key]
    assert len(entry["evidence"]) <= macro_v1.MAX_EVIDENCE
    # The flood must not evict the contrast: the success survives and the plan is still scoped,
    # not banned. A single FIFO window failed exactly here when this test was first written.
    assert any(row["ok"] for row in entry["evidence"])
    assert store.lookup(CLAUSES) is not None
    assert store.applicable(key, HAS_SIDECAR) is True
    assert store.applicable(key, NO_SIDECAR) is False


def test_an_unknown_key_withholds_nothing(store):
    assert store.applicable("no-such-key", NO_SIDECAR) is True


# --------------------------------------------------------------------------- the whole probe

def test_the_probe_holds_in_every_arm():
    summary = run()["summary"]
    assert summary["counter_only_loses_a_plan_that_works"] is True
    assert summary["context_aware_keeps_it"] is True
    assert summary["context_aware_offers_it_where_it_works"] is True
    assert summary["context_aware_withholds_it_where_it_fails"] is True
    assert summary["survivors_after_one_success_one_failure"] == 2
    assert summary["identification_status_after_contrast"] == APP.IDENTIFIED
    assert summary["required_after_contrast"] == ["docx_intent_sidecar_present"]
    assert summary["success_only_is_undetermined"] is True
    assert summary["success_only_admits_the_failing_state"] is True
    assert summary["same_context_invents_no_boundary"] is True
    assert summary["no_context_writes_no_evidence"] is True


def test_the_probe_does_not_touch_the_repositorys_macro_state():
    before = macro_v1.STATE
    original = before.read_bytes() if before.is_file() else None
    run()
    assert macro_v1.STATE == before
    assert (before.read_bytes() if before.is_file() else None) == original


# --------------------------------------------------------------- composition with `where`

def test_an_address_isolates_the_ledger_but_cannot_refuse_a_new_environment(store):
    """What this layer adds on top of the environment-address repair, measured.

    `note_failure(key, where=...)` keeps environment B from deleting A's plan -- but `lookup`
    still offers that plan in B, and an address can say nothing about an environment never seen.
    A requirement over observed facts can refuse both, which is the half an address cannot do.
    """
    assert store.record(CLAUSES, STEPS, where="a.example", context=HAS_SIDECAR)
    key = store.signature(CLAUSES)
    store.note_failure(key, "b.example", context=NO_SIDECAR)
    store.note_failure(key, "b.example", context=NO_SIDECAR)

    # Their guarantee holds: A's knowledge survives B's failures.
    assert store.lookup(CLAUSES) is not None
    entry = (store._load()["macros"])[key]
    assert int(entry.get("successes") or 0) == 1

    # The added guarantee: the plan is refused in the state that lacks the fact, including a
    # state labelled with an environment that has never been observed at all.
    assert store.applicable(key, NO_SIDECAR) is False
    assert store.applicable(key, HAS_SIDECAR) is True


def test_the_two_layers_are_independent(store):
    """Passing only `where` must not write fact evidence or change applicability."""
    assert store.record(CLAUSES, STEPS, where="a.example")
    key = store.signature(CLAUSES)
    store.note_failure(key, "b.example")
    entry = (store._load()["macros"])[key]
    assert "evidence" not in entry
    assert store.applicability(key).status == APP.UNDETERMINED
    assert store.applicable(key, NO_SIDECAR) is True
