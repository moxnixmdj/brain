"""Classify the shared professional semantic-leaf completeness blocker.

All twelve professional semantic leaves currently use the same acceptance:
domain-specific semantics/grounding/scope/uncertainty plus ALL root-relevant
defeaters resolved with typed evidence.

The current canonical 80-challenge defeater catalog explicitly disclaims
completeness. Therefore that catalog, by itself, cannot authorize whole-leaf
semantic property truth for any of the twelve leaves. This is a scheduler
classification only. It does not prove semantic closure is impossible, nor
that a new primitive is required.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_SEMANTIC_SHARED_BLOCKER_V1"
MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
MANIFEST_BLOB="a7cad32c9fd969ff2c3857bb924c7bd746237ec2"
CATALOG_PATH="canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json"
CATALOG_BLOB="8b92e5cf76f767054f55414b87014e03d43460b8"
EXPECTED_ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
COMPLETENESS_NONCLAIM="NO_CLAIM_DEFEATER_SET_COMPLETE"

def _blob(p:Path)->str:
 raw=p.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(p:Path)->dict[str,Any]:
 x=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(x,dict): raise ValueError("NOT_OBJECT")
 return x

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "semantic_leaf_count":0,"shared_acceptance_proved":False,
  "catalog_completeness_proved":False,
  "catalog_alone_can_authorize_semantic_property_truth":False,
  "new_primitive_required":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra
 }

def evaluate(manifest:Mapping[str,Any],catalog:Mapping[str,Any])->dict[str,Any]:
 roots=manifest.get("roots")
 if not isinstance(roots,list) or len(roots)!=12:
  return _fail("MANIFEST_ROOT_COUNT_INVALID")
 semantic=[]
 root_ids=[]
 for row in roots:
  if not isinstance(row,Mapping):return _fail("MANIFEST_ROOT_ROW_INVALID")
  rid=row.get("root_id");leaf=row.get("semantic_leaf")
  if not isinstance(rid,str) or not isinstance(leaf,Mapping):return _fail("SEMANTIC_LEAF_INVALID")
  if not isinstance(leaf.get("id"),str) or not isinstance(leaf.get("acceptance"),str):
   return _fail("SEMANTIC_LEAF_FIELDS_INVALID")
  semantic.append({"root_id":rid,"leaf_id":leaf["id"],"acceptance":leaf["acceptance"]})
  root_ids.append(rid)
 if len(semantic)!=12 or len(set(x["leaf_id"] for x in semantic))!=12 or len(set(root_ids))!=12:
  return _fail("SEMANTIC_LEAF_SET_INVALID")
 acceptances={x["acceptance"] for x in semantic}
 if acceptances!={EXPECTED_ACCEPTANCE}:
  return _fail("SEMANTIC_ACCEPTANCE_NOT_SHARED",observed_acceptances=sorted(acceptances))

 if catalog.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_V2":
  return _fail("CATALOG_SCHEMA_INVALID")
 if catalog.get("root_count")!=12 or catalog.get("challenge_count")!=80:
  return _fail("CATALOG_CARDINALITY_INVALID")
 catalog_roots={x.get("id") for x in catalog.get("roots") or [] if isinstance(x,Mapping)}
 if catalog_roots!=set(root_ids):
  return _fail("CATALOG_ROOT_SET_MISMATCH")
 challenges=catalog.get("challenges")
 if not isinstance(challenges,list) or len(challenges)!=80:
  return _fail("CATALOG_CHALLENGE_SET_INVALID")
 if len({x.get("id") for x in challenges if isinstance(x,Mapping)})!=80:
  return _fail("CATALOG_CHALLENGE_IDS_NOT_UNIQUE")
 nonclaims=set(catalog.get("hard_nonclaims") or [])
 if COMPLETENESS_NONCLAIM not in nonclaims:
  return _fail("CATALOG_COMPLETENESS_NONCLAIM_MISSING")
 if catalog.get("closure_state")!="OPEN":
  return _fail("CATALOG_CLOSURE_STATE_NOT_OPEN")

 root_challenge_counts={rid:0 for rid in root_ids}
 for ch in challenges:
  if not isinstance(ch,Mapping):return _fail("CATALOG_CHALLENGE_ROW_INVALID")
  for rid in ch.get("root_ids") or []:
   if rid in root_challenge_counts:root_challenge_counts[rid]+=1
 if any(n==0 for n in root_challenge_counts.values()):
  return _fail("ROOT_WITHOUT_CATALOG_CHALLENGE",root_challenge_counts=root_challenge_counts)

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__12_SEMANTIC_LEAVES_SHARE_ONE_ACCEPTANCE__CURRENT_80_CHALLENGE_CATALOG_EXPLICITLY_DISCLAIMS_COMPLETENESS__CATALOG_ALONE_CANNOT_CLOSE_SEMANTIC_PROPERTY_TRUTH",
  "semantic_leaf_count":12,
  "semantic_leaf_ids":sorted(x["leaf_id"] for x in semantic),
  "shared_acceptance":EXPECTED_ACCEPTANCE,
  "shared_acceptance_proved":True,
  "catalog_challenge_count":80,
  "root_challenge_counts":dict(sorted(root_challenge_counts.items())),
  "catalog_completeness_proved":False,
  "catalog_completeness_nonclaim":COMPLETENESS_NONCLAIM,
  "catalog_closure_state":"OPEN",
  "catalog_alone_can_authorize_semantic_property_truth":False,
  "current_shared_blocker":"STRONGER_CLAIM_SCOPED_DEFEATER_COMPLETENESS_OR_OTHER_TYPED_EVIDENCE_PROOF_REQUIRED_BEFORE_ANY_SEMANTIC_LEAF_PROPERTY_TRUTH",
  "new_primitive_required":False,
  "new_primitive_status":"NOT_ESTABLISHED__THIS_IS_A_COMPLETENESS_EVIDENCE_BOUNDARY",
  "hard_nonclaims":[
   "NO_CLAIM_SEMANTIC_PROPERTY_TRUTH_IS_IMPOSSIBLE",
   "NO_CLAIM_A_NEW_PRIMITIVE_IS_REQUIRED",
   "NO_CLAIM_THE_80_CHALLENGES_ARE_COMPLETE",
   "NO_SEMANTIC_LEAF_PROPERTY_TRUTH",
   "NO_QUALITY_ACCEPTANCE_PROMOTION_OR_TERMINAL_AUTHORITY"
  ],
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,rel,expected in (
  ("manifest",MANIFEST_PATH,MANIFEST_BLOB),
  ("catalog",CATALOG_PATH,CATALOG_BLOB),
 ):
  p=root/rel
  if not p.is_file() or p.is_symlink():return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected:return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual)
  try:docs[key]=_load(p)
  except Exception:return _fail(key.upper()+"_JSON_INVALID")
 return evaluate(docs["manifest"],docs["catalog"])

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
