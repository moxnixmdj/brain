#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
CERT="canonical/governance/SYNTHESIS_SCOPE_RELATION_CERTIFICATE_V1.json"
SOURCES={
"contracts":"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
"protocols":"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
"predicates":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
"targets":"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V3.json",
"targets_verify":"canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_V3_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
"binding":"canonical/governance/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_CANDIDATE_V1.json",
"binding_verify":"canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
}
EXPECTED={
SOURCES["contracts"]:"ee187f611a0e82b2de495ee377682f39bc31dd31",
SOURCES["protocols"]:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
SOURCES["predicates"]:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
SOURCES["targets"]:"9b400e6eb1a95bacbd9c0cdb93b155ced0f72558",
SOURCES["targets_verify"]:"b5192b1903dc603e75efe92b9a00ced0b2722f8c",
SOURCES["binding"]:"a988b6fa4baf1d753f709c757c97f17185181f0a",
SOURCES["binding_verify"]:"64ad40c1c10bd01e4c0f4418fac29efafea838fc",
}
PID="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
FAMILY="COMMUNICATION_AND_SYNTHESIS"
BID="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
DIMS=[
"claim-to-source fidelity","required evidence coverage","uncertainty/disagreement preservation",
"audience adaptation","format/style constraints","compression without decision-relevant loss",
]
ATOM_BY_DIM={
"claim-to-source fidelity":"dimension:claim_to_source_fidelity",
"required evidence coverage":"dimension:required_evidence_coverage",
"uncertainty/disagreement preservation":"dimension:uncertainty_and_disagreement_preservation",
"audience adaptation":"dimension:audience_adaptation",
"format/style constraints":"dimension:format_and_style_constraints",
"compression without decision-relevant loss":"dimension:compression_without_decision_relevant_loss",
}

def load(p:str)->dict[str,Any]:
 x=json.loads((ROOT/p).read_text(encoding="utf-8"))
 if not isinstance(x,dict): raise ValueError(p)
 return x

def blob(p:str)->str:
 b=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def evaluate(cert:Mapping[str,Any]|None=None)->dict[str,Any]:
 e=[]
 c=dict(cert or load(CERT))
 for p,h in EXPECTED.items():
  if blob(p)!=h:e.append("SOURCE_BLOB_DRIFT:"+p)
 auth=c.get("authority") or {}
 for key,p in SOURCES.items():
  row=auth.get({"contracts":"behavioral_contract_registry","protocols":"terminal_protocols","predicates":"predicate_registry","targets":"target_normalization","targets_verify":"target_normalization_verification","binding":"synthesis_binding","binding_verify":"synthesis_binding_verification"}[key])
  if not isinstance(row,Mapping) or row.get("path")!=p or row.get("git_blob_sha")!=EXPECTED[p]:
   e.append("AUTHORITY_MISMATCH:"+key)
 contracts=load(SOURCES["contracts"]); protocols=load(SOURCES["protocols"]); preds=load(SOURCES["predicates"])
 targets=load(SOURCES["targets"]); tv=load(SOURCES["targets_verify"]); binding=load(SOURCES["binding"]); bv=load(SOURCES["binding_verify"])
 pr=next((x for x in preds.get("predicates",[]) if isinstance(x,Mapping) and x.get("id")==PID),None)
 tr=next((x for x in targets.get("targets",[]) if isinstance(x,Mapping) and x.get("predicate_id")==PID),None)
 prot=next((x for x in protocols.get("protocols",[]) if isinstance(x,Mapping) and x.get("family")==FAMILY),None)
 con=next((x for x in contracts.get("active_contracted_residuals",[]) if isinstance(x,Mapping) and x.get("behavior_id")==BID),None)
 if not all(isinstance(x,Mapping) for x in (pr,tr,prot,con)): e.append("REQUIRED_ROW_MISSING")
 else:
  if pr.get("family")!=FAMILY or tr.get("family")!=FAMILY: e.append("FAMILY_MISMATCH")
  if prot.get("task_dimensions")!=DIMS: e.append("PROTOCOL_DIMENSIONS_DRIFT")
  req=set(tr.get("required_atoms") or [])
  if not set(ATOM_BY_DIM.values()).issubset(req): e.append("TARGET_DIMENSION_ATOMS_MISSING")
  fammap=contracts.get("family_to_residual_contracts") or {}
  if fammap.get(FAMILY)!=[BID]: e.append("FAMILY_NOT_SINGLETON_CONTRACT_DECOMPOSITION")
  if con.get("scope")!="Grounded evidence synthesis under audience and format constraints": e.append("CONTRACT_SCOPE_DRIFT")
  mappings=(c.get("proof") or {}).get("exact_dimension_mappings")
  if not isinstance(mappings,list) or len(mappings)!=6: e.append("DIMENSION_MAPPING_COUNT")
  else:
   seen=set()
   for m in mappings:
    if not isinstance(m,Mapping): e.append("MALFORMED_MAPPING"); continue
    d=m.get("target"); seen.add(d)
    if d not in DIMS: e.append("UNKNOWN_DIMENSION:"+str(d)); continue
    fields=m.get("contract_fields"); lits=m.get("required_literals")
    if not isinstance(fields,list) or not isinstance(lits,list) or len(fields)!=len(lits): e.append("MAPPING_SHAPE:"+d); continue
    for field,lit in zip(fields,lits):
     val=str(con.get(field,""))
     if str(lit).lower() not in val.lower(): e.append("LITERAL_NOT_IN_CONTRACT:"+d+":"+str(field))
   if seen!=set(DIMS): e.append("DIMENSION_SET_DRIFT")
 if tv.get("independent_runner",{}).get("conclusion")!="success": e.append("TARGET_NORMALIZATION_NOT_INDEPENDENT")
 if tv.get("verified",{}).get("current_live_target_set_exact") is not True: e.append("TARGET_NORMALIZATION_NOT_EXACT")
 if bv.get("public_runner",{}).get("conclusion")!="success": e.append("SYNTHESIS_BINDING_NOT_INDEPENDENT")
 if bv.get("proved_atom_count")!=7: e.append("SYNTHESIS_BINDING_ATOM_COUNT")
 if binding.get("behavior_id")!=BID or binding.get("family")!=FAMILY: e.append("BINDING_IDENTITY_MISMATCH")
 if c.get("claimed_relation")!="PROVEN_STRONGER": e.append("RELATION_NOT_PROVEN_STRONGER")
 unproved=set(c.get("deliberately_unproved") or [])
 for x in {"metric:matched_quality","matched_quality_noninferiority","required_claim_coverage_noninferiority","BRAIN_GE_OPUS_PERFORMANCE","ACCEPTANCE_PREDICATE"}:
  if x not in unproved:e.append("MISSING_NONCLAIM:"+x)
 if c.get("performance_credit_requested") is not False:e.append("PERFORMANCE_CREDIT_OVERCLAIM")
 ok=not e
 return {
  "schema":"PROJECT_BRAIN_SYNTHESIS_SCOPE_RELATION_VERIFIER_V1",
  "status":"PASS__SYNTHESIS_TARGET_SCOPE_DEFINITIONALLY_SUBSET_OF_SINGLETON_BRAIN_SYNTHESIS_CONTRACT__ROOT3_SCOPE_RELATION_ELIGIBLE__ZERO_PERFORMANCE_CREDIT" if ok else "FAIL_CLOSED",
  "pass":ok,"errors":sorted(set(e)),
  "predicate_id":PID,
  "scope_relation_verified":ok,
  "scope_relation":"PROVEN_STRONGER" if ok else None,
  "root3_scope_relation_credit_eligible":ok,
  "root2_performance_residuals_preserved":["metric:matched_quality","matched_quality_noninferiority","required_claim_coverage_noninferiority"],
  "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
 }

if __name__=="__main__":
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
