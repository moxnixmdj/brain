"""Fail-closed freeze verifier for the P1 shared one-batch experiment."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
from canonical.runtime.p1_shared_failure_semantics_batch_v1 import (
    SURFACES,DIFFICULTIES,execute_batch,normalize_native_case,CONTRACT
)
from canonical.runtime import contract_native_proof_suites as native

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/"canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json"
SCHEMA="PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_VERDICT_V1"

def _blob(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def evaluate(data:dict[str,Any]|None=None)->dict[str,Any]:
    d=data if data is not None else json.loads(SPEC.read_text())
    errors=[]
    if d.get("behavior_id")!=CONTRACT: errors.append("BEHAVIOR_DRIFT")
    if set(d.get("direct_surfaces") or [])!=set(SURFACES): errors.append("SURFACE_SET_DRIFT")
    if d.get("difficulty_schedule")!=list(DIFFICULTIES): errors.append("DIFFICULTY_SCHEDULE_DRIFT")
    if d.get("execution_authority") is not False: errors.append("PREMATURE_EXECUTION_AUTHORITY")
    if d.get("fresh_reality_units_consumed_so_far")!=0: errors.append("REALITY_ALREADY_CONSUMED")
    if d.get("incremental_spend_usd")!=0: errors.append("NONZERO_SPEND")

    pins=d.get("exact_source_blobs")
    if not isinstance(pins,dict): errors.append("SOURCE_PINS_MISSING"); pins={}
    for rel,want in pins.items():
        try: got=_blob(rel)
        except Exception: errors.append("PIN_PATH_MISSING:"+str(rel)); continue
        if got!=want: errors.append("PIN_DRIFT:"+str(rel))

    beacon=d.get("post_freeze_beacon")
    if not isinstance(beacon,dict):
        errors.append("BEACON_POLICY_MISSING"); beacon={}
    expected={
      "beacon_id":"quicknet",
      "chain_hash":"52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971",
      "genesis_time":1692803367,
      "period_seconds":3,
      "anchor":"CANONICAL_BRAIN_MAIN_MERGE_COMMIT_OF_THIS_FREEZE",
      "round_rule":"FLOOR((ANCHOR_COMMITTER_UNIX-GENESIS_TIME)/PERIOD_SECONDS)+2",
    }
    for k,v in expected.items():
        if beacon.get(k)!=v: errors.append("BEACON_POLICY_DRIFT:"+k)
    for forbidden in ("round","randomness","signature","result","seeds"):
        if forbidden in beacon: errors.append("PREFREEZE_BEACON_RESULT_PRESENT:"+forbidden)

    # Structural proof that the normalizer binds both semantics before V7 execution.
    sample=native.generate_case(CONTRACT,710031,3)
    for surface in SURFACES:
        typed=normalize_native_case(sample,surface)
        if "_oracle" in typed: errors.append("ORACLE_LEAK:"+surface)
        failed=[c for r in typed["task"]["trajectory"] for c in r["checks"] if c["pass"] is False]
        semantics={c["failure_semantics"] for c in failed}
        if semantics!={"DIRECT_CONTRACT","DERIVED_UPSTREAM"}:
            errors.append("SEMANTICS_NOT_BOTH_REPRESENTED:"+surface)
        if any(not c["evidence"] for c in failed):
            errors.append("FAILED_CHECK_WITHOUT_RECEIPT:"+surface)

    # Pre-freeze fixed-value execution tests machinery without consuming the future beacon.
    fixed="00"*32
    batch=execute_batch(fixed,1)
    if batch.get("pass") is not True or batch.get("case_count")!=15:
        errors.append("FROZEN_MACHINERY_SELF_TEST_FAIL")
    if set(batch.get("surfaces_covered") or [])!=set(SURFACES):
        errors.append("FROZEN_MACHINERY_SURFACE_COVERAGE_FAIL")
    if batch.get("fresh_reality_units_consumed")!=1:
        errors.append("BATCH_UNIT_ACCOUNTING_DRIFT")

    errors=sorted(set(errors))
    return {
      "schema":SCHEMA,
      "status":"PASS__P1_ONE_BATCH_FREEZE_SOUND__RESULTS_UNOBSERVED__EXECUTION_STILL_UNAUTHORIZED" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "surface_count":len(SURFACES),
      "case_count_if_executed":len(SURFACES)*len(DIFFICULTIES),
      "future_reality_units_if_executed":1,
      "terminal_v3_replay_required":False,
      "fresh_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
