#!/usr/bin/env python3
"""Consistency is evidence; equivalence is the goal.

Every case here executes real statements over real traces against a real
judge. Nothing is patched, pinned, or stubbed. No model, no network.
"""
from __future__ import annotations

from canonical.swe_kernel import consistency_vs_equivalence_v1 as C
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
    VerifiedSkillStore,
    anti_unify_code_rule,
    apply_crystallized_code_rule,
)
from canonical.tools.lesson_admission_harm_measure_20261113_v1 import (
    falsification_victim,
    transfer_victim,
)

import pathlib
import tempfile


# ---------------------------------------------------------------------------
# the agreement-is-not-equivalence scenario, executed
# ---------------------------------------------------------------------------

class OneCopyCounter(C.ObservationModel):
    """A counter whose alphabet can only add exactly 1 per step.

    Under this alphabet the witness trace ``[0, 2]`` (one step that adds two
    copies) is not producible at any depth: the ambiguity between
    ``created_once`` and the judge is structural, not statistical.
    """

    def initial_states(self):
        return [0]

    def actions(self, state):
        return ["inc"]

    def step(self, state, action):
        return state + 1

    def precondition_holds(self, initial_state):
        return initial_state == 0


def increases(trace):
    ev = list(trace.events)
    return sum(1 for i in range(1, len(ev)) if ev[i] > ev[i - 1])


def monotone(trace):
    ev = list(trace.events)
    return all(ev[i] >= ev[i - 1] for i in range(1, len(ev)))


def created_once(trace):
    return increases(trace) == 1 and monotone(trace)


def final_one(trace):
    ev = list(trace.events)
    return bool(ev) and monotone(trace) and ev[-1] == 1


def test_repetition_buys_zero_bits():
    """Two statements agree on every run; repeating the runs changes nothing."""
    runs = [C.Trace((0, 1)), C.Trace((0, 1, 1))]
    first = C.consistent_class([created_once, final_one], runs, final_one)
    second = C.consistent_class([created_once, final_one], runs * 50, final_one)
    assert len(first) == 2
    assert first == second
    assert C.class_bits(len(first)) == 1.0  # one bit still unresolved


def test_equivalence_proven_within_the_declared_model():
    """The one-copy alphabet can never emit [0, 2], so equivalence holds."""
    result = C.prove_admission(
        created_once, final_one, OneCopyCounter(), max_depth=6,
        precondition_name="initial count == 0",
    )
    assert result.kind == C.EQUIVALENT_UNDER_PRECONDITION
    assert result.witness is None
    assert result.precondition == "initial count == 0"
    assert result.traces_checked > 0


def test_counterexample_found_when_the_alphabet_can_emit_it():
    """An alphabet that can add two in one step exhibits the witness at depth 1."""

    class TwoCopyCounter(C.ObservationModel):
        def initial_states(self):
            return [0]

        def actions(self, state):
            return ["inc", "inc2"]

        def step(self, state, action):
            return state + (1 if action == "inc" else 2)

        def precondition_holds(self, initial_state):
            return initial_state == 0

    result = C.prove_admission(
        created_once, final_one, TwoCopyCounter(), max_depth=1,
        precondition_name="initial count == 0",
    )
    assert result.kind == C.COUNTEREXAMPLE
    assert list(result.witness.events)[:2] == [0, 2]
    assert result.traces_checked >= 2


def test_unknown_when_the_trace_space_exceeds_the_cap():
    """The prover refuses to guess: an uncapped space returns UNKNOWN."""

    class InfiniteCounter(C.ObservationModel):
        def initial_states(self):
            return [0]

        def actions(self, state):
            return ["inc"]

        def step(self, state, action):
            return state + 1

        def precondition_holds(self, initial_state):
            return initial_state == 0

    result = C.prove_admission(
        created_once, final_one, InfiniteCounter(), max_depth=6, trace_cap=2,
    )
    assert result.kind == C.UNKNOWN
    assert "TRACE_SPACE_EXCEEDS_CAP" in result.reason


# ---------------------------------------------------------------------------
# code-rule specialization: the edited program vs the judge's spec
# ---------------------------------------------------------------------------

def _boundary_rule():
    return anti_unify_code_rule(
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        language="python",
    )


def strict_spec(_source, point):
    return point < 100


def inclusive_spec(_source, point):
    return point <= 100


def test_code_rule_counterexample_is_a_named_witness():
    """The <= 100 -> < 100 lesson disagrees with the inclusive spec at point 100."""
    rule = _boundary_rule()
    result = C.prove_code_rule(
        rule,
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        inclusive_spec,
        probes=(0, 99, 100, 101),
    )
    assert result.kind == C.COUNTEREXAMPLE
    assert list(result.witness.events)[3] is False  # actual value at probe 100
    assert result.traces_checked == 3  # 0, 99 agree; 100 stops it


def test_code_rule_equivalence_under_the_right_judge():
    """The same lesson is equivalent to the strict spec on every supplied probe."""
    rule = _boundary_rule()
    result = C.prove_code_rule(
        rule,
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        strict_spec,
        probes=(0, 99, 100, 101),
    )
    assert result.kind == C.EQUIVALENT_UNDER_PRECONDITION
    assert result.traces_checked == 4


def test_combined_admission_verdict_requires_both_evidence_and_proof():
    gate_admit = {"verdict": "ADMIT", "reason": None}

    eq_proof = C.ProofResult(
        kind=C.EQUIVALENT_UNDER_PRECONDITION,
        reason="NO_DISAGREEING_TRACE_IN_DECLARED_MODEL",
        precondition="initial count == 0",
        traces_checked=4,
    )
    merged = C.combined_admission_verdict(gate_admit, eq_proof)
    assert merged["verdict"] == "ADMIT"
    assert merged["reason"] == "ADMIT_WITH_EQUIVALENCE_PROOF"

    witness_trace = C.Trace((0, 2))
    eq_refuted = C.ProofResult(
        kind=C.COUNTEREXAMPLE,
        reason="STATEMENT_DISAGREES_WITH_JUDGE",
        witness=witness_trace,
        traces_checked=2,
    )
    merged = C.combined_admission_verdict(gate_admit, eq_refuted)
    assert merged["verdict"] == "REJECT"
    assert merged["reason"].startswith("EQUIVALENCE_REFUTED:witness=")
    assert merged["witness"]["witness_sha256"] == witness_trace.sha256()

    eq_unknown = C.ProofResult(
        kind=C.UNKNOWN,
        reason="TRACE_SPACE_EXCEEDS_CAP (cap=2, checked=3)",
        traces_checked=3,
        trace_cap=2,
    )
    merged = C.combined_admission_verdict(gate_admit, eq_unknown)
    assert merged["verdict"] == "REFINE"
    assert merged["reason"].startswith("EQUIVALENCE_UNDECIDED:")


# ---------------------------------------------------------------------------
# end-to-end: the crystallizer admits only with held-out repair AND equivalence
# ---------------------------------------------------------------------------

def test_crystallizer_refuses_a_rule_that_equivocation_refutes(tmp_path):
    """Held-out evidence repairs the strict victim, but the inclusive judge
    exposes point 100 as a counterexample: nothing is written."""
    store = VerifiedSkillStore(db_path=tmp_path / "skills.sqlite", seed=False)
    taught = store.crystallize_code_fix(
        before_snippet="def classify(x):\n    return x <= 100\n",
        after_snippet="def classify(x):\n    return x < 100\n",
        language="python",
        error_class="BOUNDARY",
        oracle=strict_spec,
        probes=(0, 99, 100, 101),
        admission_victims=[transfer_victim(), falsification_victim()],
        goal_judge=inclusive_spec,
        equivalence_probes=(0, 99, 100, 101),
    )
    assert taught["crystallized"] is False
    assert taught["reason"].startswith("ADMISSION_EQUIVALENCE_REFUTED:")
    assert "equivalence" in taught
    assert taught["equivalence"]["kind"] == C.COUNTEREXAMPLE
    conn = __import__("sqlite3").connect(tmp_path / "skills.sqlite")
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )]
    count = 0
    if "crystallized_skills" in tables:
        count = len(conn.execute("SELECT skill_id FROM crystallized_skills").fetchall())
    conn.close()
    assert count == 0


def test_crystallizer_admits_when_held_out_evidence_and_equivalence_agree(tmp_path):
    store = VerifiedSkillStore(db_path=tmp_path / "skills.sqlite", seed=False)
    taught = store.crystallize_code_fix(
        before_snippet="def classify(x):\n    return x <= 100\n",
        after_snippet="def classify(x):\n    return x < 100\n",
        language="python",
        error_class="BOUNDARY",
        oracle=strict_spec,
        probes=(0, 99, 100, 101),
        admission_victims=[transfer_victim(), falsification_victim()],
        goal_judge=strict_spec,
        equivalence_probes=(0, 99, 100, 101),
        precondition_name="boundary spec: under 100 excludes 100",
    )
    assert taught["crystallized"] is True, taught.get("reason")
    rows = __import__("sqlite3").connect(tmp_path / "skills.sqlite") \
        .execute("SELECT pattern_json FROM crystallized_skills").fetchall()
    assert len(rows) == 1
    import json
    rule = json.loads(rows[0][0])
    assert rule["admission"]["verdict"] == "ADMIT"
    eq = rule["equivalence"]
    assert eq["kind"] == C.EQUIVALENT_UNDER_PRECONDITION
    assert eq["precondition"] == "boundary spec: under 100 excludes 100"
    assert eq["traces_checked"] == 4
