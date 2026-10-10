"""Fail-closed propagation of an independently verified contract-scope quarantine.

This does not modify or replay terminal evidence. It answers the narrower
post-wave question: if a whole behavioral contract is no longer admissible at
its frozen scope, which family-level provisional behavioral verdicts remain
valid under the predeclared family-to-contract mapping?
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
REDUCTION=ROOT/"canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"
SCOPE_RECEIPT=ROOT/"canonical/verification/P1_TERMINAL_EXECUTION_SCOPE_AUDIT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
TOTAL_CONTRACTS=12
TOTAL_FAMILIES=19

def load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError(str(path)+":NOT_OBJECT")
    return value

def evaluate(registry:Mapping[str,Any], reduction:Mapping[str,Any], receipt:Mapping[str,Any])->dict[str,Any]:
    errors:list[str]=[]
    fmap=registry.get("family_to_residual_contracts")
    if not isinstance(fmap,Mapping):
        fmap={}
        errors.append("FAMILY_MAPPING_MISSING")

    cv=reduction.get("contract_verdict")
    fv=reduction.get("family_verdict")
    if not isinstance(cv,Mapping) or cv.get("valid") is not True or cv.get("contract_count")!=TOTAL_CONTRACTS or cv.get("contract_pass_count")!=TOTAL_CONTRACTS:
        errors.append("SOURCE_CONTRACT_REDUCTION_NOT_12_OF_12")
    if not isinstance(fv,Mapping) or fv.get("valid") is not True or fv.get("family_count")!=TOTAL_FAMILIES or fv.get("family_pass_count")!=TOTAL_FAMILIES:
        errors.append("SOURCE_FAMILY_REDUCTION_NOT_19_OF_19")

    if receipt.get("status")!="INDEPENDENT_PUBLIC_RUNNER_PASS__EXECUTED_P1_SCOPE_PROVED_NARROWER_THAN_FROZEN_BINDING__BROAD_P1_TRANSPORT_QUARANTINED__ZERO_CREDIT":
        errors.append("SCOPE_RECEIPT_NOT_EXACT_INDEPENDENT_PASS")
    if receipt.get("scope_mismatch_proved") is not True:
        errors.append("SCOPE_MISMATCH_NOT_PROVED")
    if receipt.get("preserved_narrow_execution_evidence") is not True:
        errors.append("NARROW_EXECUTION_EVIDENCE_NOT_PRESERVED")
    if receipt.get("broad_p1_transport_admissible") is not False:
        errors.append("BROAD_P1_TRANSPORT_NOT_QUARANTINED")
    if receipt.get("recovery_acceptance_transport_admissible") is not False:
        errors.append("RECOVERY_TRANSPORT_NOT_QUARANTINED")
    if receipt.get("terminal_results_replayed") not in (None,0):
        errors.append("TERMINAL_REPLAY_NONZERO")
    if receipt.get("new_reality_units_consumed")!=0:
        errors.append("NEW_REALITY_NONZERO")

    affected=sorted(
        family for family,contracts in fmap.items()
        if isinstance(contracts,list) and BEHAVIOR in contracts
    )
    expected_affected=[
        "ADVANCED_AGENTIC_CODING",
        "AGENTIC_SCIENTIFIC_RESEARCH",
        "BUSINESS_WORKFLOW_AUTOMATION",
        "COMPLEX_MULTI_TOOL_AGENCY",
        "COMPUTER_AND_BROWSER_USE",
        "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
        "MULTI_CAPABILITY_COMPOSITION",
        "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
    ]
    if affected!=expected_affected:
        errors.append("P1_DEPENDENT_FAMILY_SET_DRIFT")

    source_passed=set(fv.get("passed_families") or []) if isinstance(fv,Mapping) else set()
    if len(source_passed)!=TOTAL_FAMILIES:
        errors.append("SOURCE_PASSED_FAMILY_SET_NOT_19")
    unaffected=sorted(source_passed-set(affected))
    if len(unaffected)!=11:
        errors.append("UNAFFECTED_FAMILY_COUNT_NOT_11")

    unique=sorted(set(errors))
    return {
        "schema":"PROJECT_BRAIN_TERMINAL_SCOPE_QUARANTINE_PROPAGATION_V1",
        "status":"PASS__P1_WHOLE_SCOPE_QUARANTINE_PROPAGATED__11_UNAFFECTED_FAMILY_PASSES__8_FAMILY_ROWS_QUARANTINED__ZERO_NEW_REALITY" if not unique else "FAIL_CLOSED",
        "pass":not unique,
        "errors":unique,
        "quarantined_behavior_id":BEHAVIOR,
        "contract_accounting":{
            "source_terminal_contract_pass_count":12,
            "whole_scope_pass_count_after_quarantine":11 if not unique else None,
            "whole_scope_quarantined_count":1 if not unique else None,
            "narrow_execution_evidence_preserved":bool(receipt.get("preserved_narrow_execution_evidence")) if not unique else None,
        },
        "family_accounting":{
            "source_behavioral_family_pass_count":19,
            "unaffected_behavioral_pass_count":len(unaffected) if not unique else None,
            "quarantined_family_count":len(affected) if not unique else None,
            "unaffected_families":unaffected if not unique else [],
            "quarantined_families":affected if not unique else [],
        },
        "terminal_results_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "rule":"INVALIDATE_ONLY_PREDECLARED_FAMILY_ROWS_CAUSALLY_DEPENDENT_ON_QUARANTINED_WHOLE_SCOPE_CONTRACT__PRESERVE_RAW_NARROW_EXECUTION_EVIDENCE__NO_TERMINAL_REPLAY",
    }

def main()->int:
    out=evaluate(load(REGISTRY),load(REDUCTION),load(SCOPE_RECEIPT))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
