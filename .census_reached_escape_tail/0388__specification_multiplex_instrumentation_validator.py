"""Fail-closed validator for portfolio-multiplexed specification instrumentation."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

MANIFEST="canonical/governance/SPECIFICATION_PORTFOLIO_MULTIPLEX_INSTRUMENTATION_V1.json"
REGISTRY="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"

def _load(root:Path,path:str)->dict[str,Any]:
    data=json.loads((root/path).read_text(encoding="utf-8"))
    if not isinstance(data,dict):
        raise ValueError(path+"_NOT_OBJECT")
    return data

def evaluate(root:Path)->dict[str,Any]:
    errors=[]
    m=_load(root,MANIFEST)
    r=_load(root,REGISTRY)
    rows=r.get("active_contracted_residuals")
    if not isinstance(rows,list):
        errors.append("REGISTRY_ROWS_INVALID"); rows=[]
    row=next((x for x in rows if isinstance(x,dict) and x.get("behavior_id")=="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"),None)
    if row is None:
        errors.append("BEHAVIOR_NOT_IN_REGISTRY")
    else:
        if "hidden verifier" not in str(row.get("allowed_information","")).lower():
            errors.append("REGISTRY_HIDDEN_VERIFIER_BOUNDARY_MISSING")
        required=str(row.get("required_output_or_action","")).lower()
        if "independently" not in required or "counterexamples" not in required:
            errors.append("REGISTRY_ACCEPTANCE_OR_COUNTEREXAMPLE_REQUIREMENT_MISSING")

    if m.get("schema")!="PROJECT_BRAIN_SPECIFICATION_PORTFOLIO_MULTIPLEX_INSTRUMENTATION_V1":
        errors.append("SCHEMA")
    if m.get("behavior_id")!="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001":
        errors.append("BEHAVIOR_ID")

    info=m.get("candidate_visible_information") or {}
    visible=set(info.get("universal") or [])
    forbidden=set(info.get("forbidden") or [])
    if "RAW_TASK_SPECIFICATION_TEXT" not in visible:
        errors.append("RAW_SPEC_VISIBILITY_MISSING")
    required_forbidden={
        "HIDDEN_ACCEPTANCE_CRITERIA","REFERENCE_SOLUTION","MUTATION_EXPECTED_EFFECT",
        "GOLD_REQUIREMENT_GRAPH","AMBIGUITY_TRUTH","FINAL_TASK_SCORE","VERIFIER_IMPLEMENTATION",
    }
    if not required_forbidden.issubset(forbidden):
        errors.append("HIDDEN_FIELDS_NOT_ALL_FORBIDDEN")

    scorer=m.get("ambiguity_and_counterexample_scorer") or {}
    if scorer.get("deterministic") is not True:
        errors.append("SCORER_NOT_DETERMINISTIC")
    muts=set(scorer.get("mutation_classes") or [])
    required_mutations={
        "REQUIRED_ITEM_OMISSION","POLARITY_FLIP","CONDITION_DROP","SUBJECT_OBJECT_SWAP",
        "DEPENDENCY_OR_ORDER_VIOLATION","UNSUPPORTED_EXTRA_REQUIREMENT","AMBIGUOUS_REFERENT",
    }
    if not required_mutations.issubset(muts):
        errors.append("MUTATION_COVERAGE_INCOMPLETE")
    critical=set(scorer.get("per_case_critical_failures") or [])
    if "PORTFOLIO_HIDDEN_ORACLE_FIELD_VISIBLE_TO_CANDIDATE" not in critical:
        errors.append("ORACLE_LEAK_NOT_CRITICAL_FAILURE")

    boundaries=m.get("portfolio_information_boundaries")
    if not isinstance(boundaries,dict) or set(boundaries)!={"T0","T1","T2","T3"}:
        errors.append("PORTFOLIO_BOUNDARIES_NOT_EXACT_T0_T1_T2_T3")
    else:
        for pid,b in boundaries.items():
            if not isinstance(b,dict) or not str(b.get("visible") or "") or not str(b.get("hidden") or ""):
                errors.append("PORTFOLIO_BOUNDARY_INVALID:"+pid)

    selector=m.get("post_freeze_selector") or {}
    if selector.get("selection_before_downstream_portfolio_freeze") is not False:
        errors.append("PRE_FREEZE_SELECTION_ALLOWED")
    for key in ("adaptive_selection","case_replacement","tuning_replay"):
        if selector.get(key) is not False:
            errors.append(key.upper()+"_NOT_FALSE")

    accounting=m.get("acceptance_accounting") or {}
    if accounting.get("terminal_promotion_from_this_manifest") is not False:
        errors.append("MANIFEST_SELF_PROMOTION_ALLOWED")
    if accounting.get("prewave_ready_if_independently_validated") is not True:
        errors.append("PREWAVE_READY_RULE_MISSING")
    required_terminal=set(accounting.get("terminal_behavior_evidence_requires") or [])
    for item in (
        "ZERO_CRITICAL_SEMANTIC_ACCEPTANCE_MISS_IN_CLAIMED_SCOPE",
        "ZERO_INFORMATION_LEAK",
        "PROVENANCE_COMPLETE",
        "DOWNSTREAM_PORTFOLIO_RESULT_ADMISSIBLE_UNDER_ITS_OWN_PROOF_MODE",
    ):
        if item not in required_terminal:
            errors.append("TERMINAL_REQUIREMENT_MISSING:"+item)

    if m.get("execution_authority") is not False:
        errors.append("EXECUTION_AUTHORITY_NOT_FALSE")
    if m.get("capability_credit_delta") != 0 or m.get("family_credit_delta") != 0:
        errors.append("NONZERO_CREDIT")

    errors=sorted(set(errors))
    return {
        "schema":"PROJECT_BRAIN_SPECIFICATION_MULTIPLEX_INSTRUMENTATION_VALIDATION_V1",
        "pass":not errors,
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "errors":errors,
        "execution_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
