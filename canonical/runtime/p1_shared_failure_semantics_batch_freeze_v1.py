"""Fail-closed verifier for the P1 shared failure-semantics batch freeze V1."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
FREEZE=ROOT/"canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json"
EXPECTED_SURFACES={
 "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
EXPECTED_REQUIREMENTS={
 "P1_FAILURE_SEMANTICS_TRANSPORT_FRONTIERCODE",
 "P1_FAILURE_SEMANTICS_TRANSPORT_CURSORBENCH",
 "P1_FAILURE_SEMANTICS_TRANSPORT_RECOVERY_SCOPE_COMPOSITION",
}

def _blob(path:Path)->str:
 data=path.read_bytes()
 return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _sha256_json(v:Any)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def evaluate(freeze:dict[str,Any]|None=None)->dict[str,Any]:
 f=json.loads(FREEZE.read_text()) if freeze is None else freeze
 errors=[]
 exact=f.get("exact_inputs") or {}
 for row in exact.values():
  if not isinstance(row,dict): continue
  p=row.get("path"); want=row.get("git_blob_sha")
  if isinstance(p,str) and isinstance(want,str):
   path=ROOT/p
   if not path.exists(): errors.append("INPUT_MISSING:"+p)
   elif _blob(path)!=want: errors.append("INPUT_BLOB_DRIFT:"+p)

 if f.get("selected_observation")!="P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH":
  errors.append("WRONG_MINIMUM_OBSERVATION")
 basis=f.get("minimum_reality_basis") or {}
 if basis.get("minimum_new_reality_units")!=1:
  errors.append("MINIMUM_REALITY_NOT_ONE")

 slots=f.get("surface_slots") or []
 surfaces={x.get("surface_id") for x in slots if isinstance(x,dict)}
 reqs={x.get("requirement") for x in slots if isinstance(x,dict)}
 if surfaces!=EXPECTED_SURFACES: errors.append("SURFACE_SET_NOT_EXACT")
 if reqs!=EXPECTED_REQUIREMENTS: errors.append("REQUIREMENT_SET_NOT_EXACT")
 if len(slots)!=3: errors.append("SURFACE_SLOT_COUNT_NOT_THREE")

 gate=json.loads((ROOT/exact["direct_surface_transport_gate"]["path"]).read_text())
 if set(gate.get("direct_surfaces") or [])!=EXPECTED_SURFACES:
  errors.append("TRANSPORT_GATE_SURFACE_DRIFT")

 portfolios=json.loads((ROOT/exact["portfolio_binding_manifest"]["path"]).read_text())
 for row in slots:
  p=(portfolios.get("portfolios") or {}).get(row["portfolio"]) or {}
  surf=next((x for x in p.get("surfaces",[]) if x.get("id")==row["surface"]),None)
  if surf is None or "P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF" not in list(surf.get("proof_routes") or []):
   errors.append("SURFACE_NOT_FROZEN_P1_DIRECT_PROOF:"+row["surface_id"])

 cut=json.loads((ROOT/exact["minimum_reality_input"]["path"]).read_text())
 shared=next((x for x in cut.get("observations",[]) if x.get("id")=="P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH"),None)
 if shared is None or set(shared.get("covers") or [])!=EXPECTED_REQUIREMENTS or shared.get("cost")!=1:
  errors.append("MINIMUM_REALITY_CUT_BINDING_DRIFT")

 n=f.get("normalization_contract") or {}
 if n.get("failure_semantics_required_on_every_failed_check") is not True:
  errors.append("FAILURE_SEMANTICS_NOT_REQUIRED")
 if set(n.get("failure_semantics_allowed") or [])!={"DIRECT_CONTRACT","DERIVED_UPSTREAM"}:
  errors.append("FAILURE_SEMANTICS_DOMAIN_DRIFT")
 if n.get("missing_failure_semantics_for_failed_check")!="FAIL_CLOSED__NO_SCOPE_CREDIT":
  errors.append("MISSING_SEMANTICS_NOT_FAIL_CLOSED")
 if n.get("failed_check_evidence_rule")!="NONEMPTY_CAUSALLY_RELEVANT_SUPPORTING_RECEIPTS_REQUIRED":
  errors.append("CAUSAL_RECEIPT_RULE_DRIFT")

 normalizer=(ROOT/exact["normalizer"]["path"]).read_text()
 for token in ("FAILED_CHECK_FAILURE_SEMANTICS_MISSING","FAILED_CHECK_CAUSAL_RECEIPT_MISSING","DIRECT_CONTRACT","DERIVED_UPSTREAM"):
  if token not in normalizer: errors.append("NORMALIZER_MISSING_TOKEN:"+token)

 s=f.get("selection_contract") or {}
 if s.get("case_selection_before_beacon") is not False: errors.append("PREBEACON_SELECTION_ALLOWED")
 if s.get("adaptive_case_selection") is not False: errors.append("ADAPTIVE_SELECTION_ALLOWED")
 if s.get("case_replacement") is not False: errors.append("CASE_REPLACEMENT_ALLOWED")
 if s.get("terminal_v3_replay") is not False: errors.append("TERMINAL_V3_REPLAY_ALLOWED")
 if "UNKNOWN_AT_THIS_FREEZE" not in str(s.get("post_freeze_beacon")):
  errors.append("BEACON_PREKNOWN_OR_INVALID")

 source=f.get("source_pool_contract") or {}
 if source.get("case_content_read_before_freeze") is not False: errors.append("CASE_CONTENT_READ_BEFORE_FREEZE")
 if source.get("post_freeze_selection_required") is not True: errors.append("POSTFREEZE_SELECTION_NOT_REQUIRED")
 if source.get("selected_cases_must_be_uncontrollable_after_commitment") is not True:
  errors.append("SELECTION_CONTROLLABILITY_NOT_FORBIDDEN")

 acc=f.get("acceptance_rule") or {}
 if acc.get("all_three_surface_slots_required") is not True: errors.append("PARTIAL_SURFACE_ACCEPTANCE")
 if acc.get("promotion_from_partial_batch") is not False: errors.append("PARTIAL_PROMOTION_ALLOWED")

 fields=f.get("package_commitment_fields") or []
 payload={k:f.get(k) for k in fields}
 if _sha256_json(payload)!=f.get("package_commitment_sha256"):
  errors.append("PACKAGE_COMMITMENT_MISMATCH")

 dep=f.get("dependency_and_cost") or {}
 carrier=dep.get("execution_carrier")
 execution_ready=(not errors and isinstance(carrier,str) and not carrier.startswith("NOT_SELECTED"))
 if dep.get("incremental_spend_usd")!=0 or dep.get("paid_fallback")!="FORBIDDEN":
  errors.append("ZERO_COST_RULE_DRIFT")
 if f.get("execution_authority") is not False or f.get("promotion_authority") is not False:
  errors.append("FREEZE_CLAIMS_AUTHORITY")

 return {
  "schema":"PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_VERDICT_V1",
  "status":("PASS__P1_SHARED_BATCH_PREEXECUTION_FREEZE__BEACON_AND_ZERO_COST_CARRIER_STILL_PENDING__ZERO_REALITY"
            if not errors else "FAIL_CLOSED"),
  "errors":errors,
  "package_commitment_sha256":f.get("package_commitment_sha256"),
  "three_surface_mapping_frozen":not any(x.startswith("SURFACE") or x.startswith("TRANSPORT_GATE") for x in errors),
  "failure_semantics_normalizer_frozen":not any(x.startswith("FAILURE_SEMANTICS") or x.startswith("NORMALIZER") or x.startswith("CAUSAL") for x in errors),
  "post_freeze_selector_semantics_frozen":not any(x in errors for x in ("PREBEACON_SELECTION_ALLOWED","ADAPTIVE_SELECTION_ALLOWED","CASE_REPLACEMENT_ALLOWED","TERMINAL_V3_REPLAY_ALLOWED")),
  "execution_ready":execution_ready,
  "execution_authority":False,
  "promotion_authority":False,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "capability_credit_delta":0,
  "family_credit_delta":0,
  "next":("FREEZE_AND_INDEPENDENTLY_VERIFY_ONE_ZERO_COST_EXECUTION_CARRIER_AND_POST_FREEZE_BEACON_POLICY__THEN_SEPARATELY_REDUCE_EXECUTION_AUTHORITY"
          if not errors else "REPAIR_FREEZE")
 }

def main()->int:
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True))
 return 0 if out["status"].startswith("PASS") else 1

if __name__=="__main__": raise SystemExit(main())
