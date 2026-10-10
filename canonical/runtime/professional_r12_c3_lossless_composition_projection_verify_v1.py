"""Verify R12 C3 abstraction soundness at the exact root-binding composition boundary.

The composition gate projects twelve full scoped root bindings to compact rows.
This verifier proves that projection is lossless for the frozen V7 composition:
every compact row retains an exact content address to the complete source binding
document and no broader authority is introduced.

It does NOT prove open-world semantic completeness inside any root.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_same_subject_composition_gate_v4 as gate

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_C3_LOSSLESS_COMPOSITION_PROJECTION_VERIFY_V1"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
INPUT_PATH="canonical/governance/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INPUT_20261010_V1.json"
CERT_PATH="canonical/governance/PROFESSIONAL_R12_C3_LOSSLESS_COMPOSITION_PROJECTION_20261010_V1.json"

PINS={
 "input":(INPUT_PATH,"8063d124d6fbd239814380ef4fbc710350a1dea8"),
 "gate":("canonical/runtime/professional_quality_same_subject_composition_gate_v4.py","e1cc6200286c7b400fc7be70ef0789b85af7fe61"),
 "composition_verify":("canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json","4ee02c41acf64b1f47ebadec55b6bb5453d676ba"),
 "truth_reconcile":("canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V1.json","b469e2f13c318d57aaca71d8b29ad1930636507d"),
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
 gate_out:Mapping[str,Any],
 bindings:Mapping[str,Mapping[str,Any]],
 verifications:Mapping[str,Mapping[str,Any]],
 composition_verify:Mapping[str,Any],
 *,
 actual_binding_blobs:Mapping[str,str],
)->dict[str,Any]:
 if not all(isinstance(x,Mapping) for x in (input_doc,gate_out,bindings,verifications,composition_verify,actual_binding_blobs)):
  return _fail("INPUT_NOT_MAPPING")
 rows=input_doc.get("root_subject_bindings")
 if not isinstance(rows,list) or len(rows)!=12:
  return _fail("INPUT_NOT_EXACT_TWELVE_BINDINGS")
 ids=[r.get("root_id") for r in rows if isinstance(r,Mapping)]
 if len(ids)!=12 or len(set(ids))!=12 or set(ids)!=set(gate.EXPECTED_ROOTS):
  return _fail("INPUT_ROOT_SET_INVALID",observed=ids)
 if gate_out.get("pass") is not True or gate_out.get("composition_admissible") is not True:
  return _fail("GATE_REPLAY_NOT_PASS",gate_status=gate_out.get("status"))
 out_rows=gate_out.get("verified_bindings")
 if not isinstance(out_rows,list) or len(out_rows)!=12:
  return _fail("GATE_OUTPUT_NOT_EXACT_TWELVE")
 out_by={r.get("root_id"):r for r in out_rows if isinstance(r,Mapping)}
 if set(out_by)!=set(ids):
  return _fail("GATE_OUTPUT_ROOT_SET_INVALID")

 scope_digests={}
 for row in rows:
  rid=row["root_id"]
  bref=row.get("binding")
  vref=row.get("verification")
  if not isinstance(bref,Mapping) or not isinstance(vref,Mapping):
   return _fail("INPUT_REFERENCE_INVALID",root_id=rid)
  b=bindings.get(rid);v=verifications.get(rid)
  if not isinstance(b,Mapping) or not isinstance(v,Mapping):
   return _fail("BOUND_DOCUMENT_MISSING",root_id=rid)
  declared=bref.get("git_blob_sha")
  actual=actual_binding_blobs.get(rid)
  if not isinstance(declared,str) or actual!=declared:
   return _fail("BINDING_CONTENT_ADDRESS_MISMATCH",root_id=rid,declared=declared,actual=actual)
  if b.get("root_id")!=rid:
   return _fail("BINDING_ROOT_ID_MISMATCH",root_id=rid)
  if (b.get("subject_id"),b.get("subject_sha256"))!=(SUBJECT_ID,SUBJECT_SHA):
   return _fail("BINDING_SUBJECT_DRIFT",root_id=rid)
  scope=b.get("binding_scope")
  if not isinstance(scope,Mapping):
   return _fail("BINDING_SCOPE_MISSING",root_id=rid)
  if not isinstance(scope.get("claim"),str) or not scope.get("claim","").strip():
   return _fail("BINDING_SCOPE_CLAIM_MISSING",root_id=rid)
  guarantees=scope.get("guarantees")
  limitations=scope.get("limitations")
  if not isinstance(guarantees,list) or not guarantees:
   return _fail("BINDING_SCOPE_GUARANTEES_MISSING",root_id=rid)
  if not isinstance(limitations,list) or not limitations:
   return _fail("BINDING_SCOPE_LIMITATIONS_MISSING",root_id=rid)
  if v.get("root_subject_binding_authority") is not True:
   return _fail("INDEPENDENT_ROOT_AUTHORITY_MISSING",root_id=rid)
  if v.get("terminal_authority") is not False:
   return _fail("ROOT_VERIFICATION_TERMINAL_OVERCLAIM",root_id=rid)

  compact=out_by[rid]
  if compact.get("subject_binding_git_blob_sha")!=declared:
   return _fail("COMPACT_ROW_LOST_BINDING_CONTENT_ADDRESS",root_id=rid)
  if (compact.get("subject_id"),compact.get("subject_sha256"))!=(SUBJECT_ID,SUBJECT_SHA):
   return _fail("COMPACT_ROW_SUBJECT_DRIFT",root_id=rid)
  if compact.get("root_id")!=rid:
   return _fail("COMPACT_ROW_ROOT_DRIFT",root_id=rid)
  scope_digests[rid]=_digest(dict(scope))

 # The compact projection is sound because each row points back to the exact
 # independently verified full binding bytes; no semantic scope is synthesized.
 for field in ("professional_quality_closed","semantic_truth_authority","execution_authority",
               "quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if gate_out.get(field) is not False:
   return _fail("COMPOSITION_AUTHORITY_WIDENING",field=field)

 proves=set(composition_verify.get("proves") or [])
 required={
  "ALL_TWELVE_CURRENT_PROFESSIONAL_ROOT_BINDINGS_BIND_THE_IDENTICAL_FROZEN_V7_SUBJECT_TUPLE",
  "ALL_TWELVE_ROOT_BINDINGS_HAVE_INDEPENDENT_ROOT_SUBJECT_BINDING_AUTHORITY",
  "SAME_SUBJECT_COMPOSITION_IS_STRUCTURALLY_ADMISSIBLE",
 }
 if not str(composition_verify.get("status") or "").startswith("PASS__") or not required<=proves:
  return _fail("INDEPENDENT_COMPOSITION_RECEIPT_INSUFFICIENT")
 nonclaims=set(composition_verify.get("hard_nonclaims") or [])
 if not {"NO_GLOBAL_LEAF_OR_ROOT_CLOSURE","NO_DOMAIN_SEMANTIC_CLOSURE"}<=nonclaims:
  return _fail("COMPOSITION_SCOPE_BOUNDARY_MISSING")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_C3_ROOT_BINDING_COMPOSITION_PROJECTION_LOSSLESS_AND_SCOPE_PRESERVING",
  "claim_id":CLAIM_ID,
  "root_binding_count":12,
  "reconstructible_binding_count":12,
  "scope_digest_by_root":scope_digests,
  "projection_injective_on_frozen_root_set":True,
  "projection_reconstructible_from_content_address":True,
  "scope_widening_introduced_by_composition":False,
  "authority_widening_introduced_by_composition":False,
  "c3_composition_abstraction_soundness_proved":True,
  "proof_scope":"ROOT_BINDING_TO_SAME_SUBJECT_COMPOSITION_BOUNDARY_ONLY",
  "does_not_prove":[
   "GLOBAL_SEMANTIC_COMPLETENESS_INSIDE_ANY_ROOT",
   "GLOBAL_ROOT_CLOSURE",
   "UNKNOWN_MATERIAL_DEFEATER_COMPLETENESS",
   "R12_CC_R3_TERMINAL_CLOSURE",
   "R12_SEMANTIC_PROPERTY_TRUTH"
  ],
  "cc_r3_terminal_closure":False,
  "semantic_property_truth_authority":False,
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
  inp=_load(root/INPUT_PATH)
  cert=_load(root/CERT_PATH)
  if cert.get("claim",{}).get("claim_id")!=CLAIM_ID:return _fail("CERT_CLAIM_ID_DRIFT")
  composition_verify=_load(root/PINS["composition_verify"][0])
  gate_out=gate.evaluate(inp,repo_root=root)

  bindings={};verifications={};actual={}
  for row in inp.get("root_subject_bindings") or []:
   rid=row.get("root_id")
   br=row.get("binding") or {};vr=row.get("verification") or {}
   bp=root/br.get("path","");vp=root/vr.get("path","")
   if not bp.is_file() or bp.is_symlink():return _fail("BINDING_FILE_MISSING",root_id=rid)
   if not vp.is_file() or vp.is_symlink():return _fail("VERIFICATION_FILE_MISSING",root_id=rid)
   actual[rid]=_blob(bp)
   if actual[rid]!=br.get("git_blob_sha"):return _fail("BINDING_BLOB_DRIFT",root_id=rid)
   if _blob(vp)!=vr.get("git_blob_sha"):return _fail("VERIFICATION_BLOB_DRIFT",root_id=rid)
   bindings[rid]=_load(bp);verifications[rid]=_load(vp)
  return analyze(inp,gate_out,bindings,verifications,composition_verify,actual_binding_blobs=actual)
 except Exception as exc:
  return _fail(type(exc).__name__+":"+str(exc))

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
