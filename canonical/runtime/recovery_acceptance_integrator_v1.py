"""Fail-closed Recovery Opus-5.5 acceptance integrator candidate."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_RECOVERY_ACCEPTANCE_INTEGRATOR_V1"
REG="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVIDENCE="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
CLOSURE="canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
AUTHORITY="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
RECEIPT="canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"
EXPECTED={
 REG:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 EVIDENCE:"7885a827b1483bfb38315c1f492848f7e4680285",
 CLOSURE:"85398c768825cd4701e9e574e37a0502079bcbb9",
 AUTHORITY:"17fdb700650d0548765fdb1dee579407777eb4cf",
 RECEIPT:"981c8ac9b66ee7fccf5b531525849e29df9be483",
}
RECOVERY={"RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR","RECOVERY_TERMINAL_NONINFERIOR","RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES"}
CURRENT_CLOSED={"EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY","SUBAGENT_DELEGATION_AND_COORDINATION"}
FAMILY="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"

def blob(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(path:str)->dict[str,Any]:
    obj=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError(path+":NOT_OBJECT")
    return obj

def evaluate()->dict[str,Any]:
    drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
    if drift:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","pass":False,"errors":["SOURCE_BLOB_DRIFT"],"drift":drift,"promotion_eligible":False,"promotion_authority":False}
    reg,evidence,closure,authority,receipt=map(load,(REG,EVIDENCE,CLOSURE,AUTHORITY,RECEIPT))
    errors=[]
    def req(cond:bool,code:str):
        if not cond: errors.append(code)

    rv=receipt.get("verified") or {}
    req(str(receipt.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"RECOVERY_RECEIPT_NOT_INDEPENDENT_PASS")
    req(receipt.get("family")==FAMILY,"RECOVERY_RECEIPT_FAMILY")
    req(set(rv.get("predicates") or [])==RECOVERY,"RECOVERY_RECEIPT_PREDICATE_SET")
    req(rv.get("scope_complete") is True,"RECOVERY_SCOPE_NOT_COMPLETE")
    req(rv.get("objective_ceiling_or_floor") is True,"RECOVERY_OBJECTIVE_BOUND_NOT_PROVED")
    req(rv.get("historical_relation_observed_bound_used_as_proof") is False,"HISTORICAL_BOUND_REUSE")
    req(rv.get("historical_narrow_terminal_run_used_as_proof") is False,"OLD_NARROW_RUN_REUSE")
    req(rv.get("quarantined_public_recovery_run_used_as_proof") is False,"QUARANTINED_RUN_REUSE")
    req(rv.get("proposed_atomic_acceptance_delta")==3,"RECEIPT_ATOMIC_DELTA")
    req(rv.get("proposed_family_acceptance_delta")==1,"RECEIPT_FAMILY_DELTA")
    req(receipt.get("new_reality_units_consumed")==0,"RECOVERY_RECEIPT_REALITY_NONZERO")
    req(receipt.get("terminal_results_replayed")==0,"RECOVERY_RECEIPT_REPLAY")

    rows=reg.get("predicates") or []
    recovery_rows=[x for x in rows if isinstance(x,dict) and x.get("family")==FAMILY]
    req({x.get("id") for x in recovery_rows}==RECOVERY,"REGISTRY_RECOVERY_PREDICATE_SET")
    req(len(rows)==38,"REGISTRY_TOTAL_NOT_38")

    claims=evidence.get("claims") or []
    state={x.get("predicate_id"):x.get("state") for x in claims if isinstance(x,dict)}
    for pid in RECOVERY:
        req(state.get(pid) not in {"PROVED","REFUTED"},"RECOVERY_ALREADY_TERMINAL:"+pid)
    sat=evidence.get("saturation") or {}
    req(sat.get("proved_predicate_count")==8,"CURRENT_PROVED_NOT_8")
    req(sat.get("unresolved_predicate_count")==30,"CURRENT_UNRESOLVED_NOT_30")

    summary=closure.get("opus55_acceptance_summary") or {}
    req(summary.get("calibrated_family_count")==3,"CURRENT_FAMILY_COUNT_NOT_3")
    req(summary.get("pending_family_count")==16,"CURRENT_OPEN_FAMILY_COUNT_NOT_16")
    req(set(summary.get("calibrated_families") or [])==CURRENT_CLOSED,"CURRENT_CLOSED_SET_DRIFT")
    req(FAMILY in set(summary.get("pending_families") or []),"RECOVERY_NOT_CURRENTLY_PENDING")
    atomic=summary.get("atomic_predicates") or {}
    req(atomic.get("proved")==8 and atomic.get("unresolved")==30 and atomic.get("total")==38,"CLOSURE_ATOMIC_COUNTS_DRIFT")

    truth=authority.get("truth") or {}
    req(truth.get("opus55_acceptance")=="3/19_PASS__16/19_OPEN","AUTHORITY_ACCEPTANCE_NOT_3_16")
    af=authority.get("atomic_acceptance_frontier") or {}
    req(af.get("proved")==8 and af.get("unresolved")==30 and af.get("total")==38,"AUTHORITY_ATOMIC_COUNTS_DRIFT")

    ok=not errors
    proposed=[
      {"predicate_id":"RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR","state":"PROVED","proof_kind":"SCOPE_COMPLETE_STRONGER_PROOF_AT_OBJECTIVE_CEILING","source_path":RECEIPT,"source_sha":EXPECTED[RECEIPT],"independent_or_objective":True,"scope_complete":True,"brain_value":1,"objective_ceiling_value":1},
      {"predicate_id":"RECOVERY_TERMINAL_NONINFERIOR","state":"PROVED","proof_kind":"SCOPE_COMPLETE_STRONGER_PROOF_AT_OBJECTIVE_CEILING","source_path":RECEIPT,"source_sha":EXPECTED[RECEIPT],"independent_or_objective":True,"scope_complete":True,"brain_value":1,"objective_ceiling_value":1},
      {"predicate_id":"RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES","state":"PROVED","proof_kind":"SCOPE_COMPLETE_STRONGER_PROOF_AT_OBJECTIVE_FLOOR","source_path":RECEIPT,"source_sha":EXPECTED[RECEIPT],"independent_or_objective":True,"scope_complete":True,"brain_value":0,"objective_floor_value":0},
    ] if ok else []
    return {
      "schema":SCHEMA,
      "status":"PASS__RECOVERY_ONLY_ACCEPTANCE_DELTA_8_TO_11_ATOMIC__3_TO_4_FAMILIES__ZERO_REALITY" if ok else "FAIL_CLOSED",
      "pass":ok,"errors":sorted(set(errors)),
      "before":{"proved_atomic":8,"unresolved_atomic":30,"accepted_families":3,"open_families":16},
      "after":{"proved_atomic":11 if ok else 8,"unresolved_atomic":27 if ok else 30,"accepted_families":4 if ok else 3,"open_families":15 if ok else 16},
      "newly_proved_predicates":sorted(RECOVERY) if ok else [],
      "newly_closed_families":[FAMILY] if ok else [],
      "preserved_closed_families":sorted(CURRENT_CLOSED) if ok else [],
      "proposed_claims":proposed,
      "promotion_eligible":ok,"promotion_authority":False,"execution_authority":False,
      "new_reality_units_consumed":0,"terminal_results_replayed":0,"incremental_spend_usd":0,
      "hard_nonclaims":["THIS_REDUCER_DOES_NOT_MUTATE_CANONICAL_ACCEPTANCE_STATE","NO_OTHER_PREDICATE_OR_FAMILY_RECEIVES_CREDIT","SEPARATE_INDEPENDENT_EXACT_BYTE_VERIFICATION_REQUIRED_BEFORE_ATOMIC_INTEGRATION"]
    }

def main()->int:
    out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out.get("pass") is True else 1
if __name__=="__main__": raise SystemExit(main())
