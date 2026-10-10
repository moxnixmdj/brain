"""Independent verifier for the final-V6 R1 professional-quality root/subject binding."""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_VERIFY_V3"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R1_TARGET_SPECIFICATION"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V3.json"
EXPECTED_BINDING_BLOB="25f02a605da31c8f9d2c6208b82597e85f00be87"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V6_DECLARED_SYSTEM_SUBJECT_20261010_V5.json"
SUBJECT_BLOB="994a6a6aef44b6bb33161f7179d1983a1b50b633"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V6_DEPENDENCY_CLOSED_AUTHENTICATED_TARGET_SYSTEM_20261010_V5"
SUBJECT_SHA256="353978ba4866d1e35794390968a14500ee1d8a4f0bddfb8f081e9a1a71ba468d"

EXPECTED_REFS={
 "subject_verification":("canonical/verification/PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V5_VERIFY_20261010_V1.json","3b4213f114ae8d6842f1e2b5ddccab61f4b91078"),
 "authenticated_target_handoff":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V6_MINIMAL_BINDING_KERNEL_VERIFY_20261010_V1.json","6d9f6ff424d1b2bca1f7c2cf71868087d686e60d"),
 "r1_target_semantics":("canonical/verification/PROFESSIONAL_QUALITY_R1_TARGET_SEMANTIC_VERIFY_20261010_V1.json","dfffdd6eff129ce7498c4e4aa8a822cd4a5cda22"),
 "r1_structural_target":("canonical/verification/PROFESSIONAL_QUALITY_R1_STRUCTURAL_TARGET_VERIFY_20261010_V1.json","dcee55ba17d15154117100de6aebd34716ad3e3e"),
}

REQUIRED_MATERIAL={
 ("canonical/runtime/professional_quality_p1_router_v6.py","88644e0517d472d9fbef8d5bc6cf3495f2b50005"),
 ("canonical/runtime/goal_to_decision_binding_authority_v1.py","5b4573475437e9fc83338b900556b5c4f31c8d65"),
 ("canonical/runtime/professional_quality_p1_router_v4.py","8e5d473b5606251752c4968dfd35290e9b991f16"),
 ("canonical/runtime/professional_quality_p1_router_v3.py","cdb6716ac6d562d1ab222242d07aeecc5cdfac78"),
 ("canonical/runtime/professional_target_semantic_certificate_v1.py","583612b0e2226053ac758683087b5c5d0f510996"),
 ("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json","ae250d5bc5da73b23600670be354ffba31e65e53"),
 ("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
}

def _blob(path:Path)->str:
    data=path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _resolve(root:Path,raw:Any)->Path|None:
    if not isinstance(raw,str) or not raw.startswith("canonical/"): return None
    p=(root/raw).resolve()
    try: p.relative_to(root.resolve())
    except ValueError: return None
    return p

def _read(root:Path,path:str,sha:str)->tuple[dict[str,Any]|None,str|None]:
    p=_resolve(root,path)
    if p is None or not p.is_file() or p.is_symlink(): return None,"FILE_INVALID:"+path
    if _blob(p)!=sha: return None,"BLOB_STALE:"+path
    try: doc=json.loads(p.read_text(encoding="utf-8"))
    except Exception: return None,"JSON_INVALID:"+path
    if not isinstance(doc,dict): return None,"DOCUMENT_INVALID:"+path
    return doc,None

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
            "root_id":ROOT_ID,"root_subject_binding_authority":False,
            "global_subject_identity_authority":False,"semantic_truth_authority":False,
            "execution_authority":False,"quality_authority":False,
            "acceptance_authority":False,"promotion_authority":False,
            "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    binding,error=_read(root,BINDING_PATH,EXPECTED_BINDING_BLOB)
    if error:return _fail(error)
    assert binding is not None
    if binding.get("schema")!=BINDING_SCHEMA:return _fail("BINDING_SCHEMA_INVALID")
    if binding.get("root_id")!=ROOT_ID:return _fail("ROOT_ID_MISMATCH")
    if binding.get("subject_kind")!="DECLARED_SYSTEM" or binding.get("subject_id")!=SUBJECT_ID or binding.get("subject_sha256")!=SUBJECT_SHA256:
        return _fail("SUBJECT_TUPLE_MISMATCH")
    for field in ("root_subject_binding_authority","global_subject_identity_authority","semantic_truth_authority",
                  "execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
        if binding.get(field) is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN:"+field)

    subject_ref=binding.get("subject") or {}
    if subject_ref.get("path")!=SUBJECT_PATH or subject_ref.get("git_blob_sha")!=SUBJECT_BLOB:
        return _fail("SUBJECT_REFERENCE_MISMATCH")
    subject,error=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
    if error:return _fail(error)
    assert subject is not None
    if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:
        return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
    if (subject.get("dependency_closure") or {}).get("v6_minimal_binding_kernel",{}).get("broad_general_controller_in_subject") is not False:
        return _fail("V6_MINIMAL_SUBJECT_BOUNDARY_INVALID")
    material={(x.get("path"),x.get("git_blob_sha")) for x in (subject.get("system_material") or {}).get("components",[]) if isinstance(x,Mapping)}
    if not REQUIRED_MATERIAL<=material:return _fail("R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")

    refs=binding.get("bridge_evidence")
    if not isinstance(refs,Mapping):return _fail("BRIDGE_EVIDENCE_INVALID")
    docs={}
    for key,(path,sha) in EXPECTED_REFS.items():
        ref=refs.get(key)
        if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=sha:
            return _fail("BRIDGE_REFERENCE_MISMATCH:"+key)
        doc,error=_read(root,path,sha)
        if error:return _fail(error)
        docs[key]=doc

    sv=docs["subject_verification"]; replay=sv.get("real_subject_replay") or {}
    if replay.get("pass") is not True or replay.get("component_count")!=20 or replay.get("component_currentness_verified") is not True or replay.get("subject_identity_verified") is not True:
        return _fail("SUBJECT_VERIFICATION_INSUFFICIENT")
    if (sv.get("authority") or {}).get("root_subject_binding_authority") is not False:
        return _fail("SUBJECT_VERIFY_AUTHORITY_OVERCLAIM")

    handoff=docs["authenticated_target_handoff"]; hr=handoff.get("replay") or {}
    if (hr.get("kernel_equivalence") or {}).get("tests_passed")!=7:return _fail("V6_KERNEL_EQUIVALENCE_INSUFFICIENT")
    if (hr.get("router_v6") or {}).get("tests_passed")!=10:return _fail("V6_ROUTER_REGRESSION_INSUFFICIENT")
    if (hr.get("real_integration") or {}).get("cases_passed")!=2:return _fail("V6_REAL_INTEGRATION_INSUFFICIENT")
    if handoff.get("quality_authority") is not False or handoff.get("terminal_authority") is not False:
        return _fail("V6_HANDOFF_AUTHORITY_OVERCLAIM")

    sem=docs["r1_target_semantics"]; scope=sem.get("claim_scope") or {}
    if (sem.get("replay") or {}).get("tests_passed")!=5 or scope.get("kind")!="EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS":
        return _fail("R1_SEMANTIC_EVIDENCE_INSUFFICIENT")
    if "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS" not in set(scope.get("limitations") or []):
        return _fail("R1_SEMANTIC_SCOPE_TOO_BROAD")

    structural=docs["r1_structural_target"]
    if (structural.get("replay") or {}).get("tests_passed")!=21 or (structural.get("current_truth") or {}).get("semantic_truth_closed") is not False:
        return _fail("R1_STRUCTURAL_EVIDENCE_INSUFFICIENT")

    bscope=binding.get("binding_scope") or {}
    if bscope.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        return _fail("BINDING_BEHAVIOR_ID_INVALID")
    required_limits={"NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS","NO_GLOBAL_R1_ROOT_CLOSURE",
                     "NO_SAME_SUBJECT_COMPOSITION_PASS","NO_LIVE_DEFAULT_PROMOTION"}
    if not required_limits<=set(bscope.get("limitations") or []):
        return _fail("BINDING_LIMITATIONS_INSUFFICIENT")

    return {"schema":SCHEMA,"pass":True,"status":"PASS__R1_ROOT_BOUND_TO_FINAL_V6_DECLARED_SYSTEM_SUBJECT",
            "root_id":ROOT_ID,"subject_kind":"DECLARED_SYSTEM","subject_id":SUBJECT_ID,
            "subject_sha256":SUBJECT_SHA256,"subject_binding_git_blob_sha":EXPECTED_BINDING_BLOB,
            "root_subject_binding_authority":True,"global_subject_identity_authority":False,
            "binding_scope":bscope,"semantic_truth_authority":False,"execution_authority":False,
            "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
            "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
