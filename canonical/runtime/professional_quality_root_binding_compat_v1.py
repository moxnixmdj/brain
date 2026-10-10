from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_BINDING_COMPAT_V1"
V1="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
V2="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V2"
ALLOWED={V1,V2}
R3_ROOT="R3_REALIZATION_OBSERVATION"
R3_V1_PATH="canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V1.json"
R3_V1_BLOB="c49c120a61620d400e372884266b63ec34a054d2"
R3_V1_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1.json"
R3_V1_VERIFY_BLOB="92cacbd5f7b37cb515db9ebbc3685c961fc9e34e"
R3_V2_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2.json"
R3_V2_VERIFY_BLOB="870bb85fbd00d670ec36e86b4b0b510f5bb9225c"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def _read(root:Path,path:str,sha:str):
 p=(root/path).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None
 if not p.is_file() or p.is_symlink() or _blob(p)!=sha:return None
 try:o=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None
 return o if isinstance(o,dict) else None
def _identity(b:Mapping[str,Any]):
 kind=b.get("subject_kind");sid=b.get("subject_id");sha=b.get("subject_sha256")
 if not isinstance(kind,str) or not kind or not isinstance(sid,str) or not sid:return None
 if not isinstance(sha,str) or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):return None
 return kind,sid,sha
def normalize(binding:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(binding,Mapping):return {"pass":False,"reason":"BINDING_NOT_OBJECT"}
 schema=binding.get("schema")
 if schema not in ALLOWED:return {"pass":False,"reason":"BINDING_SCHEMA_UNSUPPORTED"}
 if binding.get("root_subject_binding_authority") is not False:return {"pass":False,"reason":"BINDING_SELF_ROOT_AUTHORITY_FORBIDDEN"}
 if binding.get("terminal_authority") is not False:return {"pass":False,"reason":"BINDING_TERMINAL_AUTHORITY_FORBIDDEN"}
 ident=_identity(binding)
 if ident is None:return {"pass":False,"reason":"SUBJECT_IDENTITY_INVALID"}
 if schema==V1:
  if binding.get("global_subject_identity_authority") is not False:return {"pass":False,"reason":"V1_GLOBAL_SUBJECT_NONAUTHORITY_REQUIRED"}
  return {"schema":SCHEMA,"pass":True,"binding_schema":schema,"subject_kind":ident[0],"subject_id":ident[1],"subject_sha256":ident[2],"global_subject_identity_authority":False,"terminal_authority":False,"root_subject_binding_authority":False,"legacy_v2_missing_global_field_normalized":False}
 if binding.get("global_subject_identity_authority") is True:return {"pass":False,"reason":"V2_GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN"}
 if binding.get("global_subject_identity_authority") is False:
  return {"schema":SCHEMA,"pass":True,"binding_schema":schema,"subject_kind":ident[0],"subject_id":ident[1],"subject_sha256":ident[2],"global_subject_identity_authority":False,"terminal_authority":False,"root_subject_binding_authority":False,"legacy_v2_missing_global_field_normalized":False}
 # Missing V2 field is admitted only for the exact R3 V2 strengthening whose
 # independently verified V1 predecessor proves explicit non-authority.
 if binding.get("root_id")!=R3_ROOT:return {"pass":False,"reason":"V2_MISSING_GLOBAL_FIELD_WITHOUT_EXACT_INHERITANCE"}
 sup=binding.get("supersedes");base=binding.get("base_v1_verification")
 if not isinstance(sup,Mapping) or (sup.get("path"),sup.get("git_blob_sha"))!=(R3_V1_PATH,R3_V1_BLOB):return {"pass":False,"reason":"R3_V2_PREDECESSOR_REFERENCE_INVALID"}
 if not isinstance(base,Mapping) or (base.get("path"),base.get("git_blob_sha"))!=(R3_V1_VERIFY_PATH,R3_V1_VERIFY_BLOB):return {"pass":False,"reason":"R3_V2_BASE_VERIFICATION_REFERENCE_INVALID"}
 if "ALL_V1_R3_STRUCTURAL_BINDING_GUARANTEES_PRESERVED" not in set((binding.get("binding_scope") or {}).get("guarantees") or []):return {"pass":False,"reason":"R3_V2_V1_GUARANTEE_PRESERVATION_MISSING"}
 root=Path(__file__).resolve().parents[2]
 v1=_read(root,R3_V1_PATH,R3_V1_BLOB);v1v=_read(root,R3_V1_VERIFY_PATH,R3_V1_VERIFY_BLOB);v2v=_read(root,R3_V2_VERIFY_PATH,R3_V2_VERIFY_BLOB)
 if v1 is None or v1v is None or v2v is None:return {"pass":False,"reason":"R3_INHERITANCE_BYTES_INVALID"}
 if _identity(v1)!=ident:return {"pass":False,"reason":"R3_V1_V2_SUBJECT_IDENTITY_MISMATCH"}
 if v1.get("global_subject_identity_authority") is not False or v1.get("root_subject_binding_authority") is not False or v1.get("terminal_authority") is not False:return {"pass":False,"reason":"R3_V1_NONAUTHORITY_BOUNDARY_INVALID"}
 if v1v.get("root_subject_binding_authority") is not True or v1v.get("terminal_authority") is not False:return {"pass":False,"reason":"R3_V1_INDEPENDENT_VERIFICATION_INVALID"}
 exact=v2v.get("exact_blobs") or {}
 if exact.get("base_v1_binding")!=R3_V1_BLOB or exact.get("base_v1_verification")!=R3_V1_VERIFY_BLOB or exact.get("v2_binding")!="2fe91ecba3830641ed800d04b70279a3f84283bf":return {"pass":False,"reason":"R3_V2_VERIFIED_INHERITANCE_MISMATCH"}
 if v2v.get("root_subject_binding_authority") is not True or v2v.get("terminal_authority") is not False:return {"pass":False,"reason":"R3_V2_INDEPENDENT_VERIFICATION_INVALID"}
 return {"schema":SCHEMA,"pass":True,"binding_schema":schema,"subject_kind":ident[0],"subject_id":ident[1],"subject_sha256":ident[2],"global_subject_identity_authority":False,"terminal_authority":False,"root_subject_binding_authority":False,"legacy_v2_missing_global_field_normalized":True,"inheritance_proved":True}
