"""Validate frozen terminal direct-proof scope-instance bindings.

This is prequalification infrastructure only. It verifies that every P0-P3 scope
instance is bound to an existing contract-native evaluator contract and that the
candidate I/O schema matches the scorer interface expected by that evaluator.

It does not execute terminal cases and does not grant capability or family credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import contract_native_proof_suites as suites

MANIFEST_PATH=Path("canonical/governance/TERMINAL_DIRECT_PROOF_SCOPE_INSTANCES_V1.json")

EXPECTED={
    "P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF":{
        "contract":"STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
        "required_candidate_keys":{"graph"},
        "portfolios":{"T0","T1"},
    },
    "P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF":{
        "contract":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "required_candidate_keys":{"cause_step","repair_id","evidence_steps"},
        "portfolios":{"T0","T2"},
    },
    "P2_PROFESSIONAL_ARTIFACT_QUALITY_DIRECT_PROOF":{
        "contract":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
        "required_candidate_keys":{"selected_edits"},
        "portfolios":{"T1"},
    },
    "P3_EVIDENCE_AUDIENCE_SYNTHESIS_DIRECT_PROOF":{
        "contract":"EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
        "required_candidate_keys":{"selected_claims","uncertainty_claims"},
        "portfolios":{"T1","T3"},
    },
}

def _schema_keys(schema: Mapping[str,Any]) -> set[str]:
    return {str(k) for k in schema}

def validate(manifest: Mapping[str,Any]) -> dict[str,Any]:
    errors=[]
    if manifest.get("schema")!="PROJECT_BRAIN_TERMINAL_DIRECT_PROOF_SCOPE_INSTANCES_V1":
        errors.append("SCHEMA_MISMATCH")
    if manifest.get("status")!="FROZEN_SCOPE_AND_IO_BINDINGS__NO_TERMINAL_RESULTS__POPULATION_MANIFEST_FREEZES_AFTER_CANDIDATE_COMMIT_BEFORE_RESULT":
        errors.append("STATUS_NOT_FROZEN")
    evaluator=manifest.get("evaluator") or {}
    if evaluator.get("path")!="canonical/runtime/contract_native_proof_suites.py":
        errors.append("EVALUATOR_PATH_MISMATCH")
    if evaluator.get("oracle_visibility_to_candidate") is not False:
        errors.append("ORACLE_VISIBILITY_NOT_FALSE")

    rows=manifest.get("route_instances")
    if not isinstance(rows,list):
        rows=[]
        errors.append("ROUTE_INSTANCES_NOT_LIST")
    by_id={}
    for row in rows:
        if not isinstance(row,Mapping):
            errors.append("ROUTE_INSTANCE_INVALID")
            continue
        rid=row.get("route_id")
        if not isinstance(rid,str) or not rid or rid in by_id:
            errors.append("ROUTE_ID_INVALID_OR_DUPLICATE")
            continue
        by_id[rid]=row

    if set(by_id)!=set(EXPECTED):
        errors.append("ROUTE_SET_MISMATCH")

    smoke=[]
    for rid,spec in EXPECTED.items():
        row=by_id.get(rid)
        if row is None:
            continue
        if row.get("contract")!=spec["contract"]:
            errors.append(f"{rid}:CONTRACT_MISMATCH")
            continue
        if row.get("contract") not in suites.CONTRACTS:
            errors.append(f"{rid}:CONTRACT_NOT_IN_EVALUATOR")
            continue
        if set(row.get("portfolios") or [])!=spec["portfolios"]:
            errors.append(f"{rid}:PORTFOLIO_SET_MISMATCH")
        schema=row.get("candidate_output_schema")
        if not isinstance(schema,Mapping) or _schema_keys(schema)!=spec["required_candidate_keys"]:
            errors.append(f"{rid}:CANDIDATE_SCHEMA_MISMATCH")

        # Synthetic evaluator smoke only. Fixed seed is prewave machinery data,
        # not a terminal case. Oracle candidate must pass and public task must not
        # expose the hidden oracle payload.
        case=suites.generate_case(row["contract"],seed=104729,difficulty=3)
        public=suites.public_task(case)
        candidate=suites.oracle_candidate(case)
        scored=suites.score_case(case,candidate)
        if "_oracle" in public:
            errors.append(f"{rid}:PUBLIC_TASK_EXPOSES_ORACLE")
        if scored.get("pass") is not True:
            errors.append(f"{rid}:EVALUATOR_SMOKE_FAILED")
        smoke.append({"route_id":rid,"oracle_candidate_pass":scored.get("pass") is True})

    anti=manifest.get("anti_weakening") or []
    required_anti={
        "SCOPE_INSTANCE_PASS_DOES_NOT_CLAIM_REPRODUCTION_OF_A_DELETED_PRIVATE_BENCHMARK_SCORE",
        "UNEXERCISED_FAMILY_LEAVES_RECEIVE_ZERO_CREDIT",
    }
    if not required_anti.issubset(set(anti)):
        errors.append("ANTI_WEAKENING_GUARDS_MISSING")
    pre=manifest.get("prewave_state") or {}
    if pre.get("terminal_results_observed") is not False:
        errors.append("TERMINAL_RESULTS_ALREADY_OBSERVED")
    if pre.get("execution_authority") is not False:
        errors.append("SCOPE_MANIFEST_WRONGLY_GRANTS_EXECUTION_AUTHORITY")

    return {
        "schema":"PROJECT_BRAIN_TERMINAL_DIRECT_PROOF_SCOPE_INSTANCE_VALIDATION_V1",
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "errors":errors,
        "routes":smoke,
        "terminal_case_content_read":False,
        "fresh_terminal_evidence_consumed":0,
        "incremental_spend_usd":0,
    }

def main()->int:
    data=json.loads(MANIFEST_PATH.read_text())
    out=validate(data)
    print(json.dumps(out,sort_keys=True,indent=2))
    return 0 if out["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
