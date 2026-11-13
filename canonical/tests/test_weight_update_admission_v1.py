#!/usr/bin/env python3
"""A permanent weight step must earn its permanence on inputs it did not train on.

Every case runs the real `OnlineParametricPolicyModel` heads and the real typed parser. No
monkeypatching, no stubs, no pinned weights: each test builds a fresh model in a temporary path.
"""
from __future__ import annotations

import pathlib

import pytest

from canonical.swe_kernel import weight_update_admission_v1 as W
from canonical.swe_kernel.semantic_generalization_engine_v1 import (
    GeneralizationEngine,
    parse_task,
)
from canonical.tools import weight_update_interference_measure_20261113_v1 as M


@pytest.fixture()
def model(tmp_path: pathlib.Path):
    return W.fresh_model(tmp_path)


@pytest.fixture()
def probes():
    built = W.probes_from_goals(W.stream_goals())
    assert built["refused"] == [], "the fixture goals must all be typeable by the parser"
    return built["probes"]


def _others(probes, goal):
    return [p for p in probes if p.goal != goal]


# ---------------------------------------------------------------------------
# the hole, asserted so the gate cannot become decoration
# ---------------------------------------------------------------------------
def test_the_naive_receipt_reports_success_while_nothing_else_improves(model, probes):
    first = probes[0]
    report = W.evaluate_update(model, first.goal, first.operation, first.concept, first.domain,
                               probes=_others(probes, first.goal))
    assert report["naive_receipt"]["loss_delta"] > 0
    assert report["naive_receipt"]["delta_w_l2"] > 0
    assert report["counts"]["gained"] == 0
    assert report["verdict"] == W.REFINE
    assert report["reason"] == "NO_MEASURED_GAIN_ON_ANY_OTHER_INPUT"


def test_a_stream_of_self_certifying_steps_breaks_predictions_it_had_right(tmp_path, probes):
    naive = M._run_naive([p.goal for p in probes], probes, tmp_path)
    assert naive["updates_applied"] == len(probes)
    assert naive["receipts_reporting_loss_went_down"] == len(probes)
    assert naive["previously_correct_predictions_broken"] > 0, (
        "if this ever reaches zero the substrate changed and the measurement must be re-read"
    )


def test_the_gated_arm_breaks_nothing_and_says_what_it_refused(tmp_path, probes):
    gated = M._run_gated([p.goal for p in probes], probes, tmp_path)
    assert gated["previously_correct_predictions_broken"] == 0
    assert gated["weights_untouched_on_every_refusal"] is True
    assert gated["updates_refused"] > 0
    assert gated["updates_applied"] + gated["updates_refused"] == len(probes)
    # The trade is reported, not hidden: refusing steps costs reach.
    assert gated["agreement_with_parser_at_end"] <= len(probes)


# ---------------------------------------------------------------------------
# the live weights are untouched unless the verdict is ADMIT
# ---------------------------------------------------------------------------
def test_refusal_leaves_the_weight_matrices_bit_identical(model, probes):
    first = probes[0]
    before = W.fingerprint(model)
    report = W.apply_if_admitted(model, first.goal, first.operation, first.concept, first.domain,
                                 probes=_others(probes, first.goal), persist=False)
    assert report["applied"] is False
    assert report["weights_unchanged"] is True
    assert W.fingerprint(model) == before


def test_evaluating_never_writes_a_state_file(tmp_path, probes):
    model = W.fresh_model(tmp_path)
    first = probes[0]
    W.evaluate_update(model, first.goal, first.operation, first.concept, first.domain,
                      probes=_others(probes, first.goal))
    assert list(tmp_path.iterdir()) == []


def test_an_admitted_step_really_changes_the_weights_and_records_both_hashes(model, probes):
    # Warm the heads until some probe is right, then find a step that gains without losing.
    admitted = None
    for probe in probes:
        others = _others(probes, probe.goal)
        report = W.evaluate_update(model, probe.goal, probe.operation, probe.concept, probe.domain,
                                   probes=others)
        if report["verdict"] == W.ADMIT:
            admitted = (probe, others)
            break
        model.update_from_experience(probe.goal, probe.operation, probe.concept, probe.domain,
                                     persist=False)
    assert admitted is not None, "the stream must contain at least one genuinely generalising step"
    probe, others = admitted
    before = W.fingerprint(model)
    applied = W.apply_if_admitted(model, probe.goal, probe.operation, probe.concept, probe.domain,
                                  probes=others, persist=False)
    assert applied["applied"] is True
    assert applied["verdict"] == W.ADMIT
    assert applied["counts"]["lost"] == 0
    assert applied["counts"]["gained"] >= 1
    assert applied["weights_before_sha256"] == before
    assert applied["weights_after_sha256"] != before
    assert W.fingerprint(model) == applied["weights_after_sha256"]


def test_a_step_that_breaks_a_correct_prediction_is_rejected(model, probes):
    rejected = None
    for probe in probes:
        others = _others(probes, probe.goal)
        report = W.evaluate_update(model, probe.goal, probe.operation, probe.concept, probe.domain,
                                   probes=others)
        if report["verdict"] == W.REJECT:
            rejected = report
            break
        model.update_from_experience(probe.goal, probe.operation, probe.concept, probe.domain,
                                     persist=False)
    assert rejected is not None, "the measured stream contains steps that break a right prediction"
    assert rejected["reason"] == "BROKE_A_PREDICTION_THAT_WAS_RIGHT"
    assert rejected["counts"]["lost"] >= 1
    assert rejected["lost_goals"]


# ---------------------------------------------------------------------------
# refusals: unreadable or circular evidence is never a pass
# ---------------------------------------------------------------------------
def test_no_probes_is_a_refusal(model):
    report = W.evaluate_update(model, "count the functions in mod.py", "count", "function",
                               "python_ast", probes=[])
    assert report["verdict"] == W.REFUSED
    assert report["reason"] == "NO_PROBES_OFFERED"


def test_the_trained_goal_is_not_its_own_probe(model, probes):
    first = probes[0]
    report = W.evaluate_update(model, first.goal, first.operation, first.concept, first.domain,
                               probes=[first])
    assert report["verdict"] == W.REFUSED
    assert report["reason"] == "EVERY_PROBE_IS_THE_TRAINED_GOAL"


def test_a_label_the_heads_cannot_represent_is_a_refusal(model, probes):
    report = W.evaluate_update(model, "count the imports in mod.py", "count", "unknown",
                               "unknown", probes=probes)
    assert report["verdict"] == W.REFUSED
    assert report["reason"] == "TRAINED_LABEL_OUTSIDE_HEAD_VOCABULARY"


def test_probes_are_labelled_by_the_parser_and_untypeable_goals_are_named():
    built = W.probes_from_goals(["count the functions in mod.py", "count the imports in mod.py",
                                 "please do something unspecified"], exclude="")
    goals = [p.goal for p in built["probes"]]
    assert "count the functions in mod.py" in goals
    assert all(p.goal != "count the imports in mod.py" for p in built["probes"])
    assert built["refused"], "untypeable goals must be named rather than silently dropped"
    assert all(r["reason"] == "PARSER_LABEL_OUTSIDE_HEAD_VOCABULARY" for r in built["refused"])
    typed = parse_task("count the functions in mod.py")
    kept = next(p for p in built["probes"] if p.goal == "count the functions in mod.py")
    assert (kept.operation, kept.concept, kept.domain) == (typed.operation, typed.concept, typed.domain)


def test_the_trained_goal_is_excluded_when_probes_are_built_from_a_stream():
    built = W.probes_from_goals(W.stream_goals(), exclude=W.stream_goals()[0],
                               archive_goals=W.stream_goals()[:3])
    assert W.stream_goals()[0] not in [p.goal for p in built["probes"]]
    roles = {p.goal: p.role for p in built["probes"]}
    assert roles[W.stream_goals()[1]] == W.ARCHIVE
    assert roles[W.stream_goals()[-1]] == W.TRANSFER


# ---------------------------------------------------------------------------
# the engine wiring: permanence is gated, a volatile step is not
# ---------------------------------------------------------------------------
def _engine(tmp_path: pathlib.Path) -> GeneralizationEngine:
    return GeneralizationEngine(
        policy_path=tmp_path / "policy.json",
        experiences_path=tmp_path / "exp.json",
        embeddings_path=tmp_path / "emb.json",
    )


def test_the_engine_refuses_a_permanent_step_when_it_has_no_other_verified_goal(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("def a():\n    pass\n\ndef b():\n    pass\n", encoding="utf-8")
    engine = _engine(tmp_path)
    before = W.fingerprint(engine.policy)
    out = engine.solve_task("count the functions in mod.py", work_cwd=tmp_path,
                            persist_policy=True, store_experience=False)
    assert out["pass"] is True
    receipt = out.get("policy_update") or out.get("policy_receipt") or {}
    assert receipt.get("verdict") == W.REFUSED
    assert receipt.get("reason") == "NO_PROBES_OFFERED"
    assert receipt.get("applied") is False
    assert W.fingerprint(engine.policy) == before


def test_a_volatile_step_is_unchanged_and_grants_no_permanence(tmp_path):
    source = tmp_path / "mod.py"
    source.write_text("def a():\n    pass\n", encoding="utf-8")
    engine = _engine(tmp_path)
    out = engine.solve_task("count the functions in mod.py", work_cwd=tmp_path,
                            persist_policy=False, store_experience=False)
    assert out["pass"] is True
    receipt = out.get("policy_update") or out.get("policy_receipt") or {}
    assert receipt.get("schema") == "BRAIN_POLICY_UPDATE_RECEIPT_V1"
    assert "verdict" not in receipt
    assert not (tmp_path / "policy.json").exists()


def test_the_measurement_reports_both_arms_and_the_cli_runs():
    report = M.measure()
    assert report["stream_length"] == report["naive_one_step_per_verified_experience"]["goals_scored"]
    assert report["naive_one_step_per_verified_experience"]["previously_correct_predictions_broken"] > 0
    assert report["gated_by_admission_on_other_inputs"]["previously_correct_predictions_broken"] == 0
    assert report["authority"] == "NONE"
    assert report["not_a_claim_about_llm_fine_tuning"] is True
    assert M.main(["--json"]) == 0
    assert W.main([]) == 0
