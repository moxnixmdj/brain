"""Reduce independently adjudicated P1 recovery evidence into behavioral-scope restoration.

This reducer never grants Opus 5.5 acceptance credit. It only answers whether the
previous P1-only scope quarantine can be removed from the historical 12/12
contract, 19/19 behavioral-family reduction.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
BASELINE=ROOT/"canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"
QUARANTINE=ROOT/"canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"
EXECUTION=ROOT/"canonical/verification/P1_PUBLIC_RECOVERY_EXECUTION_OBSERVATION_20261003_V1.json"
ADJUDICATION=ROOT/"canonical/verification/P1_POSTRUN_VERIFIER_RECEIPT_20261003_V1.json"
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
TOTAL_CONTRACTS=12
TOTAL_FAMILIES=19
EXPECTED_AFFECTED=[
    "ADVANCED_AGENTIC_CODING",
    "AGENTIC_SCIENTIFIC_RESEARCH",
    "BUSINESS_WORKFLOW_AUTOMATION",
    "COMPLEX_MULTI_TOOL_AGENCY",
    "COMPUTER_AND_BROWSER_USE",
    "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "MULTI_CAPABILITY_COMPOSITION",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
]

def load(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v,dict):
        raise ValueError(str(path)+":NOT_OBJECT")
    return v

def evaluate(
    registry:Mapping[str,Any],
    baseline:Mapping[str,Any],
    quarantine:Mapping[str,Any],
    execution:Mapping[str,Any],
    adjudication:Mapping[str,Any],
)->dict[str,Any]:
    errors:list[str]=[]
    fmap=registry.get("family_to_residual_contracts")
    if not isinstance(fmap,Mapping):
        fmap={}
        errors.append("FAMILY_MAPPING_MISSING")
    cv=baseline.get("contract_verdict")
    fv=baseline.get("family_verdict")
    if not isinstance(cv,Mapping) or cv.get("valid") is not True or cv.get("contract_count")!=12 or cv.get("contract_pass_count")!=12:
        errors.append("BASELINE_NOT_12_OF_12")
    if not isinstance(fv,Mapping) or fv.get("valid") is not True or fv.get("family_count")!=19 or fv.get("family_pass_count")!=19:
        errors.append("BASELINE_NOT_19_OF_19")
    if quarantine.get("independent_scope_mismatch_proved") is not True:
        errors.append("ORIGINAL_QUARANTINE_NOT_PROVED")
    qactive=quarantine.get("quarantine_active")
    if not isinstance(qactive,list) or "WHOLE_FROZEN_P1_CONTRACT_PASS" not in qactive:
        errors.append("ORIGINAL_P1_WHOLE_SCOPE_QUARANTINE_MISSING")

    if execution.get("status")!="FINALIZED_RESULT_OBSERVED__192_OF_192_PASS__ONE_REALITY_UNIT_USED__POST_RUN_REVIEW_REQUIRED":
        errors.append("EXECUTION_OBSERVATION_STATUS")
    run=execution.get("run") if isinstance(execution.get("run"),Mapping) else {}
    result=execution.get("result") if isinstance(execution.get("result"),Mapping) else {}
    integ=execution.get("integrity") if isinstance(execution.get("integrity"),Mapping) else {}
    if run.get("workflow_run_id")!=37108111537 or run.get("attempt")!=1 or run.get("conclusion")!="success":
        errors.append("EXECUTION_IDENTITY")
    if result.get("cases")!=192 or result.get("passes")!=192 or result.get("failures")!=0:
        errors.append("EXECUTION_NOT_192_OF_192")
    if result.get("both_semantics_classes_present_every_case") is not True:
        errors.append("SEMANTICS_COVERAGE_MISSING")
    if integ.get("fresh_reality_units_consumed")!=1 or integ.get("terminal_v3_replayed")!=0 or integ.get("rerun_credit") is not False or integ.get("incremental_spend_usd")!=0:
        errors.append("EXECUTION_INTEGRITY")

    if adjudication.get("status")!="INDEPENDENT_PASS":
        errors.append("ADJUDICATION_NOT_PASS")
    if adjudication.get("source_run_id")!=37108111537 or adjudication.get("source_cases")!=192 or adjudication.get("source_passes")!=192 or adjudication.get("source_failures")!=0:
        errors.append("ADJUDICATION_SOURCE_MISMATCH")
    if adjudication.get("source_reality_units")!=1:
        errors.append("ADJUDICATION_REALITY_UNIT_MISMATCH")
    if adjudication.get("verified_transport_requirements") is not True or adjudication.get("verified_surface_count")!=3 or adjudication.get("verified_cases_per_surface")!=64:
        errors.append("TRANSPORT_SCOPE_NOT_VERIFIED")
    if adjudication.get("verified_dual_scorer_every_case") is not True or adjudication.get("verified_no_terminal_replay") is not True:
        errors.append("SCORER_OR_REPLAY_ADJUDICATION")

    affected=sorted(
        family for family,contracts in fmap.items()
        if isinstance(contracts,list) and BEHAVIOR in contracts
    )
    if affected!=EXPECTED_AFFECTED:
        errors.append("P1_DEPENDENT_FAMILY_SET_DRIFT")
    passed=set(fv.get("passed_families") or []) if isinstance(fv,Mapping) else set()
    if not set(affected) <= passed:
        errors.append("RESTORED_FAMILIES_NOT_IN_FROZEN_BASELINE")
    unique=sorted(set(errors))
    ok=not unique
    return {
        "schema":"PROJECT_BRAIN_P1_SCOPE_RESTORATION_REDUCER_V1",
        "status":"PASS__P1_WHOLE_SCOPE_RESTORED__12_OF_12_CONTRACTS__19_OF_19_BEHAVIORAL_FAMILIES__OPUS55_ACCEPTANCE_UNCHANGED" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":unique,
        "behavior_id":BEHAVIOR,
        "contract_accounting":{
            "whole_scope_pass_count":12 if ok else None,
            "whole_scope_quarantined_count":0 if ok else None,
            "restoration_delta":1 if ok else 0,
        },
        "behavioral_family_accounting":{
            "behavioral_pass_count":19 if ok else None,
            "quarantined_family_count":0 if ok else None,
            "restored_family_count":8 if ok else 0,
            "restored_families":affected if ok else [],
        },
        "opus55_acceptance_accounting":{
            "accepted_families":3,
            "open_families":16,
            "atomic_proved":8,
            "atomic_unresolved":30,
            "atomic_total":38,
            "acceptance_delta":0,
        },
        "p1_scope_quarantine_active":False if ok else True,
        "terminal_results_replayed":0,
        "new_reality_units_consumed_by_reducer":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "behavioral_scope_restoration_delta":8 if ok else 0,
        "contract_scope_restoration_delta":1 if ok else 0,
        "promotion_authority":False,
        "rule":"RESTORE_ONLY_THE_PRIOR_P1_CAUSAL_SCOPE_RETRACTION_FROM_THE_FROZEN_12_OF_12_19_OF_19_BASELINE__DO_NOT_GRANT_OPUS55_ACCEPTANCE_CREDIT",
    }

def main()->int:
    out=evaluate(load(REGISTRY),load(BASELINE),load(QUARANTINE),load(EXECUTION),load(ADJUDICATION))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
