"""Independent verifier for R1 binding on the V7 proof-bound professional subject."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_VERIFY_V4"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R1_TARGET_SPECIFICATION"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V4.json"
EXPECTED_BINDING_BLOB="4e29f1a01832158d9897f3c71c81e015b5e51b05"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"

REFS={
 "subject_verification":("canonical/verification/PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V7_VERIFY_20261010_V1.json","9bca985bfcef8f5cc6d62b42a51ccc72a6abfd2c"),
 "authenticated_target_handoff":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V6_MINIMAL_BINDING_KERNEL_VERIFY_20261010_V1.json","6d9f6ff424d1b2bca1f7c2cf71868087d686e60d"),
 "proof_bound_profile_execution":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V7_PROOF_BOUND_STEP_VERIFY_20261010_V1.json","b7a9df36780513ad73fd14c6a2756c8474d8434d"),
 "r1_target_semantics":("canonical/verification/PROFESSIONAL_QUALITY_R1_TARGET_SEMANTIC_VERIFY_20261010_V1.json","dfffdd6eff129ce7498c4e4aa8a822cd4a5cda22"),
 "r1_structural_target":("canonical/verification/PROFESSIONAL_QUALITY_R1_STRUCTURAL_TARGET_VERIFY_20261010_V1.json","dcee55ba17d15154117100de6aebd34716ad3e3e"),
}
REQUIRED_MATERIAL={
 ("canonical/runtime/professional_quality_p1_router_v7.py","765b5994c2fcb5eb669b5fd0d989cc79c1609908"),
 ("canonical/runtime/professional_step_binding_authority_v1.py","27f3c137dae7f00925083a0824d008c2b4d10f0a"),
 ("canonical/runtime/professional_quality_p1_router_v6.py","88644e0517d472d9fbef8d5bc6cf3495f2b50005"),
 ("canonical/runtime/goal_to_decision_binding_authority_v1.py","5b4573475437e9fc83338b900556b5c4f31c8d65"),
 ("canonical/runtime/professional_quality_p1_router_v4.py","8e5d473b5606251752c4968dfd35290e9b991f16"),
 ("canonical/runtime/professional_quality_p1_router_v3.py","cdb6716ac6d562d1ab222242d07aeecc5cdfac78"),
 ("canonical/runtime/professional_target_semantic_certificate_v1.py","583612b0e2226053ac758683087b5c5d0f510996"),
 ("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json","ae250d5bc5da73b23600670be354ffba31e65e53"),
}

def _blob(p:Path)->str:
    d=p.read_bytes(); return sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def _resolve(root:Path,raw:Any)->Path|None:
    if not isinstance(raw,str) or not raw.startswith("canonical/"): return None
    p=(root/raw).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return None
    return p
def _read(root:Path,path:str,sha:str):
    p=_resolve(root,path)
    if p is None or not p.is_file() or p.is_symlink(): return None,"FILE_INVALID:"+path
    if _blob(p)!=sha:return None,"BLOB_STALE:"+path
    try:d=json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None,"JSON_INVALID:"+path
    if not isinstance(d,dict):return None,"DOCUMENT_INVALID:"+path
    return d,None
def _fail(reason:str,**extra):
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
            "root_id":ROOT_ID,"root_subject_binding_authority":False,
            "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
            "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def verify(*,repo_root:str|Path|None=None):
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    binding,e=_read(root,BINDING_PATH,EXPECTED_BINDING_BLOB)
    if e:return _fail(e)
    if binding.get("schema")!=BINDING_SCHEMA or binding.get("root_id")!=ROOT_ID:return _fail("BINDING_IDENTITY_INVALID")
    if binding.get("subject_id")!=SUBJECT_ID or binding.get("subject_sha256")!=SUBJECT_SHA256:return _fail("SUBJECT_TUPLE_MISMATCH")
    for f in ("root_subject_binding_authority","global_subject_identity_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
        if binding.get(f) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+f)
    sref=binding.get("subject") or {}
    if sref.get("path")!=SUBJECT_PATH or sref.get("git_blob_sha")!=SUBJECT_BLOB:return _fail("SUBJECT_REFERENCE_MISMATCH")
    subject,e=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
    if e:return _fail(e)
    if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
    material={(x.get("path"),x.get("git_blob_sha")) for x in (subject.get("system_material") or {}).get("components",[]) if isinstance(x,Mapping)}
    if not REQUIRED_MATERIAL<=material:return _fail("R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")

    docs={}
    bre=binding.get("bridge_evidence")
    if not isinstance(bre,Mapping):return _fail("BRIDGE_EVIDENCE_INVALID")
    for k,(path,sha) in REFS.items():
        ref=bre.get(k)
        if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=sha:return _fail("BRIDGE_REFERENCE_MISMATCH:"+k)
        d,e=_read(root,path,sha)
        if e:return _fail(e)
        docs[k]=d

    sv=docs["subject_verification"]; sr=sv.get("real_subject_replay") or {}
    if sr.get("pass") is not True or sr.get("component_count")!=22 or sr.get("component_currentness_verified") is not True or sr.get("subject_identity_verified") is not True:
        return _fail("SUBJECT_VERIFICATION_INSUFFICIENT")

    handoff=docs["authenticated_target_handoff"]; hr=handoff.get("replay") or {}
    if (hr.get("kernel_equivalence") or {}).get("tests_passed")!=7 or (hr.get("router_v6") or {}).get("tests_passed")!=10 or (hr.get("real_integration") or {}).get("cases_passed")!=2:
        return _fail("V6_TARGET_HANDOFF_EVIDENCE_INSUFFICIENT")

    prov=docs["proof_bound_profile_execution"]
    if (prov.get("replay") or {}).get("tests_passed")!=15:return _fail("V7_STEP_PROVENANCE_REPLAY_INSUFFICIENT")
    if "CALLER_SUPPLIED_STEP_RESULTS_HAVE_ZERO_AUTHORITY_AT_V7_ENTRY" not in set(prov.get("proves") or []):
        return _fail("V7_CALLER_STEP_NONAUTHORITY_UNPROVED")
    if prov.get("quality_authority") is not False or prov.get("terminal_authority") is not False:
        return _fail("V7_PROVENANCE_AUTHORITY_OVERCLAIM")

    sem=docs["r1_target_semantics"]; scope=sem.get("claim_scope") or {}
    if (sem.get("replay") or {}).get("tests_passed")!=5 or scope.get("kind")!="EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS":
        return _fail("R1_SEMANTIC_EVIDENCE_INSUFFICIENT")
    if "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS" not in set(scope.get("limitations") or []):
        return _fail("R1_SEMANTIC_SCOPE_TOO_BROAD")
    structural=docs["r1_structural_target"]
    if (structural.get("replay") or {}).get("tests_passed")!=21 or (structural.get("current_truth") or {}).get("semantic_truth_closed") is not False:
        return _fail("R1_STRUCTURAL_EVIDENCE_INSUFFICIENT")

    bs=binding.get("binding_scope") or {}
    limits=set(bs.get("limitations") or [])
    if not {"NO_GLOBAL_R1_ROOT_CLOSURE","NO_R2_THROUGH_R12_ROOT_SUBJECT_BINDING","NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION"}<=limits:
        return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
    return {"schema":SCHEMA,"pass":True,"status":"PASS__R1_ROOT_BOUND_TO_V7_PROOF_BOUND_EXECUTION_SUBJECT",
            "root_id":ROOT_ID,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
            "subject_binding_git_blob_sha":EXPECTED_BINDING_BLOB,"root_subject_binding_authority":True,
            "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
            "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
