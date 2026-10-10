"""Fail-closed verifier for R7 causal/prescriptive binding on the frozen V7 professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R7_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R7_CAUSAL_PRESCRIPTIVE"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R7_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="d1b4af80e94048ec4093192d2b8203d47eff56ed"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
REPAIRED_RUNTIME_PATH="canonical/runtime/assurance_closure_compiler_v1.py"
REPAIRED_RUNTIME_BLOB="b4274a48edbe626a9ae9fd33da2f2227ca4dd5e8"
PREDECESSOR_RUNTIME_BLOB="a52d62d63aeb50a6bbb613c37ec76d1c86327b12"
TEST_BLOB="0eba4d1cd42d62a9a6e13830804223300e290e68"
REFS={
 "causal_scope":("canonical/governance/PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CLAIM_SCOPE_20261009_V1.json","cc86ad5c442366d772c51491dbb98615982f5896"),
 "causal_scope_verification":("canonical/verification/PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CLAIM_SCOPE_VERIFY_20261009_V1.json","761fade0036ab56e4db65fbb61619b04f8acadae"),
 "causal_instance":("canonical/verification/PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_VERIFY_20261009_V1.json","0c692f55dedb6a8523bcd78541d4cb77ef06d610"),
 "causal_compiler_verification":("canonical/verification/PROFESSIONAL_EDIT_CAUSAL_CERTIFICATE_VERIFY_20261010_V1.json","380d26afd8210096e397dacde3f2a339abc75c1c"),
}
REQUIRED_GUARANTEES={
 "EXACT_V7_SUBJECT_TUPLE_BOUND",
 "V7_SUBJECT_CONTAINS_THE_EXACT_REPAIRED_ASSURANCE_CLOSURE_COMPILER_BLOB",
 "PREDECESSOR_AND_REPAIRED_RUNTIME_BLOBS_ARE_CONTENT_ADDRESSED_AND_DISTINCT",
 "THE_IDENTICAL_REGRESSION_TEST_BYTES_FAIL_ON_PREDECESSOR_AND_PASS_ON_REPAIRED_RUNTIME",
 "THE_CAUSAL_CLAIM_SCOPE_IS_ONE_ATOMIC_WHOLE_PATCH_INSTANCE",
 "C28_PREDICTIVE_PRESCRIPTIVE_GAP_IS_DISCHARGED_FOR_THIS_EXACT_INSTANCE",
 "C30_TREATMENT_VERSION_NONINVARIANCE_IS_DISCHARGED_FOR_THIS_EXACT_INSTANCE",
 "C29_COMPOUND_EDIT_ATTRIBUTION_IS_OUTSIDE_THIS_SINGLE_EDIT_CLAIM",
 "C31_SEQUENCE_INTERACTION_IS_OUTSIDE_THIS_SINGLE_EDIT_CLAIM",
 "REUSABLE_CAUSAL_CERTIFICATE_COMPILER_ACCEPTS_ONLY_EXACT_SINGLE_EDIT_FAIL_TO_PASS_CONTENT_ADDRESSED_RECEIPTS",
}
REQUIRED_LIMITS={
 "NO_GLOBAL_R7_ROOT_CLOSURE","NO_GENERAL_PROFESSIONAL_EDIT_CAUSALITY",
 "NO_MULTI_EDIT_ATTRIBUTION","NO_SEQUENCE_INVARIANCE","NO_TREATMENT_VERSION_GENERALIZATION",
 "NO_DOMAIN_SEMANTIC_OR_EXECUTION_CLOSURE","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION",
}

def _blob(p:Path)->str:
    d=p.read_bytes(); return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def _read(root:Path,path:str,sha:str):
    p=(root/path).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return None,"OUTSIDE_ROOT:"+path
    if not p.is_file() or p.is_symlink():return None,"FILE_INVALID:"+path
    if _blob(p)!=sha:return None,"BLOB_STALE:"+path
    try:d=json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None,"JSON_INVALID:"+path
    return (d,None) if isinstance(d,dict) else (None,"DOCUMENT_INVALID:"+path)
def _fail(reason:str,**extra:Any):
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,"root_id":ROOT_ID,
      "root_subject_binding_authority":False,"global_r7_root_closed":False,
      "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}
def _components(subject:Mapping[str,Any]):
    return {(x.get("path"),x.get("git_blob_sha")) for x in ((subject.get("system_material") or {}).get("components") or []) if isinstance(x,Mapping)}

def evaluate_documents(binding:Mapping[str,Any],subject:Mapping[str,Any],docs:Mapping[str,Mapping[str,Any]]):
    if binding.get("schema")!=BINDING_SCHEMA or binding.get("root_id")!=ROOT_ID:return _fail("BINDING_IDENTITY_INVALID")
    if (binding.get("subject_kind"),binding.get("subject_id"),binding.get("subject_sha256"))!=("DECLARED_SYSTEM",SUBJECT_ID,SUBJECT_SHA):
        return _fail("SUBJECT_TUPLE_MISMATCH")
    if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA:return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
    if (REPAIRED_RUNTIME_PATH,REPAIRED_RUNTIME_BLOB) not in _components(subject):return _fail("REPAIRED_CAUSAL_TARGET_NOT_IN_V7_SUBJECT")
    for f in ("global_subject_identity_authority","root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
        if binding.get(f) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN",field=f)
    if binding.get("exact_subject_component_intervention_bound") is not True:return _fail("EXACT_COMPONENT_INTERVENTION_FLAG_MISSING")
    refs=binding.get("bridge_evidence") or {}
    for key,(path,sha) in REFS.items():
        row=refs.get(key)
        if not isinstance(row,Mapping) or row.get("path")!=path or row.get("git_blob_sha")!=sha:return _fail("BRIDGE_REF_MISMATCH",ref=key)

    scope=docs["causal_scope"]
    ss=scope.get("scope") or {}
    if ss.get("root_id")!=ROOT_ID or ss.get("claim_scope_kind")!="EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE":
        return _fail("CAUSAL_SCOPE_IDENTITY_INVALID")
    if ss.get("artifact_path")!=REPAIRED_RUNTIME_PATH:return _fail("CAUSAL_ARTIFACT_PATH_MISMATCH")
    if ss.get("predecessor_runtime_git_blob_sha")!=PREDECESSOR_RUNTIME_BLOB:return _fail("PREDECESSOR_BLOB_MISMATCH")
    if ss.get("repaired_runtime_git_blob_sha")!=REPAIRED_RUNTIME_BLOB:return _fail("REPAIRED_BLOB_MISMATCH")
    if ss.get("regression_test_git_blob_sha")!=TEST_BLOB:return _fail("REGRESSION_TEST_BLOB_MISMATCH")
    semantics=scope.get("semantics") or {}
    if semantics.get("treatment_cardinality")!=1 or semantics.get("global_r7_root_closed") is not False:return _fail("CAUSAL_SCOPE_WIDENING_FORBIDDEN")

    sv=docs["causal_scope_verification"]
    if not str(sv.get("status") or "").startswith("PASS__"):return _fail("CAUSAL_SCOPE_VERIFY_NOT_PASS")
    if (sv.get("conclusion") or {}).get("claim_sound_for_exact_scope") is not True:return _fail("CAUSAL_SCOPE_SOUNDNESS_UNPROVED")
    if (sv.get("conclusion") or {}).get("global_r7_root_closed") is not False:return _fail("CAUSAL_SCOPE_GLOBAL_OVERCLAIM")

    inst=docs["causal_instance"]
    if not str(inst.get("status") or "").startswith("PASS__REAL_PROFESSIONAL_CODE_EDIT_AB__OLD_FAIL_NEW_PASS"):return _fail("CAUSAL_INSTANCE_VERIFY_NOT_PASS")
    exact=inst.get("exact_subject") or {}
    if exact.get("predecessor_runtime_git_blob_sha")!=PREDECESSOR_RUNTIME_BLOB or exact.get("repaired_runtime_git_blob_sha")!=REPAIRED_RUNTIME_BLOB or exact.get("regression_test_git_blob_sha")!=TEST_BLOB:
        return _fail("CAUSAL_INSTANCE_IDENTITY_DRIFT")
    rex=inst.get("real_execution") or {}
    old=rex.get("predecessor_result") or {}; new=rex.get("repaired_result") or {}
    if rex.get("same_test_bytes") is not True or old.get("outcome")!="FAIL" or new.get("outcome")!="PASS" or old.get("return_code")==0 or new.get("return_code")!=0:
        return _fail("FAIL_TO_PASS_CAUSAL_SIGNATURE_MISSING")
    conc=inst.get("conclusions") or {}
    if conc.get("exact_claim_scoped_professional_edit_causality_proved") is not True:return _fail("EXACT_CAUSALITY_NOT_PROVED")
    for f in ("r7_global_root_closed","multi_edit_attribution_proved","sequence_invariance_proved","treatment_generalization_proved"):
        if conc.get(f) is True:return _fail("SOURCE_CAUSAL_OVERCLAIM",field=f)

    cv=docs["causal_compiler_verification"]
    if not str(cv.get("status") or "").startswith("PASS__EXACT_BLOBS__PYCOMPILE__8_OF_8"):return _fail("CAUSAL_COMPILER_VERIFY_NOT_PASS")
    if cv.get("reusable_scope")!="EXACT_SINGLE_EDIT_FAIL_TO_PASS_AB_EXPERIMENTS_WITH_IDENTICAL_TEST_BYTES_AND_CONTENT_ADDRESSED_SUBJECTS":
        return _fail("CAUSAL_COMPILER_SCOPE_DRIFT")

    bs=binding.get("binding_scope") or {}
    if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return _fail("BINDING_GUARANTEES_INSUFFICIENT")
    if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
    return {"schema":SCHEMA,"pass":True,
      "status":"PASS__R7_BOUND_TO_V7_SUBJECT_THROUGH_EXACT_SINGLE_EDIT_CAUSAL_INTERVENTION_ON_LOAD_BEARING_COMPONENT",
      "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA,
      "subject_binding_git_blob_sha":BINDING_BLOB,"root_subject_binding_authority":True,
      "exact_subject_component_intervention_bound":True,"global_r7_root_closed":False,
      "multi_edit_attribution_proved":False,"sequence_invariance_proved":False,"treatment_generalization_proved":False,
      "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
      "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None):
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    b,e=_read(root,BINDING_PATH,BINDING_BLOB)
    if e:return _fail(e)
    s,e=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
    if e:return _fail(e)
    docs={}
    for key,(path,sha) in REFS.items():
        d,e=_read(root,path,sha)
        if e:return _fail(e,ref=key)
        docs[key]=d
    return evaluate_documents(b,s,docs)

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
