"""Fail-closed R3 realization/observation execution challenge guard.

This is a response guard, not a detector-completeness, semantic-correctness, or
renderer-invariance oracle. Declared R3 attacks, near misses, and unknown
material realization defects may never take the ordinary acceptance path.
"""
from __future__ import annotations
from typing import Any, Iterable

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_EXECUTION_GUARD_V1"
KNOWN_R3_DEFEATERS=frozenset({
 "C07_RENDER_CAPTURE_LOSS",
 "C08_HIDDEN_SURFACE_DEPENDENCE",
 "C09_MULTISCALE_LOCAL_PASS_GLOBAL_FAIL",
 "C10_SUBJECT_SWAP_AFTER_CERTIFICATION",
 "C42_SELECTIVE_OUTCOME_CENSORING",
 "C57_EVALUATION_AWARE_BEHAVIOR",
 "C78_CONTEXT_TRUNCATION_OBLIGATION_DROP",
})
NEAR_MISS_TO_TRIGGER={
 "lossy_capture_uncertain":"C07_RENDER_CAPTURE_LOSS",
 "audience_channel_boundary_uncertain":"C08_HIDDEN_SURFACE_DEPENDENCE",
 "whole_artifact_observation_uncertain":"C09_MULTISCALE_LOCAL_PASS_GLOBAL_FAIL",
 "delivered_subject_identity_uncertain":"C10_SUBJECT_SWAP_AFTER_CERTIFICATION",
 "observation_population_censoring_uncertain":"C42_SELECTIVE_OUTCOME_CENSORING",
 "evaluation_condition_invariance_uncertain":"C57_EVALUATION_AWARE_BEHAVIOR",
 "context_region_completeness_uncertain":"C78_CONTEXT_TRUNCATION_OBLIGATION_DROP",
}

def evaluate(*,realization_receipt_pass:bool,detected_defeater_ids:Iterable[str]=(),
             near_miss_signals:Iterable[str]=(),unmapped_material_defeater:bool=False)->dict[str,Any]:
    detected=tuple(sorted(set(str(x) for x in detected_defeater_ids)))
    near=tuple(sorted(set(str(x) for x in near_miss_signals)))
    unknown=tuple(x for x in detected if x not in KNOWN_R3_DEFEATERS)
    known=tuple(x for x in detected if x in KNOWN_R3_DEFEATERS)
    triggers=tuple(sorted({NEAR_MISS_TO_TRIGGER[x] for x in near if x in NEAR_MISS_TO_TRIGGER}))
    unknown_near=tuple(x for x in near if x not in NEAR_MISS_TO_TRIGGER)
    base={
      "schema":SCHEMA,"pass":False,
      "detected_defeater_ids":list(detected),"known_r3_defeater_ids":list(known),
      "active_escalation_triggers":list(triggers),
      "realization_receipt_pass":realization_receipt_pass is True,
      "ordinary_acceptance_path_allowed":False,
      "detection_completeness_proved":False,"renderer_invariance_proved":False,
      "semantic_target_correctness_proved":False,"semantic_leaf_authority":False,
      "root_closure_authority":False,"quality_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,
    }
    if unknown or unknown_near or unmapped_material_defeater:
      return {**base,"status":"ESCALATE__UNMAPPED_R3_MATERIAL_DEFEATER",
              "unknown_detected_ids":list(unknown),"unknown_near_miss_signals":list(unknown_near)}
    if known:
      return {**base,"status":"ABSTAIN_OR_ESCALATE__KNOWN_R3_DEFEATER_ACTIVE"}
    if triggers:
      return {**base,"status":"ESCALATE__R3_NEAR_MISS_TRIGGER"}
    if realization_receipt_pass is not True:
      return {**base,"status":"FALSIFIED_OR_FAIL_CLOSED__REALIZATION_RECEIPT_NOT_ACCEPTED"}
    return {**base,"pass":True,
            "status":"PASS__R3_EXECUTION_GUARD_CLEAR__BOUND_REALIZATION_RECEIPT_ACCEPTED",
            "ordinary_acceptance_path_allowed":True}
