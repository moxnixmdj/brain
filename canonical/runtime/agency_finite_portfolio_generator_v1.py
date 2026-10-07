from __future__ import annotations
import hashlib
import json
from typing import Any

SCHEMA="PROJECT_BRAIN_AGENCY_FINITE_PORTFOLIO_GENERATOR_V1"
DIMENSIONS=(
 "multi-step planning with at least three distinct tool/action types",
 "state change after actions requiring replanning",
 "long-horizon state retention",
 "tool failure/recovery",
 "subtask dependency and fan-in",
 "minimal-oversight completion",
)
MECHANISMS={
 DIMENSIONS[0]:"STATEFUL_AGENCY_THREE_ACTION_UNIVERSAL_CELL",
 DIMENSIONS[1]:"DELEGATION_CUMULATIVE_RECEIPT_REPLAN_UNIVERSAL_CELL",
 DIMENSIONS[2]:"STATEFUL_AGENCY_CHECKPOINT_RELAUNCH_UNIVERSAL_CELL",
 DIMENSIONS[3]:"RECOVERY_CEILING_PLUS_DELEGATION_RECEIPT_REPLAN",
 DIMENSIONS[4]:"DELEGATION_DEPENDENCY_FANIN_UNIVERSAL_CELL",
 DIMENSIONS[5]:"DELEGATION_EXACT_SOLVE_PLUS_STATEFUL_TERMINAL_COMPLETION",
}
RECEIPTS={
 DIMENSIONS[1]:"STEP_UNAVAILABLE",
 DIMENSIONS[3]:"WORKER_UNAVAILABLE",
}

def _sha(value:Any)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def generate(beacon:str)->dict[str,Any]:
 if not isinstance(beacon,str) or not beacon:
  raise ValueError("BEACON")
 cases=[]
 for ordinal,dimension in enumerate(DIMENSIONS):
  seed=hashlib.sha256(f"{beacon}|agency-finite-v1|{ordinal}|{dimension}".encode()).hexdigest()
  payload={
   "schema":"PROJECT_BRAIN_AGENCY_FINITE_EXPLICIT_CONTRACT_CASE_V1",
   "ordinal":ordinal,
   "dimension":dimension,
   "mechanism":MECHANISMS[dimension],
   "seed_sha256":seed,
   "receipt_kind":RECEIPTS.get(dimension),
   "explicit_contract":True,
   "human_intervention_after_declared_input":False,
  }
  initial={
   "declared_inputs_frozen":True,
   "finite_explicit_contract":True,
   "supported_receipt_only":True,
   "case_seed_sha256":seed,
  }
  cases.append({
   "case_id":f"AGENCY-FINITE-V1-{ordinal+1:02d}",
   "dimension":dimension,
   "payload":payload,
   "payload_sha256":_sha(payload),
   "initial_state":initial,
   "initial_state_sha256":_sha(initial),
  })
 manifest_rows=[{
  "case_id":c["case_id"],
  "dimension":c["dimension"],
  "payload_sha256":c["payload_sha256"],
  "initial_state_sha256":c["initial_state_sha256"],
 } for c in cases]
 return {
  "schema":SCHEMA,
  "beacon":beacon,
  "case_count":len(cases),
  "cases":cases,
  "manifest_sha256":_sha(manifest_rows),
  "dimension_cover_complete":set(c["dimension"] for c in cases)==set(DIMENSIONS),
  "result_blind":True,
  "adaptive_case_selection":False,
 }
