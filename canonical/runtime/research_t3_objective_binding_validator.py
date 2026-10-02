"""Fail-closed validator for the direct-objective Research T3 prewave binding."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any

BINDING="canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
REQUIRED_DIMS={
"UNRESOLVED_REQUIREMENT_TARGETING","SOURCE_AUTHORITY_PRIORITIZATION",
"INFORMATION_GAIN_OR_NEW_REQUIREMENT_COVERAGE","PROVENANCE_PRESERVATION",
"REDUNDANT_RETRIEVAL_BOUND","MATERIAL_SOURCE_COVERAGE",
"SUFFICIENCY_AND_STOP_CALIBRATION","TERMINAL_CORRECTNESS_AND_COVERAGE"}
REQUIRED_CHECKS={
"QUERY_TARGETS_CURRENT_UNRESOLVED_MATERIAL_REQUIREMENT",
"SOURCE_SELECTION_RESPECTS_MINIMUM_AUTHORITY_AND_FROZEN_COST_TIEBREAK",
"FAILED_HIGH_AUTHORITY_FETCH_RECOVERS_WITHOUT_REDUNDANT_SEARCH",
"EVIDENCE_RECEIPTS_PRESERVE_PROVENANCE","REDUNDANT_REFETCH_REJECTED",
"PREMATURE_STOP_REJECTED",
"STOP_ONLY_AFTER_ALL_MATERIAL_REQUIREMENTS_HAVE_AUTHORITATIVE_SUPPORT",
"ACTION_BUDGET_RESPECTED"}
REQUIRED_NEG={"PREMATURE_STOP","IRRELEVANT_QUERY_DRIFT","REDUNDANT_REFETCH","FETCH_WITHOUT_CURRENT_SEARCH_HIT","SEARCH_ALREADY_RESOLVED_REQUIREMENT"}

def blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def evaluate(root:Path)->dict[str,Any]:
    errors=[]
    try:b=json.loads((root/BINDING).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pass":False,"errors":["BINDING_UNREADABLE:"+type(exc).__name__],"execution_authority":False,"capability_credit_delta":0,"family_credit_delta":0}
    if b.get("behavior_id")!="ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001":errors.append("BEHAVIOR_ID")
    if b.get("proof_mode")!="T3_MULTIPLEXED_DIRECT_OBJECTIVE_RESEARCH_CONTROL_GATE":errors.append("PROOF_MODE")
    exact=b.get("exact_bound_blobs") or {}
    for name,row in exact.items():
        if not isinstance(row,dict): errors.append("BLOB_ROW:"+str(name)); continue
        rel=row.get("path"); expected=row.get("blob_sha")
        if not isinstance(rel,str) or not isinstance(expected,str): errors.append("BLOB_SPEC:"+str(name)); continue
        p=root/rel
        if not p.is_file(): errors.append("BLOB_MISSING:"+rel); continue
        if blob(p)!=expected: errors.append("BLOB_MISMATCH:"+rel)
    pool=b.get("source_pool") or {}
    if pool.get("terminal_sample_count")!=600:errors.append("SAMPLE_COUNT")
    if pool.get("domain_cycle")!=["biology","finance","systems","law","energy","materials"]:errors.append("DOMAIN_CYCLE")
    if pool.get("requirement_count_cycle")!=[3,4,5]:errors.append("REQUIREMENT_COUNT_CYCLE")
    if "POST_FREEZE_BEACON" not in str(pool.get("case_generation_rule")):errors.append("POST_FREEZE_SEED_RULE")
    if "NO_TERMINAL_CASE_SEED" not in str(pool.get("fresh_terminal_rule")):errors.append("FRESH_TERMINAL_RULE")
    sel=b.get("selector") or {}
    for k in ("beacon_known_before_freeze","adaptive_case_selection","case_replacement","tuning_replay","result_to_runtime_feedback"):
        if sel.get(k) is not False:errors.append("SELECTOR:"+k)
    if set(b.get("objective_dimensions") or [])!=REQUIRED_DIMS:errors.append("OBJECTIVE_DIMENSIONS")
    info=b.get("information_boundary") or {}
    if info.get("candidate_receives_hidden_oracle") is not False:errors.append("HIDDEN_ORACLE_LEAK")
    hidden=set(info.get("hidden_from_candidate") or [])
    for x in ("HIDDEN_SOURCE_SUPPORT_TRUTH_BEFORE_FETCH","POST_FREEZE_BEACON_BEFORE_FREEZE","TERMINAL_ACCEPTANCE_RESULT","MUTATION_IDENTITY"):
        if x not in hidden:errors.append("HIDDEN_SET:"+x)
    acc=b.get("acceptance") or {}
    if acc.get("every_selected_case_must_pass") is not True:errors.append("EVERY_CASE")
    if acc.get("every_domain_class_must_be_present") is not True:errors.append("DOMAIN_COVERAGE")
    if acc.get("requirement_count_classes_required")!=[3,4,5]:errors.append("REQ_COUNT_COVERAGE")
    if set(acc.get("direct_checks") or [])!=REQUIRED_CHECKS:errors.append("DIRECT_CHECKS")
    if set(acc.get("required_negative_controls") or [])!=REQUIRED_NEG:errors.append("NEGATIVE_CONTROLS")
    bound=b.get("contract_boundary") or {}
    if bound.get("loop_control_owned_here") is not True:errors.append("LOOP_CONTROL_BOUNDARY")
    for k in ("upstream_requirement_extraction_owned_here","evidence_to_audience_synthesis_owned_here","tool_route_discovery_owned_here"):
        if bound.get(k) is not False:errors.append("CROSS_CONTRACT_OVERCLAIM:"+k)
    weak=b.get("weaker_dependency_reconciliation") or {}
    if weak.get("dependency")!="HLE_CANONICAL_CONTENT_ACCESS_AT_ZERO_INCREMENTAL_SPEND":errors.append("HLE_DEP")
    if weak.get("required_for_this_behavioral_prewave") is not False:errors.append("HLE_NOT_DELETED_FOR_DIRECT_ROUTE")
    if weak.get("deletion_authorized_before_independent_binding_verification") is not False:errors.append("PREMATURE_DELETION_AUTHORITY")
    gates=b.get("route_gates") or {}
    for k in ("candidate_package_frozen","executable_evaluator_bound","population_or_source_pool_frozen","information_boundary_frozen","post_freeze_selector_frozen","terminal_parent_binding_frozen"):
        if gates.get(k) is not True:errors.append("GATE:"+k)
    if gates.get("independent_verification_pass") is not False:errors.append("PREMATURE_INDEPENDENT_PASS")
    if b.get("prewave_admissible") is not False:errors.append("PREMATURE_PREWAVE")
    if b.get("execution_authority") is not False or b.get("promotion_authority") is not False:errors.append("AUTHORITY")
    if b.get("terminal_results_observed")!=0 or b.get("fresh_terminal_evidence_consumed")!=0:errors.append("TERMINAL_EVIDENCE")
    if b.get("capability_credit_delta")!=0 or b.get("family_credit_delta")!=0:errors.append("CREDIT")
    # Upstream preflight receipt must be independently successful, but it is not terminal evidence.
    try:
        rec=json.loads((root/"canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json").read_text())
        if "INDEPENDENT_PASS" not in str(rec.get("status","")) or rec.get("workflow_conclusion")!="success":
            errors.append("UPSTREAM_PREFLIGHT_NOT_INDEPENDENT_PASS")
    except Exception:errors.append("UPSTREAM_PREFLIGHT_UNREADABLE")
    return {"schema":"PROJECT_BRAIN_RESEARCH_T3_OBJECTIVE_BINDING_PREFLIGHT_VERDICT_V1","pass":not errors,"errors":sorted(set(errors)),"execution_authority":False,"promotion_authority":False,"terminal_results_observed":0,"fresh_terminal_evidence_consumed":0,"capability_credit_delta":0,"family_credit_delta":0}

def main()->int:
    root=Path(__file__).resolve().parents[2]
    out=evaluate(root); print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out["pass"] else 1
if __name__=="__main__":raise SystemExit(main())
