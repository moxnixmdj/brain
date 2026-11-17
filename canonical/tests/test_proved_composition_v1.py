#!/usr/bin/env python3
"""Compose only what is proved — the five checks, on the measured cases.

The first test is the measured defect itself (`SKILLS_DONT_COMPOSE_20261112_V1.md`):
two rules, each accepted by the tree's own crystallizer, which cancel each other.
`skill_sequence_verify_v1` catches it post-hoc in the text; this file asserts the
composition rule catches it with the same name, and — more importantly — that it
refuses BEFORE execution the case no textual post-hoc check can refuse: a second
operation whose premise is already dead in the world the first one left.

If `test_dead_premise_refuses_before_execution` ever passes by accident (apply called,
then a refusal), the `applied: False` assertion is the thing that fails. That
assertion is the whole module.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

from canonical.swe_kernel import proved_composition_v1 as P
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

FORWARD_BEFORE = "def f(x):\n    return x <= 10\n"
FORWARD_AFTER = "def f(x):\n    return x < 10\n"
BACKWARD_BEFORE = "def f(x):\n    return x < 10\n"
BACKWARD_AFTER = "def f(x):\n    return x <= 10\n"


def _crystallize(tmp_path: pathlib.Path, pairs: list[tuple[str, str, str]]) -> list[dict]:
    db = tmp_path / "s.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    for before, after, error_class in pairs:
        result = store.crystallize_code_fix(before_snippet=before, after_snippet=after,
                                            language="python", error_class=error_class)
        assert result.get("crystallized") is True, result
    conn = sqlite3.connect(str(db))
    try:
        return [json.loads(row[0]) for row in
                conn.execute("SELECT pattern_json FROM crystallized_skills")]
    finally:
        conn.close()


def _op(op_id: str, *, premise=None, apply=None, prove=None, survive=None) -> P.ProvedOperation:
    return P.ProvedOperation(
        op_id=op_id,
        premise=premise or (lambda _state: None),
        apply=apply or (lambda state: state),
        prove=prove or (lambda state: (True, "ok")),
        survive=survive,
    )


# --------------------------------------------------------------------------- #
# the measured no-op pair — same defect, caught by the composition rule
# --------------------------------------------------------------------------- #
def test_measured_no_op_pair_is_refused_and_named(tmp_path):
    rules = _crystallize(tmp_path, [
        (FORWARD_BEFORE, FORWARD_AFTER, "A"),
        (BACKWARD_BEFORE, BACKWARD_AFTER, "B"),
    ])
    outcome = P.compose(FORWARD_BEFORE, [P.rule_op("A", rules[0]),
                                         P.rule_op("B", rules[1])])

    assert outcome["verdict"] == P.REVERTED
    assert outcome["reason"] == "STEP_REVERTED_EARLIER_STATE:step2"
    assert outcome["reverted_to_step"] == 0
    assert outcome["steps"][0]["premise"] == "HELD"
    assert outcome["steps"][1]["premise"] == "HELD"   # B COULD fire — it fired and undid A
    assert outcome["steps"][1]["outcome"] == "REVERTED"
    assert outcome["result"] == FORWARD_BEFORE        # net change none


def test_genuine_rule_chain_passes_with_receipts(tmp_path):
    rules = _crystallize(tmp_path, [
        (FORWARD_BEFORE, FORWARD_AFTER, "A"),
        ("def f(x):\n    return x < 10\n", "def f(x):\n    return x < 11\n", "C"),
    ])
    outcome = P.compose(FORWARD_BEFORE, [P.rule_op("A", rules[0]),
                                         P.rule_op("C", rules[1])])

    assert outcome["verdict"] == P.PASS, outcome
    assert outcome["result"] == "def f(x):\n    return x < 11\n"
    assert outcome["steps_applied"] == 2
    step = outcome["steps"][1]
    assert step["outcome"] == "CHANGED"
    assert step["proof"]                      # a proof reason is on every step
    assert step["produced_sha256"]
    # A's survival predicate (pattern `<=` stays gone) held after C advanced the line
    assert step["prior_survived"][0]["holds"] is True
    assert step["prior_survived"][0]["via"] == "survive"


def test_rule_premise_death_is_refused_before_execution(tmp_path):
    rules = _crystallize(tmp_path, [
        (FORWARD_BEFORE, FORWARD_AFTER, "A"),
    ])
    source = "def f(x):\n    return x < 11\n"     # A's pattern is not here
    outcome = P.compose(source, [P.rule_op("A", rules[0])])

    assert outcome["verdict"] == P.PREMISE_DIED
    assert outcome["refused_at_step"] == 1
    assert outcome["steps"][0]["applied"] is False
    assert outcome["steps"][0]["dead_requirement"] == "NO_CANDIDATE_FOR_PATTERN"
    assert outcome["result"] == source              # nothing was written


# --------------------------------------------------------------------------- #
# premise death: the check no post-hoc textual instrument can make
# --------------------------------------------------------------------------- #
def test_dead_premise_refuses_before_execution():
    calls = {"apply": 0}

    def apply_a(state: str) -> str | None:
        return state.replace("seed = 1\n", "")

    def apply_b(state: str) -> str | None:
        calls["apply"] += 1
        return state + "# b ran\n"

    op_a = _op("A", premise=lambda s: None if "seed = 1" in s else "SEED_GONE",
               apply=apply_a, prove=lambda s: (True, "A landed"))
    op_b = _op("B", premise=P.substring_premise("seed = 1"), apply=apply_b,
               prove=lambda s: (True, "B landed"))

    source = "seed = 1\nvalue = 0\n"
    # B's premise holds on the ORIGINAL world — it is the post-effect world that kills it
    assert op_b.premise(source) is None

    outcome = P.compose(source, [op_a, op_b])

    assert outcome["verdict"] == P.PREMISE_DIED
    assert outcome["refused_at_step"] == 2
    assert outcome["op_id"] == "B"
    assert outcome["steps"][1]["applied"] is False
    assert calls["apply"] == 0                       # B never ran — refused pre-hoc
    assert "FRAGMENT_ABSENT" in outcome["dead_requirement"]
    assert outcome["result"] == "value = 0\n"        # A's effect stands, B wrote nothing


def test_premise_death_three_ops_locates_the_dead_step():
    op_a = _op("A", apply=lambda s: s.replace("seed = 1\n", ""))
    op_b = _op("B", premise=P.substring_premise("seed = 1"),
               apply=lambda s: s + "# b\n")
    op_c = _op("C", apply=lambda s: s + "# c\n")

    outcome = P.compose("seed = 1\n", [op_a, op_b, op_c])
    assert outcome["verdict"] == P.PREMISE_DIED
    assert outcome["refused_at_step"] == 2
    assert len(outcome["steps"]) == 2               # C was never reached


# --------------------------------------------------------------------------- #
# per-step proof and proof survival
# --------------------------------------------------------------------------- #
def test_step_unproved_is_refused():
    op_a = _op("A", apply=lambda s: s + "# a\n")
    op_b = _op("B", apply=lambda s: s + "# b\n",
               prove=lambda _s: (False, "THE_CLAIM_DID_NOT_HOLD"))

    outcome = P.compose("x = 1\n", [op_a, op_b])
    assert outcome["verdict"] == P.UNPROVED
    assert outcome["reason"].startswith("STEP_UNPROVED:step2")
    assert outcome["refused_at_step"] == 2
    assert "THE_CLAIM_DID_NOT_HOLD" in outcome["steps"][1]["proof"]


def test_later_effect_that_kills_an_earlier_proof_is_refused_without_revert():
    # A's claim: the marker comment is present. B removes the marker WITHOUT
    # returning the text to any earlier state — a textual history check is blind
    # to this; the survival check is not.
    op_a = _op("A", apply=lambda s: s.replace("x = 1\n", "x = 1  # kept\n"),
               prove=lambda s: (True, "marker present") if "# kept" in s
               else (False, "MARKER_GONE"))
    op_b = _op("B", apply=lambda s: "x = 2\n",
               prove=lambda s: (True, "B landed"))

    outcome = P.compose("x = 1\n", [op_a, op_b], recheck_prior=True)
    assert outcome["verdict"] == P.PROOF_DIED
    assert outcome["proving_op"] == "A"
    assert outcome["proving_step"] == 1
    assert outcome["refused_at_step"] == 2
    assert outcome["result"] == "x = 2\n"           # genuinely not a byte-revert
    assert "MARKER_GONE" in outcome["proof_why"]


def test_survival_recheck_can_be_turned_off_and_the_default_is_on():
    op_a = _op("A", apply=lambda s: s.replace("x = 1\n", "x = 1  # kept\n"),
               prove=lambda s: (True, "marker present") if "# kept" in s
               else (False, "MARKER_GONE"))
    op_b = _op("B", apply=lambda s: "x = 2\n", prove=lambda s: (True, "B landed"))

    assert P.compose("x = 1\n", [op_a, op_b])["verdict"] == P.PROOF_DIED
    off = P.compose("x = 1\n", [op_a, op_b], recheck_prior=False)
    assert off["verdict"] == P.PASS
    assert off["recheck_prior"] is False


def test_separate_survive_predicate_is_what_step_five_uses():
    # prove is strict (requires the exact replacement), survive is the durable half.
    # A later step advances the line past the exact replacement — strict prove dies,
    # survive holds, and the sequence passes. This is the documented difference
    # between "the edit landed" and "the claim still holds".
    op_a = _op("A", apply=lambda s: s.replace("x <= 10", "x < 10"),
               prove=lambda s: (True, "strict") if "x < 10" in s else (False, "STRICT_DIED"),
               survive=lambda s: (True, "durable") if "x <= 10" not in s
               else (False, "PATTERN_BACK"))
    op_b = _op("B", apply=lambda s: s.replace("x < 10", "x < 11"),
               prove=lambda s: (True, "B landed"))

    outcome = P.compose("x <= 10\n", [op_a, op_b])
    assert outcome["verdict"] == P.PASS, outcome
    assert outcome["steps"][1]["prior_survived"][0]["via"] == "survive"
    assert outcome["steps"][1]["prior_survived"][0]["holds"] is True


# --------------------------------------------------------------------------- #
# the other refusals, the receipts, the shape
# --------------------------------------------------------------------------- #
def test_no_change_is_refused_with_the_step_named():
    op_a = _op("A", apply=lambda s: s + "# a\n")
    op_b = _op("B", apply=lambda s: s)              # fires, changes nothing

    outcome = P.compose("x = 1\n", [op_a, op_b])
    assert outcome["verdict"] == P.NO_CHANGE
    assert outcome["reason"] == "STEP_DID_NOTHING:step2"
    assert outcome["steps"][1]["outcome"] == "NO_CHANGE"


def test_empty_composition_is_not_a_pass():
    outcome = P.compose("x = 1\n", [])
    assert outcome["verdict"] == P.EMPTY_COMPOSITION


def test_an_invalid_operation_is_named():
    outcome = P.compose("x = 1\n", [object()])
    assert outcome["verdict"] == P.OP_INVALID


def test_mapping_operations_are_accepted():
    outcome = P.compose("x = 1\n", [{
        "op_id": "M",
        "premise": lambda s: None if "x = 1" in s else "GONE",
        "apply": lambda s: s.replace("x = 1", "x = 2"),
        "prove": lambda s: (True, "landed"),
    }])
    assert outcome["verdict"] == P.PASS
    assert outcome["result"] == "x = 2\n"


def test_raising_premise_is_not_a_holding_premise():
    def boom(_state):
        raise RuntimeError("boom")

    outcome = P.compose("x = 1\n", [_op("A", premise=boom)])
    assert outcome["verdict"] == P.RAISED
    assert "PREMISE_RAISED:step1" in outcome["reason"]
    assert outcome["steps"][0]["applied"] is False


def test_every_step_carries_a_full_receipt():
    op_a = _op("A", apply=lambda s: s + "# a\n", prove=lambda _s: (True, "A ok"))
    op_b = _op("B", apply=lambda s: s + "# b\n", prove=lambda _s: (True, "B ok"))

    outcome = P.compose("x = 1\n", [op_a, op_b])
    assert outcome["verdict"] == P.PASS
    assert outcome["schema"] == P.SCHEMA
    assert outcome["authority"] == P.AUTHORITY
    for step in outcome["steps"]:
        assert step["premise"] == "HELD"
        assert step["applied"] is True
        assert step["proof"]
        assert step["produced_sha256"]
    assert outcome["steps"][1]["prior_survived"] == [
        {"step": 1, "op_id": "A", "holds": True, "why": "A ok", "via": "prove"}
    ]


def test_cli_without_measure_is_rejected():
    with pytest.raises(SystemExit):
        P.main([])
