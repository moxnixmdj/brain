"""Explicit-path declared-system subject verifier V2.

Same fail-closed identity/currentness semantics as V1, but with no hardcoded
subject path. This makes the verifier a clean load-bearing runtime dependency
for proof-bound routers without dragging a historical default subject into the
declared-system dependency cone.
"""
from __future__ import annotations
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_VERIFY_V2"
SUBJECT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V2"
MATERIAL_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_V3_DECLARED_SYSTEM_SUBJECT_MATERIAL_V2"

def _blob(p:Path)->str:
    d=p.read_bytes(); return sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _base(status:str,*,passed=False,**extra):
    return {"schema":SCHEMA,"status":status,"pass":passed,"subject_identity_verified":False,
      "component_currentness_verified":False,"root_subject_binding_authority":False,
      "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
      "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}
def _fail(reason:str,**extra): return _base("FAIL_CLOSED",reason=reason,**extra)
def _resolve(root:Path,raw:Any)->Path|None:
    if not isinstance(raw,str) or not raw.startswith("canonical/"): return None
    p=(root/raw).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return None
    return p

def verify(subject_path:str,*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(subject_path,str) or not subject_path.startswith("canonical/governance/"):
        return _fail("SUBJECT_PATH_REQUIRED")
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    path=_resolve(root,subject_path)
    if path is None or not path.is_file() or path.is_symlink(): return _fail("SUBJECT_FILE_INVALID")
    try: subject=json.loads(path.read_text(encoding="utf-8"))
    except Exception:return _fail("SUBJECT_JSON_INVALID")
    if not isinstance(subject,dict):return _fail("SUBJECT_DOCUMENT_INVALID")
    if subject.get("schema")!=SUBJECT_SCHEMA:return _fail("SUBJECT_SCHEMA_INVALID")
    if subject.get("subject_kind")!="DECLARED_SYSTEM":return _fail("SUBJECT_KIND_INVALID")
    sid=subject.get("subject_id"); declared=subject.get("subject_sha256")
    if not isinstance(sid,str) or not sid.strip():return _fail("SUBJECT_ID_INVALID")
    if not isinstance(declared,str) or len(declared)!=64 or any(c not in "0123456789abcdef" for c in declared):
        return _fail("SUBJECT_SHA256_INVALID")
    material=subject.get("system_material")
    if not isinstance(material,dict) or material.get("schema")!=MATERIAL_SCHEMA:return _fail("SYSTEM_MATERIAL_INVALID")
    actual=sha256(_canon(material)).hexdigest()
    if actual!=declared:return _fail("SUBJECT_HASH_MISMATCH",declared_subject_sha256=declared,actual_subject_sha256=actual)
    comps=material.get("components")
    if not isinstance(comps,list) or not comps:return _fail("COMPONENTS_INVALID")
    seen=set(); verified=[]
    for i,ref in enumerate(comps):
        if not isinstance(ref,Mapping):return _fail("COMPONENT_REFERENCE_INVALID",component_index=i)
        rel=ref.get("path"); exp=ref.get("git_blob_sha")
        if not isinstance(rel,str) or rel in seen:return _fail("COMPONENT_PATH_INVALID_OR_DUPLICATE",component_index=i)
        seen.add(rel); p=_resolve(root,rel)
        if p is None or not p.is_file() or p.is_symlink():return _fail("COMPONENT_FILE_INVALID",component_index=i,component_path=rel)
        got=_blob(p)
        if not isinstance(exp,str) or got!=exp:return _fail("COMPONENT_BLOB_STALE",component_index=i,component_path=rel,declared_git_blob_sha=exp,actual_git_blob_sha=got)
        verified.append({"path":rel,"git_blob_sha":got})
    ident=subject.get("identity_semantics")
    if not isinstance(ident,Mapping):return _fail("IDENTITY_SEMANTICS_INVALID")
    if ident.get("component_inclusion_does_not_imply_root_satisfaction") is not True:return _fail("ROOT_SATISFACTION_NONAUTHORITY_REQUIRED")
    if ident.get("scoped_evidence_inclusion_does_not_transport_scope") is not True:return _fail("SCOPE_NONTRANSPORT_REQUIRED")
    if ident.get("root_subject_binding_requires_independent_verification") is not True:return _fail("INDEPENDENT_ROOT_BINDING_REQUIRED")
    if ident.get("global_subject_identity_authority") is not False:return _fail("GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")
    if subject.get("terminal_authority") is not False:return _fail("TERMINAL_AUTHORITY_FORBIDDEN")
    return _base("PASS__DECLARED_SYSTEM_SUBJECT_CURRENT_AND_CONTENT_ADDRESSED",passed=True,
      subject_identity_verified=True,component_currentness_verified=True,subject_kind="DECLARED_SYSTEM",
      subject_id=sid,subject_sha256=declared,subject_git_blob_sha=_blob(path),component_count=len(verified),
      verified_components=verified)

if __name__=="__main__":
    raise SystemExit("EXPLICIT_SUBJECT_PATH_REQUIRED")
