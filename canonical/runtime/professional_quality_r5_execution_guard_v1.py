"""Fail-closed R5 evaluator/reference execution challenge guard.

Response guard only. It never proves evaluator completeness, owner-evaluator
containment, reference correctness, cross-model calibration, semantic closure,
or root closure.
"""
from __future__ import annotations
from typing import Any, Iterable

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R5_EXECUTION_GUARD_V1"
KNOWN_R5_DEFEATERS=frozenset({
 "C06_NOVELTY_PENALTY",
 "C17_REFERENCE_STANDARD_ERROR",
 "C18_ANCHOR_PRESTIGE_BIAS",
 "C19_ANCHOR_MEMORIZATION",
 "C20_FRONTIER_LOCAL_JUDGE_FAILURE",
 "C21_JUDGE_ARTIFACT_INTERACTION",
 "C22_WITHIN_EPISODE_EVALUATOR_DRIFT",
 "C34_MEASUREMENT_NONINVARIANCE",
 "C50_BASELINE_LAUNDERED_EXCELLENCE",
 "C59_META_ROUTER_SELECTION_OVERFIT",
 "C67_STAKES_SIGNALING_JUDGE_LENIENCY",
 "C68_SELF_PREFERENCE_JUDGE_BIAS",
 "C69_CROSS_MODEL_CALIBRATION_SIGN_REVERSAL",
 "C70_STYLE_BIAS_DOMINATES_CONTENT",
 "C73_BASE_RATE_PRECISION_LAUNDERING",
 "C79_FALLBACK_EVALUATOR_SCOPE_WEAKENING",
})
NEAR_MISS_TO_TRIGGER={
 "novelty_penalty_uncertain":"C06_NOVELTY_PENALTY",
 "reference_standard_fallibility_uncertain":"C17_REFERENCE_STANDARD_ERROR",
 "anchor_prestige_uncertain":"C18_ANCHOR_PRESTIGE_BIAS",
 "anchor_memorization_uncertain":"C19_ANCHOR_MEMORIZATION",
 "frontier_local_judge_validity_uncertain":"C20_FRONTIER_LOCAL_JUDGE_FAILURE",
 "judge_artifact_interaction_uncertain":"C21_JUDGE_ARTIFACT_INTERACTION",
 "within_episode_evaluator_drift_uncertain":"C22_WITHIN_EPISODE_EVALUATOR_DRIFT",
 "measurement_invariance_uncertain":"C34_MEASUREMENT_NONINVARIANCE",
 "baseline_absolute_quality_uncertain":"C50_BASELINE_LAUNDERED_EXCELLENCE",
 "meta_router_selection_uncertain":"C59_META_ROUTER_SELECTION_OVERFIT",
 "stakes_signaling_uncertain":"C67_STAKES_SIGNALING_JUDGE_LENIENCY",
 "self_preference_uncertain":"C68_SELF_PREFERENCE_JUDGE_BIAS",
 "cross_model_calibration_uncertain":"C69_CROSS_MODEL_CALIBRATION_SIGN_REVERSAL",
 "style_content_separation_uncertain":"C70_STYLE_BIAS_DOMINATES_CONTENT",
 "release_base_rate_transport_uncertain":"C73_BASE_RATE_PRECISION_LAUNDERING",
 "fallback_evaluator_scope_uncertain":"C79_FALLBACK_EVALUATOR_SCOPE_WEAKENING",
}

def evaluate(*,evaluator_preflight_pass:bool,root_binding_pass:bool,
             detected_defeater_ids:Iterable[str]=(),near_miss_signals:Iterable[str]=(),
             unmapped_material_defeater:bool=False)->dict[str,Any]:
    detected=tuple(sorted(set(str(x) for x in detected_defeater_ids)))
    near=tuple(sorted(set(str(x) for x in near_miss_signals)))
    unknown=tuple(x for x in detected if x not in KNOWN_R5_DEFEATERS)
    known=tuple(x for x in detected if x in KNOWN_R5_DEFEATERS)
    triggers=tuple(sorted({NEAR_MISS_TO_TRIGGER[x] for x in near if x in NEAR_MISS_TO_TRIGGER}))
    unknown_near=tuple(x for x in near if x not in NEAR_MISS_TO_TRIGGER)
    base={
      "schema":SCHEMA,"pass":False,
      "detected_defeater_ids":list(detected),"known_r5_defeater_ids":list(known),
      "active_escalation_triggers":list(triggers),
      "evaluator_preflight_pass":evaluator_preflight_pass is True,
      "root_binding_pass":root_binding_pass is True,
      "ordinary_acceptance_path_allowed":False,
      "detection_completeness_proved":False,
      "true_owner_evaluator_containment_proved":False,
      "reference_correctness_proved":False,
      "cross_model_calibration_proved":False,
      "semantic_leaf_authority":False,"root_closure_authority":False,
      "quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
    }
    if unknown or unknown_near or unmapped_material_defeater:
      return {**base,"status":"ESCALATE__UNMAPPED_R5_MATERIAL_DEFEATER",
              "unknown_detected_ids":list(unknown),"unknown_near_miss_signals":list(unknown_near)}
    if known:
      return {**base,"status":"ABSTAIN_OR_ESCALATE__KNOWN_R5_DEFEATER_ACTIVE"}
    if triggers:
      return {**base,"status":"ESCALATE__R5_NEAR_MISS_TRIGGER"}
    if evaluator_preflight_pass is not True:
      return {**base,"status":"FALSIFIED_OR_FAIL_CLOSED__EVALUATOR_PREFLIGHT_NOT_ACCEPTED"}
    if root_binding_pass is not True:
      return {**base,"status":"FALSIFIED_OR_FAIL_CLOSED__R5_ROOT_BINDING_NOT_ACCEPTED"}
    return {**base,"pass":True,
            "status":"PASS__R5_EXECUTION_GUARD_CLEAR__BOUND_EVALUATOR_MECHANICS_AND_ROOT_BINDING_ACCEPTED",
            "ordinary_acceptance_path_allowed":True}
