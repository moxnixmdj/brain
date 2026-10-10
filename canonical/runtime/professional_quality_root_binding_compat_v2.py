from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_BINDING_COMPAT_V2"
V1="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
V2="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V2"
ALLOWED={V1,V2}

R3_ROOT="R3_REALIZATION_OBSERVATION"
R3_V1_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V1.json"
R3_V1_BLOB="c49c120a61620d400e372884266b63ec34a054d2"
R3_V1_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1.json"
R3_V1_VERIFY_BLOB="92cacbd5f7b37cb515db9ebbc3685c961fc9e34e"

def _blob(path:Path)->str:
    data=path.read_bytes()
    return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _read(root:Path,path:str,sha:str)->dict[str,Any]|None:
    p=(root/path).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return None
    if not p.is_file() or p.is_symlink() or _blob(p)!=sha:return None
    try:o=json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None
    return o if isinstance(o,dict) else None

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"pass":False,"reason":reason,**extra}

def _identity(binding:Mapping[str,Any])->tuple[str,str,str]|None:
    kind=binding.get("subject_kind");sid=binding.get("subject_id");sha=binding.get("subject_sha256")
    if not isinstance(kind,str) or not kind or not isinstance(sid,str) or not sid:
        return None
    if not isinstance(sha,str) or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
        return None
    return kind,sid,sha

def normalize(
    binding:Mapping[str,Any],
    *,
    verification:Mapping[str,Any]|None=None,
    repo_root:str|Path|None=None,
)->dict[str,Any]:
    if not isinstance(binding,Mapping):return _fail("BINDING_NOT_OBJECT")
    schema=binding.get("schema")
    if schema not in ALLOWED:return _fail("BINDING_SCHEMA_UNSUPPORTED")
    if binding.get("root_subject_binding_authority") is not False:
        return _fail("BINDING_SELF_ROOT_AUTHORITY_FORBIDDEN")
    if binding.get("terminal_authority") is not False:
        return _fail("BINDING_TERMINAL_AUTHORITY_FORBIDDEN")
    ident=_identity(binding)
    if ident is None:return _fail("SUBJECT_IDENTITY_INVALID")

    if schema==V1:
        if binding.get("global_subject_identity_authority") is not False:
            return _fail("V1_GLOBAL_SUBJECT_NONAUTHORITY_REQUIRED")
        return {
            "schema":SCHEMA,"pass":True,"binding_schema":schema,
            "subject_kind":ident[0],"subject_id":ident[1],"subject_sha256":ident[2],
            "global_subject_identity_authority":False,"terminal_authority":False,
            "root_subject_binding_authority":False,"legacy_v2_inheritance_used":False,
        }

    # V2 may explicitly preserve the old non-authority field.
    if binding.get("global_subject_identity_authority") is True:
        return _fail("V2_GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")
    if binding.get("global_subject_identity_authority") is False:
        return {
            "schema":SCHEMA,"pass":True,"binding_schema":schema,
            "subject_kind":ident[0],"subject_id":ident[1],"subject_sha256":ident[2],
            "global_subject_identity_authority":False,"terminal_authority":False,
            "root_subject_binding_authority":False,"legacy_v2_inheritance_used":False,
        }

    # Missing V2 field is admissible only for the exact known R3 V2 extension and
    # only when its independently verified V1 predecessor proves the boundary.
    if binding.get("root_id")!=R3_ROOT:
        return _fail("V2_MISSING_GLOBAL_FIELD_WITHOUT_EXACT_INHERITANCE")
    sup=binding.get("supersedes")
    base_verify=binding.get("base_v1_verification")
    if not isinstance(sup,Mapping) or (sup.get("path"),sup.get("git_blob_sha"))!=(R3_V1_PATH,R3_V1_BLOB):
        return _fail("R3_V2_PREDECESSOR_REFERENCE_INVALID")
    if not isinstance(base_verify,Mapping) or (base_verify.get("path"),base_verify.get("git_blob_sha"))!=(R3_V1_VERIFY_PATH,R3_V1_VERIFY_BLOB):
        return _fail("R3_V2_BASE_VERIFICATION_REFERENCE_INVALID")
    if not isinstance(verification,Mapping):
        return _fail("R3_V2_CURRENT_VERIFICATION_REQUIRED")
    exact=verification.get("exact_blobs")
    if not isinstance(exact,Mapping):
        return _fail("R3_V2_CURRENT_VERIFICATION_EXACT_BLOBS_INVALID")
    if exact.get("base_v1_binding")!=R3_V1_BLOB or exact.get("base_v1_verification")!=R3_V1_VERIFY_BLOB:
        return _fail("R3_V2_CURRENT_VERIFICATION_INHERITANCE_MISMATCH")
    if verification.get("root_subject_binding_authority") is not True:
        return _fail("R3_V2_CURRENT_VERIFICATION_AUTHORITY_REQUIRED")

    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    v1=_read(root,R3_V1_PATH,R3_V1_BLOB)
    v1v=_read(root,R3_V1_VERIFY_PATH,R3_V1_VERIFY_BLOB)
    if v1 is None or v1v is None:return _fail("R3_V1_INHERITANCE_BYTES_INVALID")
    v1_ident=_identity(v1)
    if v1_ident!=ident:return _fail("R3_V1_V2_SUBJECT_IDENTITY_MISMATCH")
    if v1.get("global_subject_identity_authority") is not False:
        return _fail("R3_V1_GLOBAL_SUBJECT_NONAUTHORITY_NOT_PROVED")
    if v1.get("root_subject_binding_authority") is not False or v1.get("terminal_authority") is not False:
        return _fail("R3_V1_SELF_AUTHORITY_BOUNDARY_INVALID")
    if v1v.get("root_subject_binding_authority") is not True or v1v.get("terminal_authority") is not False:
        return _fail("R3_V1_INDEPENDENT_VERIFICATION_AUTHORITY_INVALID")
    if binding.get("binding_scope",{}).get("guarantees") is None or "ALL_V1_R3_STRUCTURAL_BINDING_GUARANTEES_PRESERVED" not in set(binding.get("binding_scope",{}).get("guarantees") or []):
        return _fail("R3_V2_V1_GUARANTEE_PRESERVATION_MISSING")

    return {
        "schema":SCHEMA,"pass":True,"binding_schema":schema,
        "subject_kind":ident[0],"subject_id":ident[1],"subject_sha256":ident[2],
        "global_subject_identity_authority":False,"terminal_authority":False,
        "root_subject_binding_authority":False,
        "legacy_v2_inheritance_used":True,
        "inheritance_basis":{
            "binding":{"path":R3_V1_PATH,"git_blob_sha":R3_V1_BLOB},
            "verification":{"path":R3_V1_VERIFY_PATH,"git_blob_sha":R3_V1_VERIFY_BLOB},
        },
    }
