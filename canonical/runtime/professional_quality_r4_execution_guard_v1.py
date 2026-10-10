"""Fail-closed R4 measurement-construct execution challenge guard.

This is a runtime response guard, not a detector-completeness or construct-validity
oracle. It guarantees that declared R4 attacks, near misses, and unknown material
measurement/construct defects cannot take the ordinary acceptance path.
"""
from __future__ import annotations
from typing import Any, Iterable

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R4_EXECUTION_GUARD_V1"
KNOWN_R4_DEFEATERS=frozenset({
 "C11_RUBRIC_UNDERREPRESENTATION",
 "C12_ASSESSMENT_OVERFIT",
 "C13_ABSOLUTE_FLOOR_MISSING",
 "C14_ONTOLOGY_CLONING",
 "C15_NORMALIZATION_RANGE_EXPLOIT",
 "C16_INVALID_CHALLENGE_GENERATOR",
 "C70_STYLE_BIAS_DOMINATES_CONTENT",
})
NEAR_MISS_TO_TRIGGER={
 "rubric_coverage_uncertain":"C11_RUBRIC_UNDERREPRESENTATION",
 "deployment_relevance_uncertain":"C12_ASSESSMENT_OVERFIT",
 "professional_floor_unbound":"C13_ABSOLUTE_FLOOR_MISSING",
 "criterion_dependence_uncertain":"C14_ONTOLOGY_CLONING",
 "normalization_stability_uncertain":"C15_NORMALIZATION_RANGE_EXPLOIT",
 "challenge_validity_uncertain":"C16_INVALID_CHALLENGE_GENERATOR",
 "style_content_confounding_uncertain":"C70_STYLE_BIAS_DOMINATES_CONTENT",
}

def evaluate(*,measurement_pass:bool,detected_defeater_ids:Iterable[str]=(),
             near_miss_signals:Iterable[str]=(),unmapped_material_defeater:bool=False)->dict[str,Any]:
    detected=tuple(sorted(set(str(x) for x in detected_defeater_ids)))
    near=tuple(sorted(set(str(x) for x in near_miss_signals)))
    unknown=tuple(x for x in detected if x not in KNOWN_R4_DEFEATERS)
    known=tuple(x for x in detected if x in KNOWN_R4_DEFEATERS)
    triggers=tuple(sorted({NEAR_MISS_TO_TRIGGER[x] for x in near if x in NEAR_MISS_TO_TRIGGER}))
    unknown_near=tuple(x for x in near if x not in NEAR_MISS_TO_TRIGGER)

    base={
      "schema":SCHEMA,
      "detected_defeater_ids":list(detected),
      "known_r4_defeater_ids":list(known),
      "active_escalation_triggers":list(triggers),
      "measurement_pass":measurement_pass is True,
      "ordinary_acceptance_path_allowed":False,
      "detection_completeness_proved":False,
      "construct_validity_completeness_proved":False,
      "semantic_leaf_authority":False,
      "root_closure_authority":False,
      "quality_authority":False,
      "terminal_authority":False,
      "terminal_credit_delta":0,
    }
    if unknown or unknown_near or unmapped_material_defeater:
      return {**base,"pass":False,"status":"ESCALATE__UNMAPPED_R4_MATERIAL_DEFEATER",
              "unknown_detected_ids":list(unknown),"unknown_near_miss_signals":list(unknown_near)}
    if known:
      return {**base,"pass":False,"status":"ABSTAIN_OR_ESCALATE__KNOWN_R4_DEFEATER_ACTIVE"}
    if triggers:
      return {**base,"pass":False,"status":"ESCALATE__R4_NEAR_MISS_TRIGGER"}
    if measurement_pass is not True:
      return {**base,"pass":False,"status":"FALSIFIED_OR_FAIL_CLOSED__MECHANICAL_MEASUREMENT_NOT_ACCEPTED"}
    return {**base,"pass":True,"status":"PASS__R4_EXECUTION_GUARD_CLEAR__MECHANICAL_MEASUREMENT_ACCEPTED",
            "ordinary_acceptance_path_allowed":True}
