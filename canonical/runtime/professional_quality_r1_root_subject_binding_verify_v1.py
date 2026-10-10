"""Independent verifier for the R1 professional-quality root/subject binding."""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
ROOT_ID="R1_TARGET_SPECIFICATION"
BINDING_PATH="canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V1.json"
EXPECTED_BINDING_BLOB="e702e0d0ea567db92869cfe0be7ca9745d94c8cc"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V4_DECLARED_SYSTEM_SUBJECT_20261010_V3.json"
SUBJECT_BLOB="ad6867e59b4279e34a3e0058cf539ee94f8d094c"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V4_TARGET_BOUND_SYSTEM_20261010_V3"
SUBJECT_SHA256="e7292fbe697c2dcd06fc2c4346fc3e3bb231428a6511a88d575c655dd0f0c53a"

EXPECTED_REFS={
 "subject_verification":("canonical/verification/PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V3_VERIFY_20261010_V1.json","38925a742e9964bd5d045db58db19ebb539f2dc0"),
 "target_bound_router_regression":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V4_INHERITED_REGRESSION_VERIFY_20261010_V1.json","19c287a8424ded099713263f016a23aeb5fc64b3"),
 "r1_target_semantics":("canonical/verification/PROFESSIONAL_QUALITY_R1_TARGET_SEMANTIC_VERIFY_20261010_V1.json","dfffdd6eff129ce7498c4e4aa8a822cd4a5cda22"),
 "r1_structural_target":("canonical/verification/PROFESSIONAL_QUALITY_R1_STRUCTURAL_TARGET_VERIFY_20261010_V1.json","dcee55ba17d15154117100de6aebd34716ad3e3e"),
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
    try: doc=json.loads(p.read_text())
    except Exception: return None,"JSON_INVALID:"+path
    if not isinstance(doc,dict): return None,"DOCUMENT_INVALID:"+path
    return doc,None

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
            "root_id":ROOT_ID,"root_subject_binding_authority":False,
            "global_subject_identity_authority":False,"quality_authority":False,
            "terminal_authority":False,"terminal_credit_delta":0,**extra}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    binding,error=_read(root,BINDING_PATH,EXPECTED_BINDING_BLOB)
    if error:return _fail(error)
    assert binding is not None
    if binding.get("schema")!=BINDING_SCHEMA:return _fail("BINDING_SCHEMA_INVALID")
    if binding.get("root_id")!=ROOT_ID:return _fail("ROOT_ID_MISMATCH")
    if binding.get("subject_kind")!="DECLARED_SYSTEM" or binding.get("subject_id")!=SUBJECT_ID or binding.get("subject_sha256")!=SUBJECT_SHA256:
        return _fail("SUBJECT_TUPLE_MISMATCH")
    if binding.get("root_subject_binding_authority") is not False:return _fail("BINDING_SELF_AUTHORITY_FORBIDDEN")
    if binding.get("global_subject_identity_authority") is not False:return _fail("GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")
    if binding.get("terminal_authority") is not False:return _fail("TERMINAL_AUTHORITY_FORBIDDEN")
    subject_ref=binding.get("subject") or {}
    if subject_ref.get("path")!=SUBJECT_PATH or subject_ref.get("git_blob_sha")!=SUBJECT_BLOB:
        return _fail("SUBJECT_REFERENCE_MISMATCH")
    subject,error=_read(root,SUBJECT_PATH,SUBJECT_BLOB)
    if error:return _fail(error)
    assert subject is not None
    if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:
        return _fail("SUBJECT_DOCUMENT_IDENTITY_MISMATCH")
    material={(x.get("path"),x.get("git_blob_sha")) for x in (subject.get("system_material") or {}).get("components",[]) if isinstance(x,Mapping)}
    required_material={
      ("canonical/runtime/professional_quality_p1_router_v4.py","8e5d473b5606251752c4968dfd35290e9b991f16"),
      ("canonical/runtime/professional_quality_p1_router_v3.py","cdb6716ac6d562d1ab222242d07aeecc5cdfac78"),
      ("canonical/runtime/professional_target_semantic_certificate_v1.py","583612b0e2226053ac758683087b5c5d0f510996"),
      ("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json","ae250d5bc5da73b23600670be354ffba31e65e53"),
      ("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
    }
    if not required_material<=material:return _fail("R1_LOAD_BEARING_MATERIAL_NOT_IN_SUBJECT")
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
    sv=docs["subject_verification"]
    if sv.get("real_subject_replay",{}).get("pass") is not True or sv.get("real_subject_replay",{}).get("component_count")!=13:
        return _fail("SUBJECT_VERIFICATION_INSUFFICIENT")
    if sv.get("root_subject_binding_authority") is not False:return _fail("SUBJECT_VERIFY_AUTHORITY_OVERCLAIM")
    rr=docs["target_bound_router_regression"]
    if rr.get("replay",{}).get("tests_passed")!=21 or rr.get("replay",{}).get("tests_failed")!=0:
        return _fail("ROUTER_REGRESSION_INSUFFICIENT")
    if rr.get("live_default") is not False or rr.get("quality_authority") is not False:
        return _fail("ROUTER_RECEIPT_AUTHORITY_OVERCLAIM")
    sem=docs["r1_target_semantics"]
    scope=sem.get("claim_scope") or {}
    if sem.get("replay",{}).get("tests_passed")!=5 or scope.get("kind")!="EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS":
        return _fail("R1_SEMANTIC_EVIDENCE_INSUFFICIENT")
    limitations=set(scope.get("limitations") or [])
    if "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS" not in limitations:
        return _fail("R1_SEMANTIC_SCOPE_TOO_BROAD")
    structural=docs["r1_structural_target"]
    if structural.get("replay",{}).get("tests_passed")!=21 or structural.get("current_truth",{}).get("semantic_truth_closed") is not False:
        return _fail("R1_STRUCTURAL_EVIDENCE_INSUFFICIENT")
    bscope=binding.get("binding_scope") or {}
    if bscope.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        return _fail("BINDING_BEHAVIOR_ID_INVALID")
    blimits=set(bscope.get("limitations") or [])
    required_limits={"NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS","NO_GLOBAL_R1_ROOT_CLOSURE","NO_LIVE_DEFAULT_PROMOTION"}
    if not required_limits<=blimits:return _fail("BINDING_LIMITATIONS_INSUFFICIENT")
    return {
      "schema":SCHEMA,"pass":True,"status":"PASS__R1_ROOT_BOUND_TO_TARGET_BOUND_CANDIDATE_SUBJECT",
      "root_id":ROOT_ID,"subject_kind":"DECLARED_SYSTEM","subject_id":SUBJECT_ID,
      "subject_sha256":SUBJECT_SHA256,"subject_binding_git_blob_sha":EXPECTED_BINDING_BLOB,
      "root_subject_binding_authority":True,"global_subject_identity_authority":False,
      "binding_scope":bscope,"semantic_truth_authority":False,"execution_authority":False,
      "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
