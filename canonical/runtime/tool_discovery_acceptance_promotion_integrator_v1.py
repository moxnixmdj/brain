"""Fail-closed Tool Discovery acceptance promotion integrator V1."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_INTEGRATOR_V1"
FAMILY="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
TARGET="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
REG="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVIDENCE="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
CLOSURE="canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
AUTHORITY="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
PROTOCOLS="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
OWNERSHIP="canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
RECEIPT="canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
EXPECTED={
 REG:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 EVIDENCE:"0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
 CLOSURE:"dc629d69b1bbf1ebf25e99c474588ad0aa76fb92",
 AUTHORITY:"f47a69253e7eb75e139b445b736d3d18b33be622",
 PROTOCOLS:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 OWNERSHIP:"3cbbcd1ddabde7dbf4c3f4d118bdb9d78d0c8605",
 RECEIPT:"913d171b3c855000d322e183b142b3200eeaf0a9",
}
CLOSED_BEFORE={"EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY","SUBAGENT_DELEGATION_AND_COORDINATION","SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"}
OTHER_TOOL_ATOMS={"TOOL_LEARNING_SECOND_TASK_TRANSFER","TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION"}

def blob(p):
 d=(ROOT/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def evaluate():
 drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
 if drift: return {"schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","pass":False,"errors":["SOURCE_BLOB_DRIFT"],"drift":drift,"promotion_eligible":False,"promotion_authority":False}
 reg,evidence,closure,auth,protocols,ownership,receipt=map(load,(REG,EVIDENCE,CLOSURE,AUTHORITY,PROTOCOLS,OWNERSHIP,RECEIPT))
 errors=[]
 def req(x,c):
  if not x: errors.append(c)
 vr=receipt.get("verified") or {}
 req(receipt.get("independent_runner",{}).get("conclusion")=="success","REDUCTION_NOT_INDEPENDENT_PASS")
 req(vr.get("target_predicate")==TARGET,"REDUCTION_TARGET")
 req(vr.get("candidate_target_state")=="PROVED","REDUCTION_NOT_PROVED")
 req(vr.get("proof_kind")=="ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS","REDUCTION_PROOF_KIND")
 req(vr.get("scope_complete") is True and vr.get("objective_ceiling") is True,"REDUCTION_SCOPE_OR_CEILING")
 req(vr.get("brain_value")==1 and vr.get("objective_ceiling_value")==1,"REDUCTION_BOUND")
 req(vr.get("tool_discovery_family_candidate_state")=="PASS_3_OF_3","REDUCTION_FAMILY_STATE")
 req(vr.get("uses_empirical_generalization") is False and vr.get("source_180_of_180_load_bearing") is False,"EMPIRICAL_SCOPE_LEAK")
 rows=reg.get("predicates") or []
 req(len(rows)==38,"REGISTRY_TOTAL")
 req({x.get("id") for x in rows if x.get("family")==FAMILY}==OTHER_TOOL_ATOMS|{TARGET},"REGISTRY_TOOL_SET")
 claims={x.get("predicate_id"):x for x in evidence.get("claims",[]) if isinstance(x,dict)}
 req((claims.get(TARGET) or {}).get("state")=="EXTERNAL_BLOCKED","TARGET_NOT_OPEN")
 req((claims.get(TARGET) or {}).get("blocker")=="ABSOLUTE_SCOPE_COMPLETENESS_MISSING","TARGET_BLOCKER_DRIFT")
 for pid in OTHER_TOOL_ATOMS: req((claims.get(pid) or {}).get("state")=="PROVED","OTHER_ATOM_NOT_PROVED:"+pid)
 sat=evidence.get("saturation") or {}
 req(sat.get("proved_predicate_count")==11 and sat.get("unresolved_predicate_count")==27,"EVIDENCE_COUNTS")
 summ=closure.get("opus55_acceptance_summary") or {}
 req(summ.get("calibrated_family_count")==4 and summ.get("pending_family_count")==15,"CLOSURE_COUNTS")
 req(set(summ.get("calibrated_families") or [])==CLOSED_BEFORE,"CLOSED_SET")
 req(FAMILY in set(summ.get("pending_families") or []),"TOOL_FAMILY_NOT_PENDING")
 req((summ.get("atomic_predicates") or {}).get("proved")==11 and (summ.get("atomic_predicates") or {}).get("unresolved")==27,"CLOSURE_ATOMIC")
 req((auth.get("truth") or {}).get("opus55_acceptance")=="4/19_PASS__15/19_OPEN","AUTHORITY_COUNTS")
 af=auth.get("atomic_acceptance_frontier") or {}
 req(af.get("proved")==11 and af.get("unresolved")==27 and af.get("total")==38,"AUTHORITY_ATOMIC")
 prow=next((x for x in protocols.get("protocols",[]) if x.get("family")==FAMILY),{})
 req(prow.get("status")=="DEFINED_RESULT_OPEN","PROTOCOL_NOT_OPEN")
 orow=next((x for x in ownership.get("rows",[]) if x.get("family")==FAMILY),{})
 req(orow.get("status")=="OWNED_COMPONENT_NOT_FULL_FAMILY","OWNERSHIP_STATE_DRIFT")
 req(orow.get("postwave_opus55_acceptance_status")=="DEFINED_RESULT_OPEN__REOPENED_ABSOLUTE_SCOPE_COMPLETENESS_MISSING","OWNERSHIP_ACCEPTANCE_MIRROR_DRIFT")
 ok=not errors
 return {
  "schema":SCHEMA,
  "status":"PASS__TOOL_DISCOVERY_ONLY_ACCEPTANCE_DELTA_11_TO_12_ATOMIC__4_TO_5_FAMILIES__ZERO_REALITY" if ok else "FAIL_CLOSED",
  "pass":ok,"errors":sorted(set(errors)),
  "before":{"proved_atomic":11,"unresolved_atomic":27,"accepted_families":4,"open_families":15},
  "after":{"proved_atomic":12 if ok else 11,"unresolved_atomic":26 if ok else 27,"accepted_families":5 if ok else 4,"open_families":14 if ok else 15},
  "newly_proved_predicates":[TARGET] if ok else [],
  "newly_closed_families":[FAMILY] if ok else [],
  "preserved_closed_families":sorted(CLOSED_BEFORE) if ok else [],
  "proposed_claim":{"predicate_id":TARGET,"state":"PROVED","proof_kind":"ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS","source_path":RECEIPT,"source_sha":EXPECTED[RECEIPT],"independent_or_objective":True,"scope_complete":True,"objective_ceiling":True,"brain_value":1,"objective_ceiling_value":1} if ok else None,
  "ownership_credit_delta":0,"promotion_eligible":ok,"promotion_authority":False,"execution_authority":False,
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "hard_nonclaims":["THIS_REDUCER_DOES_NOT_MUTATE_CANONICAL_STATE","NO_TOOL_DISCOVERY_WHOLE_FAMILY_OWNERSHIP_PROMOTION","NO_OTHER_PREDICATE_OR_FAMILY_CREDIT","NO_FRESH_REALITY_OR_TERMINAL_REPLAY","SEPARATE_INDEPENDENT_EXACT_BYTE_VERIFICATION_REQUIRED_BEFORE_ATOMIC_INTEGRATION"]
 }
if __name__=="__main__": print(json.dumps(evaluate(),indent=2,sort_keys=True))
