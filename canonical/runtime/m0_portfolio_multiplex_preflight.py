"""Fail-closed pre-wave verifier for the M0 portfolio-multiplex binding.

This verifier checks only frozen protocol structure and information separation.
It does not execute terminal cases and grants no capability credit.
"""
from __future__ import annotations
import json
from pathlib import Path

BINDING = "canonical/governance/M0_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json"

REQUIRED_PORTFOLIOS = {"T0","T1","T2","T3"}
FORBIDDEN_VISIBLE = {
    "HIDDEN_VERIFIER","REFERENCE_SOLUTION","GOLD_NORMALIZED_REQUIREMENTS",
    "GOLD_ACCEPTANCE_CONSEQUENCES","MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON",
}
REQUIRED_MUTATIONS = {
    "DROP_REQUIRED_ATOM","INVERT_REQUIREMENT_POLARITY","DELETE_MATERIAL_CONDITION",
    "COLLAPSE_AMBIGUITY_TO_ARBITRARY_SINGLE_INTERPRETATION",
    "REMOVE_INDEPENDENT_ACCEPTANCE_FAILURE_MODE",
}

def evaluate(root: Path) -> dict:
    p=root/BINDING
    errors=[]
    try:
        d=json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pass":False,"errors":["BINDING_UNREADABLE:"+type(exc).__name__]}
    if d.get("behavior_id")!="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001":
        errors.append("BEHAVIOR_ID")
    if d.get("proof_mode")!="PORTFOLIO_MULTIPLEXED_OPEN_DOMAIN_TERMINAL_PROOF":
        errors.append("PROOF_MODE")
    if set(d.get("portfolio_bindings") or [])!=REQUIRED_PORTFOLIOS:
        errors.append("PORTFOLIO_BINDINGS")
    visible=set(d.get("candidate_visible_information") or [])
    forbidden=set(d.get("candidate_must_not_receive") or [])
    if visible & FORBIDDEN_VISIBLE:
        errors.append("HIDDEN_ORACLE_LEAK_IN_VISIBLE_FIELDS")
    if not FORBIDDEN_VISIBLE <= forbidden:
        errors.append("FORBIDDEN_INFORMATION_SET_INCOMPLETE")
    ev=d.get("evaluator") or {}
    if set(ev.get("required_mutations") or []) != REQUIRED_MUTATIONS:
        errors.append("MUTATION_SET")
    ta=d.get("terminal_acceptance") or {}
    if ta.get("prewave_binding_is_terminal_result") is not False:
        errors.append("PREWAVE_CREDIT_LEAK")
    if ta.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_SUPERSET_OVERCLAIM_NOT_FORBIDDEN")
    if "T0_T1_T2_T3" not in str(ta.get("terminal_evidence_source") or ""):
        errors.append("TERMINAL_EVIDENCE_SOURCE")
    con=d.get("contamination") or {}
    for k in ("post_freeze_case_specific_tuning","case_replacement","result_to_runtime_feedback_during_wave","evaluator_or_threshold_edit_after_first_terminal_result"):
        if con.get(k) is not False:
            errors.append("CONTAMINATION_FLAG:"+k)
    if d.get("execution_authority") is not False:
        errors.append("EXECUTION_AUTHORITY")
    if d.get("terminal_results_observed") != 0:
        errors.append("TERMINAL_RESULTS_OBSERVED")
    if d.get("capability_credit_delta") != 0 or d.get("family_credit_delta") != 0:
        errors.append("CREDIT_DELTA")
    for rel in [
        "canonical/runtime/source_contract_compiler.py",
        "canonical/runtime/independent_acceptance_model.py",
        "canonical/runtime/m0a_raw_source_terminal_suite_v2.py",
        "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json",
        "canonical/governance/TERMINAL_PORTFOLIO_PREWAVE_PROTOCOL_V1.json",
    ]:
        if not (root/rel).is_file():
            errors.append("DEPENDENCY_MISSING:"+rel)
    return {
        "schema":"PROJECT_BRAIN_M0_PORTFOLIO_MULTIPLEX_PREFLIGHT_VERDICT_V1",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "execution_authority":False,
        "capability_credit_delta":0,
    }
