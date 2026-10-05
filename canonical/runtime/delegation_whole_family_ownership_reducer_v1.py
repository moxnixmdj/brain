"""Fail-closed delegation whole-family ownership reducer V1."""
from __future__ import annotations
import ast, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_DELEGATION_WHOLE_FAMILY_OWNERSHIP_REDUCER_V1"
FILES={
"candidate":"canonical/governance/DELEGATION_WHOLE_FAMILY_OWNERSHIP_CANDIDATE_V1.json",
"runtime":"canonical/runtime/delegation_whole_scope_candidate_v2.py",
"scope":"canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
"acceptance":"canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
"whole":"canonical/verification/DELEGATION_WHOLE_DIMENSION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
"variety":"canonical/verification/DELEGATION_STRUCTURAL_VARIETY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
"reassign":"canonical/verification/DYNAMIC_DELEGATION_REASSIGNMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
"protocols":"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
}
EXPECTED={
FILES["runtime"]:"f1a93ee66d90093de61dc17c6ebf2e24073df522",
FILES["scope"]:"955ac8f4bd0db2527bfbb465fc8252df6d916156",
FILES["acceptance"]:"d04f2a8c5594d261158835db1cae3822411b6b23",
FILES["whole"]:"ae24117149e6acdcc8c4db977f8460b89480f0b2",
FILES["variety"]:"c99c1fba7f006e065937b4a272d346efbbe2cb49",
FILES["reassign"]:"b05d5dd02c741bad2dcabc05b82d94f36ae413ea",
}
ALLOWED_IMPORT_ROOTS={"__future__","collections","heapq","itertools","math","typing"}

def blob(rel):
 d=(ROOT/rel).read_bytes(); return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))
def imports(rel):
 t=ast.parse((ROOT/rel).read_text(encoding="utf-8")); out=set()
 for n in ast.walk(t):
  if isinstance(n,ast.Import):
   out.update(x.name.split(".")[0] for x in n.names)
  elif isinstance(n,ast.ImportFrom) and n.module:
   out.add(n.module.split(".")[0])
 return out

def evaluate():
 errors=[]
 for rel,want in EXPECTED.items():
  got=blob(rel)
  if got!=want: errors.append(f"BLOB_DRIFT:{rel}:{got}:{want}")
 cand=load(FILES["candidate"])
 if cand.get("family")!="SUBAGENT_DELEGATION_AND_COORDINATION": errors.append("FAMILY_MISMATCH")
 unexpected=imports(FILES["runtime"])-ALLOWED_IMPORT_ROOTS
 if unexpected: errors.append("NON_STDLIB_RUNTIME_IMPORTS:"+",".join(sorted(unexpected)))
 scope=load(FILES["scope"]); acc=load(FILES["acceptance"]); whole=load(FILES["whole"]); variety=load(FILES["variety"]); reassign=load(FILES["reassign"])
 if scope.get("public_runner",{}).get("conclusion")!="success" or "UNIVERSAL_SCOPE_PROVED_TRUE" not in scope.get("verified",[]): errors.append("UNIVERSAL_SCOPE_NOT_VERIFIED")
 vr=acc.get("verified_result") or {}
 if acc.get("public_runner",{}).get("conclusion")!="success" or "SUBAGENT_DELEGATION_AND_COORDINATION" not in vr.get("newly_closed_families",[]): errors.append("ACCEPTANCE_NOT_INDEPENDENTLY_CLOSED")
 required_whole={"MINIMUM_COST_REQUIRED_TASK_SET_AND_DEPENDENCY_GRAPH","MINIMUM_WAVE_CAPABILITY_AND_RESOURCE_FEASIBLE_SCHEDULING","EVIDENCE_OWNERSHIP_AND_TERMINAL_FANIN_COMPLETENESS","WORKER_UNAVAILABLE_REASSIGNMENT","STEP_UNAVAILABLE_REPARTITION","WORKER_CAPABILITY_LOSS_REASSIGNMENT","RESOURCE_CAPACITY_CHANGE_RESCHEDULING","NO_REPLAY_OF_COMPLETED_WORK"}
 if not required_whole.issubset(set(whole.get("verified") or [])): errors.append("WHOLE_DIMENSION_GAP")
 if "FIVE_STRUCTURALLY_DISTINCT_TOPOLOGY_CLASSES_CONFIRMED" not in (variety.get("verified") or []): errors.append("STRUCTURAL_VARIETY_GAP")
 if not {"WORKER_UNAVAILABLE_RECEIPT_CAUSES_REASSIGNMENT","STEP_UNAVAILABLE_RECEIPT_CAUSES_REPARTITION_TO_BACKUP_STEP","WORKER_CAPABILITY_LOSS_CAUSES_COMPATIBLE_REASSIGNMENT"}.issubset(set(reassign.get("verified") or [])): errors.append("REASSIGNMENT_GAP")
 protocols=load(FILES["protocols"])
 row=next(x for x in protocols["protocols"] if x["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
 if row.get("status")!="PASS": errors.append("FROZEN_PROTOCOL_NOT_PASS")
 if errors:
  return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":errors,"ownership_promotion_candidate":False,"ownership_credit_delta":0,"promotion_authority":False}
 return {"schema":SCHEMA,"status":"PASS__DELEGATION_WHOLE_FAMILY_OWNERSHIP_PROMOTION_CANDIDATE__SEPARATE_ATOMIC_PROMOTION_REQUIRED","pass":True,"errors":[],"family":"SUBAGENT_DELEGATION_AND_COORDINATION","brain_owned_operative_runtime":FILES["runtime"],"external_model_or_api_required":False,"donor_runtime_required":False,"frozen_scope_complete":True,"acceptance_equal_or_better":True,"ownership_promotion_candidate":True,"ownership_credit_delta":0,"capability_credit_delta":0,"family_credit_delta":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,"promotion_authority":False}
if __name__=="__main__": print(json.dumps(evaluate(),indent=2,sort_keys=True))
