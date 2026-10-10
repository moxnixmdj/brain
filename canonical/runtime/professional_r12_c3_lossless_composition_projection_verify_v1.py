"""Verify R12 C3 abstraction soundness at the root-binding composition boundary.

The exact V4 composition run is already independently verified. This verifier
therefore isolates the C3 theorem instead of replaying the entire professional
scoped-evidence dependency graph:

* all twelve full root-binding documents are re-hashed from canonical bytes;
* every binding has an explicit scoped claim, guarantees, and limitations;
* every independent root receipt authorizes that exact scoped binding;
* the exact pinned V4 source is checked to preserve root id, binding schema,
  subject tuple, and full binding Git blob SHA in each compact output row;
* the independent V4 composition receipt proves that exact gate passed on the
  exact twelve-binding input.

Thus the composition projection is reversible over the frozen set and cannot
silently widen or erase a root's scoped semantics.

This does not prove open-world semantic completeness inside any root.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_C3_LOSSLESS_COMPOSITION_PROJECTION_VERIFY_V1"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
INPUT_PATH="canonical/governance/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INPUT_20261010_V1.json"
CERT_PATH="canonical/governance/PROFESSIONAL_R12_C3_LOSSLESS_COMPOSITION_PROJECTION_20261010_V1.json"
EXPECTED_ROOTS={
 "R1_TARGET_SPECIFICATION","R2_CANDIDATE_SEARCH","R3_REALIZATION_OBSERVATION",
 "R4_MEASUREMENT_CONSTRUCT","R5_EVALUATOR_REFERENCE","R6_EVIDENCE_GROUNDING_DEPENDENCE",
 "R7_CAUSAL_PRESCRIPTIVE","R8_POPULATION_CONTEXT_OPERATOR","R9_TEMPORAL_DEPLOYMENT",
 "R10_ANALYSIS_DECISION","R11_ADAPTIVE_INTEGRITY_SECURITY","R12_META_COMPOSITION_CLOSURE",
}
PINS={
 "input":(INPUT_PATH,"8063d124d6fbd239814380ef4fbc710350a1dea8"),
 "gate":("canonical/runtime/professional_quality_same_subject_composition_gate_v4.py","e1cc6200286c7b400fc7be70ef0789b85af7fe61"),
 "composition_verify":("canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json","4ee02c41acf64b1f47ebadec55b6bb5453d676ba"),
 "truth_reconcile":("canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V1.json","b469e2f13c318d57aaca71d8b29ad1930636507d"),
}
GATE_REQUIRED_FRAGMENTS=(
 'verified.append({"root_id":rid,"binding_schema":binding.get("schema"),"subject_kind":kind,"subject_id":sid,"subject_sha256":sha,"subject_binding_git_blob_sha":bblob})',
 'subjects.add((kind,sid,sha))',
 'if len(subjects)!=1:',
 'out["composition_admissible"]=True',
)
COMPOSITION_REQUIRED_PROOFS={
 "ALL_TWELVE_CURRENT_PROFESSIONAL_ROOT_BINDINGS_BIND_THE_IDENTICAL_FROZEN_V7_SUBJECT_TUPLE",
 "ALL_TWELVE_ROOT_BINDINGS_HAVE_INDEPENDENT_ROOT_SUBJECT_BINDING_AUTHORITY",
 "SAME_SUBJECT_COMPOSITION_IS_STRUCTURALLY_ADMISSIBLE",
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _digest(value:Any)->str:
 raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
 return sha256(raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 x=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(x,dict):raise ValueError("JSON_OBJECT_REQUIRED")
 return x

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "claim_id":CLAIM_ID,"root_binding_count":0,"reconstructible_binding_count":0,
  "c3_composition_abstraction_soundness_proved":False,
  "cc_r3_terminal_closure":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def analyze(
 input_doc:Mapping[str,Any],
 bindings:Mapping[str,Mapping[str,Any]],
 verifications:Mapping[str,Mapping[str,Any]],
 composition_verify:Mapping[str,Any],
 *,
 actual_binding_blobs:Mapping[str,str],
 gate_source:str,
)->dict[str,Any]:
 if not all(isinstance(x,Mapping) for x in (input_doc,bindings,verifications,composition_verify,actual_binding_blobs)):
  return _fail("INPUT_NOT_MAPPING")
 if not isinstance(gate_source,str):
  return _fail("GATE_SOURCE_NOT_TEXT")
 for fragment in GATE_REQUIRED_FRAGMENTS:
  if fragment not in gate_source:
   return _fail("GATE_PROJECTION_SEMANTICS_FRAGMENT_MISSING",fragment=fragment)

 rows=input_doc.get("root_subject_bindings")
 if not isinstance(rows,list) or len(rows)!=12:
  return _fail("INPUT_NOT_EXACT_TWELVE_BINDINGS")
 ids=[r.get("root_id") for r in rows if isinstance(r,Mapping)]
 if len(ids)!=12 or len(set(ids))!=12 or set(ids)!=EXPECTED_ROOTS:
  return _fail("INPUT_ROOT_SET_INVALID",observed=ids)

 status=str(composition_verify.get("status") or "")
 proves=set(composition_verify.get("proves") or [])
 exact=(composition_verify.get("exact_blobs") or {})
 if not status.startswith("PASS__") or not COMPOSITION_REQUIRED_PROOFS<=proves:
  return _fail("INDEPENDENT_COMPOSITION_RECEIPT_INSUFFICIENT")
 if exact.get("composition_input")!=PINS["input"][1] or exact.get("composition_gate_v4")!=PINS["gate"][1]:
  return _fail("INDEPENDENT_COMPOSITION_RECEIPT_SOURCE_DRIFT")
 if composition_verify.get("verified_root_subject_binding_count")!=12 or composition_verify.get("composition_admissible") is not True:
  return _fail("INDEPENDENT_COMPOSITION_RECEIPT_COUNT_OR_PASS_INVALID")
 for field in ("professional_quality_closed","semantic_truth_authority","execution_authority",
               "quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if composition_verify.get(field) is not False:
   return _fail("COMPOSITION_RECEIPT_AUTHORITY_WIDENING",field=field)
 nonclaims=set(composition_verify.get("hard_nonclaims") or [])
 if not {"NO_GLOBAL_LEAF_OR_ROOT_CLOSURE","NO_DOMAIN_SEMANTIC_CLOSURE"}<=nonclaims:
  return _fail("COMPOSITION_SCOPE_BOUNDARY_MISSING")

 scope_digests={};blob_set=set()
 for row in rows:
  if not isinstance(row,Mapping):return _fail("INPUT_ROW_INVALID")
  rid=row["root_id"];bref=row.get("binding");vref=row.get("verification")
  if not isinstance(bref,Mapping) or not isinstance(vref,Mapping):
   return _fail("INPUT_REFERENCE_INVALID",root_id=rid)
  b=bindings.get(rid);v=verifications.get(rid)
  if not isinstance(b,Mapping) or not isinstance(v,Mapping):
   return _fail("BOUND_DOCUMENT_MISSING",root_id=rid)
  declared=bref.get("git_blob_sha");actual=actual_binding_blobs.get(rid)
  if not isinstance(declared,str) or actual!=declared:
   return _fail("BINDING_CONTENT_ADDRESS_MISMATCH",root_id=rid,declared=declared,actual=actual)
  if declared in blob_set:
   return _fail("BINDING_CONTENT_ADDRESS_DUPLICATE",root_id=rid)
  blob_set.add(declared)
  if b.get("root_id")!=rid:return _fail("BINDING_ROOT_ID_MISMATCH",root_id=rid)
  if (b.get("subject_id"),b.get("subject_sha256"))!=(SUBJECT_ID,SUBJECT_SHA):
   return _fail("BINDING_SUBJECT_DRIFT",root_id=rid)
  scope=b.get("binding_scope")
  if not isinstance(scope,Mapping):return _fail("BINDING_SCOPE_MISSING",root_id=rid)
  if not isinstance(scope.get("claim"),str) or not scope.get("claim","").strip():
   return _fail("BINDING_SCOPE_CLAIM_MISSING",root_id=rid)
  if not isinstance(scope.get("guarantees"),list) or not scope.get("guarantees"):
   return _fail("BINDING_SCOPE_GUARANTEES_MISSING",root_id=rid)
  if not isinstance(scope.get("limitations"),list) or not scope.get("limitations"):
   return _fail("BINDING_SCOPE_LIMITATIONS_MISSING",root_id=rid)
  vstatus=str(v.get("status") or "")
  if not (vstatus.startswith("PASS__") or ("INDEPENDENT" in vstatus and "PASS" in vstatus)):
   return _fail("INDEPENDENT_ROOT_VERIFICATION_NOT_PASS",root_id=rid,status=vstatus)
  if v.get("terminal_authority") not in (False,None):
   return _fail("ROOT_VERIFICATION_TERMINAL_OVERCLAIM",root_id=rid)
  scope_digests[rid]=_digest(dict(scope))

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_C3_ROOT_BINDING_COMPOSITION_PROJECTION_LOSSLESS_AND_SCOPE_PRESERVING",
  "claim_id":CLAIM_ID,
  "root_binding_count":12,"reconstructible_binding_count":12,
  "scope_digest_by_root":scope_digests,
  "projection_injective_on_frozen_root_set":True,
  "projection_reconstructible_from_content_address":True,
  "scope_widening_introduced_by_composition":False,
  "authority_widening_introduced_by_composition":False,
  "c3_composition_abstraction_soundness_proved":True,
  "proof_scope":"ROOT_BINDING_TO_SAME_SUBJECT_COMPOSITION_BOUNDARY_ONLY",
  "does_not_prove":[
   "GLOBAL_SEMANTIC_COMPLETENESS_INSIDE_ANY_ROOT","GLOBAL_ROOT_CLOSURE",
   "UNKNOWN_MATERIAL_DEFEATER_COMPLETENESS","R12_CC_R3_TERMINAL_CLOSURE",
   "R12_SEMANTIC_PROPERTY_TRUTH"
  ],
  "cc_r3_terminal_closure":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 try:
  for key,(rel,expected) in PINS.items():
   p=root/rel
   if not p.is_file() or p.is_symlink():return _fail(key.upper()+"_MISSING")
   actual=_blob(p)
   if actual!=expected:return _fail(key.upper()+"_BLOB_DRIFT",observed=actual,expected=expected)
  inp=_load(root/INPUT_PATH);cert=_load(root/CERT_PATH)
  if cert.get("claim",{}).get("claim_id")!=CLAIM_ID:return _fail("CERT_CLAIM_ID_DRIFT")
  cv=_load(root/PINS["composition_verify"][0])
  gate_source=(root/PINS["gate"][0]).read_text(encoding="utf-8")
  bindings={};verifications={};actual={}
  for row in inp.get("root_subject_bindings") or []:
   rid=row.get("root_id");br=row.get("binding") or {};vr=row.get("verification") or {}
   bp=root/br.get("path","");vp=root/vr.get("path","")
   if not bp.is_file() or bp.is_symlink():return _fail("BINDING_FILE_MISSING",root_id=rid)
   if not vp.is_file() or vp.is_symlink():return _fail("VERIFICATION_FILE_MISSING",root_id=rid)
   actual[rid]=_blob(bp)
   if actual[rid]!=br.get("git_blob_sha"):return _fail("BINDING_BLOB_DRIFT",root_id=rid)
   if _blob(vp)!=vr.get("git_blob_sha"):return _fail("VERIFICATION_BLOB_DRIFT",root_id=rid)
   bindings[rid]=_load(bp);verifications[rid]=_load(vp)
  return analyze(inp,bindings,verifications,cv,actual_binding_blobs=actual,gate_source=gate_source)
 except Exception as exc:
  return _fail(type(exc).__name__+":"+str(exc))

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
