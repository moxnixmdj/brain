"""Professional P1 Router V10: V9 plus fixed trusted local-totality authority.

V9 proves that positive routes execute a content-addressed semantic verifier.
V10 removes the remaining verifier-selection freedom: every positive route must
use the exact trusted R12 local-totality verifier frozen into the V10 subject.
Thus arbitrary verifier bytes cannot mint a positive certificate.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v9 as base
from canonical.runtime import professional_r12_trusted_local_totality_verifier_v1 as trusted

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V10"
TRUSTED_VERIFIER_PATH="canonical/runtime/professional_r12_trusted_local_totality_verifier_v1.py"
TRUSTED_VERIFIER_BLOB="2778edd768c340b204580e625441278a4da114be"
REQUIRED_V10_COMPONENTS=frozenset({
    "canonical/runtime/professional_quality_p1_router_v10.py",
    TRUSTED_VERIFIER_PATH,
})

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":reason,
            "semantic_truth_authority":False,"execution_authority":False,
            "quality_authority":False,"acceptance_authority":False,
            "promotion_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _safe_cert(root:Path,ref:Any)->Path|None:
    if not isinstance(ref,Mapping): return None
    rel=ref.get("path"); expected=ref.get("git_blob_sha")
    if not isinstance(rel,str) or rel.startswith("/") or not rel.startswith(("canonical/governance/","canonical/evidence/","canonical/verification/")):
        return None
    p=Path(rel)
    if ".." in p.parts: return None
    full=(root/p).resolve()
    try: full.relative_to(root.resolve())
    except ValueError: return None
    if not full.is_file() or full.is_symlink() or not isinstance(expected,str) or _blob(full)!=expected:
        return None
    return full

def _v10_subject_ok(ref:Any,*,root:Path)->dict[str,Any]:
    prior=base._v9_subject_ok(ref,root=root)
    if prior.get("pass") is not True:
        return {"pass":False,"reason":"V9_SUBJECT_REJECTED","v9_subject_state":prior}
    doc,state=base.base._load_subject(ref,root=root)
    if doc is None:
        return {"pass":False,"reason":"V10_SUBJECT_REJECTED","subject_state":state}
    comps=(doc.get("system_material") or {}).get("components") or []
    paths={x.get("path") for x in comps if isinstance(x,Mapping)}
    missing=sorted(REQUIRED_V10_COMPONENTS-paths)
    if missing:
        return {"pass":False,"reason":"V10_LOAD_BEARING_COMPONENTS_NOT_IN_SUBJECT","missing":missing}
    pinned={x.get("path"):x.get("git_blob_sha") for x in comps if isinstance(x,Mapping)}
    if pinned.get(TRUSTED_VERIFIER_PATH)!=TRUSTED_VERIFIER_BLOB:
        return {"pass":False,"reason":"V10_TRUSTED_VERIFIER_SUBJECT_PIN_MISMATCH"}
    return {"pass":True,"subject_id":state.get("subject_id"),
            "subject_sha256":state.get("subject_sha256"),
            "subject_git_blob_sha":state.get("subject_git_blob_sha")}

def route(state:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(state,Mapping): return _fail("STATE_NOT_OBJECT")
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    subject=_v10_subject_ok(state.get(base.base.SUBJECT_REF_KEY),root=root)
    if subject.get("pass") is not True:
        return _fail("V10_DECLARED_SYSTEM_SUBJECT_INVALID",subject_verification=subject)

    out=base.route(state,repo_root=root)
    if not isinstance(out,Mapping): return _fail("V9_RESULT_NOT_OBJECT")
    result=deepcopy(dict(out)); result["schema"]=SCHEMA
    if result.get("final_step_outcome")!="POSITIVE_CERTIFICATE" or result.get("positive_certification_authorized") is not True:
        result["v10_trusted_local_totality_verified"]=False
        return result

    bindings=state.get(base.base.STEP_BINDINGS_KEY)
    if not isinstance(bindings,Mapping): return _fail("V10_STEP_BINDINGS_REQUIRED_AFTER_V9_POSITIVE")
    final=bindings.get(base.base.FINAL_STEP)
    if not isinstance(final,Mapping): return _fail("V10_FINAL_BINDING_REQUIRED_AFTER_V9_POSITIVE")
    vr=final.get("material_totality_semantic_verifier")
    if not isinstance(vr,Mapping) or vr.get("path")!=TRUSTED_VERIFIER_PATH or vr.get("git_blob_sha")!=TRUSTED_VERIFIER_BLOB:
        return _fail("V10_UNTRUSTED_SEMANTIC_VERIFIER_REJECTED")
    cert_path=_safe_cert(root,final.get("material_totality_certificate"))
    if cert_path is None: return _fail("V10_MATERIAL_TOTALITY_CERTIFICATE_REF_INVALID")
    local=trusted.verify_certificate(root=root,certificate_path=cert_path,expected_binding=base._expected_binding())
    if local.get("pass") is not True or local.get("local_material_totality_verified") is not True:
        return _fail("V10_TRUSTED_LOCAL_TOTALITY_REJECTED",local_totality=local)

    result["v10_trusted_local_totality_verified"]=True
    result["v10_universal_positive_route_invariant"]="EVERY_POSITIVE_ROUTE_REQUIRES_EXACT_PINNED_TRUSTED_LOCAL_TOTALITY_VERIFIER"
    result["semantic_truth_authority"]=False
    result["quality_authority"]=False
    result["acceptance_authority"]=False
    result["promotion_authority"]=False
    result["terminal_authority"]=False
    result["terminal_credit_delta"]=0
    result["incremental_spend_usd"]=0
    return result

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return route(args or {},repo_root=root)
