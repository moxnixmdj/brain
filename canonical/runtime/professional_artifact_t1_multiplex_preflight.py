"""Fail-closed pre-wave verifier for professional artifact T1 multiplex binding."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

BINDING="canonical/governance/PROFESSIONAL_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json"
REQUIRED_VISIBLE={
    "OBJECTIVE","AUDIENCE","REQUIRED_TOPICS","RUBRIC_WEIGHTS",
    "SOURCE_FACTS_WITH_PROVENANCE","CURRENT_DRAFT_OR_RENDER_STATE",
    "EDIT_CANDIDATES","EDIT_BUDGET","DECLARED_NATIVE_FORMAT_METADATA"
}
FORBIDDEN_VISIBLE={
    "HIDDEN_ORACLE_FACTORS","REFERENCE_SOLUTION","GOLD_PLAN",
    "ABLATION_LABELS","EXPECTED_SCORE_DELTA","TERMINAL_ACCEPTANCE_LABEL"
}
REQUIRED_INSTRUMENTATION={
    "SELECTED_EDIT_IDS_EXIST_AND_EDIT_BUDGET_IS_RESPECTED",
    "EVERY_SELECTED_CLAIM_IS_TRACEABLE_TO_VISIBLE_SOURCE_FACTS",
    "SUPPORTED_REQUIRED_TOPICS_ARE_NOT_SILENTLY_DROPPED",
    "AUDIENCE_AND_ANALYSIS_KIND_ARE_LOAD_BEARING",
    "INDEPENDENT_RUBRIC_DELTA_BEATS_MECHANICS_ONLY_BASELINE_WHEN_QUALITY_JUDGMENT_IS_LOAD_BEARING",
    "SEEDED_PLAN_ABLATION_DEGRADES_OR_FAILS_THE_RELEVANT_RUBRIC_DIMENSION",
    "SEEDED_RESCUE_EDIT_RESTORES_OR_IMPROVES_THE_RELEVANT_RUBRIC_DIMENSION",
    "ANY_NATIVE_EDIT_USED_BY_THE_CASE_PASSES_THE_SEPARATE_NATIVE_ARTIFACT_MECHANICAL_GATE",
}

def evaluate(root:Path)->dict:
    errors=[]
    try:
        d=json.loads((root/BINDING).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema":"PROJECT_BRAIN_PROFESSIONAL_ARTIFACT_T1_MULTIPLEX_PREFLIGHT_VERDICT_V1","pass":False,"errors":["BINDING_UNREADABLE:"+type(exc).__name__],"execution_authority":False,"capability_credit_delta":0}
    if d.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001": errors.append("BEHAVIOR_ID")
    if d.get("proof_mode")!="T1_MULTIPLEXED_DIRECT_PROFESSIONAL_QUALITY_GATE": errors.append("PROOF_MODE")
    dec=d.get("decomposition") or {}
    if dec.get("reused_adjacent_gate")!="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001": errors.append("ADJACENT_GATE")
    if dec.get("no_cross_behavior_score_inheritance") is not True: errors.append("CROSS_BEHAVIOR_INHERITANCE")
    visible=set(d.get("candidate_visible_information") or [])
    if not REQUIRED_VISIBLE <= visible: errors.append("VISIBLE_INFORMATION_INCOMPLETE")
    if FORBIDDEN_VISIBLE & visible: errors.append("ORACLE_LEAK")
    forbidden=set(d.get("candidate_must_not_receive") or [])
    if not FORBIDDEN_VISIBLE <= forbidden: errors.append("FORBIDDEN_INFORMATION_INCOMPLETE")
    ts=d.get("terminal_surface") or {}
    if ts.get("portfolio")!="T1": errors.append("PORTFOLIO")
    if ts.get("synthetic_whole_domain_superset_required") is not False: errors.append("SYNTHETIC_SCOPE_STRETCH")
    if ts.get("named_private_benchmarks_required_for_execution") is not False: errors.append("PRIVATE_SURFACE_DEPENDENCY")
    if not str(ts.get("deletion_policy") or "").endswith("PRIVATE_SURFACE_DEPENDENCY_DELETION_AND_ABSOLUTE_PROOF_MAP_V1.json"): errors.append("DELETION_POLICY")
    instr=set(d.get("direct_instrumentation") or [])
    if not REQUIRED_INSTRUMENTATION <= instr: errors.append("DIRECT_INSTRUMENTATION_INCOMPLETE")
    if "NO_SCOPE_INHERITANCE" not in str(d.get("uncovered_scope_rule") or ""): errors.append("UNCOVERED_SCOPE_RULE")
    accounting=d.get("post_freeze_accounting") or {}
    for key in ("adaptive_case_selection","case_replacement","tuning_replay","result_to_runtime_feedback_during_wave","oracle_or_threshold_edit_after_first_terminal_result"):
        if accounting.get(key) is not False: errors.append("CONTAMINATION:"+key)
    if accounting.get("failed_case_counts_as_failure") is not True: errors.append("FAILURE_ACCOUNTING")
    if d.get("prewave_admissible") is not False: errors.append("PREMATURE_ADMISSION")
    if d.get("independent_verification") is not None: errors.append("PREMATURE_VERIFICATION_BINDING")
    if d.get("execution_authority") is not False or d.get("terminal_results_observed")!=0: errors.append("AUTHORITY_OR_RESULT")
    for rel in d.get("dependencies") or []:
        if not isinstance(rel,str) or not (root/rel).is_file(): errors.append("DEPENDENCY_MISSING:"+str(rel))
    return {
        "schema":"PROJECT_BRAIN_PROFESSIONAL_ARTIFACT_T1_MULTIPLEX_PREFLIGHT_VERDICT_V1",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "execution_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("repo_root",type=Path,nargs="?",default=Path("."))
    args=ap.parse_args()
    out=evaluate(args.repo_root)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
