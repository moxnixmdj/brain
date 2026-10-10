"""V10 professional property-truth ledger.

Combines two independently governed evidence lanes without weakening either:

1. Execution lane: the independently replayed legacy Binder V2 result proves
   all twelve execution leaves. The V2 semantic truth repair explicitly changed
   zero execution leaves and zero root contracts; this runtime additionally
   compares those old/new execution identities byte-semantically before reuse.
2. Semantic lane: only current V10 truth-repaired semantic receipts admitted by
   Binder V3 count.

The ledger grants no global quality/acceptance/promotion/terminal authority
until all 24 leaves are verified. It is a counting/integration authority only.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_semantic_admission_binder_v3 as semantic_binder
from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as claim_batch

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_V10_PROPERTY_TRUTH_LEDGER_V1"

OLD_MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
OLD_MANIFEST_BLOB="a7cad32c9fd969ff2c3857bb924c7bd746237ec2"
EXEC_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_LEAF_REGISTRY_PROPERTY_TRUTH_VERIFY_20261010_V9.json"
EXEC_VERIFY_BLOB="0650125baac22d5c424021915fef51c170dd1e4c"
NEW_MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
NEW_MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"
SEMANTIC_REGISTRY_PATH="canonical/governance/PROFESSIONAL_QUALITY_V10_SEMANTIC_EVIDENCE_REGISTRY_20261011_V1.json"
SEMANTIC_REGISTRY_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_V10_SEMANTIC_EVIDENCE_REGISTRY_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_VERIFICATION_RECEIPT_V1"


def _blob(path:Path)->str:
 raw=path.read_bytes();return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def _load(root:Path,rel:str,expected:str|None=None)->Mapping[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink(): raise ValueError("PIN_MISSING:"+rel)
 if expected is not None:
  got=_blob(p)
  if got!=expected: raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)
 obj=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(obj,Mapping): raise ValueError("PIN_NOT_OBJECT:"+rel)
 return obj


def _safe_entry(root:Path,entry:Any)->tuple[Mapping[str,Any]|None,str|None]:
 if not isinstance(entry,Mapping): return None,"REGISTRY_ENTRY_NOT_OBJECT"
 rel=entry.get("path");decl=entry.get("git_blob_sha")
 if not isinstance(rel,str) or not rel.startswith("canonical/") or ".." in Path(rel).parts:
  return None,"REGISTRY_ENTRY_PATH_INVALID"
 try: doc=_load(root,rel,str(decl))
 except Exception as exc: return None,type(exc).__name__+":"+str(exc)
 return doc,None


def _zero()->dict[str,Any]:
 return {
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }


def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "verified_execution_leaf_ids":[],"verified_semantic_leaf_ids":[],
  "verified_leaf_count":0,"open_leaf_count":24,"promotion_ready":False,
  **_zero(),**extra}


def _rows_by_root(manifest:Mapping[str,Any])->dict[str,Mapping[str,Any]]:
 rows=manifest.get("roots") or []
 out={}
 for row in rows:
  if not isinstance(row,Mapping): continue
  rid=row.get("root_id")
  if isinstance(rid,str) and rid: out[rid]=row
 return out


def _execution_identity(row:Mapping[str,Any])->dict[str,Any]:
 leaf=row.get("execution_leaf") or {}
 return {
  "root_id":row.get("root_id"),
  "contract":row.get("contract"),
  "leaf_id":leaf.get("id"),
  "obligation":leaf.get("obligation"),
  "acceptance":leaf.get("acceptance"),
 }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  old=_load(root,OLD_MANIFEST_PATH,OLD_MANIFEST_BLOB)
  exec_verify=_load(root,EXEC_VERIFY_PATH,EXEC_VERIFY_BLOB)
  new=_load(root,NEW_MANIFEST_PATH,NEW_MANIFEST_BLOB)
  semreg=_load(root,SEMANTIC_REGISTRY_PATH,None)
 except Exception as exc:
  return _fail(type(exc).__name__+":"+str(exc))

 if new.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_V2":
  return _fail("NEW_MANIFEST_SCHEMA_INVALID")
 repair=new.get("semantic_contract_truth_repair") or {}
 if repair.get("execution_leaves_changed")!=0 or repair.get("root_contracts_changed")!=0:
  return _fail("TRUTH_REPAIR_CHANGED_EXECUTION_OR_ROOT_CONTRACT")

 oldrows=_rows_by_root(old);newrows=_rows_by_root(new)
 if len(oldrows)!=12 or len(newrows)!=12 or set(oldrows)!=set(newrows):
  return _fail("OLD_NEW_ROOT_SET_DRIFT")
 execution_ids=[]
 for rid in sorted(newrows):
  if _execution_identity(oldrows[rid])!=_execution_identity(newrows[rid]):
   return _fail("EXECUTION_IDENTITY_DRIFT:"+rid)
  execution_ids.append(str((newrows[rid].get("execution_leaf") or {}).get("id")))

 if not str(exec_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
  return _fail("EXECUTION_INDEPENDENT_VERIFY_NOT_PASS")
 replay=exec_verify.get("independent_replay") or {}
 direct=replay.get("direct_registry_v2_eval") or {}
 if (
  replay.get("py_compile")!="PASS"
  or replay.get("tests_failed")!=0
  or direct.get("existing_evidence_current") is not True
  or direct.get("structural_errors")!=[]
  or direct.get("rejected_receipt_count")!=0
  or direct.get("verified_execution_leaf_count")!=12
  or direct.get("open_execution_leaf_count")!=0
  or direct.get("verified_semantic_leaf_count")!=0
 ):
  return _fail("EXECUTION_INDEPENDENT_REPLAY_NOT_EXACT_12_OF_12",execution_replay=direct)

 if semreg.get("schema")!=SEMANTIC_REGISTRY_SCHEMA:
  return _fail("SEMANTIC_REGISTRY_SCHEMA_INVALID")
 for key,path,blob in (
  ("manifest",NEW_MANIFEST_PATH,NEW_MANIFEST_BLOB),
  ("claim_batch","canonical/runtime/professional_semantic_v2_v10_claim_batch_v1.py","75fcbaf92a2b84b0d670ef7d784107590c5f1d08"),
  ("semantic_binder","canonical/runtime/professional_quality_semantic_admission_binder_v3.py","6e8e5ac7c4cf4cc38e5e7a6f0ad6a0c80f0683be"),
 ):
  ref=semreg.get(key) or {}
  if ref.get("path")!=path or ref.get("git_blob_sha")!=blob:
   return _fail("SEMANTIC_REGISTRY_"+key.upper()+"_BINDING_DRIFT")

 batch=claim_batch.verify(root=root)
 if batch.get("pass") is not True or batch.get("claim_count")!=12 or batch.get("scope_complete_count")!=12:
  return _fail("CURRENT_V10_CLAIM_BATCH_NOT_PASS",claim_batch=batch)
 claims={}
 for row in batch.get("rows") or []:
  if isinstance(row,Mapping) and isinstance(row.get("leaf_id"),str):
   claims[row["leaf_id"]]=row
 if len(claims)!=12:return _fail("CURRENT_V10_CLAIM_SET_NOT_EXACTLY_12")

 receipts=semreg.get("semantic_receipts")
 if not isinstance(receipts,Mapping):return _fail("SEMANTIC_RECEIPTS_NOT_OBJECT")
 unknown=sorted(set(receipts)-set(claims))
 if unknown:return _fail("UNKNOWN_SEMANTIC_LEAF_IDS",unknown_leaf_ids=unknown)

 semantic_verified=[];semantic_results=[];rejected=[]
 for leaf_id,entries in sorted(receipts.items()):
  if not isinstance(entries,list) or not entries:
   rejected.append({"leaf_id":leaf_id,"errors":["RECEIPT_LIST_EMPTY_OR_INVALID"]});continue
  claim=claims[leaf_id]
  rid=str(claim.get("root_id"))
  mrow=newrows.get(rid)
  if not isinstance(mrow,Mapping):
   rejected.append({"leaf_id":leaf_id,"errors":["MANIFEST_ROOT_ROW_MISSING"]});continue
  accepted=False
  local=[]
  for entry in entries:
   receipt,err=_safe_entry(root,entry)
   if receipt is None:
    result={"leaf_id":leaf_id,"pass":False,"errors":[err]}
   else:
    if receipt.get("schema")!=RECEIPT_SCHEMA:
     result={"leaf_id":leaf_id,"pass":False,"errors":["RECEIPT_SCHEMA_INVALID"]}
    else:
     result=semantic_binder.validate_semantic_receipt(
      receipt,
      claim["claim_scope"],
      leaf_id=leaf_id,
      root_id=rid,
      acceptance=(mrow.get("semantic_leaf") or {}).get("acceptance") or "",
      contract=mrow.get("contract") or "",
      manifest_git_blob_sha=NEW_MANIFEST_BLOB,
      repo_root=root,
     )
   local.append(result)
   if result.get("pass") is True and result.get("positive_semantic_admission_authorized") is True:
    accepted=True
  semantic_results.append({"leaf_id":leaf_id,"attempts":local,"admitted":accepted})
  if accepted: semantic_verified.append(leaf_id)
  else: rejected.append({"leaf_id":leaf_id,"errors":["NO_CURRENT_V10_SEMANTIC_RECEIPT_ADMITTED"]})

 all_semantic_ids=sorted(claims)
 open_semantic=sorted(set(all_semantic_ids)-set(semantic_verified))
 verified=sorted(execution_ids)+sorted(semantic_verified)
 promotion_ready=len(verified)==24 and not rejected
 return {
  "schema":SCHEMA,
  "pass":True,
  "status":(
   "PASS__ALL_24_PROPERTY_LEAVES_VERIFIED"
   if promotion_ready else
   "PASS__PARTIAL_V10_PROPERTY_TRUTH_LEDGER__ZERO_GLOBAL_AUTHORITY"
  ),
  "verified_execution_leaf_ids":sorted(execution_ids),
  "verified_semantic_leaf_ids":sorted(semantic_verified),
  "open_semantic_leaf_ids":open_semantic,
  "open_execution_leaf_ids":[],
  "verified_execution_leaf_count":12,
  "verified_semantic_leaf_count":len(semantic_verified),
  "open_execution_leaf_count":0,
  "open_semantic_leaf_count":len(open_semantic),
  "verified_leaf_count":len(verified),
  "open_leaf_count":24-len(verified),
  "semantic_receipt_results":semantic_results,
  "rejected_semantic_receipt_count":len(rejected),
  "rejected_semantic_receipts":rejected,
  "execution_identity_transport_proved":True,
  "semantic_truth_repair_execution_delta_zero":True,
  "promotion_ready":promotion_ready,
  **_zero(),
 }
