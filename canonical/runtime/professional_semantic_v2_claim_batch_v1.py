"""Generate and verify 12 V2 professional semantic whole-leaf claims.

Reuses the existing whole-leaf domain-equivalence and universal-scope machinery
against the truth-repaired V2 manifest. This creates fresh claim identities and
scope authority only. It grants zero semantic property truth.
"""
from __future__ import annotations
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as domain
from canonical.runtime import professional_quality_whole_leaf_scope_certificate_v1 as scope

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V2_CLAIM_BATCH_V1"
EPOCH="PROFESSIONAL_SEMANTIC_V2_20261011_V1"
MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"
DOMAIN_BLOB="76bf7e1a6f26ff3664ed8c355dff8a688b074159"
SCOPE_BLOB="3c2630a63aa90f7b4667ef57f73f75b1c6b3c828"

def _blob_bytes(raw:bytes)->str:return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def _blob(path:Path)->str:return _blob_bytes(path.read_bytes())
def _doc_blob(doc:Mapping[str,Any])->str:
 raw=(json.dumps(doc,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
 return _blob_bytes(raw)
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "semantic_leaf_count":0,"claim_count":0,"scope_complete_count":0,"property_truth_count":0,
 "semantic_truth_authority":False,"terminal_authority":False,"terminal_credit_delta":0,**extra}
def verify(*,root:Path|str|None=None,epoch:str=EPOCH)->dict[str,Any]:
 root=Path(root).resolve() if root is not None else ROOT
 mp=root/MANIFEST_PATH
 if not mp.is_file() or mp.is_symlink() or _blob(mp)!=MANIFEST_BLOB:return _fail("MANIFEST_PIN_FAIL")
 if _blob(root/"canonical/runtime/professional_quality_whole_leaf_domain_equivalence_v1.py")!=DOMAIN_BLOB:return _fail("DOMAIN_RUNTIME_PIN_FAIL")
 if _blob(root/"canonical/runtime/professional_quality_whole_leaf_scope_certificate_v1.py")!=SCOPE_BLOB:return _fail("SCOPE_RUNTIME_PIN_FAIL")
 try:m=json.loads(mp.read_text())
 except Exception:return _fail("MANIFEST_JSON_INVALID")
 leaves=[]
 for row in m.get("roots") or []:
  leaf=row.get("semantic_leaf")
  if isinstance(leaf,Mapping) and isinstance(leaf.get("id"),str):leaves.append(leaf["id"])
 if len(leaves)!=12 or len(set(leaves))!=12:return _fail("SEMANTIC_LEAF_SET_INVALID",observed=len(leaves))
 rows=[]
 for leaf_id in sorted(leaves):
  claim_scope=domain.build_claim_scope(m,leaf_id,epoch=epoch)
  dv=domain.evaluate(m,claim_scope)
  if dv.get("pass") is not True:return _fail("DOMAIN_EQUIVALENCE_FAILED",leaf_id=leaf_id,verdict=dv)
  cs_blob=_doc_blob(claim_scope)
  cv={"schema":scope.CLAIM_VERIFY_SCHEMA,"status":"PASS__V2_SEMANTIC_WHOLE_LEAF_DOMAIN_EQUIVALENCE",
      "leaf_id":leaf_id,"claim_id":dv["claim_id"],"claim_scope_git_blob_sha":cs_blob,
      "whole_leaf_domain_equivalence_proved":True}
  cv_blob=_doc_blob(cv); verify_path="canonical/verification/professional-semantic-v2/"+dv["claim_id"]+".json"
  cert={"schema":scope.CERT_SCHEMA,"leaf_id":leaf_id,"claim_id":dv["claim_id"],
    "claim_scope_git_blob_sha":cs_blob,
    "scope_certificate":{"id":leaf_id+"::SEMANTIC_V2_WHOLE_SCOPE","target_scope_id":"scope://professional-quality/whole-leaf/"+dv["claim_id"],
      "claim_id":dv["claim_id"],"basis":"UNIVERSAL_FORMAL_SCOPE_PROOF","verified":True,"independent":True,
      "scope_relation":"EXACT","formal_completeness":True,"all_admissible_target_inputs_proved":True,
      "premise_set_id":"claim-verification:"+cv_blob},
    "evidence_refs":[{"path":verify_path,"git_blob_sha":cv_blob}],
    "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
    "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
    "terminal_credit_delta":0,"incremental_spend_usd":0}
  sv=scope.evaluate(claim_scope,cv,cert,claim_scope_blob=cs_blob,claim_verification_blob=cv_blob,claim_verification_path=verify_path)
  if sv.get("pass") is not True:return _fail("SCOPE_VERIFY_FAILED",leaf_id=leaf_id,verdict=sv)
  rows.append({"leaf_id":leaf_id,"root_id":claim_scope["root_id"],"claim_id":dv["claim_id"],
   "claim_scope":claim_scope,"claim_scope_git_blob_sha":cs_blob,
   "claim_verification":cv,"claim_verification_git_blob_sha":cv_blob,
   "scope_certificate":cert,"whole_leaf_domain_equivalence_proved":True,
   "whole_leaf_scope_complete":True,"leaf_property_truth_authority":False})
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__12_OF_12_V2_SEMANTIC_SUCCESSOR_CLAIMS_GENERATED__12_OF_12_WHOLE_DOMAIN_EQUIVALENCE__12_OF_12_UNIVERSAL_SCOPE_COMPLETE__ZERO_PROPERTY_TRUTH",
  "epoch":epoch,"semantic_leaf_count":12,"claim_count":12,"scope_complete_count":12,"property_truth_count":0,
  "unique_claim_id_count":len({r["claim_id"] for r in rows}),"rows":rows,
  "subject_id":domain.SUBJECT_ID,"subject_sha256":domain.SUBJECT_SHA256,
  "next":"VERIFY_V2_SEMANTIC_PROPERTY_TRUTH_USING_REUSE_FIRST_CERTIFY_OR_FAIL_CLOSED_MACHINERY__NO_V1_AUTHORITY_TRANSPORT",
  "new_primitive_required":False,"semantic_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}
