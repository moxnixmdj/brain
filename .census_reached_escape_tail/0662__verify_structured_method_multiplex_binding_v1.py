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
REQUIRED_CHECKS={
 "EVERY_APPLICABLE_REQUIREMENT_HAS_TRACED_CONSUMER",
 "EVERY_EXCLUDED_REQUIREMENT_HAS_EXPLICIT_JUSTIFICATION",
 "EVERY_MATERIAL_INPUT_TO_OUTPUT_EDGE_IS_PRESENT",
 "DEPENDENCY_ORDER_IS_ACYCLIC_AND_COMPLETE",
 "DECLARED_TYPE_AND_DIMENSION_CONTRACTS_HOLD",
 "DECLARED_INVARIANTS_ARE_PRESERVED_IN_GRAPH",
 "EVERY_REQUIRED_OUTPUT_IS_TRACED",
 "INDEPENDENT_EDGE_ACCEPTANCE_IS_NOT_BUILDER_DERIVED",
}
REQUIRED_MUTATIONS={
 "DELETE_MATERIAL_EDGE","REWIRE_MATERIAL_EDGE","DROP_REQUIRED_CONSUMER",
 "DELETE_JUSTIFIED_EXCLUSION","MUTATE_TYPE_OR_DIMENSION",
 "DELETE_DECLARED_INVARIANT","MUTATE_REQUIRED_OUTPUT",
}
DEPENDENCIES=[
 "canonical/runtime/structured_method_normalized_rule_graph_v3.py",
 "canonical/runtime/structured_method_normalized_rule_oracle_v3.py",
 "canonical/runtime/scope_equivalent_proof_gate_v2.py",
 "canonical/verification/STRUCTURED_METHOD_SCOPE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
]

def evaluate(root:Path)->dict:
    errors=[]
    try:
        d=json.loads((root/BINDING).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema":"PROJECT_BRAIN_STRUCTURED_METHOD_MULTIPLEX_PREFLIGHT_V1","pass":False,"errors":["BINDING_UNREADABLE:"+type(exc).__name__]}
    if d.get("behavior_id")!="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001": errors.append("BEHAVIOR_ID")
    if d.get("proof_mode")!="PORTFOLIO_MULTIPLEXED_DETERMINISTIC_TERMINAL_PROOF": errors.append("PROOF_MODE")
    if set(d.get("portfolio_bindings") or [])!=REQUIRED_PORTFOLIOS: errors.append("PORTFOLIOS")
    if set(d.get("direct_surface_bindings") or [])!=REQUIRED_SURFACES: errors.append("DIRECT_SURFACES")
    visible=set(d.get("candidate_visible_information") or [])
    hidden=set(d.get("hidden_evaluator_information") or [])
    forbidden=set(d.get("candidate_must_not_receive") or [])
    if visible & hidden: errors.append("VISIBLE_HIDDEN_OVERLAP")
    if visible & forbidden: errors.append("FORBIDDEN_VISIBLE")
    e=d.get("evaluator") or {}
    if set(e.get("required_checks") or [])!=REQUIRED_CHECKS: errors.append("CHECK_SET")
    if set(e.get("required_mutations") or [])!=REQUIRED_MUTATIONS: errors.append("MUTATION_SET")
    if e.get("mutation_acceptance")!="ALL_APPLICABLE_MATERIAL_MUTATIONS_MUST_BE_DETECTED_OR_FAIL_CLOSED": errors.append("MUTATION_ACCEPTANCE")
    t=d.get("terminal_acceptance") or {}
    if t.get("prewave_binding_is_terminal_result") is not False: errors.append("PREWAVE_RESULT_OVERCLAIM")
    if t.get("standalone_synthetic_whole_domain_score_forbidden") is not True: errors.append("SYNTHETIC_OVERCLAIM")
    if t.get("terminal_evidence_source")!="THE_FROZEN_T0_T1_TERMINAL_OBSERVATIONS": errors.append("TERMINAL_SOURCE")
    if t.get("any_load_bearing_structured_method_failure_blocks_behavior_proof") is not True: errors.append("FAILURE_GATE")
    for k,v in (d.get("contamination") or {}).items():
        if v is not False: errors.append("CONTAMINATION:"+k)
    if d.get("execution_authority") is not False or d.get("terminal_results_observed")!=0 or d.get("fresh_terminal_evidence_consumed")!=0:
        errors.append("PREWAVE_AUTHORITY_OR_RESULT")
    for rel in DEPENDENCIES:
        if not (root/rel).is_file(): errors.append("DEPENDENCY_MISSING:"+rel)
    return {
      "schema":"PROJECT_BRAIN_STRUCTURED_METHOD_MULTIPLEX_PREFLIGHT_V1",
      "pass":not errors,"errors":sorted(set(errors)),
      "execution_authority":False,"terminal_results_observed":0,
      "capability_credit_delta":0,"family_credit_delta":0,
    }
