from __future__ import annotations
from copy import deepcopy
import re
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_RECEIPT_COMPAT_V1"
VERSIONED=re.compile(r"^v[0-9]+_binding$")

def normalize(verification:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(verification,Mapping):return {"pass":False,"reason":"VERIFICATION_NOT_OBJECT"}
 out=deepcopy(dict(verification))
 replay=out.get("replay")
 replay_pass_normalized=False
 if isinstance(replay,dict) and replay.get("verifier_pass") is not True:
  if replay.get("package_execution")=="PASS" and str(replay.get("verifier_status") or "").startswith("PASS__"):
   replay["verifier_pass"]=True
   replay_pass_normalized=True
 exact=out.get("exact_blobs")
 if not isinstance(exact,dict):return {"pass":True,"verification":out,"alias_applied":False,"replay_pass_normalized":replay_pass_normalized}
 direct=exact.get("binding")
 aliases=[(k,v) for k,v in exact.items() if VERSIONED.match(str(k)) and isinstance(v,str)]
 if direct is not None:
  if not isinstance(direct,str):return {"pass":False,"reason":"DIRECT_BINDING_BLOB_INVALID"}
  conflicting=[k for k,v in aliases if v!=direct]
  if conflicting:return {"pass":False,"reason":"CONFLICTING_VERSIONED_BINDING_ALIAS","aliases":sorted(conflicting)}
  return {"pass":True,"verification":out,"alias_applied":False,"replay_pass_normalized":replay_pass_normalized}
 if len(aliases)>1:
  vals={v for _,v in aliases}
  if len(vals)>1:return {"pass":False,"reason":"AMBIGUOUS_VERSIONED_BINDING_ALIASES","aliases":sorted(k for k,_ in aliases)}
 if not aliases:return {"pass":True,"verification":out,"alias_applied":False,"replay_pass_normalized":replay_pass_normalized}
 k,v=aliases[-1]
 exact["binding"]=v
 return {"schema":SCHEMA,"pass":True,"verification":out,"alias_applied":True,"alias_key":k,"binding_git_blob_sha":v,"replay_pass_normalized":replay_pass_normalized}
