"""Frozen one-batch P1 failure-semantics transport machinery V1.

This module does NOT fetch a beacon and does NOT authorize execution.  It is the
frozen deterministic transform that will be fed one post-freeze drand value.

Source reality:
  canonical/runtime/contract_native_proof_suites.py
Candidate:
  canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py

The contract-native P1 generator already exposes an execution trajectory with a
single injected fault plus downstream degraded symptoms.  The normalizer binds
that existing source semantics before candidate execution:
  FAULT_INJECTED + failed invariant   -> DIRECT_CONTRACT
  DOWNSTREAM_DEGRADED + failed invariant -> DERIVED_UPSTREAM
No _oracle field is exposed to V7.
"""
from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping

from canonical.runtime import contract_native_proof_suites as native
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as v7

SCHEMA="PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_V1"
CONTRACT="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
SURFACES=(
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
)
DIFFICULTIES=(1,2,3,4,5)


class BatchError(ValueError):
    pass


def derive_seed(randomness_hex:str, surface:str, difficulty:int)->int:
    if not isinstance(randomness_hex,str) or len(randomness_hex)!=64:
        raise BatchError("RANDOMNESS_HEX_INVALID")
    try:
        raw=bytes.fromhex(randomness_hex)
    except ValueError as exc:
        raise BatchError("RANDOMNESS_HEX_INVALID") from exc
    if surface not in SURFACES or difficulty not in DIFFICULTIES:
        raise BatchError("SURFACE_OR_DIFFICULTY_INVALID")
    h=hashlib.sha256()
    h.update(b"PROJECT_BRAIN_P1_SHARED_BATCH_V1\0")
    h.update(raw)
    h.update(b"\0")
    h.update(surface.encode("utf-8"))
    h.update(b"\0")
    h.update(str(difficulty).encode("ascii"))
    return int.from_bytes(h.digest()[:8],"big",signed=False)


def normalize_native_case(case:Mapping[str,Any], surface:str)->dict[str,Any]:
    if surface not in SURFACES:
        raise BatchError("SURFACE_INVALID")
    if case.get("contract")!=CONTRACT:
        raise BatchError("CONTRACT_INVALID")
    task=case.get("task")
    if not isinstance(task,Mapping):
        raise BatchError("TASK_INVALID")
    source_rows=task.get("trajectory")
    if not isinstance(source_rows,list) or not source_rows:
        raise BatchError("SOURCE_TRAJECTORY_INVALID")

    rows=[]
    prior_action=None
    prior_resource=None
    direct_count=0
    derived_count=0
    for pos,src in enumerate(source_rows):
        if not isinstance(src,Mapping):
            raise BatchError("SOURCE_ROW_INVALID")
        step=src.get("step")
        action=src.get("action")
        state=src.get("state")
        invariant=src.get("invariant_pass")
        symptom=src.get("terminal_symptom")
        if step!=pos or action!=f"A{pos}" or type(invariant) is not bool or type(symptom) is not bool:
            raise BatchError("SOURCE_ROW_SHAPE_DRIFT")

        out_resource=f"{surface}::STATE::{pos}"
        checks=[]
        if invariant:
            if state!="OK" or symptom:
                raise BatchError("PASSING_SOURCE_STATE_DRIFT")
            checks.append({
                "kind":"INVARIANT",
                "id":f"{action}:INVARIANT",
                "pass":True,
                "evidence":[],
                "failure_semantics":"DIRECT_CONTRACT",
            })
        else:
            if state=="FAULT_INJECTED" and symptom is False:
                semantics="DIRECT_CONTRACT"; direct_count+=1
            elif state=="DOWNSTREAM_DEGRADED" and symptom is True:
                semantics="DERIVED_UPSTREAM"; derived_count+=1
            else:
                raise BatchError("FAILED_SOURCE_STATE_NOT_IDENTIFIABLE")
            evidence=[
                f"surface:{surface}",
                f"source_seed:{case.get('seed')}",
                f"source_step:{pos}",
                f"source_state:{state}",
                "source_invariant:FAIL",
            ]
            checks.append({
                "kind":"INVARIANT",
                "id":f"{action}:INVARIANT",
                "pass":False,
                "evidence":evidence,
                "failure_semantics":semantics,
            })

        rows.append({
            "step":pos,
            "action_id":action,
            "domain":"CONTRACT_NATIVE_P1",
            "reads":[] if prior_resource is None else [prior_resource],
            "writes":[out_resource],
            "depends_on":[] if prior_action is None else [prior_action],
            "dependency_composition":"SEQUENTIAL",
            "checks":checks,
        })
        prior_action=action
        prior_resource=out_resource

    if direct_count!=1 or derived_count<1:
        raise BatchError("SOURCE_SEMANTICS_CARDINALITY_DRIFT")

    return {
        "schema":SCHEMA,
        "behavior_id":CONTRACT,
        "surface_binding":surface,
        "source_schema":case.get("schema"),
        "source_seed":case.get("seed"),
        "task":{
            "domain":"CONTRACT_NATIVE_P1",
            "trajectory":rows,
            "terminal_failed_resources":[prior_resource],
            "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE",
        },
    }


def score_typed_result(source_case:Mapping[str,Any], typed:Mapping[str,Any],
                       candidate:Mapping[str,Any])->dict[str,Any]:
    oracle=source_case.get("_oracle")
    if not isinstance(oracle,Mapping):
        return {"pass":False,"reason":"SOURCE_ORACLE_MISSING"}
    cause=oracle.get("cause_step")
    if not isinstance(cause,int):
        return {"pass":False,"reason":"SOURCE_CAUSE_INVALID"}
    aid=f"A{cause}"
    expected_repair=f"restore:{aid}:INVARIANT"

    reasons=[]
    if candidate.get("status")!="IDENTIFIED":
        reasons.append("V7_STATUS_NOT_IDENTIFIED")
    if candidate.get("cause_action_id")!=aid or candidate.get("cause_action_ids")!=[aid]:
        reasons.append("V7_CAUSE_MISMATCH")
    if candidate.get("critical_action_id")!=aid:
        reasons.append("V7_CRITICAL_ACTION_MISMATCH")
    if candidate.get("repair_targets")!=[expected_repair]:
        reasons.append("V7_REPAIR_TARGET_MISMATCH")
    receipts=candidate.get("supporting_receipts")
    if not isinstance(receipts,list) or not receipts:
        reasons.append("V7_SUPPORTING_RECEIPTS_MISSING")
    else:
        direct_token=f"source_step:{cause}"
        if direct_token not in receipts:
            reasons.append("V7_DIRECT_SOURCE_RECEIPT_MISSING")

    native_candidate={
        "cause_step":cause if candidate.get("cause_action_id")==aid else None,
        "repair_id":f"repair_{cause}" if candidate.get("repair_targets")==[expected_repair] else None,
        "evidence_steps":[cause] if isinstance(receipts,list) and f"source_step:{cause}" in receipts else [],
    }
    native_verdict=native.score_case(source_case,native_candidate)
    if native_verdict.get("pass") is not True or native_verdict.get("rescue_pass") is not True:
        reasons.append("CONTRACT_NATIVE_RESCUE_ORACLE_FAIL")

    return {
        "pass":not reasons,
        "reasons":reasons,
        "surface_binding":typed.get("surface_binding"),
        "source_seed":source_case.get("seed"),
        "cause_step":cause,
        "candidate_status":candidate.get("status"),
        "native_rescue_pass":native_verdict.get("rescue_pass") is True,
    }


def execute_case(surface:str, seed:int, difficulty:int)->dict[str,Any]:
    source=native.generate_case(CONTRACT,seed,difficulty)
    typed=normalize_native_case(source,surface)
    # copy ensures V7 cannot mutate source evidence used by the independent scorer.
    candidate=v7.solve(copy.deepcopy(typed))
    verdict=score_typed_result(source,typed,candidate)
    return {
        "surface":surface,
        "difficulty":difficulty,
        "seed":seed,
        "pass":verdict["pass"],
        "verdict":verdict,
    }


def execute_batch(randomness_hex:str, beacon_round:int)->dict[str,Any]:
    if not isinstance(beacon_round,int) or isinstance(beacon_round,bool) or beacon_round<1:
        raise BatchError("BEACON_ROUND_INVALID")
    rows=[]
    for surface in SURFACES:
        for difficulty in DIFFICULTIES:
            seed=derive_seed(randomness_hex,surface,difficulty)
            rows.append(execute_case(surface,seed,difficulty))
    all_pass=all(row["pass"] for row in rows)
    covered={row["surface"] for row in rows if row["pass"]}
    return {
        "schema":SCHEMA,
        "status":"PASS__ONE_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH" if all_pass else "FAIL_CLOSED__P1_SHARED_BATCH_CASE_FAILURE",
        "pass":all_pass,
        "beacon_round":beacon_round,
        "randomness_sha256":hashlib.sha256(bytes.fromhex(randomness_hex)).hexdigest(),
        "case_count":len(rows),
        "surfaces_covered":sorted(covered),
        "all_three_surfaces_covered":covered==set(SURFACES),
        "difficulty_schedule":list(DIFFICULTIES),
        "results":rows,
        "fresh_reality_units_consumed":1,
        "terminal_v3_results_replayed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
