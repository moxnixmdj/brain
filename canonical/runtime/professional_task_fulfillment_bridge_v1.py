"""Professional task-fulfillment bridge V1.

Bounded evidence composer for one exact professional task/output pair.

Positive authorization requires:
* a content-addressed obligation-scope certificate;
* a separate independent verification receipt for that exact scope certificate;
* one independently verified semantic-satisfaction receipt for every required
  obligation, all bound to the same exact task and realized artifact.

Caller booleans and checklists have zero completeness authority. This module
grants no global quality, owner-evaluator, GDPval, acceptance, promotion, or
terminal authority.
"""
from __future__ import annotations

from hashlib import sha1,sha256
import json
from pathlib import Path
from string import hexdigits
from typing import Any,Mapping

from canonical.runtime import universal_scope_closure_compiler_v1 as scope_compiler

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_TASK_FULFILLMENT_BRIDGE_V1"
SCOPE_VERIFY_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_TASK_OBLIGATION_SCOPE_INDEPENDENT_VERIFY_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_TASK_OBLIGATION_SEMANTIC_RECEIPT_V1"
VERIFY_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_TASK_OBLIGATION_SEMANTIC_VERIFY_V1"
BOUND_PREFIXES=("canonical/governance/","canonical/evidence/","canonical/verification/")
VERIFY_PREFIXES=("canonical/verification/",)
SCOPE_COMPILER_PATH="canonical/runtime/universal_scope_closure_compiler_v1.py"
SCOPE_COMPILER_BLOB="b208255789b14e44e86c82c196e06b5c41b3d039"


def _canon(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _sha(text:str)->str:
    return sha256(text.encode("utf-8")).hexdigest()


def _is_sha256(value:Any)->bool:
    return isinstance(value,str) and len(value)==64 and all(c in hexdigits for c in value)


def git_blob_sha(path:Path)->str:
    data=path.read_bytes()
    return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def obligation_universe_digest(obligations:Any)->str:
    if not isinstance(obligations,list): raise ValueError("OBLIGATIONS_NOT_LIST")
    rows=[];seen=set()
    for i,row in enumerate(obligations):
        if not isinstance(row,Mapping): raise ValueError(f"OBLIGATION_NOT_MAPPING:{i}")
        oid=str(row.get("obligation_id") or "").strip()
        semantics=str(row.get("semantics") or "").strip()
        if not oid: raise ValueError(f"OBLIGATION_ID_MISSING:{i}")
        if oid in seen: raise ValueError("OBLIGATION_ID_DUPLICATE:"+oid)
        if not semantics: raise ValueError("OBLIGATION_SEMANTICS_MISSING:"+oid)
        if row.get("required") is not True: raise ValueError("OBLIGATION_NOT_REQUIRED:"+oid)
        seen.add(oid)
        rows.append({"obligation_id":oid,"semantics_sha256":_sha(semantics),"required":True})
    if not rows: raise ValueError("OBLIGATIONS_EMPTY")
    rows.sort(key=lambda x:x["obligation_id"])
    return _sha(_canon(rows))


def task_scope_id(*,task_id:str,task_sha256:str,obligation_digest:str)->str:
    return "scope://professional-task-fulfillment/"+_sha(_canon({
      "task_id":task_id,"task_sha256":task_sha256,
      "obligation_universe_digest":obligation_digest,
    }))


def _bound_json(root:Path,ref:Any,prefixes:tuple[str,...])->tuple[dict[str,Any],str,str]:
    if not isinstance(ref,Mapping): raise ValueError("BOUND_REF_REQUIRED")
    rel=str(ref.get("path") or "").strip();expected=str(ref.get("git_blob_sha") or "").strip()
    p=Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts: raise ValueError("BOUND_PATH_INVALID")
    if not any(rel.startswith(x) for x in prefixes): raise ValueError("BOUND_PATH_OUTSIDE_ALLOWED_SCOPE")
    base=root.resolve(strict=True);full=base/p;resolved=full.resolve(strict=False)
    if not any(resolved.is_relative_to((base/x).resolve(strict=False)) for x in prefixes):
        raise ValueError("BOUND_RESOLVED_PATH_OUTSIDE_ALLOWED_SCOPE")
    if not full.is_file() or full.is_symlink(): raise ValueError("BOUND_FILE_INVALID:"+rel)
    actual=git_blob_sha(full)
    if actual!=expected: raise ValueError("BOUND_BLOB_DRIFT:"+rel)
    doc=json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(doc,dict): raise ValueError("BOUND_JSON_NOT_OBJECT:"+rel)
    return doc,rel,actual


def _base(status:str,passed:bool,**extra:Any)->dict[str,Any]:
    return {
      "schema":SCHEMA,"status":status,"pass":passed,
      "positive_task_fulfillment_authorized":passed,
      "scope_complete":False,"obligation_count":0,"verified_obligation_count":0,
      "quality_authority":False,"owner_evaluator_authority":False,
      "acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"gdpval_credit_delta":0,
      "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }


def verify(bundle:Any,*,repo_root:str|Path)->dict[str,Any]:
    if not isinstance(bundle,Mapping):
        return _base("FAIL_CLOSED",False,errors=["BUNDLE_NOT_MAPPING"])
    try:
        task=bundle.get("task")
        if not isinstance(task,Mapping): raise ValueError("TASK_NOT_MAPPING")
        task_id=str(task.get("task_id") or "").strip()
        task_sha=str(task.get("task_sha256") or "").strip()
        artifact_sha=str(bundle.get("artifact_sha256") or "").strip()
        if not task_id: raise ValueError("TASK_ID_REQUIRED")
        if not _is_sha256(task_sha): raise ValueError("TASK_SHA256_INVALID")
        if not _is_sha256(artifact_sha): raise ValueError("ARTIFACT_SHA256_INVALID")
        obligations=task.get("obligations")
        digest=obligation_universe_digest(obligations)
        expected_scope=task_scope_id(task_id=task_id,task_sha256=task_sha,obligation_digest=digest)

        root=Path(repo_root)
        scope_compiler_file=root/SCOPE_COMPILER_PATH
        if not scope_compiler_file.is_file() or scope_compiler_file.is_symlink():
            raise ValueError("SCOPE_COMPILER_FILE_INVALID")
        if git_blob_sha(scope_compiler_file)!=SCOPE_COMPILER_BLOB:
            raise ValueError("SCOPE_COMPILER_BLOB_DRIFT")
        scope_binding=task.get("obligation_scope_binding")
        if not isinstance(scope_binding,Mapping): raise ValueError("OBLIGATION_SCOPE_BINDING_REQUIRED")
        scope_cert,scope_path,scope_blob=_bound_json(root,scope_binding.get("certificate"),BOUND_PREFIXES)
        scope_verify,scope_verify_path,scope_verify_blob=_bound_json(root,scope_binding.get("verification"),VERIFY_PREFIXES)
        scope_out=scope_compiler.evaluate(scope_cert)
        if scope_out.get("scope_complete") is not True: raise ValueError("OBLIGATION_SCOPE_NOT_COMPLETE")
        if scope_out.get("target_scope_id")!=expected_scope: raise ValueError("OBLIGATION_SCOPE_TARGET_MISMATCH")
        if scope_cert.get("obligation_universe_digest")!=digest:
            raise ValueError("OBLIGATION_SCOPE_DIGEST_MISMATCH")
        if scope_cert.get("basis")=="EXACT_COMPLETE_TARGET_CASE_UNIVERSE" and scope_cert.get("case_universe_digest")!=digest:
            raise ValueError("OBLIGATION_EXACT_CASE_UNIVERSE_DIGEST_MISMATCH")
        scope_producer=str(scope_cert.get("producer_id") or "").strip()
        if not scope_producer: raise ValueError("OBLIGATION_SCOPE_PRODUCER_REQUIRED")
        expected_scope_verify={
          "schema":SCOPE_VERIFY_SCHEMA,"subject_git_blob_sha":scope_blob,
          "task_id":task_id,"task_sha256":task_sha,
          "obligation_universe_digest":digest,"target_scope_id":expected_scope,
          "scope_complete":True,"pass":True,"independent_verified":True,
          "scope_complete_verified":True,
        }
        for field,expected in expected_scope_verify.items():
            if scope_verify.get(field)!=expected:
                raise ValueError("OBLIGATION_SCOPE_VERIFY_FIELD_MISMATCH:"+field)
        scope_verifier=str(scope_verify.get("independent_verifier_id") or "").strip()
        if not scope_verifier: raise ValueError("OBLIGATION_SCOPE_VERIFIER_REQUIRED")
        if scope_verifier==scope_producer:
            raise ValueError("OBLIGATION_SCOPE_PRODUCER_VERIFIER_NOT_INDEPENDENT")

        bindings=bundle.get("obligation_bindings")
        if not isinstance(bindings,list): raise ValueError("OBLIGATION_BINDINGS_NOT_LIST")
        by_id={}
        for i,row in enumerate(bindings):
            if not isinstance(row,Mapping): raise ValueError(f"OBLIGATION_BINDING_NOT_MAPPING:{i}")
            oid=str(row.get("obligation_id") or "").strip()
            if not oid: raise ValueError(f"OBLIGATION_BINDING_ID_MISSING:{i}")
            if oid in by_id: raise ValueError("OBLIGATION_BINDING_DUPLICATE:"+oid)
            by_id[oid]=row
        required_ids={str(x["obligation_id"]) for x in obligations}
        if set(by_id)!=required_ids:
            missing=sorted(required_ids-set(by_id));extra=sorted(set(by_id)-required_ids)
            if missing: raise ValueError("OBLIGATION_BINDINGS_MISSING:"+",".join(missing))
            raise ValueError("UNDECLARED_OBLIGATION_BINDINGS:"+",".join(extra))

        verified=[]
        for obligation in obligations:
            oid=str(obligation["obligation_id"]);sem_hash=_sha(str(obligation["semantics"]))
            binding=by_id[oid]
            receipt,rpath,rblob=_bound_json(root,binding.get("receipt"),BOUND_PREFIXES)
            verification,vpath,vblob=_bound_json(root,binding.get("verification"),VERIFY_PREFIXES)
            expected_receipt={
              "schema":RECEIPT_SCHEMA,"task_id":task_id,"task_sha256":task_sha,
              "artifact_sha256":artifact_sha,"obligation_id":oid,
              "obligation_semantics_sha256":sem_hash,"obligation_universe_digest":digest,
              "target_scope_id":expected_scope,"verdict":"PASS","semantic_satisfaction_proved":True,
            }
            for field,expected in expected_receipt.items():
                if receipt.get(field)!=expected:
                    raise ValueError("OBLIGATION_RECEIPT_FIELD_MISMATCH:"+oid+":"+field)
            producer=str(receipt.get("producer_id") or "").strip()
            evidence_sha=str(receipt.get("evidence_sha256") or "").strip()
            if not producer: raise ValueError("OBLIGATION_RECEIPT_PRODUCER_REQUIRED:"+oid)
            if not _is_sha256(evidence_sha): raise ValueError("OBLIGATION_RECEIPT_EVIDENCE_SHA_INVALID:"+oid)
            expected_verify={
              "schema":VERIFY_SCHEMA,"subject_git_blob_sha":rblob,"task_id":task_id,
              "task_sha256":task_sha,"artifact_sha256":artifact_sha,"obligation_id":oid,
              "obligation_semantics_sha256":sem_hash,"obligation_universe_digest":digest,
              "target_scope_id":expected_scope,"evidence_sha256":evidence_sha,
              "pass":True,"independent_verified":True,"semantic_satisfaction_verified":True,
            }
            for field,expected in expected_verify.items():
                if verification.get(field)!=expected:
                    raise ValueError("OBLIGATION_VERIFY_FIELD_MISMATCH:"+oid+":"+field)
            verifier=str(verification.get("independent_verifier_id") or "").strip()
            if not verifier: raise ValueError("OBLIGATION_VERIFIER_REQUIRED:"+oid)
            if verifier==producer: raise ValueError("OBLIGATION_PRODUCER_VERIFIER_NOT_INDEPENDENT:"+oid)
            verified.append({
              "obligation_id":oid,"receipt_path":rpath,"receipt_git_blob_sha":rblob,
              "verification_path":vpath,"verification_git_blob_sha":vblob,
              "evidence_sha256":evidence_sha,"producer_id":producer,
              "independent_verifier_id":verifier,
            })

        return _base(
          "PASS__CONTENT_ADDRESSED_SCOPE_AND_ALL_TASK_OBLIGATION_SEMANTICS_BOUND",True,
          errors=[],task_id=task_id,task_sha256=task_sha,artifact_sha256=artifact_sha,
          target_scope_id=expected_scope,obligation_universe_digest=digest,
          scope_complete=True,scope_basis=scope_out.get("basis"),
          scope_certificate_path=scope_path,scope_certificate_git_blob_sha=scope_blob,
          scope_verification_path=scope_verify_path,scope_verification_git_blob_sha=scope_verify_blob,
          scope_producer_id=scope_producer,scope_independent_verifier_id=scope_verifier,
          scope_compiler_path=SCOPE_COMPILER_PATH,scope_compiler_git_blob_sha=SCOPE_COMPILER_BLOB,
          obligation_count=len(obligations),verified_obligation_count=len(verified),
          obligation_receipts=verified,
          hard_boundary=[
            "NO_CALLER_CHECKLIST_OR_SCOPE_BOOLEAN_SELF_CERTIFICATION",
            "NO_OWNER_EVALUATOR_CONTAINMENT","NO_HOLISTIC_PRESENTATION_TOP",
            "NO_GLOBAL_PROFESSIONAL_COVERAGE","NO_GDPVAL_SCORE_OR_BRAIN_GE_OPUS_CLAIM",
          ],
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",False,errors=[type(exc).__name__+":"+str(exc)])
