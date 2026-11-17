#!/usr/bin/env python3
"""One loop, one tail — the verdict receipt is pinned to the merged numbers it cites.

CAN FAIL (mutations documented in the receipt `tests.can_fail` field):
  * `the_claim_as_stated` flipped to TRUE                        -> first assertion fails
  * any required external id removed                            -> external-set assertion fails
  * `coverage_axis.largest_class` claimed above the taxonomy    -> taxonomy equality fails
  * a pinned source receipt drifts (headline, held-out, aimed)   -> its equality fails
  * the note stops carrying the FALSE verdict                    -> note assertion fails

No number here is re-measured: this file RE-READS merged receipts and the thesis note,
which is the honest form for an aggregation receipt (re-testing known results is banned).
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "canonical/verification/ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1.json"
NOTE = ROOT / "ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1.md"

REQUIRED_EXTERNAL_IDS = [
    "2610.00972",  # VeriHarness — verifier skills +6.4
    "2610.11464",  # Who Verifies the Verifier — always-pass collapse
    "2602.20946",  # Measurability Gap — verification bandwidth caps
    "2611.01386",  # Learning by Doing — training-free gains, only where teacher solved
    "2611.04456",  # GitHub skills study — 28.9% lack trigger conditions
    "2608.01678",  # Progressive skill generation beats one-shot
    "2606.01139",  # SkillRevise — one-shot skills behaviorally weak
    "2604.01687",  # EvoSkills — surrogate-verifier ablation -30pp
    "2605.21810",  # Trace2Skill — dense verifier, training-free
    "2603.23013",  # Knowledge access beats model size
    "2604.27003",  # Continual learning moves to memory (retrieval bottleneck)
    "2610.11781",  # Skill-V — versioned falsifiable contracts
    "2608.16246",  # CompoSkill — per-item verification != composition verification
    "2606.05066",  # SkillComposer — harness cannot verify composition
    "2601.04748",  # Skill-selection scaling — libraries do not scale
    "2606.05395",  # VASO — formal contracts
    "2603.07670",  # Agent memory survey — parametric un-auditable
]


def _load(path: pathlib.Path):
    return json.loads(path.read_text())


def test_receipt_exists_and_carries_the_false_verdict():
    r = _load(RECEIPT)
    assert r["schema"] == "PROJECT_BRAIN_VERIFICATION_RECEIPT_V1"
    assert r["receipt_id"] == "ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1"
    assert r["authority"].startswith("NONE__")
    # CAN FAIL: flipping this to TRUE fails here.
    assert r["verdict"]["the_claim_as_stated"] == "FALSE"
    assert len(r["verdict"]["five_transitions"]) == 5
    statuses = {t["status"] for t in r["verdict"]["five_transitions"]}
    assert "FALSE" in statuses  # link 5 (all computer use + SWE) must stay false
    assert any("CONDITIONAL" in s for s in statuses)  # permanence is gated, not free


def test_five_transition_numbers_match_the_open_benchmark_receipt():
    r = _load(RECEIPT)
    p = ROOT / "canonical/verification/OPEN_BENCHMARK_ONE_SUCCESS_GENERALISATION_20261114_V1.json"
    assert r["pinned_source_files_sha256"][str(p.relative_to(ROOT))] == __import__("hashlib").sha256(p.read_bytes()).hexdigest()
    h = _load(p)["headline"]
    assert h["one_success_mean_success_where_generalisation_is_required"] == 0.6
    assert h["cache_verbatim_same_metric"] == 0.15
    assert h["existing_compiler_same_metric"] == 0.1886
    assert "52 of 92" in h["interpretation"]
    link2 = r["verdict"]["five_transitions"][1]
    assert "60.0%" in link2["measured"] and "15.0%" in link2["measured"]


def test_v5_held_out_and_taxonomy_are_unchanged():
    v5 = _load(ROOT / "canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json")
    ho = v5["summary"]["held_out"]
    assert ho["demonstrated"] == 55
    assert ho["tasks"] == 92
    tax = _load(ROOT / "canonical/verification/DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json")["taxonomy"]
    assert tax["classes"] == 16
    assert tax["largest_class"] == 6
    assert tax["pages_unsolved"] == 46
    # CAN FAIL: any receipt edit claiming a single lever above six fails against this.
    cov = _load(RECEIPT)["two_axes_of_the_single_bottleneck_question"]["coverage_axis"]
    assert cov["finding"] == "NO_SINGLE_LEVER_ON_COVERAGE"
    assert "16 classes, largest class 6" in cov["measured"]


def test_aimed_arm_and_value_nothing_stated_are_unchanged():
    r = _load(RECEIPT)
    aim = _load(ROOT / "canonical/verification/AIMED_ACTIONS_OVER_THE_UNSOLVED_SET_20261116_V1.json")
    res = aim["result"]
    assert (res["A_pass"], res["G_pass"], res["D_pass"], res["of"]) == (0, 13, 0, 46)
    val = _load(ROOT / "canonical/verification/THE_ANSWER_WAS_A_VALUE_NOTHING_STATED_20261117_V1.json")
    assert val["measured_effect"]["four_arms_at_1200_actions"]["all_failed"] is True
    assert "CANDIDATE_SET_CAN_ONLY_COPY" in val["decision"]
    # receipt cites both
    reasons = " ".join(x["measured"] for x in r["can_we_do_it_now"]["reasons"])
    assert "13/46" in reasons and "0/46" in reasons


def test_certificate_and_replay_pins():
    cert = _load(ROOT / "canonical/verification/INSUFFICIENCY_CERTIFICATE_20261113_V1.json")
    assert any("unrepairable_by_repetition True" in w for w in cert["what_is_not"])
    proof = (ROOT / "canonical/verification/PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json").read_text()
    assert "228 real compositions, 53.5% stale, 31.1% silently corrupt" in proof
    r = _load(RECEIPT)
    barriers = json.dumps(r["the_three_barriers_measured"])
    assert "unrepairable_by_repetition" in barriers
    assert "53.5% stale" in barriers


def test_thesis_note_still_carries_the_chain():
    text = (ROOT / "THESIS_VERDICT_ONE_DEMO_AND_THE_SINGLE_BOTTLENECK_20261116_V1.md").read_text()
    assert "56/92" in text
    assert "60.0%** vs **15.0%** cache vs **18.9%** prior" in text
    assert "20.6%" in text


def test_external_confirmation_set_is_complete_and_current():
    r = _load(RECEIPT)
    ext = r["external_confirmations_fetched_2026_11_16_17"]
    assert len(ext) >= 15
    for name, item in ext.items():
        assert item["url"].startswith("https://arxiv.org/"), name
        assert item["takeaway"], name
    joined = json.dumps(ext)
    for ident in REQUIRED_EXTERNAL_IDS:  # CAN FAIL: removing any id fails here
        assert ident in joined, ident


def test_two_axes_reconciliation_is_pinned():
    r = _load(RECEIPT)
    two = r["two_axes_of_the_single_bottleneck_question"]
    assert two["loop_axis"]["deepest_station"] == "OBSERVATION_VERDICT_INSTRUMENT"
    stations = " ".join(x["claim"] for x in two["loop_axis"]["each_station_was_once_called_the_single_bottleneck"])
    for word in ("goal", "candidate", "instrument", "index"):
        assert word in stations.lower()
    assert len(two["loop_axis"]["why"]) == 3  # one reason per barrier
    assert "16 classes, largest class 6" in two["coverage_axis"]["measured"]
    assert "not contradictions" in two["reconciliation"]


def test_now_answer_and_ranked_plan_and_nonclaims():
    r = _load(RECEIPT)
    assert r["can_we_do_it_now"]["answer"] == "NO_AS_STATED_THREE_MEASURED_REASONS"
    assert len(r["can_we_do_it_now"]["reasons"]) == 3
    ranked = r["ranked_next_with_pass_fail"]
    assert len(ranked) == 5 and [x["rank"] for x in ranked] == [1, 2, 3, 4, 5]
    for move in ranked:
        assert move["pass"] and move["kill"], move["rank"]
    nonclaims = " ".join(r["nonclaims"])
    assert "no new execution" in nonclaims
    assert "no external model" in nonclaims
    assert "sentience is not claimed" in nonclaims
    assert r["is_it_revolutionary"]["answer"] == "REVOLUTIONARY_IN_THE_LOOP_NOT_IN_ONE_SHOT"


def test_note_exists_and_carries_the_verdict():
    assert NOTE.exists()
    text = NOTE.read_text()
    assert "FALSE as stated" in text
    assert "one loop (instrument deepest) + one long tail" in text
    assert "0/200" in text and "53.5%" in text and "20.6%" in text
    assert "Revolutionary in the loop, refuted in the one-shot form" in text
