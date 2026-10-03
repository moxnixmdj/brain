"""Verify the synthesis lossless protocol-to-behavior scope decomposition."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_VERIFIER_V1"
CAND="canonical/governance/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_V1.json"
PROT="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REG="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
RES="canonical/governance/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_INPUT_V2.json"
ATOM="canonical/verification/SYNTHESIS_OVERLAY_V3_REBIND_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
EXPECTED={
 PROT:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 REG:"ee187f611a0e82b2de495ee377682f39bc31dd31",
 RES:"4e5b944c86b8745083cc9d97fe186aa4b1322747",
 ATOM:"1a67bc568944212c4d235a463c8bd7bea21b3993",
}
FAMILY="COMMUNICATION_AND_SYNTHESIS"
BEHAVIOR="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
TARGET={
 "claim-to-source fidelity",
 "required evidence coverage",
 "uncertainty/disagreement preservation",
 "audience adaptation",
 "format/style constraints",
 "compression without decision-relevant loss",
}

def blob(p:str)->str:
 b=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(p:str)->dict[str,Any]:
 x=json.loads((ROOT/p).read_text(encoding="utf-8"))
 if not isinstance(x,dict): raise ValueError(p)
 return x

def evaluate()->dict[str,Any]:
 e=[]
 for p,h in EXPECTED.items():
  if blob(p)!=h: e.append("SOURCE_BLOB_DRIFT:"+p)
 c=load(CAND); prot=load(PROT); reg=load(REG); res=load(RES); atom=load(ATOM)
 prow=next((x for x in prot.get("protocols",[]) if isinstance(x,Mapping) and x.get("family")==FAMILY),None)
 brow=next((x for x in reg.get("active_contracted_residuals",[]) if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR),None)
 if not isinstance(prow,Mapping): e.append("PROTOCOL_ROW_MISSING")
 if not isinstance(brow,Mapping): e.append("BEHAVIOR_ROW_MISSING")
 pdims=set(prow.get("task_dimensions") or []) if isinstance(prow,Mapping) else set()
 if pdims!=TARGET or len(prow.get("task_dimensions") or [])!=6: e.append("TARGET_DIMENSION_SET_DRIFT")
 cdims=c.get("target_dimensions")
 if not isinstance(cdims,list) or set(cdims)!=TARGET or len(cdims)!=6: e.append("CANDIDATE_DIMENSION_SET_DRIFT")
 bindings=c.get("dimension_bindings")
 if not isinstance(bindings,list) or len(bindings)!=6:
  e.append("BINDING_COUNT")
  bindings=[]
 seen=set()
 for row in bindings:
  if not isinstance(row,Mapping):
   e.append("BINDING_INVALID"); continue
  d=row.get("target_dimension")
  if d not in TARGET: e.append("UNKNOWN_DIMENSION:"+str(d))
  if d in seen: e.append("DUPLICATE_DIMENSION:"+str(d))
  seen.add(d)
  ws=row.get("contract_witnesses")
  if not isinstance(ws,list) or not ws:
   e.append("WITNESS_MISSING:"+str(d)); continue
  for w in ws:
   if not isinstance(w,Mapping):
    e.append("WITNESS_INVALID:"+str(d)); continue
   field=w.get("field"); fragment=w.get("fragment")
   actual=brow.get(field) if isinstance(brow,Mapping) else None
   if not isinstance(actual,str): e.append("CONTRACT_FIELD_MISSING:"+str(field))
   elif not isinstance(fragment,str) or fragment not in actual:
    e.append("CONTRACT_FRAGMENT_MISMATCH:"+str(d)+":"+str(field))
 if seen!=TARGET: e.append("UNBOUND_DIMENSIONS")
 dec=c.get("decomposition_claim") or {}
 if dec.get("coverage_complete") is not True: e.append("COVERAGE_NOT_COMPLETE")
 if dec.get("coverage_relation")!="EXACT_UNION": e.append("COVERAGE_RELATION")
 if dec.get("exact_target_dimension_count")!=6 or dec.get("exact_bound_dimension_count")!=6:
  e.append("COVERAGE_COUNT_DRIFT")
 if dec.get("duplicate_or_unbound_dimensions")!=0: e.append("COVERAGE_DUP_OR_OPEN")
 if dec.get("witness_contract_scope")!=(brow.get("scope") if isinstance(brow,Mapping) else None):
  e.append("WITNESS_SCOPE_DRIFT")
 ar=res.get("algebra_input") or {}
 target=ar.get("target") or {}
 witness=ar.get("witness") or {}
 if set(x.replace("dimension:","").replace("_"," ") for x in []): pass
 expected_atoms={
  "dimension:claim_to_source_fidelity","dimension:required_evidence_coverage",
  "dimension:uncertainty_and_disagreement_preservation","dimension:audience_adaptation",
  "dimension:format_and_style_constraints","dimension:compression_without_decision_relevant_loss",
 }
 if not expected_atoms.issubset(set(target.get("required_atoms") or [])): e.append("TARGET_ATOM_DIMENSIONS_DRIFT")
 if not expected_atoms.issubset(set(witness.get("proved_atoms") or [])): e.append("WITNESS_DIMENSION_ATOMS_NOT_PROVED")
 exp=res.get("expected_residual") or {}
 if exp.get("missing_scope_relation") is not True: e.append("SCOPE_RELATION_NOT_OPEN_AT_INPUT")
 if atom.get("verified",{}).get("transported_proved_atom_count")!=7: e.append("SEVEN_ATOM_RECEIPT_DRIFT")
 if atom.get("verified",{}).get("missing_scope_relation") is not True: e.append("ATOM_RECEIPT_SCOPE_STATE_DRIFT")
 if c.get("target_scope_id")!="scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR": e.append("TARGET_SCOPE_ID")
 if c.get("witness_scope_id")!="scope://brain/EVIDENCE_TO_AUDIENCE_SYNTHESIS_001/T1_T3_TERMINAL": e.append("WITNESS_SCOPE_ID")
 if c.get("basis")!="LOSSLESS_DECOMPOSITION" or c.get("scope_relation")!="PROVEN_STRONGER":
  e.append("CERTIFICATE_TYPE")
 ok=not e
 return {
  "schema":SCHEMA,
  "status":"PASS__EXACT_SIX_DIMENSION_LOSSLESS_SCOPE_RELATION__SYNTHESIS_ROOT3_SCOPE_RELATION_ELIGIBLE__ZERO_PERFORMANCE_CREDIT" if ok else "FAIL_CLOSED",
  "pass":ok,"errors":sorted(set(e)),
  "target_predicate_id":"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
  "target_dimension_count":6 if ok else None,
  "bound_dimension_count":6 if ok else None,
  "scope_relation":"PROVEN_STRONGER" if ok else None,
  "scope_relation_eligible":ok,
  "seven_operational_atoms_preserved":ok,
  "remaining_root2_residuals":["metric:matched_quality","matched_quality_noninferiority","required_claim_coverage_noninferiority"] if ok else [],
  "acceptance_closed":False,
  "performance_credit":False,
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
 }
if __name__=="__main__":
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
