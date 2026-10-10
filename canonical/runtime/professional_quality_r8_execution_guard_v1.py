"""Fail-closed R8 population/context/operator execution challenge guard.

This is a response guard, not a detection-completeness, constituency,
operator-generalization, measurement-invariance, or semantic oracle.
Declared R8 attacks, near misses, and unknown material R8 defects may never
take the ordinary acceptance path.
"""
from __future__ import annotations
from typing import Any, Iterable

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R8_EXECUTION_GUARD_V1"
KNOWN_R8_DEFEATERS=frozenset({
 "C21_JUDGE_ARTIFACT_INTERACTION",
 "C22_WITHIN_EPISODE_EVALUATOR_DRIFT",
 "C32_PRESENTER_CONFOUNDING",
 "C33_CONSTITUENCY_SUPPORT_GAP",
 "C34_MEASUREMENT_NONINVARIANCE",
 "C35_PANEL_SOCIAL_INFLUENCE",
 "C36_RATER_ASSIGNMENT_CONFOUNDING",
 "C37_STRATEGIC_PREFERENCE_REPORT",
 "C38_ELICITATION_PERFORMATIVITY",
 "C39_MEASUREMENT_REACTIVITY_RANK_REVERSAL",
 "C42_SELECTIVE_OUTCOME_CENSORING",
 "C73_BASE_RATE_PRECISION_LAUNDERING",
})
NEAR_MISS_TO_TRIGGER={
 "judge_artifact_region_uncertain":"C21_JUDGE_ARTIFACT_INTERACTION",
 "within_episode_severity_drift_uncertain":"C22_WITHIN_EPISODE_EVALUATOR_DRIFT",
 "presenter_rescue_uncertain":"C32_PRESENTER_CONFOUNDING",
 "constituency_support_uncertain":"C33_CONSTITUENCY_SUPPORT_GAP",
 "measurement_invariance_uncertain":"C34_MEASUREMENT_NONINVARIANCE",
 "panel_independence_uncertain":"C35_PANEL_SOCIAL_INFLUENCE",
 "rater_assignment_connectivity_uncertain":"C36_RATER_ASSIGNMENT_CONFOUNDING",
 "strategic_reporting_uncertain":"C37_STRATEGIC_PREFERENCE_REPORT",
 "elicitation_performativity_uncertain":"C38_ELICITATION_PERFORMATIVITY",
 "measurement_reactivity_uncertain":"C39_MEASUREMENT_REACTIVITY_RANK_REVERSAL",
 "outcome_censoring_uncertain":"C42_SELECTIVE_OUTCOME_CENSORING",
 "release_base_rate_transport_uncertain":"C73_BASE_RATE_PRECISION_LAUNDERING",
}

def evaluate(*,population_preflight_pass:bool,detected_defeater_ids:Iterable[str]=(),
             near_miss_signals:Iterable[str]=(),unmapped_material_defeater:bool=False)->dict[str,Any]:
    detected=tuple(sorted(set(str(x) for x in detected_defeater_ids)))
    near=tuple(sorted(set(str(x) for x in near_miss_signals)))
    unknown=tuple(x for x in detected if x not in KNOWN_R8_DEFEATERS)
    known=tuple(x for x in detected if x in KNOWN_R8_DEFEATERS)
    triggers=tuple(sorted({NEAR_MISS_TO_TRIGGER[x] for x in near if x in NEAR_MISS_TO_TRIGGER}))
    unknown_near=tuple(x for x in near if x not in NEAR_MISS_TO_TRIGGER)
    base={
      "schema":SCHEMA,"pass":False,
      "detected_defeater_ids":list(detected),"known_r8_defeater_ids":list(known),
      "active_escalation_triggers":list(triggers),
      "population_preflight_pass":population_preflight_pass is True,
      "ordinary_acceptance_path_allowed":False,
      "detection_completeness_proved":False,
      "constituency_support_proved":False,"operator_generalization_proved":False,
      "measurement_invariance_proved":False,"social_reactivity_closure_proved":False,
      "semantic_leaf_authority":False,"root_closure_authority":False,
      "quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
    }
    if unknown or unknown_near or unmapped_material_defeater:
      return {**base,"status":"ESCALATE__UNMAPPED_R8_MATERIAL_DEFEATER",
              "unknown_detected_ids":list(unknown),"unknown_near_miss_signals":list(unknown_near)}
    if known:
      return {**base,"status":"ABSTAIN_OR_ESCALATE__KNOWN_R8_DEFEATER_ACTIVE"}
    if triggers:
      return {**base,"status":"ESCALATE__R8_NEAR_MISS_TRIGGER"}
    if population_preflight_pass is not True:
      return {**base,"status":"FALSIFIED_OR_FAIL_CLOSED__POPULATION_PREFLIGHT_NOT_ACCEPTED"}
    return {**base,"pass":True,
            "status":"PASS__R8_EXECUTION_GUARD_CLEAR__BOUND_FROZEN_POPULATION_PREFLIGHT_ACCEPTED",
            "ordinary_acceptance_path_allowed":True}
