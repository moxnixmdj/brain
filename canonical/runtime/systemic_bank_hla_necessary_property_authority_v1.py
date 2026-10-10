"""Bounded systemic-bank higher-loss-absorbency necessary-property authority V1.

Authenticates one-way semantic entailments from two Basel RBC40 concepts:
- G-SIB higher loss absorbency requirement
- D-SIB higher loss absorbency requirement

Every edge is bound to the pinned BIS RBC40 source projection. Reverse
property->concept classification is forbidden. Unlisted properties remain
UNKNOWN, not false. No open-world ontology completeness or terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.https_source_fragment_projection_authority_v2 import verify_projection_pack
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA as EDGE_RECEIPT_SCHEMA

SCHEMA="PROJECT_BRAIN_SYSTEMIC_BANK_HLA_NECESSARY_PROPERTY_AUTHORITY_V1"
REQUEST_SCHEMA="PROJECT_BRAIN_SYSTEMIC_BANK_HLA_NECESSARY_PROPERTY_REQUEST_V1"
PACK_SCHEMA="PROJECT_BRAIN_SYSTEMIC_BANK_HLA_NECESSARY_PROPERTY_SOURCE_PACK_V1"
PACK_PATH="canonical/evidence/SYSTEMIC_BANK_HLA_NECESSARY_PROPERTY_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA="a4fb3d22277136a97269a953a970700a2258ca5f"
SCOPE_ID="REGCAP_BIS_RBC40_SYSTEMIC_BANK_HLA_V1"

GSIB_HLA="REGCAP::G_SIB_HIGHER_LOSS_ABSORBENCY_REQUIREMENT"
DSIB_HLA="REGCAP::D_SIB_HIGHER_LOSS_ABSORBENCY_REQUIREMENT"

RULES={
 (GSIB_HLA,"FUNCTION::LOSS_ABSORPTION"):("GSIB_GOING_CONCERN_CET1",),
 (GSIB_HLA,"DISPOSITION::LOSS_ABSORPTION"):("GSIB_GOING_CONCERN_CET1",),
 (GSIB_HLA,"REGIME::GOING_CONCERN"):("GSIB_GOING_CONCERN_CET1",),
 (GSIB_HLA,"COMPOSITION::CET1"):("GSIB_GOING_CONCERN_CET1",),
 (GSIB_HLA,"SCOPE::G_SIB"):("GSIB_GOING_CONCERN_CET1",),
 (GSIB_HLA,"RELATION::EXTENDS_CCOB"):("GSIB_EXTENDS_CCOB",),
 (DSIB_HLA,"FUNCTION::LOSS_ABSORPTION"):("DSIB_EFFECTIVE_LOSS_ABSORBING_CET1",),
 (DSIB_HLA,"DISPOSITION::LOSS_ABSORPTION"):("DSIB_EFFECTIVE_LOSS_ABSORBING_CET1",),
 (DSIB_HLA,"COMPOSITION::CET1"):("DSIB_EFFECTIVE_LOSS_ABSORBING_CET1",),
 (DSIB_HLA,"SCOPE::D_SIB"):("DSIB_EFFECTIVE_LOSS_ABSORBING_CET1",),
 (DSIB_HLA,"RELATION::EXTENDS_CCOB"):("DSIB_EXTENDS_CCOB",),
 (DSIB_HLA,"CALIBRATION::COMMENSURATE_SYSTEMIC_IMPORTANCE"):("DSIB_SYSTEMIC_IMPORTANCE_CALIBRATION",),
}

ROOT=Path(__file__).resolve().parents[2]

def _canon(v:Any)->bytes:
 return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _sha(v:Any)->str:return sha256(_canon(v)).hexdigest()

def _git_blob(raw:bytes)->str:return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _base(status:str,*,passed:bool=False,**x:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"status":status,"pass":passed,
  "semantic_truth_authority":False,"source_authority":False,
  "policy_adequacy_authority":False,"execution_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,**x}

def load_pack(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 path=(root/PACK_PATH).resolve(strict=True); path.relative_to(root)
 if not path.is_file() or path.is_symlink(): raise ValueError("PACK_FILE_INVALID")
 raw=path.read_bytes(); blob=_git_blob(raw)
 if blob!=PACK_GIT_BLOB_SHA: raise ValueError("PACK_GIT_BLOB_DRIFT:"+blob)
 doc=json.loads(raw.decode())
 if not isinstance(doc,Mapping) or doc.get("schema")!=PACK_SCHEMA: raise ValueError("PACK_SCHEMA_INVALID")
 if doc.get("scope_id")!=SCOPE_ID: raise ValueError("PACK_SCOPE_INVALID")
 sources=doc.get("sources")
 if not isinstance(sources,list) or len(sources)!=1 or not isinstance(sources[0],Mapping):
  raise ValueError("PACK_SINGLE_SOURCE_REQUIRED")
 available={str(r.get("fragment_id") or "") for r in sources[0].get("fragments",[]) if isinstance(r,Mapping)}
 required={fid for fids in RULES.values() for fid in fids}
 if not required.issubset(available): raise ValueError("PACK_MISSING_RULE_FRAGMENT")
 return {"pack":dict(doc),"source_pack":dict(sources[0]),"pack_git_blob_sha":blob}

def verify_property_request(request:Mapping[str,Any],*,repo_root:str|Path|None=None,
 projection_verifier=verify_projection_pack)->dict[str,Any]:
 try:
  if not isinstance(request,Mapping) or request.get("schema")!=REQUEST_SCHEMA:
   return _base("FAIL_CLOSED",reason="REQUEST_SCHEMA_INVALID")
  if set(request)!={"schema","scope_id","concept_id","property_id"}:
   return _base("FAIL_CLOSED",reason="REQUEST_FIELD_SET_INVALID")
  if request.get("scope_id")!=SCOPE_ID:return _base("FAIL_CLOSED",reason="SCOPE_ID_MISMATCH")
  concept=str(request.get("concept_id") or ""); prop=str(request.get("property_id") or "")
  if not concept or not prop:return _base("FAIL_CLOSED",reason="CONCEPT_OR_PROPERTY_ID_REQUIRED")
  rule=RULES.get((concept,prop))
  if rule is None:
   return _base("UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",concept_id=concept,property_id=prop,
    reverse_inference_authorized=False,absence_means_false=False)
  checked=load_pack(repo_root=repo_root)
  source=projection_verifier(checked["source_pack"])
  if not isinstance(source,Mapping) or source.get("pass") is not True:
   return _base("FAIL_CLOSED",reason="PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED",source_result=source)
  authenticated=set(str(x) for x in source.get("receipt",{}).get("fragment_ids",[]))
  if not set(rule).issubset(authenticated):
   return _base("FAIL_CLOSED",reason="REQUIRED_SOURCE_FRAGMENT_NOT_AUTHENTICATED",required_fragment_ids=list(rule))
  material={"scope_id":SCOPE_ID,"concept_id":concept,"property_id":prop,
   "pack_git_blob_sha":checked["pack_git_blob_sha"],
   "source_receipt_sha256":source["receipt"]["receipt_sha256"],"fragment_ids":list(rule),"relation":"ENTAILS"}
  core={"pass":True,"schema":EDGE_RECEIPT_SCHEMA,"scope_id":SCOPE_ID,
   "source_id":concept,"target_id":prop,"relation":"ENTAILS",
   "source_semantics_authenticated":True,"target_semantics_authenticated":True,
   "relation_semantics_authenticated":True,"verification_authority_mutated":False,
   "evidence_sha256":_sha(material)}
  edge=dict(core);edge["receipt_sha256"]=_sha(core)
  return _base("PASS__SYSTEMIC_BANK_HLA_NECESSARY_PROPERTY_AUTHENTICATED",passed=True,
   semantic_truth_authority=True,source_authority=True,concept_id=concept,property_id=prop,
   relation="ENTAILS",edge_receipt=edge,required_fragment_ids=list(rule),
   reverse_inference_authorized=False,exact_concept_identity_authority=False,
   open_world_ontology_complete=False,
   boundary="BOUND_SYSTEMIC_BANK_HLA_TO_NECESSARY_PROPERTY_ONLY__NO_REVERSE_INFERENCE__NO_UNLISTED_NEGATION__NO_GLOBAL_COMPLETENESS")
 except Exception as exc:
  return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))
