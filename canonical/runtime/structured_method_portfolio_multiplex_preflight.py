"""Fail-closed prewave verifier for structured-method T0/T1 multiplex binding."""
from __future__ import annotations
import json
from pathlib import Path

BINDING="canonical/governance/STRUCTURED_METHOD_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json"
REQUIRED_PORTFOLIOS={"T0","T1"}
REQUIRED_SURFACES={
 "T0/FRONTIERCODE_V1_1::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF",
 "T1/FINANCE_ACCOUNTING_INDEX::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF",
 "T1/FINANCE_AGENT_V2::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF",
}
FORBIDDEN_VISIBLE={
 "HIDDEN_VERIFIER","REFERENCE_GRAPH","GOLD_REQUIREMENT_LINEAGE",
 "GOLD_JUSTIFIED_EXCLUSIONS","GOLD_EDGE_ACCEPTANCE_RESULT",
 "MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON",
}
REQUIRED_MUTATIONS={
 "DELETE_MATERIAL_EDGE","REWIRE_MATERIAL_EDGE","DROP_REQUIRED_CONSUMER",
 "DELETE_JUSTIFIED_EXCLUSION","MUTATE_TYPE_OR_DIMENSION",
 "DELETE_DECLARED_INVARIANT","MUTATE_REQUIRED_OUTPUT",
}
REQUIRED_DEPS=(
 "canonical/runtime/structured_method_normalized_rule_graph_v3.py",
 "canonical/runtime/structured_method_normalized_rule_oracle_v3.py",
 "canonical/runtime/scope_equivalent_proof_gate_v2.py",
 "canonical/governance/STRUCTURED_METHOD_SCOPE_AUDIT_V3.json",
 "canonical/verification/STRUCTURED_METHOD_SCOPE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
 "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json",
 "canonical/governance/TERMINAL_PORTFOLIO_PREWAVE_PROTOCOL_V1.json",
)

def evaluate(root:Path)->dict:
    errors=[]
    try:
        d=json.loads((root/BINDING).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pass":False,"errors":["BINDING_UNREADABLE:"+type(exc).__name__]}
    if d.get("behavior_id")!="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
        errors.append("BEHAVIOR_ID")
    if d.get("proof_mode")!="PORTFOLIO_MULTIPLEXED_DETERMINISTIC_TERMINAL_PROOF":
        errors.append("PROOF_MODE")
    if set(d.get("portfolio_bindings") or [])!=REQUIRED_PORTFOLIOS:
        errors.append("PORTFOLIO_BINDINGS")
    if set(d.get("direct_surface_bindings") or [])!=REQUIRED_SURFACES:
        errors.append("DIRECT_SURFACE_BINDINGS")
    visible=set(d.get("candidate_visible_information") or [])
    forbidden=set(d.get("candidate_must_not_receive") or [])
    if visible & FORBIDDEN_VISIBLE:
        errors.append("HIDDEN_ORACLE_LEAK_IN_VISIBLE_FIELDS")
    if not FORBIDDEN_VISIBLE <= forbidden:
        errors.append("FORBIDDEN_INFORMATION_SET_INCOMPLETE")
    ev=d.get("evaluator") or {}
    if set(ev.get("required_mutations") or [])!=REQUIRED_MUTATIONS:
        errors.append("MUTATION_SET")
    ta=d.get("terminal_acceptance") or {}
    if ta.get("prewave_binding_is_terminal_result") is not False:
        errors.append("PREWAVE_CREDIT_LEAK")
    if ta.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_SUPERSET_OVERCLAIM_NOT_FORBIDDEN")
    if "T0_T1" not in str(ta.get("terminal_evidence_source") or ""):
        errors.append("TERMINAL_EVIDENCE_SOURCE")
    if ta.get("any_load_bearing_structured_method_failure_blocks_behavior_proof") is not True:
        errors.append("LOAD_BEARING_FAILURE_NOT_BLOCKING")
    con=d.get("contamination") or {}
    for k in ("post_freeze_case_specific_tuning","case_replacement","result_to_runtime_feedback_during_wave","evaluator_or_threshold_edit_after_first_terminal_result"):
        if con.get(k) is not False:
            errors.append("CONTAMINATION_FLAG:"+k)
    if d.get("execution_authority") is not False:
        errors.append("EXECUTION_AUTHORITY")
    if d.get("terminal_results_observed")!=0:
        errors.append("TERMINAL_RESULTS_OBSERVED")
    if d.get("capability_credit_delta")!=0 or d.get("family_credit_delta")!=0:
        errors.append("CREDIT_DELTA")
    for rel in REQUIRED_DEPS:
        if not (root/rel).is_file():
            errors.append("DEPENDENCY_MISSING:"+rel)
    return {
      "schema":"PROJECT_BRAIN_STRUCTURED_METHOD_PORTFOLIO_MULTIPLEX_PREFLIGHT_VERDICT_V1",
      "pass":not errors,"errors":sorted(set(errors)),
      "execution_authority":False,"capability_credit_delta":0,"family_credit_delta":0,
    }
