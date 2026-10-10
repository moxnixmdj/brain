from __future__ import annotations
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_BINDING_COMPAT_V1"
V1="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
V2="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V2"
ALLOWED={V1,V2}

def normalize(binding:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(binding,Mapping):return {"pass":False,"reason":"BINDING_NOT_OBJECT"}
 schema=binding.get("schema")
 if schema not in ALLOWED:return {"pass":False,"reason":"BINDING_SCHEMA_UNSUPPORTED"}
 if binding.get("root_subject_binding_authority") is not False:return {"pass":False,"reason":"BINDING_SELF_ROOT_AUTHORITY_FORBIDDEN"}
 if binding.get("terminal_authority") is not False:return {"pass":False,"reason":"BINDING_TERMINAL_AUTHORITY_FORBIDDEN"}
 if schema==V1 and binding.get("global_subject_identity_authority") is not False:
  return {"pass":False,"reason":"V1_GLOBAL_SUBJECT_NONAUTHORITY_REQUIRED"}
 if schema==V2 and binding.get("global_subject_identity_authority") is True:
  return {"pass":False,"reason":"V2_GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN"}
 kind=binding.get("subject_kind");sid=binding.get("subject_id");sha=binding.get("subject_sha256")
 if not isinstance(kind,str) or not kind or not isinstance(sid,str) or not sid or not isinstance(sha,str) or len(sha)!=64:
  return {"pass":False,"reason":"SUBJECT_IDENTITY_INVALID"}
 return {"schema":SCHEMA,"pass":True,"binding_schema":schema,"subject_kind":kind,"subject_id":sid,"subject_sha256":sha,
 "global_subject_identity_authority":False,"terminal_authority":False,"root_subject_binding_authority":False,
 "legacy_v2_missing_global_field_normalized":schema==V2 and "global_subject_identity_authority" not in binding}
