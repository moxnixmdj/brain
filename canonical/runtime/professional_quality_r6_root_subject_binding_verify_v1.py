"""Fail-closed verifier for R6 evidence-grounding binding on the frozen V7 professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R6_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R6_EVIDENCE_GROUNDING_DEPENDENCE"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R6_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="ced1e7e5fa6b2393c7571f03df1fdb2623014ffd"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
REFS={
 "execution_profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
 "proof_bound_step_verification":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json","b7a9df36780513ad73fd14c6a2756c8474d8434d"),
 "scoped_evidence_registry":("canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json","b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"),
 "leaf_evidence_registry":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json","d25cb6fe746eef992f71b138446dc999c0f2a307"),
 "leaf_binding_manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "leaf_binder_runtime":("canonical/runtime/professional_quality_leaf_binder_v2.py","1a181b453271a2ce4fc112c3f6586afaf5effbd7"),
 "leaf_binder_verification":("canonical/verification/PROFESSIONAL_QUALITY_LEAF_BINDER_V2_VERIFY_20261010_V1.json","b65a67e8edaee925338fe3f2d61dad6b0f52d129"),
}
REQUIRED_SUBJECT_COMPONENTS={
 ("canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json","b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"),
 ("canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json","d25cb6fe746eef992f71b138446dc999c0f2a307"),
 ("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 ("canonical/runtime/professional_quality_leaf_binder_v2.py","1a181b453271a2ce4fc112c3f6586afaf5effbd7"),
 ("canonical/runtime/professional_quality_p1_router_v7.py","765b5994c2fcb5eb669b5fd0d989cc79c1609908"),
 ("canonical/runtime/professional_step_binding_authority_v1.py","27f3c137dae7f00925083a0824d008c2b4d10f0a"),
}
REQUIRED_GUARANTEES={
 "EXACT_V7_SUBJECT_TUPLE_BOUND",
 "SCOPED_EVIDENCE_REGISTRY_IS_AN_EXACT_COMPONENT_OF_THE_V7_SUBJECT",
 "LEAF_EVIDENCE_REGISTRY_AND_LEAF_BINDER_ARE_EXACT_COMPONENTS_OF_THE_V7_SUBJECT",
 "LEAF_CLOSURE_REQUIRES_SCOPE_MATCHED_CONTENT_ADDRESSED_VERIFICATION_RECEIPTS",
 "RECEIPT_MUST_BIND_EXACT_ROOT_CONTRACT_AND_EXACT_LEAF_ACCEPTANCE",
 "VERIFICATION_BASIS_MUST_BE_CONTENT_ADDRESSED_AND_CURRENT",
 "MANIFEST_STATUS_STRINGS_HAVE_ZERO_PROMOTION_AUTHORITY",
 "SCOPED_EVIDENCE_CONTRIBUTES_ONLY_WITHIN_ITS_PROVED_SCOPE",
 "CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY",
 "ALL_SEVEN_PREVIOUSLY_UNBOUND_LOAD_BEARING_PROFILE_STEPS_REQUIRE_CONTENT_ADDRESSED_STEP_BINDINGS",
}
REQUIRED_LIMITS={
 "NO_GLOBAL_EVIDENCE_COMPLETENESS_PROOF","NO_GLOBAL_LEAF_OR_ROOT_CLOSURE",
 "NO_DOMAIN_SEMANTIC_OR_EXECUTION_CLOSURE","NO_CLAIM_ALL_REAL_TASK_EVIDENCE_HAS_ALREADY_BEEN_ADMITTED",
 "NO_CLAIM_ALL_V7_STEPS_HAVE_REAL_TASK_RECEIPTS","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION",
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
      "root_subject_binding_authority":False,"global_evidence_completeness_proved":False,
      "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}
def _components(subject:Mapping[str,Any]):
    return {(x.get("path"),x.get("git_blob_sha")) for x in ((subject.get("system_material") or {}).get("components") or []) if isinstance(x,Mapping)}

def evaluate_documents(binding:Mapping[str,Any],subject:Mapping[str,Any],docs:Mapping[str,Mapping[str,Any]]):
    if binding.get("schema")!=BINDING_SCHEMA or binding.get("root_id")!=ROOT_ID:return _fail("BINDING_IDENTITY_INVALID")
    if (binding.get("subject_kind"),binding.get("subject_id"),binding.get("subject_sha256"))!=("DECLARED_SYSTEM",SUBJECT_ID,SUBJECT_SHA):
        return _fail("SUBJECT_TUPLE_MISMATCH")
    if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA:return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
    comps=_components(subject)
    if not REQUIRED_SUBJECT_COMPONENTS<=comps:return _fail("REQUIRED_EVIDENCE_COMPONENTS_NOT_IN_SUBJECT")
    for f in ("global_subject_identity_authority","root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
        if binding.get(f) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN",field=f)
    if binding.get("actual_v7_evidence_receipts_required_for_execution") is not True:return _fail("REAL_EVIDENCE_RECEIPT_REQUIREMENT_MISSING")
    if binding.get("evidence_status_string_authority") is not False:return _fail("STATUS_STRING_AUTHORITY_FORBIDDEN")
    refs=binding.get("bridge_evidence") or {}
    for key,(path,sha) in REFS.items():
        row=refs.get(key)
        if not isinstance(row,Mapping) or row.get("path")!=path or row.get("git_blob_sha")!=sha:return _fail("BRIDGE_REF_MISMATCH",ref=key)

    scoped=docs["scoped_evidence_registry"]
    entries=[x for x in (scoped.get("entries") or []) if isinstance(x,Mapping) and x.get("root_id")==ROOT_ID]
    if len(entries)!=1:return _fail("R6_SCOPED_ENTRY_CARDINALITY_INVALID")
    e=entries[0]
    if e.get("scope_id")!="PQ::R6::LEAF_EVIDENCE::CONTENT_ADDRESSED_SCOPE_MATCHED_ADMISSION":return _fail("R6_SCOPE_ID_MISMATCH")
    if set(e.get("contributes_to_leaf_ids") or [])!={"PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::SEMANTIC","PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION"}:
        return _fail("R6_LEAF_SCOPE_MISMATCH")
    if e.get("global_leaf_closure") is not False or e.get("global_root_closure") is not False:return _fail("R6_SCOPE_WIDENING_FORBIDDEN")

    leafreg=docs["leaf_evidence_registry"]
    law=str(leafreg.get("admission_law") or "")
    for phrase in ("SCOPE_MATCHED_CONTENT_ADDRESSED_VERIFICATION_RECEIPT","MANIFEST_STATUS_STRINGS_HAVE_ZERO_PROMOTION_AUTHORITY"):
        if phrase not in law:return _fail("LEAF_ADMISSION_LAW_MISSING",phrase=phrase)
    if leafreg.get("terminal_authority") is not False:return _fail("LEAF_REGISTRY_TERMINAL_AUTHORITY_INVALID")

    lv=docs["leaf_binder_verification"]
    proved=set(lv.get("proved") or [])
    for premise in ("MANIFEST_VERIFIED_STATUS_HAS_ZERO_PROMOTION_AUTHORITY","LEAF_CLOSURE_REQUIRES_SCOPE_MATCHED_CONTENT_ADDRESSED_RECEIPT","RECEIPT_MUST_BIND_EXACT_ROOT_CONTRACT_AND_EXACT_LEAF_ACCEPTANCE","RECEIPT_VERIFICATION_BASIS_MUST_BE_CONTENT_ADDRESSED_AND_CURRENT"):
        if premise not in proved:return _fail("LEAF_BINDER_PREMISE_MISSING",premise=premise)

    pv=docs["proof_bound_step_verification"]
    proves=set(pv.get("proves") or [])
    for premise in ("CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY","ALL_SEVEN_PREVIOUSLY_UNBOUND_LOAD_BEARING_PROFILE_STEPS_REQUIRE_CONTENT_ADDRESSED_STEP_BINDINGS","STEP_BINDINGS_ARE_BOUND_TO_EXACT_BEHAVIOR_SUBJECT_RUN_CONTEXT_STEP_RESULT_AND_EVIDENCE_DIGEST"):
        if premise not in proves:return _fail("V7_STEP_PREMISE_MISSING",premise=premise)

    bs=binding.get("binding_scope") or {}
    if not REQUIRED_GUARANTEES<=set(bs.get("guarantees") or []):return _fail("BINDING_GUARANTEES_INSUFFICIENT")
    if not REQUIRED_LIMITS<=set(bs.get("limitations") or []):return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
    return {"schema":SCHEMA,"pass":True,"status":"PASS__R6_BOUND_TO_V7_SUBJECT_THROUGH_CONTENT_ADDRESSED_SCOPE_MATCHED_EVIDENCE_DEPENDENCE",
      "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA,
      "subject_binding_git_blob_sha":BINDING_BLOB,"root_subject_binding_authority":True,
      "global_evidence_completeness_proved":False,"real_task_all_evidence_receipts_proved":False,
      "global_r6_root_closed":False,"semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

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
