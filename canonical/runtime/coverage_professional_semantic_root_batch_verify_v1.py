"""Generic semantic verifier for one active claim/root from the 12-claim batch proof.

One shared proof-compression certificate is allowed, but authority is still
strictly indexed by the active frozen claim and requested canonical root.
The batch proof is rerun on current bytes.  No claim can consume another
claim's root status because the selected row must match the active claim's
exact claim/scope/target/semantics binding.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime import professional_semantic_root_batch_prover_v1 as batch

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_ROOT_BATCH_VERIFY_V1"
CERT_PATH="canonical/governance/PROFESSIONAL_SEMANTIC_ROOT_BATCH_CERTIFICATE_20261011_V1.json"
CERT_BLOB="0ec9887037bcaefb0791aea8ffbcde6014cd3a28"
INDEPENDENT_PATH="canonical/verification/PROFESSIONAL_SEMANTIC_ROOT_BATCH_INDEPENDENT_VERIFY_20261011_V1.json"
INDEPENDENT_BLOB="fafc9c4686904544fe6608e51aa51b878e985dd5"
EXPECTED_BATCH_RESULT_SHA256="430b888c3499f08a8fd1be294dbbfb643f3047707fc7502db882d6a6ca5b696e"
ROOT_FIELD={
 "CC_R1_REALITY_CONTAINMENT_V1":"cc_r1_reality_containment_proved",
 "CC_R2_MISSION_SOUNDNESS_V1":"cc_r2_mission_soundness_proved",
 "CC_R3_TERMINAL_CLOSURE_V1":"cc_r3_terminal_closure_proved",
}

def _blob(p:Path)->str:
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _digest(v:Any)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _fail(root_id:str,claim_id:str,reason:str)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "root_id":root_id,"claim_id":claim_id,"semantic_claim_verified":False,
  "r4_proof_realization_authority":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0}

def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 root=Path(root).resolve();cid=str(active_claim.get("claim_id") or "")
 if root_id not in ROOT_FIELD:return _fail(root_id,cid,"ROOT_ID_UNSUPPORTED")
 cp=Path(certificate_path)
 try:
  if cp.resolve()!=(root/CERT_PATH).resolve():return _fail(root_id,cid,"CERTIFICATE_PATH_NOT_BATCH_CERT")
  if not cp.is_file() or cp.is_symlink() or _blob(cp)!=CERT_BLOB:return _fail(root_id,cid,"CERTIFICATE_BLOB_INVALID")
  cert=json.loads(cp.read_text(encoding="utf-8"))
 except Exception:return _fail(root_id,cid,"CERTIFICATE_INVALID")
 if cert.get("proof_mode")!="FORMAL_REDUCTION":return _fail(root_id,cid,"CERTIFICATE_PROOF_MODE_DRIFT")
 if root_id not in (cert.get("supported_root_ids") or []):return _fail(root_id,cid,"CERTIFICATE_ROOT_NOT_SUPPORTED")
 for k in ("semantic_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if cert.get(k) is not False:return _fail(root_id,cid,"CERTIFICATE_AUTHORITY_OVERCLAIM:"+k)
 ip=root/INDEPENDENT_PATH
 try:
  if not ip.is_file() or ip.is_symlink() or _blob(ip)!=INDEPENDENT_BLOB:return _fail(root_id,cid,"INDEPENDENT_BATCH_RECEIPT_STALE")
  iv=json.loads(ip.read_text(encoding="utf-8"))
 except Exception:return _fail(root_id,cid,"INDEPENDENT_BATCH_RECEIPT_INVALID")
 if iv.get("status")!="PASS__INDEPENDENT_SPRITE__12_OF_12_CC_R1_CC_R2_CC_R3__R4_PER_CLAIM_OPEN__ZERO_PROPERTY_OR_TERMINAL_CREDIT":
  return _fail(root_id,cid,"INDEPENDENT_BATCH_RECEIPT_NOT_PASS")
 if (iv.get("independent_replay") or {}).get("result_sha256")!=EXPECTED_BATCH_RESULT_SHA256:
  return _fail(root_id,cid,"INDEPENDENT_BATCH_RESULT_HASH_DRIFT")

 out=batch.verify(repo_root=root)
 if out.get("pass") is not True:return _fail(root_id,cid,"BATCH_RERUN_REJECTED")
 if _digest(out)!=EXPECTED_BATCH_RESULT_SHA256:return _fail(root_id,cid,"BATCH_RERUN_RESULT_HASH_MISMATCH")
 rows=[x for x in out.get("rows") or [] if isinstance(x,Mapping) and x.get("claim_id")==cid]
 if len(rows)!=1:return _fail(root_id,cid,"ACTIVE_CLAIM_NOT_UNIQUE_IN_BATCH")
 row=rows[0]
 for k in ("scope_sha256","target_predicate_sha256","semantics_sha256"):
  if row.get(k)!=active_claim.get(k):return _fail(root_id,cid,"ACTIVE_CLAIM_BINDING_MISMATCH:"+k)
 if active_claim.get("mission_blob_sha")!=batch.MISSION_BLOB:return _fail(root_id,cid,"ACTIVE_CLAIM_MISSION_DRIFT")
 if active_claim.get("claim_kind")!="PROPERTY_CERTIFICATE":return _fail(root_id,cid,"ACTIVE_CLAIM_KIND_DRIFT")
 if row.get(ROOT_FIELD[root_id]) is not True:return _fail(root_id,cid,"REQUESTED_ROOT_NOT_PROVED")
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__ACTIVE_CLAIM_ROOT_SELECTED_FROM_RERUN_12_CLAIM_BATCH_PROOF",
  "root_id":root_id,"claim_id":cid,"semantic_claim_verified":True,
  "proof_mode":"FORMAL_REDUCTION","batch_result_sha256":EXPECTED_BATCH_RESULT_SHA256,
  "claim_specific_selection":True,"cross_claim_transport":False,
  ROOT_FIELD[root_id]:True,
  "r4_proof_realization_authority":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0}
