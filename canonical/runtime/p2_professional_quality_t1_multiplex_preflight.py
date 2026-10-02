"""Fail-closed prewave verifier for P2 professional-quality T1 multiplex binding."""
from __future__ import annotations
import json
from pathlib import Path

BINDING="canonical/governance/P2_PROFESSIONAL_QUALITY_T1_MULTIPLEX_TERMINAL_BINDING_V1.json"
MANIFEST="canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"
REQUIRED_SURFACES={
 "T1/GDPVAL_AA_V2_1::P2_PROFESSIONAL_ARTIFACT_QUALITY_DIRECT_PROOF",
 "T1/AA_BRIEFCASE_V1_1::P2_PROFESSIONAL_ARTIFACT_QUALITY_DIRECT_PROOF",
}
REQUIRED_ROUTE="P2_PROFESSIONAL_ARTIFACT_QUALITY_DIRECT_PROOF"
FORBIDDEN_VISIBLE={
 "HIDDEN_VERIFIER","REFERENCE_PLAN","GOLD_EDIT_QUALITY_SCORES",
 "GOLD_FINAL_RUBRIC_SCORE","GOLD_AUDIENCE_PRIORITY",
 "MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON",
}
REQUIRED_CHECKS={
 "NO_UNSUPPORTED_MATERIAL_CONTENT",
 "REQUIRED_ANALYSIS_COVERED",
 "AUDIENCE_EMPHASIS_MATCHES_VISIBLE_OBJECTIVE",
 "LAYOUT_OR_STRUCTURE_CHOICE_DOES_NOT_OBSCURE_REQUIRED_INFORMATION",
 "SELECTED_PLAN_IMPROVES_INDEPENDENT_RUBRIC_VERSUS_MECHANICS_ONLY_BASELINE",
 "PLAN_ABLATION_DEGRADES_AND_RESCUE_RESTORES_RELEVANT_QUALITY",
}
REQUIRED_MUTATIONS={
 "UNSUPPORTED_POLISHED_CLAIM","MISSING_REQUIRED_ANALYSIS",
 "AUDIENCE_PRIORITY_SWAP","LAYOUT_OBSCURES_REQUIRED_INFORMATION",
 "REMOVE_HIGHEST_VALUE_SUPPORTED_EDIT","ADD_HIGH_COST_LOW_VALUE_EDIT",
}
REQUIRED_DEPS=(
 "canonical/runtime/p2_p3_information_safe_candidate_v2.py",
 "canonical/runtime/p2_p3_information_safe_proof_suites_v2.py",
 "canonical/verification/P2_P3_INFORMATION_SAFE_PREFLIGHT_VERIFICATION_20261002_V1.json",
 "canonical/governance/PROFESSIONAL_ARTIFACT_INTERNAL_PREWAVE_BINDING_V1.json",
 "canonical/governance/NATIVE_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json",
 "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json",
 "canonical/governance/TERMINAL_PORTFOLIO_PREWAVE_PROTOCOL_V1.json",
)

def _manifest_has_route(m:dict,surface_id:str)->bool:
    t1=((m.get("portfolios") or {}).get("T1") or {})
    for s in t1.get("surfaces") or []:
        if s.get("id")==surface_id and REQUIRED_ROUTE in (s.get("proof_routes") or []):
            return True
    return False

def evaluate(root:Path)->dict:
    errors=[]
    try:
        d=json.loads((root/BINDING).read_text(encoding="utf-8"))
        manifest=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pass":False,"errors":["INPUT_UNREADABLE:"+type(exc).__name__],"execution_authority":False}
    if d.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        errors.append("BEHAVIOR_ID")
    if d.get("proof_mode")!="T1_MULTIPLEXED_DIRECT_PROFESSIONAL_QUALITY_GATE":
        errors.append("PROOF_MODE")
    if set(d.get("portfolio_bindings") or [])!={"T1"}:
        errors.append("PORTFOLIO_BINDING")
    if set(d.get("direct_surface_bindings") or [])!=REQUIRED_SURFACES:
        errors.append("DIRECT_SURFACE_BINDINGS")
    if not _manifest_has_route(manifest,"GDPVAL_AA_V2_1"):
        errors.append("T1_GDPVAL_P2_ROUTE_NOT_BOUND")
    if not _manifest_has_route(manifest,"AA_BRIEFCASE_V1_1"):
        errors.append("T1_AA_BRIEFCASE_P2_ROUTE_NOT_BOUND")
    visible=set(d.get("candidate_visible_information") or [])
    forbidden=set(d.get("candidate_must_not_receive") or [])
    if visible & FORBIDDEN_VISIBLE:
        errors.append("HIDDEN_ORACLE_LEAK")
    if not FORBIDDEN_VISIBLE <= forbidden:
        errors.append("FORBIDDEN_INFORMATION_SET_INCOMPLETE")
    ev=d.get("evaluator") or {}
    if set(ev.get("required_checks") or [])!=REQUIRED_CHECKS:
        errors.append("CHECK_SET")
    if set(ev.get("required_mutations") or [])!=REQUIRED_MUTATIONS:
        errors.append("MUTATION_SET")
    if ev.get("mutation_acceptance")!="ALL_APPLICABLE_MATERIAL_QUALITY_MUTATIONS_MUST_BE_DETECTED_OR_DEGRADE_INDEPENDENT_RUBRIC":
        errors.append("MUTATION_ACCEPTANCE")
    priv=d.get("private_or_named_surface_execution") or {}
    if priv.get("required_for_this_prewave_binding") is not False:
        errors.append("PRIVATE_SURFACE_EXECUTION_DEPENDENCE")
    if priv.get("score_inference_forbidden") is not True:
        errors.append("PRIVATE_SCORE_INFERENCE_NOT_FORBIDDEN")
    ta=d.get("terminal_acceptance") or {}
    if ta.get("prewave_binding_is_terminal_result") is not False:
        errors.append("PREWAVE_RESULT_OVERCLAIM")
    if ta.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_SCOPE_OVERCLAIM")
    if ta.get("terminal_evidence_source")!="THE_FROZEN_T1_TERMINAL_OBSERVATIONS_WITH_DIRECT_P2_INSTRUMENTATION":
        errors.append("TERMINAL_EVIDENCE_SOURCE")
    if ta.get("public_bar_credit_only_for_declared_surface_scope") is not True:
        errors.append("PUBLIC_BAR_SCOPE_INHERITANCE")
    if ta.get("any_load_bearing_p2_failure_blocks_behavior_proof") is not True:
        errors.append("P2_FAILURE_NOT_BLOCKING")
    if "NO_PRIVATE_SCORE_INFERENCE" not in str(ta.get("proof_rule") or ""):
        errors.append("PRIVATE_SCORE_PROOF_RULE")
    if "NO_CROSS_BEHAVIOR_SCORE_INHERITANCE" not in str(ta.get("proof_rule") or ""):
        errors.append("CROSS_BEHAVIOR_INHERITANCE")
    con=d.get("contamination") or {}
    for k in ("post_freeze_case_specific_tuning","case_replacement","result_to_runtime_feedback_during_wave","evaluator_or_threshold_edit_after_first_terminal_result"):
        if con.get(k) is not False:
            errors.append("CONTAMINATION:"+k)
    if d.get("prewave_admissible") is not False:
        errors.append("PREMATURE_ADMISSION")
    if d.get("independent_verification") is not None:
        errors.append("PREMATURE_VERIFICATION_BINDING")
    if d.get("execution_authority") is not False or d.get("terminal_results_observed")!=0 or d.get("fresh_terminal_evidence_consumed")!=0:
        errors.append("AUTHORITY_OR_RESULT")
    if d.get("capability_credit_delta")!=0 or d.get("family_credit_delta")!=0:
        errors.append("CREDIT_DELTA")
    for rel in REQUIRED_DEPS:
        if not (root/rel).is_file():
            errors.append("DEPENDENCY_MISSING:"+rel)
    return {
      "schema":"PROJECT_BRAIN_P2_T1_MULTIPLEX_PREFLIGHT_VERDICT_V1",
      "pass":not errors,"errors":sorted(set(errors)),
      "execution_authority":False,"terminal_results_observed":0,
      "capability_credit_delta":0,"family_credit_delta":0,
    }
