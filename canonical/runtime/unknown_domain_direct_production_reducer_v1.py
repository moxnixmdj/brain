"""Fail-closed reducer for the frozen Unknown-Domain production result.

This reducer is frozen before the one-use production outcome. It consumes only
the persisted sanitized result and the precommitted acceptance conditions.
It grants no acceptance credit by itself.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_REDUCTION_V1"
TARGET="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
CLAIM="refs/heads/unknown-domain-direct-claims/76e8040db826990a90f5ab36b833c40af1ade15c89c579eeef2ca44bf1d0c7e9"
LEASE="76e8040db826990a90f5ab36b833c40af1ade15c89c579eeef2ca44bf1d0c7e9"
TRANSFER="CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN="CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"

def reduce_result(result: Mapping[str,Any]) -> dict[str,Any]:
    errors:list[str]=[]
    if not isinstance(result,Mapping):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":["RESULT_NOT_MAPPING"],"acceptance_credit_delta":0,"promotion_authority":False}
    exact={
      "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_V1",
      "status":"PRODUCTION_PASS",
      "target_predicate":TARGET,
      "authority_claim_id":CLAIM,
      "claim_create_http_status":201,
      "claim_uniqueness_source":"ATOMIC_CREATE_RESPONSE",
      "execution_lease_sha256":LEASE,
      "production_cases_generated":27,
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
      "incremental_spend_usd":0,
      "raw_hidden_records_persisted":False,
      "raw_evaluator_secret_persisted":False,
      "raw_beacon_persisted":False,
      "replay_allowed":False,
      "replacement_allowed":False,
      "promotion_authority":False,
      "separate_independent_reduction_required":True,
    }
    for key,val in exact.items():
        if result.get(key)!=val:
            errors.append(f"FIELD_MISMATCH:{key}")
    rows=result.get("case_results")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or len(rows)!=27:
        errors.append("CASE_RESULTS_COUNT_INVALID")
        rows=[]
    ids=[]
    leaves={TRANSFER:0,ABSTAIN:0}
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            errors.append(f"CASE_NOT_MAPPING:{i}")
            continue
        cid=str(row.get("case_id") or "")
        if not cid:
            errors.append(f"CASE_ID_MISSING:{i}")
        ids.append(cid)
        leaf=str(row.get("leaf_id") or "")
        if leaf not in leaves:
            errors.append(f"LEAF_INVALID:{i}")
        else:
            leaves[leaf]+=1
        probes=row.get("probe_count")
        if isinstance(probes,bool) or not isinstance(probes,int) or probes<0 or probes>2:
            errors.append(f"PROBE_COUNT_INVALID:{i}")
        sr=row.get("scorer_result")
        if not isinstance(sr,Mapping) or sr.get("pass") is not True:
            errors.append(f"SCORER_PASS_REQUIRED:{i}")
    if len(ids)!=len(set(ids)):
        errors.append("CASE_IDS_NOT_UNIQUE")
    if leaves!={TRANSFER:12,ABSTAIN:15}:
        errors.append("LEAF_COUNTS_INVALID")
    agg=result.get("aggregate")
    if not isinstance(agg,Mapping):
        errors.append("AGGREGATE_INVALID")
        agg={}
    expected_agg={
      "transfer_leaf_pass":True,
      "abstention_leaf_pass":True,
      "all_27_cases_pass":True,
      "case_count":27,
      "class_balance":{"IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5},
      "separate_independent_reduction_required":True,
    }
    for key,val in expected_agg.items():
        if agg.get(key)!=val:
            errors.append(f"AGGREGATE_MISMATCH:{key}")
    passed=not errors
    return {
      "schema":SCHEMA,
      "status":"PREDICATE_LOCAL_PROOF_CANDIDATE" if passed else "FAIL_CLOSED",
      "pass":passed,
      "target_predicate":TARGET,
      "errors":sorted(set(errors)),
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "capability_credit_delta":0,
      "ownership_credit_delta":0,
      "promotion_authority":False,
      "independent_reduction_receipt_required":True,
      "hard_nonclaim":"PASS_IS_ONLY_A_PREDICATE_LOCAL_PROOF_CANDIDATE_UNTIL_INDEPENDENT_REDUCTION_AND_SEPARATE_ACCEPTANCE_PROMOTION"
    }
